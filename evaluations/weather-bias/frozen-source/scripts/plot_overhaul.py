"""Export reproducible figures from recorded overhaul results; never run inference."""

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


NEW = "mixture-0.3.0"
OLD = "legacy-0.2.1"
COLORS = {"new": "#176c75", "legacy": "#b16d32", "spread": "#687c3c", "wind": "#836692"}
METHODS = {
    "new": "Redesigned",
    "legacy": "Old planner",
    "spread": "Spread",
    "wind": "Wind",
}
FAMILIES = (
    "weak_signal",
    "strong_signal",
    "direction_bias",
    "two_sources",
    "boundary",
    "correlated_errors",
    "episodic",
    "missingness",
)
OUTPUTS = (
    "source-overhaul.svg",
    "source-overhaul.png",
    "planner-overhaul.svg",
    "planner-overhaul.png",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wilson(count, n):
    if not n:
        return None
    z = 1.959963984540054
    p = count / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def distribution(values):
    a = np.asarray(values, dtype=float)
    if not len(a) or not np.all(np.isfinite(a)):
        raise ValueError(
            "Every plotted distribution needs finite recorded observations."
        )
    q = np.quantile(a, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])
    return dict(
        zip(("min", "p10", "p25", "median", "p75", "p90", "max"), map(float, q))
    ) | {"n": len(a), "mean": float(a.mean())}


def draw_distribution(ax, values, position, color, marker="o"):
    d = distribution(values)
    ax.plot([d["p10"], d["p90"]], [position, position], color=color, lw=1.2)
    ax.plot(
        [d["p25"], d["p75"]],
        [position, position],
        color=color,
        lw=5,
        solid_capstyle="butt",
    )
    ax.plot(
        d["median"],
        position,
        marker=marker,
        color=color,
        markeredgecolor="white",
        ms=6,
        zorder=4,
    )
    # Each light dot is one world. Fixed offsets are solely a display aid.
    offsets = np.sin(np.arange(len(values)) * 2.399963229728653) * 0.055
    ax.scatter(values, position + offsets, color=color, alpha=0.3, s=9, zorder=2)
    return d


def save(fig, out, stem):
    fig.savefig(out / (stem + ".svg"), metadata={"Date": None})
    fig.savefig(out / (stem + ".png"), dpi=170)
    plt.close(fig)


def source_figure(science, summary, out, label):
    fig, axes = plt.subplots(
        1, 2, figsize=(15.5, 8.4), layout="constrained", width_ratios=[1.1, 1]
    )
    coverage_ax, error_ax = axes
    plotted = {"regions": [], "localization": []}
    families = [
        family for family in FAMILIES if any(r["family"] == family for r in science)
    ]
    for y, family in enumerate(families):
        all_new = [r for r in science if r["model"] == NEW and r["family"] == family]
        rows = [
            r
            for r in all_new
            if r["status"] == "retained" and r.get("region90_truth_covered") is not None
        ]
        if rows:
            n = len(rows)
            count = sum(bool(r["region90_truth_covered"]) for r in rows)
            rate = count / n
            low, high = wilson(count, n)
            area = float(np.median([r["region90_area_m2"] for r in rows]))
            fraction = float(np.median([r["region90_area_fraction"] for r in rows]))
            coverage_ax.errorbar(
                rate,
                y,
                xerr=[[max(0, rate - low)], [max(0, high - rate)]],
                fmt="o",
                capsize=4,
                color=COLORS["new"],
                ms=6,
            )
            coverage_ax.text(
                1.08,
                y,
                f"{count}/{n}    {area / 1e6:.3f} / {100 * fraction:.0f}%",
                va="center",
                fontsize=10,
            )
            plotted["regions"].append(
                {
                    "family": family,
                    "covered": count,
                    "n": n,
                    "fraction": rate,
                    "wilson95": [low, high],
                    "median_area_m2": area,
                    "median_domain_fraction": fraction,
                    "all_new_worlds": len(all_new),
                }
            )
        else:
            coverage_ax.text(
                0.03, y, "No retained source-region result", va="center", fontsize=9
            )
        for model, offset, color, marker in (
            (OLD, -0.13, COLORS["legacy"], "s"),
            (NEW, 0.13, COLORS["new"], "o"),
        ):
            rows = [
                r
                for r in science
                if r["family"] == family
                and r["model"] == model
                and r["status"] == "retained"
                and r.get("source_present")
            ]
            values = [r["localization_error_m"] for r in rows]
            if values:
                plotted["localization"].append(
                    {
                        "family": family,
                        "model": model,
                        "metric": "conditional_MAP_center_error_m",
                        **draw_distribution(
                            error_ax, values, y + offset, color, marker
                        ),
                    }
                )
    coverage_ax.axvline(0.9, color="#777", ls="--", lw=1)
    coverage_ax.text(
        1.08,
        -0.7,
        "Covered    median km² / domain",
        fontsize=9,
        weight="bold",
        va="center",
    )
    coverage_ax.set_xlim(-0.035, 1.84)
    coverage_ax.set_xticks(
        [0, 0.25, 0.5, 0.75, 0.9, 1], ["0", "25", "50", "75", "90", "100"]
    )
    coverage_ax.set_xlabel(
        "Continuous source in conditional 90% region (%)\nWilson 95% intervals; dashed line is nominal mass"
    )
    coverage_ax.set_title(
        "A. Region coverage has a geographic cost",
        loc="left",
        fontweight="bold",
        pad=28,
    )
    error_ax.set_title(
        "B. Conditional localization distributions",
        loc="left",
        fontweight="bold",
        pad=28,
    )
    error_ax.set_xlabel(
        "Distance from MAP center to continuous primary source (m)\nDots: worlds · thick: IQR · thin: 10th–90th percentiles"
    )
    error_ax.set_xlim(left=0)
    error_ax.legend(
        handles=[
            Line2D(
                [],
                [],
                color=COLORS["legacy"],
                marker="s",
                label="Old discrete-grid MAP",
            ),
            Line2D(
                [], [], color=COLORS["new"], marker="o", label="New refined-cell MAP"
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        fontsize=9,
        ncols=2,
        frameon=False,
    )
    for ax in axes:
        ax.set_yticks(
            range(len(families)),
            [f.replace("_", " ") for f in families] if ax is coverage_ax else [],
        )
        ax.set_ylim(len(families) - 0.5, -1)
        ax.grid(axis="x", alpha=0.14)
    rejected = [
        (
            g["model"],
            g["total"] - sum(v for k, v in g["statuses"].items() if k == "retained"),
            g["total"],
        )
        for g in summary["by_condition"]
        if g["family"] == "unsupported_weather"
    ]
    rejection_note = "; ".join(
        f"{'new' if model == NEW else 'old'} {n}/{total} weather cases refused"
        for model, n, total in rejected
    )
    fig.suptitle(
        f"{label} · Source inference on an independent synthetic transport challenge",
        fontsize=15,
        fontweight="bold",
    )
    all_new = [r for r in science if r["model"] == NEW]
    population = f"{len(all_new)} condition-worlds / {len({r['seed'] for r in all_new})} seed blocks"
    fig.supxlabel(
        "Regions condition on a single source; two-source coverage is descriptive. Old point sets have no geographic coverage/area.\nMAP grid resolutions differ. "
        + population
        + "; "
        + rejection_note
        + ". No field validation.",
        fontsize=9,
    )
    save(fig, out, "source-overhaul")
    return plotted


def paired_planner(followup, summary):
    records = []
    for group in summary["planner"]:
        family, method = group["family"], group["method"]
        selected = [
            r
            for r in followup
            if r["family"] == family
            and r["method"] == method
            and r["status"] == "retained"
        ]
        differences = []
        for row in selected:
            random = [
                r
                for r in followup
                if r["family"] == family
                and r["seed"] == row["seed"]
                and r["status"] == "retained"
                and r["method"].startswith("random-")
            ]
            if len(random) != 20:
                raise ValueError(
                    f"Expected all 20 random methods for {family}, seed {row['seed']}; got {len(random)}."
                )
            differences.append(
                float(np.mean([r["prediction"]["rmse_ug_m3"] for r in random]))
                - row["prediction"]["rmse_ug_m3"]
            )
        if not differences:
            continue
        worse = sum(d < 0 for d in differences)
        if (
            worse != group["worse_rmse_than_random20"]["count"]
            or len(differences) != group["n"]
            or not np.isclose(
                np.mean(differences),
                group["rmse_advantage_vs_random20"]["mean"],
                rtol=1e-10,
                atol=1e-10,
            )
        ):
            raise ValueError(
                "Raw paired planner outcomes disagree with the saved summary."
            )
        records.append(
            {
                "family": family,
                "method": method,
                "differences": differences,
                "worse": worse,
                "n": len(differences),
                "wilson95_worse": wilson(worse, len(differences)),
                "mean_cost": float(np.mean([r["cost"] for r in selected])),
            }
        )
    return records


def planner_figure(science, followup, summary, out, label):
    fig, axes = plt.subplots(
        1, 2, figsize=(16.5, 8.8), layout="constrained", width_ratios=[1.65, 1]
    )
    plan_ax, reliability_ax = axes
    paired = paired_planner(followup, summary)
    order = {
        family: i
        for i, family in enumerate(("weak_signal", "strong_signal", "direction_bias"))
    }
    paired.sort(
        key=lambda r: (order.get(r["family"], 9), list(METHODS).index(r["method"]))
    )
    plotted = {"planner": [], "reliability": []}
    labels = []
    for y, group in enumerate(paired):
        d = draw_distribution(plan_ax, group["differences"], y, COLORS[group["method"]])
        labels.append(
            f"{group['family'].replace('_', ' ')} / {METHODS[group['method']]}   {group['worse']}/{group['n']} worse"
        )
        plotted["planner"].append(
            {k: v for k, v in group.items() if k != "differences"}
            | {"rmse_advantage_distribution": d}
        )
    plan_ax.set_yticks(range(len(labels)), labels, fontsize=9)
    plan_ax.set_ylim(len(labels) - 0.5, -0.8)
    plan_ax.axvline(0, color="#777", lw=1, ls="--")
    for y in (3.5, 7.5):
        if y < len(labels) - 0.5:
            plan_ax.axhline(y, color="#ddd", lw=0.8)
    plan_ax.set_xlabel(
        "Mean random target RMSE − method target RMSE (µg/m³)\nPositive favors method; negative favors random · dots: paired worlds"
    )
    plan_ax.set_title(
        "C. Realized benefit can be worse than random",
        loc="left",
        fontweight="bold",
        pad=20,
    )
    plan_ax.grid(axis="x", alpha=0.14)
    rows = [
        r
        for r in science
        if r["model"] == NEW
        and r["status"] == "retained"
        and r.get("source_probability") is not None
    ]
    for i, b in enumerate(summary["source_reliability_bins"]):
        selected = [
            r
            for r in rows
            if b["lower"] <= r["source_probability"]
            and (r["source_probability"] < b["upper"] or i == 4)
        ]
        if len(selected) != b["n"]:
            raise ValueError(
                "Reliability-bin counts disagree with recorded science outcomes."
            )
        if not selected:
            plotted["reliability"].append(
                {"lower": b["lower"], "upper": b["upper"], "n": 0}
            )
            continue
        n = len(selected)
        count = sum(bool(r["source_present"]) for r in selected)
        x = float(np.mean([r["source_probability"] for r in selected]))
        y = count / n
        reliability_ax.plot(x, y, "o", color=COLORS["new"], ms=7)
        reliability_ax.annotate(
            f"n={n}",
            (x, y),
            xytext=(0, -19 if y > 0.7 else 10),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )
        plotted["reliability"].append(
            {
                "lower": b["lower"],
                "upper": b["upper"],
                "n": n,
                "source_worlds": count,
                "mean_weight": x,
                "fraction_source": y,
            }
        )
    prevalence = (
        sum(bool(r["source_present"]) for r in rows) / len(rows) if rows else None
    )
    reliability_ax.plot([0, 1], [0, 1], color="#888", ls="--", lw=1)
    reliability_ax.set_xlim(-0.025, 1.025)
    reliability_ax.set_ylim(-0.025, 1.08)
    reliability_ax.set_aspect("equal", adjustable="box")
    reliability_ax.set_xlabel("Mean single-source model weight")
    reliability_ax.set_ylabel("Fraction of challenge worlds with any source")
    reliability_ax.set_title(
        "D. Artificial source prevalence", loc="left", fontweight="bold", pad=20
    )
    reliability_ax.grid(alpha=0.14)
    reliability_ax.text(
        0.5,
        -0.24,
        f"Synthetic prevalence: {prevalence:.1%} of {len(rows)} condition-worlds\nCounts share seed blocks; no independence-based CI\nThis does not establish field probability calibration.",
        transform=reliability_ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
    )
    plotted["reliability_population"] = {
        "retained_worlds": len(rows),
        "source_prevalence": prevalence,
        "brier_score": float(
            np.mean(
                [
                    (r["source_probability"] - bool(r["source_present"])) ** 2
                    for r in rows
                ]
            )
        )
        if rows
        else None,
    }
    fig.suptitle(
        f"{label} · Placement outcomes and model-weight reliability",
        fontsize=15,
        fontweight="bold",
    )
    worlds = {(r["family"], r["seed"]) for r in followup}
    population = f"{len(worlds)} condition-worlds / {len({r['seed'] for r in followup})} seed blocks"
    fig.supxlabel(
        "Plans locked before outcomes; identical candidate outcomes and constraints. Random = mean of 20 plans within each world.\n"
        + population
        + ". All acquisitions refitted with the new engine. IQR/10th–90th percentiles describe worlds, not CIs. No field validation.",
        fontsize=9,
    )
    save(fig, out, "planner-overhaul")
    return plotted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="Defaults to the input directory.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Explicitly replace generated figures/manifests; raw outcomes remain read-only.",
    )
    args = parser.parse_args()
    root, out = args.input, args.out or args.input
    names = ("summary.json", "science.json", "followup.json", "metadata.json")
    raw = {name: (root / name).read_bytes() for name in names}
    data = {name: json.loads(content) for name, content in raw.items()}
    summary, science, followup, metadata = (data[name] for name in names)
    if (
        len(science) != summary["science_world_results"]
        or len(followup) != summary["planner_results"]
    ):
        raise ValueError("Summary and raw outcome counts disagree.")
    split = metadata["split"]
    if any(r["split"] != split for r in science + followup):
        raise ValueError("Cannot combine different evaluation splits in one figure.")
    label = split.upper() + (" · PARTIAL" if metadata.get("partial") else "")
    out.mkdir(parents=True, exist_ok=True)
    if not args.replace and any(
        (out / name).exists() for name in OUTPUTS + ("figures.json", "FIGURES.md")
    ):
        raise FileExistsError(
            "Figure outputs already exist; use a fresh directory or explicit --replace."
        )
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "upwind-overhaul-figures-v1",
        }
    )
    values = source_figure(science, summary, out, label)
    values.update(planner_figure(science, followup, summary, out, label))
    repository = Path(__file__).resolve().parents[1]
    packages = (
        "matplotlib",
        "numpy",
        "contourpy",
        "cycler",
        "fonttools",
        "kiwisolver",
        "packaging",
        "pillow",
        "pyparsing",
        "python-dateutil",
        "six",
    )
    dependencies = {}
    for package in packages:
        dist = importlib.metadata.distribution(package)
        dependencies[package] = {
            "version": dist.version,
            "distribution_metadata_sha256": sha(
                (dist.read_text("METADATA") or "").encode()
            ),
        }
    notes = f"""# Overhaul figures — {label}

These figures display the recorded {split} split. They do not run or tune inference. Development and calibration figures are not final evaluation evidence.

![Source coverage and conditional localization](source-overhaul.png)

The left panel pairs continuous-region coverage with Wilson 95% intervals and median area/domain fraction. Regions condition on a single source; coverage for a two-source world is descriptive under a false model. The old engine's discrete point set has no asserted geographic area or off-grid coverage. The right panel compares distance to the continuous primary source using the old discrete-grid MAP and new refined-cell MAP: grid resolutions differ. Every light dot is one retained source-containing world, with median/IQR and 10th–90th percentile summaries. Background-only worlds have no source to localize; unsupported and failed cases remain in the source JSON/summary denominators.

![Paired realized placement outcomes and model-weight reliability](planner-overhaul.png)

Positive target-RMSE differences favor the stated method; negative differences favor the mean of 20 random plans within the same world. The labels retain the worsened-world counts. These are paired condition-worlds sharing seed blocks, not 20 independent random campaigns. Old/new denotes acquisition algorithms; all outcomes are refitted with the same redesigned engine. The source-model reliability plot has artificial prevalence and counts any source (including two-source worlds). Because pooled bins share seed blocks across conditions, no independence-based intervals are plotted. It does not establish field calibration or responsibility probabilities; the diagonal is a reference, not an empirical guarantee.

Inputs: `{root}`. Protocol: `{summary["protocol"]}`. Code-stability field recorded by evaluation: `{summary.get("source_hashes_unchanged", "unavailable")}`. Exact plot values, input/script hashes, dependency metadata hashes and output hashes are in `figures.json`. No measured-data validation was performed.
"""
    (out / "FIGURES.md").write_text(notes)
    manifest = {
        "schema_version": 1,
        "split": split,
        "partial": bool(metadata.get("partial")),
        "protocol": summary["protocol"],
        "input_directory": str(root),
        "input_sha256": {name: sha(content) for name, content in raw.items()},
        "script_sha256": sha(Path(__file__).read_bytes()),
        "python": platform.python_version(),
        "dependencies": dependencies,
        "dependency_lock_sha256": {
            name: sha((repository / name).read_bytes())
            for name in ("requirements.lock", "requirements-research.lock")
        },
        "outputs": {
            name: sha((out / name).read_bytes()) for name in OUTPUTS + ("FIGURES.md",)
        },
        "plot_values": values,
        "scientific_evaluation_mutated": False,
    }
    (out / "figures.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"Saved four {split} figure exports and provenance in {out}.")


if __name__ == "__main__":
    main()
