"""Reproduce baseline-only diagnostic toys against the immutable source snapshot.

This script is an audit instrument, not production inference or a new held-out test.
"""

from pathlib import Path
import hashlib
import json
import sys
import importlib.metadata as metadata
import platform
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "evaluations/overhaul/baseline-source"
sys.path.insert(0, str(SNAPSHOT / "backend"))

import numpy as np
import upwind.engine as engine
from upwind.numerics import flow_vector, projector
from upwind.validation.cases import make_case, scalar_plume


def main():
    manifest = json.loads((SNAPSHOT.parent / "baseline-manifest.json").read_text())
    for rel, expected in manifest["snapshot_source_sha256"].items():
        actual = hashlib.sha256((SNAPSHOT / rel).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Baseline snapshot changed: {rel}")
    output = {
        "model": engine.MODEL_VERSION,
        "source_file": str(Path(engine.__file__).relative_to(ROOT)),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "evidence": "baseline development-used diagnostic toys; no held-out validation",
    }
    reproduced = SNAPSHOT.parent / "baseline-reproduced"
    original = ROOT / "evaluations/stress/v0.2.1-final"
    comparison = {}
    for name in ["science", "followup"]:
        old = json.loads((original / f"{name}.json").read_text())
        new = json.loads((reproduced / f"{name}.json").read_text())
        strip = lambda row: {
            key: value
            for key, value in row.items()
            if key not in {"wall_ms", "runtime_ms"}
        }
        differing = [
            {"index": i, "old": strip(a), "new": strip(b)}
            for i, (a, b) in enumerate(zip(old, new))
            if strip(a) != strip(b)
        ]
        comparison[name] = {
            "original_rows": len(old),
            "reproduced_rows": len(new),
            "non_timing_identical": len(old) == len(new) and not differing,
            "differing_rows": len(differing),
            "first_differences": differing[:2],
        }
    (reproduced / "reproduction-comparison.json").write_text(
        json.dumps({"comparison": comparison}, indent=2) + "\n"
    )
    packages = {
        item.metadata["Name"]: item.version
        for item in metadata.distributions()
        if item.metadata["Name"]
    }
    (reproduced / "dependencies.json").write_text(
        json.dumps(
            {
                "python_executable": sys.executable,
                "python": platform.python_version(),
                "packages": dict(sorted(packages.items())),
            },
            indent=2,
        )
        + "\n"
    )
    output["cardinal_downwind_vectors"] = {
        str(angle): flow_vector(angle).tolist() for angle in [0, 90, 180, 270]
    }
    transformed = projector(0, 0).transform(0.001, 0)
    output["projection_0_001_degree_east_m"] = list(transformed)
    # The plume depends on Q/u: independent physical non-identifiability example.
    a = scalar_plume((100, 0), (0, 0), 5000, 2, 270)
    b = scalar_plume((100, 0), (0, 0), 10000, 4, 270)
    output["strength_speed_confounding"] = {
        "Q5000_u2": a,
        "Q10000_u4": b,
        "absolute_difference": abs(a - b),
    }
    conditions = {}
    for case in [
        "strong_signal",
        "weak_signal",
        "two_sources",
        "direction_bias",
        "speed_bias",
        "off_grid",
    ]:
        rows = []
        for seed in range(220000, 220040):
            inv, truth = make_case(case, seed)
            fit = engine.ensemble(inv)
            rows.append(
                {
                    "seed": seed,
                    "standardized_residual_rms": fit["standardized_residual_rms"],
                    "fitted_rmse_ug_m3": fit["rmse"],
                    "max_location_weight": float(fit["location_weights"].max()),
                }
            )
        initial = truth["initial_xy"]
        contribution = [
            scalar_plume(
                p,
                truth["source_xy"],
                truth["strength"],
                truth["speed"],
                truth["direction"],
            )
            for p in initial
        ]
        conditions[case] = {
            "true_plume_contribution_per_site_ug_m3": contribution,
            "transport_direction_from_deg": truth["direction"],
            "transport_speed_m_s": truth["speed"],
            "observation_sigma_ug_m3": truth["measurement_noise"],
            "residual_standardized_rms_min_median_max": np.quantile(
                [r["standardized_residual_rms"] for r in rows], [0, 0.5, 1]
            ).tolist(),
            "individual_runs": rows,
        }
        if case == "two_sources":
            conditions[case]["second_source_contribution_per_site_ug_m3"] = [
                scalar_plume(p, (-180, 30), 30000, truth["speed"], 270) for p in initial
            ]
    output["conditions"] = conditions

    # Rare transient construction tests *selection*, not a valid steady-release fit.
    inv, _ = make_case("strong_signal", 220023)
    base_rows = inv.measurements[:4]
    start = datetime(2025, 7, 1, 10, tzinfo=timezone.utc)
    inv.measurements = [
        row.model_copy(
            update={"timestamp": (start + timedelta(seconds=t * 60)).isoformat()}
        )
        for t in range(60)
        for row in base_rows
    ]
    inv.weather = [
        inv.weather[0].model_copy(
            update={"timestamp": (start + timedelta(seconds=t * 60)).isoformat()}
        )
        for t in range(60)
    ]
    selected = engine.balanced_rows(inv.measurements)
    selected_keys = {(m.sensor_id, m.timestamp) for m in selected}
    spike_index = next(
        i
        for i, m in enumerate(inv.measurements)
        if (m.sensor_id, m.timestamp) not in selected_keys
    )
    before = inv.measurements[spike_index]
    inv.measurements[spike_index] = before.model_copy(
        update={"pm25_ug_m3": before.pm25_ug_m3 + 40}
    )
    fit_subset = engine.ensemble(inv)
    original_selector = engine.balanced_rows
    try:
        engine.balanced_rows = lambda rows: sorted(
            rows, key=lambda m: (m.sensor_id, m.timestamp)
        )
        fit_full = engine.ensemble(inv)
    finally:
        engine.balanced_rows = original_selector
    output["rare_transient_selection_toy"] = {
        "loaded_rows": len(inv.measurements),
        "subset_rows": fit_subset["rows_used"],
        "full_rows": fit_full["rows_used"],
        "spike_sensor": before.sensor_id,
        "spike_timestamp": before.timestamp,
        "spike_increment_ug_m3": 40,
        "spike_selected": (before.sensor_id, before.timestamp) in selected_keys,
        "subset_standardized_residual_rms": fit_subset["standardized_residual_rms"],
        "full_standardized_residual_rms": fit_full["standardized_residual_rms"],
        "subset_rmse_ug_m3": fit_subset["rmse"],
        "full_rmse_ug_m3": fit_full["rmse"],
        "subset_location_weights": fit_subset["location_weights"].tolist(),
        "full_location_weights": fit_full["location_weights"].tolist(),
        "limitation": "Transient violates steady-release assumption; demonstrates potential loss of a diagnostic episode, not recoverable source-location truth.",
    }
    target = SNAPSHOT.parent / "baseline-reproduced/diagnostic-toys.json"
    target.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": str(target.relative_to(ROOT)),
                "conditions": {
                    k: v["residual_standardized_rms_min_median_max"]
                    for k, v in conditions.items()
                },
                "selection": output["rare_transient_selection_toy"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
