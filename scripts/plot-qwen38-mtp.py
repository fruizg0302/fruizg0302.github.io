# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib==3.10.8"]
# ///
"""Rebuild with: uv run scripts/plot-qwen38-mtp.py.

Reads the public measurement JSON. No model runs or private logs needed.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public/data/qwen38-27b-perf-2026-09-21.json"
runs = {run["run_id"]: run for run in json.loads(DATA.read_text())["runs"]}


def rate(run_id, depth):
    return next(
        p["decode_tps"] for p in runs[run_id]["points"]
        if p["prompt_tokens"] == depth
    )


plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 14,
    "text.color": "#4c4f69",
    "axes.labelcolor": "#4c4f69",
    "xtick.color": "#4c4f69",
    "ytick.color": "#4c4f69",
    "axes.edgecolor": "#9ca0b0",
    "svg.fonttype": "path",
    "svg.hashsalt": "qwen38-mtp-2026-09-21",
})
fig, ax = plt.subplots(figsize=(9, 7.8))
background = "#eff1f5"
fig.patch.set_facecolor(background)
ax.set_facecolor(background)
depths = [1316, 10173, 40847, 246678]
for row, depth in enumerate(depths):
    if row < 3:
        samples = (
            [rate("baseline-b", depth), rate("baseline-c", depth)]
            if row < 2 else [rate("baseline-deep", depth)]
        )
        value = max(samples)
        ax.barh(row - 0.17, value, height=0.28, color="#6c6f85",
                label="MTP off" if row == 0 else None, zorder=3)
        if len(samples) > 1:
            ax.errorbar(value, row - 0.17,
                        xerr=[[value - min(samples)], [0]], fmt="none",
                        color="#1e2030", capsize=4, zorder=4)
        ax.text(value + 0.35, row - 0.17, f"{value:.2f}", va="center",
                fontsize=12)
    else:
        ax.text(0.2, row - 0.17, "MTP off: untested", va="center",
                fontsize=12, color="#6c6f85", style="italic")

    selected_run = "mtp-2-native" if row == 3 else "mtp-2-confirm"
    value = rate(selected_run, depth)
    ax.barh(row + 0.17, value, height=0.28, color="#1e66f5",
            label="MTP 2" if row == 0 else None, zorder=3)
    if row < 2:
        first = rate("mtp-2", depth)
        ax.errorbar(value, row + 0.17,
                    xerr=[[value - min(first, value)], [max(first, value) - value]],
                    fmt="none", color="#1e2030", capsize=4, zorder=4)
    ax.text(value + 0.35, row + 0.17, f"{value:.2f}", va="center",
            fontsize=12, fontweight="bold")

ax.set_yticks(range(len(depths)), [f"{depth:,}" for depth in depths])
ax.set_ylim(3.55, -0.55)
ax.set_xlim(0, 27)
ax.set_ylabel("Actual prompt tokens", labelpad=12)
ax.set_xlabel("Generated tokens / second", labelpad=12)
ax.xaxis.set_major_locator(MultipleLocator(5))
ax.grid(axis="x", color="#bcc0cc", alpha=0.6, linewidth=0.7, zorder=0)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0, pad=10)
ax.axhline(2.5, color="#9ca0b0", linewidth=0.8, linestyle="--")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2,
          frameon=False, fontsize=13, borderaxespad=0)
fig.text(0.06, 0.95, "Qwen3.8-27B: generation with MTP", fontsize=21,
         fontweight="bold")
fig.text(0.06, 0.91, "UD-Q5_K_S · Q8_0 main + draft caches · Vulkan 2.42.0",
         fontsize=12)
fig.subplots_adjust(left=0.22, right=0.97, top=0.80, bottom=0.25)
fig.text(0.06, 0.065,
         "Short depths: faster baseline, MTP 2 confirmation; whiskers show repeat ranges.\n"
         "Deeper points: single measurements. 246,678-token prefill took 46.5 minutes.\n"
         "September 21, 2026 · Fresh loads · Greedy sampling · Thinking off",
         fontsize=10.5, linespacing=1.6)
out = ROOT / "public/images/strix-halo-qwen38-mtp.svg"
fig.savefig(out, metadata={"Date": None, "Creator": "Matplotlib"})
out.write_text("\n".join(line.rstrip() for line in out.read_text().splitlines()) + "\n")
plt.close(fig)
print(out)
