"""Standalone publication-style figures from recorded outcomes, never forecasts."""

import argparse, hashlib, json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    root = args.input
    science = json.loads((root / "science.json").read_text())
    follow = json.loads((root / "followup.json").read_text())
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    cases = [
        "strong_signal",
        "weak_signal",
        "ambiguous",
        "high_noise",
        "two_sources",
        "off_grid",
        "direction_bias",
        "speed_bias",
        "clustered",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout="constrained")
    for y, case in enumerate(cases):
        rows = [r for r in science if r["case"] == case and "localization_error_m" in r]
        unique = [r for r in rows if r.get("map_unique", True)]
        if unique:
            errors = [r["localization_error_m"] for r in unique]
            q = np.quantile(errors, [0.25, 0.5, 0.75])
            axes[0].errorbar(
                q[1],
                y,
                xerr=[[q[1] - q[0]], [q[2] - q[1]]],
                fmt="o",
                color="#297e88",
                capsize=4,
            )
        else:
            axes[0].text(10, y, "Unresolved tied maxima", va="center", color="#a46b20")
        covered = [r for r in rows if r["truth_in_90"] is not None]
        if covered:
            n = len(covered)
            count = sum(r["truth_in_90"] for r in covered)
            prop = count / n
            z = 1.96
            d = 1 + z * z / n
            center = (prop + z * z / (2 * n)) / d
            radius = z * np.sqrt(prop * (1 - prop) / n + z * z / (4 * n * n)) / d
            axes[1].errorbar(
                prop,
                y,
                xerr=[
                    [prop - max(0, center - radius)],
                    [min(1, center + radius) - prop],
                ],
                fmt="o",
                color="#c3782e" if prop < 0.9 else "#297e88",
                capsize=4,
            )
            axes[1].text(
                1.04,
                y,
                f"{np.median([r['grid_points_90'] for r in rows]):.0f}/9 points",
                va="center",
                fontsize=9,
            )
        else:
            axes[1].text(
                0.05, y, "N/A: truth outside grid", va="center", color="#7c6c59"
            )
    axes[0].set_yticks(range(len(cases)), [c.replace("_", " ") for c in cases])
    axes[1].set_yticks(range(len(cases)), [])
    axes[0].set_xlabel("MAP location error, metres · median and IQR")
    axes[0].set_xlim(-8, 260)
    axes[1].set_xlabel(
        "True grid location in conditional 90% set · Wilson 95% interval"
    )
    axes[1].set_xlim(-0.04, 1.35)
    axes[1].set_xticks([0, 0.25, 0.5, 0.75, 1])
    axes[1].axvline(0.9, color="#888", ls="--", lw=1, label="Nominal 90%")
    axes[1].legend(loc="upper left", fontsize=8)
    for ax in axes:
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.15)
    fig.suptitle(
        "Synthetic source stress: strong matched cases succeed; wrong weather breaks coverage",
        fontsize=13,
    )
    fig.supxlabel(
        "40 seeds per condition · 9 discrete source locations · broad sets are not precise localization · no field validation",
        fontsize=9,
    )
    fig.savefig(root / "source-stress.svg")
    fig.savefig(root / "source-stress.png", dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    colors = ["#3a8a80", "#7c93a5", "#d0a365", "#a3b77c"]
    for ax, (case, regime) in zip(
        axes.flat,
        [
            (a, b)
            for a in ["strong_signal", "weak_signal"]
            for b in ["matched", "mismatched"]
        ],
    ):
        rows = [
            r
            for r in follow
            if r.get("case") == case
            and r.get("error_model") == regime
            and r["status"] == "ok"
        ]
        values = []
        for prefix in ["Optimized", "Spatial", "Wind", "Random"]:
            points = []
            for seed in sorted({r["seed"] for r in rows}):
                selected = [
                    r["entropy_reduction"]
                    for r in rows
                    if r["seed"] == seed and r["method"].startswith(prefix)
                ]
                points.append(float(np.mean(selected)))
            values.append(points)
        boxes = ax.boxplot(
            values,
            tick_labels=["Optimized", "Spread", "Wind", "Random"],
            patch_artist=True,
            widths=0.5,
            showmeans=True,
            meanprops={
                "marker": "D",
                "markerfacecolor": "white",
                "markeredgecolor": "#222",
                "markersize": 4,
            },
            medianprops={"color": "#222"},
        )
        for box, color in zip(boxes["boxes"], colors):
            box.set_facecolor(color)
            box.set_alpha(0.65)
        ax.axhline(0, color="#888", lw=1, ls="--")
        ax.grid(axis="y", alpha=0.15)
        ax.set_title(case.replace("_", " ") + " · " + regime + " errors")
        ax.set_ylabel("Realized entropy reduction, nats")
    fig.suptitle(
        "Follow-up outcomes: information scores do not guarantee realized improvement",
        fontsize=13,
    )
    fig.supxlabel(
        "40 paired seeds per panel · random is mean of 20 plans within seed · negative outcomes retained · synthetic only",
        fontsize=9,
    )
    fig.savefig(root / "followup-stress.svg")
    fig.savefig(root / "followup-stress.png", dpi=170)
    plt.close(fig)
    metadata = {
        "matplotlib": matplotlib.__version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": {
            n: hashlib.sha256((root / n).read_bytes()).hexdigest()
            for n in ["science.json", "followup.json"]
        },
        "outputs": [
            "source-stress.svg",
            "source-stress.png",
            "followup-stress.svg",
            "followup-stress.png",
        ],
    }
    (root / "figures.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Saved source and follow-up figures from recorded data.")


if __name__ == "__main__":
    main()
