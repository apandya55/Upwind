"""Model evaluation against reference test cases."""

from datetime import datetime, timezone
import time
import numpy as np
from .engine import analyze
from .inference import fit, region, MODEL_VERSION
from .fixtures import synthetic_case, CASES


def evaluate():
    records = []
    for case in CASES:
        for seed in (101, 202, 303):
            inv, truth = synthetic_case(case, seed)
            start = time.perf_counter()
            result = analyze(inv)
            row = {
                "case": case,
                "seed": seed,
                "status": result["status"],
                "reason": result.get("reason"),
                "warnings": result["warnings"],
                "plans": result["plans"],
            }
            if result.get("sources"):
                fitted = fit(inv, diagnostics=False)
                xy = np.array(
                    fitted["projection"].transform(
                        truth["source"]["longitude"], truth["source"]["latitude"]
                    )
                )
                probability = fitted["cell_weights"]
                center = probability @ fitted["source_xy"]
                order = np.argsort(-probability, kind="stable")
                chosen = order[
                    : min(
                        len(order),
                        int(np.searchsorted(np.cumsum(probability[order]), 0.9)) + 1,
                    )
                ]
                cells = fitted["cells_xy"][chosen]
                inside = np.all(
                    (xy >= cells[:, :2] - 1e-7) & (xy <= cells[:, 2:] + 1e-7), axis=1
                ).any()
                source_region = region(fitted)
                row.update(
                    source_probability=fitted["source_probability"],
                    conditional_mean_localization_error_m=float(
                        np.linalg.norm(center - xy)
                    ),
                    truth_in_conditional_region90=bool(inside),
                    region90_area_m2=source_region["area_m2"],
                    domain_area_m2=source_region["domain_area_m2"],
                    rows_loaded=len(inv.measurements),
                    rows_fitted=fitted["rows_used"],
                    diagnostics=result.get("diagnostics"),
                )
            row["wall_ms"] = (time.perf_counter() - start) * 1000
            records.append(row)
    retained = [r for r in records if "conditional_mean_localization_error_m" in r]
    return {
        "evidence": "Synthetic regression suite",
        "model_version": MODEL_VERSION,
        "protocol": "small original-fixture regression only",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "cases": len(records),
            "completed_inference": len(retained),
            "refused": len(records) - len(retained),
            "median_conditional_mean_error_m": float(
                np.median(
                    [r["conditional_mean_localization_error_m"] for r in retained]
                )
            )
            if retained
            else None,
            "conditional_region90_coverage": sum(
                r["truth_in_conditional_region90"] for r in retained
            ),
            "status": "Research only; inspect source probability, area, warnings and rejected cases.",
        },
        "results": records,
    }
