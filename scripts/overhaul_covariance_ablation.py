"""Development-only covariance/quadrature sensitivity; never tune from final data.

Four declared configurations revisit paired old-family and independent-generator
development worlds. CONFIG is restored after each fit and again on process exit.
No production source or final evaluation is modified.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np

from upwind.inference import CONFIG, MODEL_VERSION, fit
from upwind.models import Investigation, Measurement
from upwind.validation.overhaul import (
    lonlat,
    make_world,
    new_predictive,
    predictive_scores,
    reveal_future,
)
from upwind.validation.overhaul_regression import baseline_generator, hashes

ROOT = Path(__file__).resolve().parents[1]
CONFIGURATIONS = [
    {
        "id": f"tau{tau:g}-target{target:g}",
        "temporal_scale_s": tau,
        "cell_target_m": target,
    }
    for tau in (600.0, 1e12)
    for target in (20.0, 10.0)
]
SEEDS = range(410000, 410012)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def metrics(fitted, truth_lonlat):
    truth = np.array(
        fitted["projection"].transform(
            truth_lonlat["longitude"], truth_lonlat["latitude"]
        )
    )
    weights = fitted["cell_weights"]
    cells = fitted["cells_xy"]
    order = np.argsort(-weights, kind="stable")
    chosen = order[
        : min(len(weights), int(np.searchsorted(np.cumsum(weights[order]), 0.9)) + 1)
    ]
    contains = np.all(
        (truth[None] >= cells[:, :2] - 1e-7) & (truth[None] <= cells[:, 2:] + 1e-7),
        axis=1,
    )
    areas = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    fraction = float(areas[chosen].sum() / areas.sum())
    covered = bool(contains[chosen].any())
    return {
        "source_probability": fitted["source_probability"],
        "source_mean_error_m": float(
            np.linalg.norm(weights @ fitted["source_xy"] - truth)
        ),
        "source_map_error_m": float(
            np.linalg.norm(fitted["source_xy"][order[0]] - truth)
        ),
        "region90_truth_covered": covered,
        "region90_area_m2": float(areas[chosen].sum()),
        "region90_area_fraction": fraction,
        "region90_conditional_mass": float(weights[chosen].sum()),
        "sharp_wrong_region": fitted["source_probability"] > 0.9
        and not covered
        and fraction < 0.25,
        "truth_in_supported_domain": bool(contains.any()),
        "domain_area_m2": float(areas.sum()),
        "excluded_domain_area_m2": fitted["excluded_domain_area_m2"],
        "cell_count": len(weights),
        "maximum_cell_side_m": float((cells[:, 2:] - cells[:, :2]).max()),
        "rows_loaded": fitted["rows_loaded"],
        "rows_fitted": fitted["rows_used"],
        "predictive_warning": fitted["diagnostics"]["predictive_warning"],
        "diagnostic_sensor_count": sum(
            "rmse_ug_m3" in row for row in fitted["diagnostics"]["held_out_sensor"]
        ),
        "fitted_rmse_ug_m3": fitted["rmse"],
    }


def wilson(success, total):
    if not total:
        return None
    z = 1.959963984540054
    p = success / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [float(center - half), float(center + half)]


def summarize(rows):
    groups = []
    for generator in ("old_scalar_family", "independent_development"):
        families = (
            ["strong_signal", "two_sources", "direction_bias"]
            if generator == "old_scalar_family"
            else ["strong_signal", "correlated_errors", "weak_signal"]
        )
        for family in families:
            for config in CONFIGURATIONS:
                selected = [
                    row
                    for row in rows
                    if row["generator"] == generator
                    and row["family"] == family
                    and row["configuration"] == config["id"]
                ]
                valid = [row for row in selected if row["status"] == "fitted"]
                median = (
                    lambda key: float(np.median([row[key] for row in valid]))
                    if valid
                    else None
                )
                groups.append(
                    {
                        "generator": generator,
                        "family": family,
                        "configuration": config["id"],
                        "worlds": len(selected),
                        "fits": len(valid),
                        "covered": sum(row["region90_truth_covered"] for row in valid),
                        "coverage_wilson95": wilson(
                            sum(row["region90_truth_covered"] for row in valid),
                            len(valid),
                        ),
                        "mean_error_median_m": median("source_mean_error_m"),
                        "region_area_median_m2": median("region90_area_m2"),
                        "region_area_fraction_median": median("region90_area_fraction"),
                        "source_probability_median": median("source_probability"),
                        "sharp_wrong_regions": sum(
                            row["sharp_wrong_region"] for row in valid
                        ),
                        "predictive_warnings": sum(
                            row["predictive_warning"] for row in valid
                        ),
                        "maximum_cell_side_median_m": median("maximum_cell_side_m"),
                        "cell_count_median": median("cell_count"),
                        "target_prediction_rmse_median_ug_m3": float(
                            np.median(
                                [
                                    row["target_predictive"]["rmse_ug_m3"]
                                    for row in valid
                                ]
                            )
                        )
                        if valid and generator == "independent_development"
                        else None,
                        "target_latent_mean_rmse_median_ug_m3": median(
                            "target_latent_mean_rmse_ug_m3"
                        )
                        if generator == "independent_development"
                        else None,
                    }
                )
    paired = []
    lookup = {
        (row["generator"], row["family"], row["seed"], row["configuration"]): row
        for row in rows
        if row["status"] == "fitted"
    }
    for group in groups:
        if group["configuration"] == CONFIGURATIONS[0]["id"]:
            continue
        generator, family, config = (
            group["generator"],
            group["family"],
            group["configuration"],
        )
        values = []
        for seed in SEEDS:
            base = lookup.get((generator, family, seed, CONFIGURATIONS[0]["id"]))
            other = lookup.get((generator, family, seed, config))
            if base and other:
                values.append(
                    {
                        "seed": seed,
                        "source_mean_error_change_m": other["source_mean_error_m"]
                        - base["source_mean_error_m"],
                        "region_area_fraction_change": other["region90_area_fraction"]
                        - base["region90_area_fraction"],
                        "source_probability_change": other["source_probability"]
                        - base["source_probability"],
                        "coverage_change": int(other["region90_truth_covered"])
                        - int(base["region90_truth_covered"]),
                        "prediction_rmse_change_ug_m3": other["target_predictive"][
                            "rmse_ug_m3"
                        ]
                        - base["target_predictive"]["rmse_ug_m3"]
                        if generator == "independent_development"
                        else None,
                    }
                )
        paired.append(
            {
                "generator": generator,
                "family": family,
                "configuration": config,
                "baseline": CONFIGURATIONS[0]["id"],
                "worlds": len(values),
                "differences": values,
                "mean_error_change_m": float(
                    np.mean([v["source_mean_error_change_m"] for v in values])
                ),
                "net_coverage_change_count": sum(v["coverage_change"] for v in values),
                "mean_target_prediction_rmse_change_ug_m3": float(
                    np.mean([v["prediction_rmse_change_ug_m3"] for v in values])
                )
                if generator == "independent_development"
                else None,
            }
        )
    return {"groups": groups, "paired_changes": paired}


def report(metadata, summary, out):
    lines = [
        "# Development-only covariance and quadrature sensitivity",
        "",
        "**No production parameters were changed. No calibration or final worlds were accessed.** These are 72 development condition/seed worlds revisited under four declared configurations (288 fits), with the same observations paired across configurations. Old scalar-family cases use fresh development seeds 410000–410011; independent challenge cases use the declared development split with those same seeds. Seeds are reused across conditions, so neither the 72 condition/seed worlds nor the 288 fits represent that many independent campaigns. Neither dataset is untouched evaluation.",
        "",
        "The factorial compares temporal model-error correlation scales of 600 seconds and 10¹² seconds (effectively persistent over the steady window), crossed with midpoint-cell targets of 20 m and 10 m. The 24-cell-per-axis cap stays fixed. Therefore a target of 10 m does **not** guarantee 10 m resolution; actual cell side lengths and retained cells are reported. The old generator has persistent spatial errors. The independent development generator has a decaying spatial/temporal field, heteroscedastic noise and a different transport family. This contrast investigates sensitivity rather than selecting a universally correct covariance.",
        "",
        "| Generator / condition | Time scale s / target m | Fits | Region coverage | 95% Wilson interval | Median mean error m | Median region area m² (% domain) | Median source weight | Wrong sharp | Alarms | Target RMSE µg/m³ |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    configs = {c["id"]: c for c in CONFIGURATIONS}
    for row in summary["groups"]:
        c = configs[row["configuration"]]
        ci = row["coverage_wilson95"]
        target = row["target_prediction_rmse_median_ug_m3"]
        lines.append(
            f"| {row['generator']} / {row['family']} | {c['temporal_scale_s']:g} / {c['cell_target_m']:g} | {row['fits']}/{row['worlds']} | {row['covered']}/{row['fits']} | {ci[0]:.2f}–{ci[1]:.2f} | {row['mean_error_median_m']:.1f} | {row['region_area_median_m2']:.0f} ({100 * row['region_area_fraction_median']:.1f}%) | {row['source_probability_median']:.3f} | {row['sharp_wrong_regions']} | {row['predictive_warnings']} | {target:.2f} |"
            if target is not None
            else f"| {row['generator']} / {row['family']} | {c['temporal_scale_s']:g} / {c['cell_target_m']:g} | {row['fits']}/{row['worlds']} | {row['covered']}/{row['fits']} | {ci[0]:.2f}–{ci[1]:.2f} | {row['mean_error_median_m']:.1f} | {row['region_area_median_m2']:.0f} ({100 * row['region_area_fraction_median']:.1f}%) | {row['source_probability_median']:.3f} | {row['sharp_wrong_regions']} | {row['predictive_warnings']} | — |"
        )
    lines += [
        "",
        "The location estimate and 90% cell union are conditional on the single-source family. Wrong sharp means source-model weight >0.9 plus a region smaller than25% of supported domain that misses primary truth. Two-source coverage of designated primary truth is descriptive under model misspecification. Region area and error must be considered with coverage; broader regions alone are not useful localization. Twelve worlds per condition give wide intervals, so small differences cannot establish a preferred setting.",
        "",
        "Independent-generator target predictions concern three withheld instruments at the final observed timestamp. They use the available historical steady-window wind, with future observations revealed only inside this evaluator. Their outcomes and hidden transport parameters never enter fitting. Raw outputs also include prediction against noiseless transport means, which is a separate task from predicting noisy readings. No planner runs in this sensitivity experiment.",
        "",
        "## Paired changes from the production 600 s / 20 m setting",
        "",
        "| Generator / condition | Alternative time s / target m | Mean error change m | Net covered worlds change | Mean target RMSE change µg/m³ |",
        "|---|---|---|---|---|",
    ]
    for row in summary["paired_changes"]:
        c = configs[row["configuration"]]
        delta = row["mean_target_prediction_rmse_change_ug_m3"]
        d = "—" if delta is None else f"{delta:+.3f}"
        lines.append(
            f"| {row['generator']} / {row['family']} | {c['temporal_scale_s']:g} / {c['cell_target_m']:g} | {row['mean_error_change_m']:+.2f} | {row['net_coverage_change_count']:+d} | {d} |"
        )
    lines += [
        "",
        "Positive error/RMSE changes are worse. All paired seed-level differences are retained. Covariance and quadrature can both change the answer; this experiment cannot separate every physical cause or validate field calibration. In particular, missing multiple-source physics cannot be repaired by finer quadrature or a different correlation time.",
        "",
        "## Reproduction",
        "",
        "```sh",
        "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/overhaul_covariance_ablation.py \\",
        f"  --out {out.relative_to(ROOT)} --report docs/ENGINE_SENSITIVITY.md",
        "```",
        "",
        f"The process restored CONFIG after every fit and at exit: **{metadata['configuration_restored']}**. Relevant source hashes unchanged during execution: **{metadata['source_unchanged_during_run']}**. The numerical source/configuration, generator, evaluator script and protocol hashes, input hashes, every fit and paired difference are saved in `{out.relative_to(ROOT)}`. Use a fresh output folder to repeat. Production remains the documented 600 s / 20 m configuration; no final-set outcome was used to choose a setting.",
    ]
    return "\n".join(lines).replace("smaller than25%", "smaller than 25%") + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--report", type=Path, default=Path("docs/ENGINE_SENSITIVITY.md")
    )
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Refusing overwrite of nonempty evaluation directory")
    out.mkdir(parents=True, exist_ok=True)
    original_config = deepcopy(CONFIG)
    before = hashes()
    cases = baseline_generator()
    metadata = {
        "evidence": "development-only sensitivity; not configuration selection or final evaluation",
        "model": MODEL_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "source_hashes_before": before,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "independent_generator_sha256": hashlib.sha256(
            (ROOT / "backend/upwind/validation/overhaul.py").read_bytes()
        ).hexdigest(),
        "old_generator_sha256": hashlib.sha256(
            (
                ROOT
                / "evaluations/overhaul/baseline-source/backend/upwind/validation/cases.py"
            ).read_bytes()
        ).hexdigest(),
        "protocol_sha256": hashlib.sha256(
            (ROOT / "docs/ENGINE_EVALUATION_PROTOCOL.md").read_bytes()
        ).hexdigest(),
        "seeds": list(SEEDS),
        "production_configuration": original_config,
        "configurations": CONFIGURATIONS,
    }
    write(out / "metadata.json", metadata)
    started = time.perf_counter()
    rows = []
    try:
        for generator, families in [
            ("old_scalar_family", ["strong_signal", "two_sources", "direction_bias"]),
            (
                "independent_development",
                ["strong_signal", "correlated_errors", "weak_signal"],
            ),
        ]:
            for family in families:
                for seed in SEEDS:
                    if generator == "old_scalar_family":
                        old, truth = cases.make_case(family, seed)
                        inv = Investigation.model_validate_json(old.model_dump_json())
                        true_point = cases.point(truth["source_xy"])
                        state = None
                    else:
                        inv, state = make_world(family, seed, "development")
                        state = reveal_future(state)
                        true_point = lonlat(state["source_xy"], "development")
                    for config in CONFIGURATIONS:
                        row = {
                            "generator": generator,
                            "family": family,
                            "seed": seed,
                            "configuration": config["id"],
                            "input_sha256": hashlib.sha256(
                                inv.model_dump_json().encode()
                            ).hexdigest(),
                        }
                        tick = time.perf_counter()
                        try:
                            CONFIG.update(
                                {
                                    key: value
                                    for key, value in config.items()
                                    if key != "id"
                                }
                            )
                            fitted = fit(inv, diagnostics=True)
                            row.update(status="fitted", **metrics(fitted, true_point))
                            if state is not None:
                                targets = [
                                    Measurement(
                                        sensor_id=f"T{i}",
                                        timestamp=state["stamps"][-1],
                                        pm25_ug_m3=float(value),
                                        uncertainty_ug_m3=float(sigma),
                                        origin="synthetic",
                                        **lonlat(xy, "development"),
                                    )
                                    for i, (xy, value, sigma) in enumerate(
                                        zip(
                                            state["target_xy"],
                                            state["target_outcomes"],
                                            state["target_sigma"],
                                        )
                                    )
                                ]
                                mean, cov = new_predictive(fitted, targets)
                                row["target_predictive"] = predictive_scores(
                                    fitted["weights"],
                                    mean,
                                    cov,
                                    state["target_outcomes"],
                                )
                                row["target_latent_mean_rmse_ug_m3"] = float(
                                    np.sqrt(
                                        np.mean(
                                            (
                                                fitted["weights"] @ mean
                                                - np.asarray(state["target_mean"])
                                            )
                                            ** 2
                                        )
                                    )
                                )
                        except ValueError as exc:
                            row.update(status="refused", reason=str(exc))
                        except Exception as exc:
                            row.update(
                                status="crash",
                                exception=type(exc).__name__,
                                reason=str(exc),
                            )
                        finally:
                            CONFIG.clear()
                            CONFIG.update(deepcopy(original_config))
                        row["wall_ms"] = (time.perf_counter() - tick) * 1000
                        rows.append(row)
                write(out / "outcomes.json", rows)
                print(
                    f"{generator} / {family}: 12 paired worlds × 4 settings; {len(rows)} fits attempted",
                    flush=True,
                )
    finally:
        CONFIG.clear()
        CONFIG.update(deepcopy(original_config))
    metadata.update(
        source_hashes_after=hashes(),
        wall_seconds=time.perf_counter() - started,
        configuration_restored=CONFIG == original_config,
    )
    metadata["source_unchanged_during_run"] = metadata["source_hashes_after"] == before
    metadata["worlds"] = 72
    metadata["fits_attempted"] = len(rows)
    metadata["fits_completed"] = sum(row["status"] == "fitted" for row in rows)
    metadata["crashes"] = sum(row["status"] == "crash" for row in rows)
    write(out / "metadata.json", metadata)
    summary = summarize(rows)
    write(out / "summary.json", summary)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(metadata, summary, out))
    print(
        json.dumps(
            {
                key: metadata[key]
                for key in [
                    "fits_attempted",
                    "fits_completed",
                    "crashes",
                    "source_unchanged_during_run",
                    "configuration_restored",
                    "wall_seconds",
                ]
            }
        ),
        flush=True,
    )
    if (
        metadata["crashes"]
        or not metadata["configuration_restored"]
        or not metadata["source_unchanged_during_run"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
