# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib==3.10.8"]
# ///
"""Rebuild with: uv run scripts/plot-halogen-qwen38.py.

Uses only the public measurement summary. Does not load a model.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "public/data/halogen-qwen38-coding-2026-09-28.json").read_text()
)
BG, INK, BLUE, ORANGE = "#eff1f5", "#4c4f69", "#1e66f5", "#b45309"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.edgecolor": "#9ca0b0",
    "svg.fonttype": "path",
    "svg.hashsalt": "halogen-qwen38-2026-09-28",
})


def canvas(title, subtitle):
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#bcc0cc", alpha=0.6, linewidth=0.7, zorder=0)
    ax.tick_params(axis="y", length=0, pad=10)
    fig.text(0.05, 0.94, title, fontsize=20, fontweight="bold")
    fig.text(0.05, 0.89, subtitle, fontsize=11.5)
    fig.subplots_adjust(left=0.21, right=0.95, top=0.73, bottom=0.23)
    return fig, ax


def save(fig, name):
    path = ROOT / "public/images" / name
    fig.savefig(path, metadata={"Date": None, "Creator": "Matplotlib"})
    path.write_text("\n".join(s.rstrip() for s in path.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(path)


fig, ax = canvas(
    "64K coding: the cache changed the wait",
    "Qwen3.8-27B · Halogen 0.1.4 · MTP · Greedy generation, thinking off",
)
for i, row in enumerate(DATA["greedy_cache_experiment"]["runs"]):
    prefill, total = row["prefill_seconds"], row["total_request_seconds"]
    ax.barh(i, prefill, height=0.48, color=BLUE, zorder=3,
            label="Prefill" if i == 0 else None)
    ax.barh(i, total - prefill, left=prefill, height=0.48,
            color="#6c6f85", zorder=3,
            label="Generation + request overhead" if i == 0 else None)
    ax.text(total + 2.5, i, f"{total:.2f} s", va="center", fontweight="bold")
ax.set_yticks(range(3), ["Cold repair", "Identical repeat", "Follow-up"])
ax.set_ylim(2.6, -0.6)
ax.set_xlim(0, 190)
ax.set_xlabel("Total request time, seconds", labelpad=10)
ax.legend(loc="lower left", bbox_to_anchor=(-0.02, 1.04), ncol=2,
          frameon=False, fontsize=10.5)
fig.text(0.05, 0.06,
         "64,468 input tokens; follow-up: 64,675. Warm requests reused 63,488 tokens.\n"
         "170 / 170 / 190 output tokens. One sequential synthetic conversation.\n"
         "These are not timings for the later sampled medium-reasoning preset.",
         fontsize=10.5, linespacing=1.5)
save(fig, "strix-halo-halogen-27b-cache.svg")

fig, ax = canvas(
    "Prefill precision: all four long-context runs",
    "57,281 input tokens · Sampled medium reasoning · MTP · Prompt cache off",
)
deep = [r for r in DATA["precision_experiment"]["runs"] if r["task"] == "repo"]
for i, row in enumerate(deep):
    value = row["prefill_seconds"]
    ax.barh(i, value, height=0.5, color=BLUE if row["w4a4"] else ORANGE, zorder=3)
    ax.text(value + 4, i, f"{value:.2f} s", va="center", fontweight="bold")
ax.set_yticks(range(4), [
    f"{r['leg']}: {'enabled' if r['w4a4'] else 'disabled'}\nseed {r['seed']}" for r in deep
])
ax.set_ylim(3.6, -0.6)
ax.set_xlim(0, 300)
ax.set_xlabel("Cold prefill time, seconds", labelpad=10)
fig.text(0.05, 0.79, "Execution order, top to bottom: A1 → B1 → B2 → A2", fontsize=11)
fig.text(0.05, 0.055,
         "Fresh load per leg. W4A4 enabled = 64; disabled = 0. Checkpoint unchanged.\n"
         "Both settings passed 6/6 answers across three tasks and two seeds.\n"
         "Two deep measurements per setting; substantial run drift, not confidence intervals.",
         fontsize=10.5, linespacing=1.5)
save(fig, "strix-halo-halogen-27b-precision.svg")
