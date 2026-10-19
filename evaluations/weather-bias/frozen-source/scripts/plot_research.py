"""Standalone research figures from frozen artifacts; no inference or tuning."""

import hashlib, importlib.metadata, json, platform
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/research"
OUT = BASE / "final/figures"
LABELS = {
    "single_window_original": "Original single window",
    "informative_campaign": "Diverse steady winds",
    "same_wind_repetition": "Repeated same wind",
    "weak_campaign": "Weak release",
    "two_sources_campaign": "Two sources (primary)",
    "changing_release_campaign": "Changing release",
    "biased_met_campaign": "Biased meteorology",
    "correlated_campaign": "Correlated error",
    "boundary_campaign": "Boundary source",
    "independent_transport": "Independent transport",
}
COLOR = "#196b71"
ORANGE = "#b66536"


def read(p):
    return json.loads(p.read_text())


def save(fig, stem):
    for ext in ("png", "svg", "pdf"):
        kwargs = {"dpi": 160}
        if ext == "svg":
            kwargs["metadata"] = {"Date": None}
        if ext == "pdf":
            kwargs["metadata"] = {"CreationDate": None, "ModDate": None}
        fig.savefig(OUT / f"{stem}.{ext}", **kwargs)
    plt.close(fig)


def main():
    if OUT.exists():
        raise SystemExit("Preserve prior figures; output directory already exists")
    OUT.mkdir(parents=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "svg.hashsalt": "upwind-research-0.4",
            "figure.facecolor": "white",
        }
    )
    summary = read(BASE / "final/summary.json")
    science = read(BASE / "final/science.json")
    ab = read(BASE / "development-ablations/results.json")
    conditions = [
        r
        for r in summary["conditions"]
        if r["model"] == "plume-campaign-0.4.0" and r["family"] in LABELS
    ]
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 6.5), sharey=True, gridspec_kw={"width_ratios": [1, 1.2]}
    )
    ys = np.arange(len(conditions))
    for i, r in enumerate(conditions):
        rate = r["region90_covered"]
        p = 100 * rate["count"] / rate["n"]
        lo, hi = np.array(rate["wilson95"]) * 100
        axes[0].errorbar(
            p, i, xerr=np.array([[p - lo], [hi - p]]), fmt="o", color=COLOR, capsize=3
        )
    values = [
        [
            100 * r["region90_area_fraction"]
            for r in science
            if r["family"] == c["family"]
            and r["model"] == "plume-campaign-0.4.0"
            and r["status"] == "fitted"
        ]
        for c in conditions
    ]
    axes[1].boxplot(
        values,
        positions=ys,
        orientation="horizontal",
        widths=0.5,
        whis=(10, 90),
        patch_artist=True,
        boxprops={"facecolor": "#d2e7e6", "edgecolor": COLOR},
        medianprops={"color": COLOR},
        flierprops={
            "marker": ".",
            "markersize": 3,
            "markerfacecolor": ORANGE,
            "markeredgecolor": ORANGE,
        },
    )
    axes[0].set_yticks(ys, [LABELS[r["family"]] for r in conditions])
    axes[0].invert_yaxis()
    axes[0].axvline(90, color="#777", linestyle=":", label="Nominal 90% mass")
    axes[0].set_xlim(-2, 102)
    axes[1].set_xlim(0, 100)
    axes[0].set_xlabel("Primary-source coverage %, Wilson 95% interval")
    axes[1].set_xlabel("Conditional region area, % of supported domain")
    axes[0].set_title("Does the region contain truth?")
    axes[1].set_title("How much of the domain does it cover?")
    for a in axes:
        a.grid(axis="x", alpha=0.18)
        a.set_axisbelow(True)
    fig.suptitle("Conditional source regions: coverage and usefulness", fontsize=15)
    fig.text(
        0.02,
        0.025,
        "40 paired synthetic seed blocks per condition. Region area: median, quartiles, p10–p90 whiskers and remaining points.\nA narrow region or a non-warning is not validated attribution; two-source coverage refers to the primary release only.",
        fontsize=9,
    )
    fig.subplots_adjust(left=0.22, right=0.98, top=0.88, bottom=0.16, wspace=0.12)
    save(fig, "source-coverage-area")
    methods = {
        "prediction_risk": "Prediction risk",
        "information": "Information",
        "spread": "Spread",
        "wind": "Wind",
        "baseline_0.3_planner": "Prior 0.3 planner",
    }
    families = [
        "single_window_original",
        "informative_campaign",
        "weak_campaign",
        "biased_met_campaign",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for a, family in zip(axes.flat, families):
        rows = [
            r
            for r in summary["planner"]
            if r["family"] == family
            and (
                r["method"] != "baseline_0.3_planner"
                or family == "single_window_original"
            )
        ]
        for i, r in enumerate(rows):
            x = r["rmse_advantage_vs_random20"]["mean"]
            lo, hi = r["mean_advantage_bootstrap95"]
            a.errorbar(
                x,
                i,
                xerr=[[x - lo], [hi - x]],
                fmt="o",
                capsize=4,
                color=COLOR if r["method"] == "prediction_risk" else "#777",
            )
        a.set_yticks(range(len(rows)), [methods[r["method"]] for r in rows])
        a.invert_yaxis()
        a.axvline(0, color=ORANGE, linestyle=":")
        a.grid(axis="x", alpha=0.18)
        a.set_axisbelow(True)
        a.set_title(LABELS[family])
        a.set_xlabel("Mean RMSE advantage vs random (µg/m³)")
    fig.suptitle(
        "Actual withheld-target prediction after selected measurements", fontsize=15
    )
    fig.text(
        0.02,
        0.025,
        "12 paired synthetic worlds per condition; 20 random plans/world. 95% seed-bootstrap intervals (5,000 resamples).\nPositive means lower RMSE than random. Equal costs/equipment/sites; independent target instruments. Not a source-localization score.",
        fontsize=9,
    )
    fig.subplots_adjust(
        left=0.17, right=0.98, top=0.9, bottom=0.16, hspace=0.47, wspace=0.55
    )
    save(fig, "planner-realized-outcomes")
    variants = [
        ("informative_campaign", "first_window_0.3", "First window / 0.3"),
        ("informative_campaign", "first_window", "First window / 0.4"),
        ("same_wind_repetition", "four_windows", "Four / same wind"),
        ("informative_campaign", "four_windows", "Four / diverse wind"),
        ("informative_campaign", "broad_met", "Diverse / broad met"),
        ("informative_campaign", "midpoint", "Diverse / midpoint"),
        ("informative_campaign", "dense10m", "Diverse / 10m grid"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    for a, key, title in zip(
        axes,
        ["map_error_m", "region90_area_fraction"],
        ["MAP error (m)", "Region area (% of domain)"],
    ):
        v = [
            [
                r[key] * (100 if key == "region90_area_fraction" else 1)
                for r in ab
                if r["family"] == family and r["intervention"] == change
            ]
            for family, change, label in variants
        ]
        a.boxplot(
            v,
            positions=np.arange(len(v)),
            orientation="horizontal",
            patch_artist=True,
            widths=0.5,
            whis=(10, 90),
            boxprops={"facecolor": "#d2e7e6", "edgecolor": COLOR},
            medianprops={"color": COLOR},
        )
        a.set_xlabel(title)
        a.grid(axis="x", alpha=0.18)
        a.set_axisbelow(True)
    axes[0].set_yticks(np.arange(len(variants)), [v[2] for v in variants])
    axes[0].invert_yaxis()
    axes[1].set_xlim(0, 100)
    fig.suptitle(
        "Development ablations: data collection, met assumptions and integration",
        fontsize=14,
    )
    fig.text(
        0.02,
        0.025,
        "12 paired development worlds; same source/Q/domain. Extra periods require extra data/time.\nDeclared met3°/5%; broad20°/30%. 0.3 uses its original broad met. These are development results, not untouched final estimates.",
        fontsize=9,
    )
    fig.subplots_adjust(left=0.23, right=0.98, top=0.87, bottom=0.17, wspace=0.15)
    save(fig, "development-ablations")
    inputs = [
        BASE / "final/summary.json",
        BASE / "final/science.json",
        BASE / "development-ablations/results.json",
    ]
    manifest = {
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "matplotlib": importlib.metadata.version("matplotlib"),
        "inputs": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in inputs
        },
        "outputs": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUT.iterdir())
        },
        "note": "No inference executed. PNG/SVG/PDF standalone exports. Statistical definitions match raw summary and reports.",
    }
    (BASE / "final/figures.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Wrote nine standalone plots")


if __name__ == "__main__":
    main()
