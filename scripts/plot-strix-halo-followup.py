"""Rebuild the follow-up figure: python scripts/plot-strix-halo-followup.py.

Requires matplotlib. Reads the published measurement JSON; no model runs needed.
"""

import json
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "public/data/strix-halo-perf-2026-09-19.json").read_text())
runs = {run["run_id"]: run for run in data["runs"]}


def points(run_ids, metric):
    grouped = {}
    for run_id in run_ids:
        for point in runs[run_id]["points"]:
            depth = point["actual_context_tokens"]
            if depth <= 74385:
                grouped.setdefault(depth, []).append(point[metric])
    xs = sorted(grouped)
    ys = [mean(grouped[x]) for x in xs]
    lower = [y - min(grouped[x]) for x, y in zip(xs, ys)]
    upper = [max(grouped[x]) - y for x, y in zip(xs, ys)]
    return xs, ys, [lower, upper]


plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 14,
    "text.color": "#4c4f69",
    "axes.labelcolor": "#4c4f69",
    "xtick.color": "#4c4f69",
    "ytick.color": "#4c4f69",
    "axes.edgecolor": "#9ca0b0",
    "svg.fonttype": "none",
    "svg.hashsalt": "strix-halo-followup-2026-09-19",
})
fig, axes = plt.subplots(2, 1, figsize=(8, 8.8), sharex=True)
fig.patch.set_facecolor("#eff1f5")
series = [
    ("30B · f16", ["B0a", "B0b"], "#6c6f85", "s", "--"),
    ("30B · q8_0", ["B1", "B1-midpoints"], "#1e66f5", "o", "-"),
    ("Next · f16", ["C0a-measured", "C0b", "C0-midpoints"], "#8839ef", "D", "-"),
]
for ax, metric, title, ceiling, tick in zip(
    axes,
    ["prefill_tps", "decode_tps"],
    ["Prompt processing", "Token generation"],
    [1000, 70],
    [200, 10],
):
    ax.set_facecolor("#eff1f5")
    ax.axvspan(20000, 30000, color="#ccd0da", alpha=0.65, zorder=0)
    for label, run_ids, color, marker, linestyle in series:
        xs, ys, errors = points(run_ids, metric)
        ax.errorbar(xs, ys, yerr=errors, color=color, marker=marker,
                    linestyle=linestyle, linewidth=2.2, markersize=6,
                    capsize=4, elinewidth=1.4, label=label)
    ax.set_title(title, loc="left", fontsize=19, fontweight="bold", pad=12)
    ax.set_ylabel("Tokens / second")
    ax.set_ylim(0, ceiling)
    ax.set_xlim(0, 78000)
    ax.yaxis.set_major_locator(MultipleLocator(tick))
    ax.grid(axis="y", color="#bcc0cc", alpha=0.6, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(frameon=False, fontsize=12, ncol=3, loc="upper right",
               columnspacing=1, handlelength=1.5)
axes[1].set_xlabel("Actual prompt tokens", labelpad=10)
axes[1].xaxis.set_major_locator(MultipleLocator(20000))
axes[1].xaxis.set_major_formatter(FuncFormatter(lambda x, _: "0" if x == 0 else f"{x / 1000:.0f}K"))
fig.subplots_adjust(left=0.14, right=0.97, bottom=0.19, top=0.95, hspace=0.36)
fig.text(0.14, 0.035, "Shaded band: 20–30K transition · Whiskers: baseline range\n"
         "September 19, 2026 · Vulkan · Sequential requests", fontsize=11, linespacing=1.5)
out = ROOT / "public/images/strix-halo-follow-up-throughput.svg"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, metadata={"Date": None, "Creator": "Matplotlib"})
out.write_text("\n".join(line.rstrip() for line in out.read_text().splitlines()) + "\n")
plt.close(fig)
print(out)
