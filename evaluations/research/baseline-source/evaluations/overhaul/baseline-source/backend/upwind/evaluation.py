"""Predeclared synthetic evaluation. Never calls hidden truth from inference."""

import platform
from pathlib import Path
import time
from datetime import datetime, timezone
import numpy as np
from scipy.spatial import ConvexHull
from .engine import analyze, ensemble, plume, projector, matched_weather, MODEL_VERSION
from .fixtures import synthetic_case, CASES


def evaluate():
    results = []
    for case in CASES:
        for seed in [101, 202, 303]:
            inv, truth = synthetic_case(case, seed)
            started = time.perf_counter()
            result = analyze(inv)
            record = {
                "case": case,
                "seed": seed,
                "status": result["status"],
                "reason": result.get("reason"),
                "warnings": result["warnings"],
                "runtime_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            if result.get("sources"):
                weights = np.array([s["weight"] for s in result["sources"]])
                tr = projector(
                    truth["source"]["latitude"], truth["source"]["longitude"]
                )
                xy = np.array(
                    [
                        tr.transform(s["longitude"], s["latitude"])
                        for s in result["sources"]
                    ]
                )
                order = np.argsort(-weights)
                selected = order[: np.searchsorted(np.cumsum(weights[order]), 0.9) + 1]
                area = (
                    float(ConvexHull(xy[selected]).volume) if len(selected) > 2 else 0.0
                )
                record.update(
                    localization_error_m=float(np.linalg.norm(xy[np.argmax(weights)])),
                    credible_grid_points_90=len(selected),
                    credible_hull_m2=area,
                    truth_in_90_set=bool(truth["source_index"] in selected),
                    entropy_nats=result["entropy_nats"],
                    fitted_rmse_ug_m3=result["fitted_rmse_ug_m3"],
                    plans=result["plans"],
                )
                held_id = inv.measurements[-1].sensor_id
                held = [m for m in inv.measurements if m.sensor_id == held_id]
                training = inv.model_copy(deep=True)
                training.measurements = [
                    m for m in inv.measurements if m.sensor_id != held_id
                ]
                try:
                    fit = ensemble(training)
                    weather, _, _ = matched_weather(training, held)
                    point_xy = np.array(
                        [
                            fit["projection"].transform(m.longitude, m.latitude)
                            for m in held
                        ]
                    )
                    predictions = np.array(
                        [
                            [
                                bg
                                + float(
                                    plume(
                                        [p],
                                        fit["source_xy"][loc],
                                        q,
                                        w.wind_speed_m_s * scale,
                                        w.wind_from_deg + dw,
                                    )[0]
                                )
                                for p, w in zip(point_xy, weather)
                            ]
                            for loc, q, bg, dw, scale in fit["configs"]
                        ]
                    )
                    mean = fit["weights"] @ predictions
                    record["held_out_sensor"] = held_id
                    record["held_out_rmse_ug_m3"] = float(
                        np.sqrt(
                            np.mean(
                                (mean - np.array([m.pm25_ug_m3 for m in held])) ** 2
                            )
                        )
                    )
                except ValueError as e:
                    record["held_out_unavailable"] = str(e)
            results.append(record)
    valid = [r for r in results if "localization_error_m" in r]
    cpu = platform.processor() or "not exposed"
    if Path("/proc/cpuinfo").exists():
        cpu = next(
            (
                s.split(":", 1)[1].strip()
                for s in Path("/proc/cpuinfo").read_text().splitlines()
                if s.startswith("model name")
            ),
            cpu,
        )
    return {
        "evidence": "SYNTHETIC ONLY; no independent field validation",
        "model_version": MODEL_VERSION,
        "protocol": "docs/EVALUATION_PROTOCOL.md",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": cpu,
            "python": platform.python_version(),
            "python_processes": 1,
            "blas_threads": "library default; not pinned",
        },
        "summary": {
            "cases": len(results),
            "completed_inference": len(valid),
            "refused": len(results) - len(valid),
            "truth_in_90_set": sum(r["truth_in_90_set"] for r in valid),
            "median_localization_error_m": float(
                np.median([r["localization_error_m"] for r in valid])
            ),
            "max_runtime_ms": max(r["runtime_ms"] for r in results),
            "status": "experimental; inspect all mismatches and ambiguity, no field accuracy claim",
        },
        "results": results,
    }
