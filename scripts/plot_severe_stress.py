"""Standalone stress tradeoffs; refuses overwriting existing figures."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/severe-stress"
source = BASE / "summary.json"
summary = json.loads(source.read_text())
rows = [
    {"family": "nominal confirmation (480)", **summary["nominal_confirmation"]}
] + summary["main"]["conditions"]
folder = BASE / "figures"
folder.mkdir(exist_ok=False)
fig, axes = plt.subplots(1, 4, figsize=(18, 11), sharey=True, layout="constrained")
y = np.arange(len(rows))
labels = [row["family"].replace("_", " ") for row in rows]
for index, row in enumerate(rows):
    point = row["map_error_m"]
    if point:
        axes[0].plot(
            [point["median"], point["p90"]],
            [index, index],
            color="#0f766e",
            linewidth=2,
        )
        axes[0].scatter(point["median"], index, color="#0f766e", s=18)
    area = row["region_area_fraction"]
    if area:
        axes[1].barh(index, 100 * area["mean"], color="#0f766e", height=0.6)
    coverage = row["conditional_region_coverage"]
    if coverage["n"]:
        value = coverage["count"] / coverage["n"]
        axes[2].barh(index, 100 * value, color="#0f766e", height=0.6)
        axes[2].errorbar(
            100 * value,
            index,
            xerr=[
                [max(0.0, 100 * (value - coverage["wilson95"][0]))],
                [max(0.0, 100 * (coverage["wilson95"][1] - value))],
            ],
            fmt="none",
            ecolor="#172033",
            capsize=2,
            linewidth=0.8,
        )
    for offset, key, color, label in [
        (-0.17, "acceptance", "#64748b", "Accepted / generated"),
        (
            0.17,
            "accepted_wrong_per_generated",
            "#dc2626",
            "Accepted geographic error / generated",
        ),
    ]:
        rate = row[key]
        value = rate["count"] / rate["n"]
        axes[3].barh(
            index + offset,
            100 * value,
            height=0.3,
            color=color,
            label=label if index == 0 else None,
        )
axes[0].set_yticks(y, labels, fontsize=9)
axes[0].invert_yaxis()
axes[0].set_title("MAP median → p90 error")
axes[0].set_xlabel("Metres (distribution, not CI)")
axes[0].axvline(50, color="#64748b", linestyle=":", linewidth=1)
axes[1].set_title("Mean conditional90% region area")
axes[1].set_xlabel("% supported domain")
axes[2].set_title("Conditional region coverage")
axes[2].set_xlabel("% fitted positive-source worlds; Wilson95%")
axes[2].axvline(90, color="#64748b", linestyle=":", linewidth=1)
axes[3].set_title("Usefulness and geographic errors")
axes[3].set_xlabel("% all generated worlds")
handles, legend_labels = axes[3].get_legend_handles_labels()
fig.legend(handles, legend_labels, loc="outside lower center", ncols=2, fontsize=9)
for ax in axes:
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
for ax in axes[1:]:
    ax.set_xlim(0, 105)
fig.suptitle(
    "UPWIND frozen-model severe stress: precision, uncertainty and errors together\n1,440 synthetic inference attempts; blanks mean no fit/source truth; no measured-field claim",
    fontsize=14,
)
manifest = {
    "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "artifacts": {},
}
for extension in ["png", "svg", "pdf"]:
    output = folder / ("stress-tradeoffs." + extension)
    fig.savefig(output, dpi=180)
    manifest["artifacts"][str(output.relative_to(ROOT))] = hashlib.sha256(
        output.read_bytes()
    ).hexdigest()
(BASE / "figure-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
