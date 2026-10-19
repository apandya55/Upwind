"""Standalone final weather-repair figure; refuses to overwrite prior artifacts."""

import hashlib, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/weather-bias"
source = BASE / "final-summary.json"
data = json.loads(source.read_text())["conditions"]
folder = BASE / "figures"
folder.mkdir(exist_ok=False)
families = [
    "characterized_nominal",
    "unknown_nominal",
    "direction_unknown",
    "direction_characterized",
    "clock_lag",
    "spatial_winds",
]
names = [
    "Nominal + comparison",
    "Nominal, unknown",
    "Direction bias, unknown",
    "Direction bias + comparison",
    "Clock lag",
    "Spatial wind difference",
]
fig, axes = plt.subplots(1, 3, figsize=(15, 6), sharey=True, layout="constrained")
for j, (title, key) in enumerate(
    [
        ("Conditional region coverage, fitted", "coverage"),
        ("Accepted / all generated", "acceptance"),
        ("Accepted wrong / all generated", "wrong"),
    ]
):
    ax = axes[j]
    for k, (version, color) in enumerate(
        [("baseline-0.4.0", "#64748b"), ("plume-weather-0.5.0", "#0f766e")]
    ):
        vals = []
        errors = []
        for family in families:
            r = next(r for r in data if r["family"] == family and r["model"] == version)
            rate = (
                r["all"]["region90_covered"]
                if key == "coverage"
                else r["acceptance_rate"]
                if key == "acceptance"
                else r["wrong_per_generated"]
            )
            value = 100 * rate["count"] / rate["n"]
            ci = rate["wilson95"]
            vals.append(value)
            errors.append([value - 100 * ci[0], 100 * ci[1] - value])
        y = np.arange(len(families)) + (k - 0.5) * 0.32
        ax.barh(y, vals, height=0.3, color=color, label="0.4" if k == 0 else "0.5")
        ax.errorbar(
            vals,
            y,
            xerr=np.array(errors).T,
            fmt="none",
            ecolor="#172033",
            capsize=2,
            linewidth=0.8,
        )
    ax.set_title(title, fontsize=11)
    ax.set_xlim(0, 105)
    ax.set_xlabel("% (Wilson95% interval)")
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
axes[0].set_yticks(range(len(families)), names)
axes[0].invert_yaxis()
axes[0].legend(loc="lower right", title="Model")
fig.suptitle(
    "Fresh weather holdout: usefulness and failures together\n32 synthetic worlds per condition; conditional regions are not field calibration",
    fontsize=13,
)
manifest = {
    "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "artifacts": {},
}
for extension in ["png", "svg", "pdf"]:
    p = folder / ("weather-tradeoffs." + extension)
    fig.savefig(p, dpi=180)
    manifest["artifacts"][str(p.relative_to(ROOT))] = hashlib.sha256(
        p.read_bytes()
    ).hexdigest()
(BASE / "figure-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
