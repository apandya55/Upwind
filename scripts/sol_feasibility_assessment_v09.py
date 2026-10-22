"""Summarize the Sol feasibility evidence without rerunning inference.

The expensive mechanism runs are kept append-only under ``evaluations``.  This
reporting-only command joins their public rows with the evaluator-private truth
to make denominators and simple baselines explicit.  It never feeds truth to
the engine and refuses to overwrite an output file.
"""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]


def _rate(rows, predicate):
    return sum(bool(predicate(row)) for row in rows)


def _ladder_summary(ladder):
    results = json.loads((ladder / "results.json").read_text())
    truth = json.loads((ladder / "private_truth.json").read_text())
    source_rows = [row for row in results if truth[row["case"]].get("source") is not None]
    source_free = [row for row in results if truth[row["case"]].get("source") is None]
    fitted = [row for row in results if row.get("fit_error") is None]
    errors = [row["mean_error_m_diagnostic"] for row in source_rows if row.get("mean_error_m_diagnostic") is not None]
    centers = [row["prior_domain_center_error_m"] for row in source_rows if row.get("prior_domain_center_error_m") is not None]
    return {
        "attempts": len(results),
        "fitted": len(fitted),
        "fit_failures": len(results) - len(fitted),
        "source_present_attempts": len(source_rows),
        "source_free_attempts": len(source_free),
        "evidence_status_counts": {
            status: sum(row.get("evidence_status") == status for row in results)
            for status in ("source_supported", "ambiguous", "model_mismatch")
        },
        "source_supported_denominator": len(results),
        "source_present_mean_error_median_m": median(errors) if errors else None,
        "domain_center_baseline_median_error_m": median(centers) if centers else None,
        "mean_error_within_m": {
            str(limit): {"candidate": _rate(errors, lambda value: value <= limit), "denominator": len(errors), "baseline": _rate(centers, lambda value: value <= limit)}
            for limit in (50, 100, 200)
        },
        "region_area_fraction_median": median(
            row["region_area_fraction"] for row in source_rows if row.get("region_area_fraction") is not None
        ),
        "source_present_region_area_denominator": sum(row.get("region_area_fraction") is not None for row in source_rows),
        "prior_sensitivity_blocks": sum(bool(row.get("sensitivity_blocking")) for row in results),
        "numerical_convergence_failures": sum(row.get("numerical_converged") is False for row in results),
        "independent_scalar_abs_delta": json.loads((ladder / "summary.json").read_text())["independent_scalar_vs_production_abs_delta"],
        "interpretation": "The domain-center values are an evaluator-only prior-only baseline. They are never supplied to production inference. Region area is conditional area, and ladder rows do not expose cell membership; source-region coverage is therefore reported from the v0.8 final artifact below.",
    }


def _v08_summary(path):
    candidate = json.loads((path / "summary.json").read_text())["candidate"]
    return {
        "attempts": candidate["attempts"],
        "evidence_status_counts": candidate["evidence_status_counts"],
        "median_mean_error_m": candidate["mean_error_distribution_all"]["median"],
        "median_mode_error_m": candidate["mode_error_distribution_all"]["median"],
        "region_coverage_correct_source_count": candidate["region_coverage_correct_source_count"],
        "region_coverage_denominator": candidate["region_coverage_denominator"],
        "median_region_area_fraction": candidate["family_summary"]["nominal"]["median_region_area_fraction"],
        "runtime_ms_median": candidate["runtime_ms_median"],
        "source_free_attempts": 0,
        "meaning": "The v0.8 family set contains source-present worlds only; its 224/256 value is correct source-count region inclusion, not a source-count or acceptance probability.",
    }


def run(out, ladder, v08):
    out = Path(out)
    if out.exists():
        raise FileExistsError("Refusing to overwrite an assessment artifact")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "assessment": "Sol feasibility and substantive repair v0.9",
        "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "ladder": _ladder_summary(Path(ladder)),
        "v08_final": _v08_summary(Path(v08)),
        "scientific_call_path": {
            "input_quality_and_sampling": "backend/upwind/quality.py: measurement_quality/select_rows",
            "coordinate_and_forward_physics": "backend/upwind/numerics.py: projector/plume",
            "weather_matching_and_shared_error": "backend/upwind/campaign.py + backend/upwind/weather_evidence.py",
            "posterior_and_gls": "backend/upwind/inference.py: _fit_once/fit/positive-normal integration",
            "source_cell_quadrature": "backend/upwind/inference.py: four tensor Gauss nodes and nested convergence",
            "profile_likelihood_diagnostic": "backend/upwind/identifiability.py: whiten_profile/diagnose_fit",
            "public_support_decision": "backend/upwind/engine.py: _cached_analysis",
            "planning": "backend/upwind/design.py + backend/upwind/prediction_design.py",
        },
        "decision": {
            "outcome": "C",
            "reason": "The feasible weak/noisy ladder has no supported result, broad conditional regions, and a source-present median mean error that does not beat the domain-center baseline. Strong controls show that missing independent strength/background/weather information changes the result, while one extra colocated sensor does not remove the ridge.",
            "required_information": [
                "independent release-strength or background measurement",
                "independent local weather over the same period or multiple wind directions",
                "spatially diverse monitors that separate competing plume geometries",
            ],
            "field_validation": "not performed; synthetic evidence does not establish attribution, calibration, or organizational usefulness",
        },
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=ROOT / "evaluations/engine-v09/ladder")
    parser.add_argument("--v08", type=Path, default=ROOT / "evaluations/engine-v08/final")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.out, args.ladder, args.v08)
