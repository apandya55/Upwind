"""Old stress inputs revisited as development data, never a fresh final test.

Loads the original generator in a separate package namespace from the immutable
baseline snapshot. The new model receives ordinary inputs only; truth stays here.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np

from ..inference import CONFIG, MODEL_VERSION, fit, region
from ..models import Investigation

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "evaluations/overhaul/baseline-source/backend/upwind"
RELEVANT = ("inference.py", "quality.py", "weather.py", "numerics.py", "models.py")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def hashes():
    source = Path(__file__).resolve().parents[1]
    return {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in RELEVANT
    }


def baseline_generator():
    name = "upwind_immutable_baseline"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, BASE / "__init__.py", submodule_search_locations=[str(BASE)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return importlib.import_module(name + ".validation.cases")


def new_metrics(inv, truth, original_cases):
    started = time.perf_counter()
    try:
        fitted = fit(inv, diagnostics=True)
    except ValueError as exc:
        return {
            "status": "refused",
            "reason": str(exc),
            "wall_ms": (time.perf_counter() - started) * 1000,
            "rows_loaded": len(inv.measurements),
        }
    weights = fitted["cell_weights"]
    centers = fitted["source_xy"]
    true_ll = original_cases.point(truth["source_xy"])
    xy = np.array(
        fitted["projection"].transform(true_ll["longitude"], true_ll["latitude"])
    )
    mean = weights @ centers
    best = np.flatnonzero(weights.max() - weights <= 1e-12)
    distances = np.linalg.norm(centers[best] - xy, axis=1)
    order = np.argsort(-weights, kind="stable")
    chosen = order[
        : min(len(order), int(np.searchsorted(np.cumsum(weights[order]), 0.9)) + 1)
    ]
    cells = fitted["cells_xy"]
    inside = np.all(
        (xy[None] >= cells[:, :2] - 1e-7) & (xy[None] <= cells[:, 2:] + 1e-7), axis=1
    )
    covered = bool(inside[chosen].any()) if fitted["continuous"] else None
    geographic = region(fitted)
    area = geographic["area_m2"]
    domain = geographic["domain_area_m2"]
    fraction = area / domain if domain > 0 else None
    narrow_miss = covered is False and fraction is not None and fraction < 0.25
    diagnostics = fitted["diagnostics"]
    checked = [row for row in diagnostics["held_out_sensor"] if "rmse_ug_m3" in row]
    held_id = inv.measurements[-1].sensor_id
    same_sensor = next((row for row in checked if row["sensor_id"] == held_id), None)
    return {
        "status": "fitted",
        "rows_loaded": fitted["rows_loaded"],
        "rows_excluded": fitted["rows_excluded"],
        "rows_usable": fitted["rows_input"],
        "rows_fitted": fitted["rows_used"],
        "source_probability": fitted["source_probability"],
        "mean_error_m": float(np.linalg.norm(mean - xy)),
        "map_error_m": float(distances[0]) if len(best) == 1 else None,
        "map_tie_count": len(best),
        "map_error_min_m": float(distances.min()),
        "map_error_max_m": float(distances.max()),
        "continuous_source_support": fitted["continuous"],
        "truth_in_supported_domain": bool(inside.any()),
        "region90_coverage": covered,
        "region90_mass": float(weights[chosen].sum()),
        "region90_area_m2": area,
        "domain_area_m2": domain,
        "excluded_domain_area_m2": fitted["excluded_domain_area_m2"],
        "region90_area_fraction": fraction,
        "narrow_region_miss": narrow_miss,
        "wrong_sharp_region": narrow_miss and fitted["source_probability"] > 0.9,
        "predictive_warning": diagnostics["predictive_warning"],
        "diagnostic_sensors_checked": len(checked),
        "heldout_last_sensor": same_sensor,
        "fitted_rmse_ug_m3": fitted["rmse"],
        "standardized_residual_rms": fitted["standardized_residual_rms"],
        "wall_ms": (time.perf_counter() - started) * 1000,
    }


def quantile(rows, key, q):
    values = [row[key] for row in rows if row.get(key) is not None]
    return float(np.quantile(values, q)) if values else None


def summarize(records):
    groups = {}
    for family in dict.fromkeys(row["case"] for row in records):
        rows = [row for row in records if row["case"] == family]
        old = [row["old"] for row in rows if "localization_error_m" in row["old"]]
        unique_old = [row for row in old if row["map_unique"]]
        new = [row["new"] for row in rows if row["new"]["status"] == "fitted"]
        groups[family] = {
            "worlds": len(rows),
            "old_fits": len(old),
            "new_fits": len(new),
            "new_refusals": sum(row["new"]["status"] == "refused" for row in rows),
            "new_crashes": sum(row["new"]["status"] == "crash" for row in rows),
            "old_unique_map_count": len(unique_old),
            "old_map_error_median_m": quantile(unique_old, "localization_error_m", 0.5),
            "old_map_error_p90_m": quantile(unique_old, "localization_error_m", 0.9),
            "new_mean_error_median_m": quantile(new, "mean_error_m", 0.5),
            "new_mean_error_p90_m": quantile(new, "mean_error_m", 0.9),
            "new_map_error_median_m": quantile(new, "map_error_m", 0.5),
            "new_map_error_p90_m": quantile(new, "map_error_m", 0.9),
            "old_grid90_truth_count": sum(
                row.get("truth_in_90") is True for row in old
            ),
            "old_grid90_coverage_denominator": sum(
                row.get("truth_in_90") is not None for row in old
            ),
            "new_region90_truth_count": sum(
                row["region90_coverage"] is True for row in new
            ),
            "new_region90_coverage_denominator": sum(
                row["region90_coverage"] is not None for row in new
            ),
            "new_region90_area_median_m2": quantile(new, "region90_area_m2", 0.5),
            "new_region90_area_fraction_median": quantile(
                new, "region90_area_fraction", 0.5
            ),
            "new_region90_narrow_misses": sum(row["narrow_region_miss"] for row in new),
            "new_wrong_sharp_regions": sum(row["wrong_sharp_region"] for row in new),
            "new_source_probability_median": quantile(new, "source_probability", 0.5),
            "new_source_probability_below_half": sum(
                row["source_probability"] < 0.5 for row in new
            ),
            "new_outside_supported_domain": sum(
                not row["truth_in_supported_domain"] for row in new
            ),
            "old_alarm_count": sum(row.get("mismatch_warning", False) for row in old),
            "new_alarm_count": sum(row["predictive_warning"] for row in new),
            "new_diagnostic_available_count": sum(
                row["diagnostic_sensors_checked"] > 0 for row in new
            ),
            "new_wall_ms_median": quantile(new, "wall_ms", 0.5),
        }
    return groups


def report(out, metadata, groups):
    fmt = lambda value: "—" if value is None else f"{value:.1f}"
    text = [
        "# Old-case development comparison",
        "",
        f"Baseline `plume-ensemble-0.2.1` versus `{MODEL_VERSION}` on the original 16 × 40 stress inputs. **All cases are development-used. This is not untouched evaluation.** The original generator is loaded from the immutable baseline snapshot, with hidden truth confined to this evaluator. No planner is executed in this comparison; realized planning belongs to the independent challenge experiment.",
        "",
        "The baseline output is the exactly reproduced earlier run. New inputs are the original JSON validated into the current schema, receiving its documented new defaults. Source-domain anchors now define a continuous rectangle with unsupported cells explicitly removed. The estimands differ: old MAP selects a declared point; the new primary estimate is the conditional source-cell mean, with MAP-center error also shown. Neither is a probability of responsibility.",
        "",
        "| Condition | Old/new fits | Old MAP median / p90 m | New mean median / p90 m | New MAP median m | New region coverage | Median area m² / domain % | Old/new alarms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for family, row in groups.items():
        coverage = (
            f"{row['new_region90_truth_count']}/{row['new_region90_coverage_denominator']}"
            if row["new_region90_coverage_denominator"]
            else "—"
        )
        fraction = row["new_region90_area_fraction_median"]
        text.append(
            f"| {family} | {row['old_fits']}/{row['new_fits']} | {fmt(row['old_map_error_median_m'])} / {fmt(row['old_map_error_p90_m'])} | {fmt(row['new_mean_error_median_m'])} / {fmt(row['new_mean_error_p90_m'])} | {fmt(row['new_map_error_median_m'])} | {coverage} | {fmt(row['new_region90_area_median_m2'])} / {fmt(100 * fraction if fraction is not None else None)} | {row['old_alarm_count']}/{row['new_alarm_count']} |"
        )
    fits = sum(row["new_fits"] for row in groups.values())
    crashes = sum(row["new_crashes"] for row in groups.values())
    text += [
        "",
        f"Retained {fits}/{metadata['worlds']} worlds; {metadata['worlds'] - fits - crashes} explicit refusals; {crashes} crashes. Unsupported conditions remain in this denominator. Alarms are different tests: old in-sample residual screen versus new leave-one-sensor-out predictive screen. An absence of alarms is not proof of adequacy; missing diagnostic blocks are recorded in raw outcomes.",
        "",
        "| Condition | Median source-model weight | New narrow region misses | New wrong sharp regions | Truth outside supported cells |",
        "|---|---|---|---|---|",
    ]
    for family, row in groups.items():
        if row["new_fits"]:
            text.append(
                f"| {family} | {row['new_source_probability_median']:.3f} | {row['new_region90_narrow_misses']}/{row['new_fits']} | {row['new_wrong_sharp_regions']}/{row['new_fits']} | {row['new_outside_supported_domain']}/{row['new_fits']} |"
            )
    text += [
        "",
        "A narrow miss means the conditional 90% region occupies <25% of supported domain area and misses the actual continuous primary source. A wrong sharp region also has source-model weight >0.9. Two-source truth refers to the designated primary source; its coverage under a one-source model is descriptive. Old 90% grid-set coverage is saved separately and has no geographic area meaning. Ambiguous old MAP ties receive no fabricated unique-error summary.",
        "",
        "## Reproduction and integrity",
        "",
        "```sh",
        "OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.overhaul_regression \\",
        f"  --out {out.relative_to(ROOT)} --report docs/ENGINE_DEVELOPMENT_COMPARISON.md",
        "```",
        "",
        f"Relevant production source hashes stayed unchanged during this run: **{metadata['source_unchanged_during_run']}**. Exact before/after hashes, configuration, generator and evaluator hashes, environment, every seed's input hash, loaded/excluded/fitted counts, diagnostics, source weights and numerical outcomes are saved beside this report in `{out.relative_to(ROOT)}`. If the source changed during the run, this mixed-version run must not be treated as a frozen comparison.",
        "",
        "Measured-data source validation remains absent. These old inputs use the same scalar Gaussian transport family as the original model, with controlled mismatches; improvements here do not establish generalization. Read the separately frozen overhaul protocol and independent challenge results for that evidence. Regressions remain in this table and raw outputs.",
    ]
    return "\n".join(text) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--report", type=Path, default=Path("docs/ENGINE_DEVELOPMENT_COMPARISON.md")
    )
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Refusing to overwrite nonempty evaluation directory")
    out.mkdir(parents=True, exist_ok=True)
    cases = baseline_generator()
    baseline = json.loads(
        (ROOT / "evaluations/overhaul/baseline-reproduced/science.json").read_text()
    )
    previous = {(row["case"], row["seed"]): row for row in baseline}
    before = hashes()
    metadata = {
        "protocol": "UW-OVERHAUL-2026-01-old-development-regression",
        "evidence": "development-used, not untouched final",
        "model": MODEL_VERSION,
        "baseline_model": "plume-ensemble-0.2.1",
        "worlds": len(cases.CASES) * 40,
        "seeds": [220000, 220039],
        "configuration": CONFIG.copy(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "source_hashes_before": before,
        "original_generator_sha256": hashlib.sha256(
            (BASE / "validation/cases.py").read_bytes()
        ).hexdigest(),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(
            (ROOT / "docs/ENGINE_EVALUATION_PROTOCOL.md").read_bytes()
        ).hexdigest(),
    }
    write(out / "metadata.json", metadata)
    records = []
    started = time.perf_counter()
    for family in cases.CASES:
        for seed in range(220000, 220040):
            original, truth = cases.make_case(family, seed)
            encoded = original.model_dump_json()
            inv = Investigation.model_validate_json(encoded)
            row = {
                "case": family,
                "seed": seed,
                "original_input_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                "new_schema_input_sha256": hashlib.sha256(
                    inv.model_dump_json().encode()
                ).hexdigest(),
                "old": previous[family, seed],
            }
            try:
                row["new"] = new_metrics(inv, truth, cases)
            except Exception as exc:
                row["new"] = {
                    "status": "crash",
                    "exception": type(exc).__name__,
                    "reason": str(exc),
                }
            records.append(row)
        write(out / "outcomes.json", records)
        print(f"{family}: 40 complete; {len(records)} total", flush=True)
    metadata.update(
        source_hashes_after=hashes(),
        wall_seconds=time.perf_counter() - started,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    )
    metadata["source_unchanged_during_run"] = metadata["source_hashes_after"] == before
    groups = summarize(records)
    write(out / "metadata.json", metadata)
    write(out / "summary.json", groups)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(out, metadata, groups))
    print(
        json.dumps(
            {
                "worlds": len(records),
                "fits": sum(row["new_fits"] for row in groups.values()),
                "crashes": sum(row["new_crashes"] for row in groups.values()),
                "source_unchanged_during_run": metadata["source_unchanged_during_run"],
                "wall_seconds": metadata["wall_seconds"],
            }
        ),
        flush=True,
    )
    if (
        any(row["new_crashes"] for row in groups.values())
        or not metadata["source_unchanged_during_run"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
