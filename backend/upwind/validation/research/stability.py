"""Model stability and perturbation tests."""

import argparse
import time
from pathlib import Path
import numpy as np
from ...inference import fit, CONFIG
from ...engine import analyze
from .cases import world, FAMILIES, SPLITS
from .run import write, source_hashes, source_metrics


def location(f):
    return f["source_xy"][np.argmax(f["cell_weights"])], f["cell_weights"] @ f[
        "source_xy"
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=SPLITS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Use a new output directory")
    args.out.mkdir(parents=True)
    before = source_hashes()
    rows = []
    start = time.perf_counter()
    write(
        args.out / "metadata.json",
        {
            "split": args.split,
            "source_hashes_before": before,
            "seed_blocks": list(SPLITS[args.split])[:4],
            "perturbations": [
                "reverse_rows",
                "wind_plus3",
                "background_plus5",
                "one_sensor_plus2",
                "grid10m",
            ],
            "plans": "first seed only, prediction-risk objective",
            "grid": "10m target/48 cells per axis for refinement",
        },
    )
    for family in FAMILIES:
        for j, seed in enumerate(list(SPLITS[args.split])[:4]):
            inv, state = world(family, seed, args.split)
            try:
                base = fit(inv, diagnostics=False)
            except ValueError as exc:
                rows.append(
                    {
                        "family": family,
                        "seed": seed,
                        "status": "baseline_refused",
                        "reason": str(exc),
                    }
                )
                continue
            inv.settings.objective = "prediction_variance"
            base_plan = analyze(inv)["plans"][0]["site_ids"] if j == 0 else None
            for change in (
                "reverse_rows",
                "wind_plus3",
                "background_plus5",
                "one_sensor_plus2",
                "grid10m",
            ):
                trial = inv.model_copy(deep=True)
                old_grid = (CONFIG["cell_target_m"], CONFIG["max_cells_axis"])
                if change == "reverse_rows":
                    trial.measurements.reverse()
                    trial.weather.reverse()
                    trial.source_locations.reverse()
                    trial.sites.reverse()
                if change == "wind_plus3":
                    for w in trial.weather:
                        w.wind_from_deg = (w.wind_from_deg + 3) % 360
                if change == "background_plus5":
                    for m in trial.measurements:
                        m.pm25_ug_m3 += 5
                if change == "one_sensor_plus2":
                    first = sorted({m.sensor_id for m in trial.measurements})[0]
                    for m in trial.measurements:
                        if m.sensor_id == first:
                            m.pm25_ug_m3 += 2
                if change == "grid10m":
                    CONFIG["cell_target_m"] = 10.0
                    CONFIG["max_cells_axis"] = 48
                row = {"family": family, "seed": seed, "change": change}
                try:
                    altered = fit(trial, diagnostics=False)
                    a, b = location(base)
                    c, d = location(altered)
                    row.update(
                        status="fitted",
                        map_shift_m=float(np.linalg.norm(a - c)),
                        mean_shift_m=float(np.linalg.norm(b - d)),
                        source_probability_change=altered["source_probability"]
                        - base["source_probability"],
                        **source_metrics(altered, state),
                    )
                    if j == 0:
                        selected = analyze(trial)["plans"][0]["site_ids"]
                        row.update(
                            baseline_plan=base_plan,
                            altered_plan=selected,
                            plan_jaccard=len(set(base_plan) & set(selected))
                            / max(1, len(set(base_plan) | set(selected))),
                        )
                except Exception as exc:
                    row.update(status="failure", reason=f"{type(exc).__name__}: {exc}")
                finally:
                    CONFIG["cell_target_m"], CONFIG["max_cells_axis"] = old_grid
                rows.append(row)
        write(args.out / "results.json", rows)
        print(family, flush=True)
    after = source_hashes()
    write(
        args.out / "completion.json",
        {
            "wall_seconds": time.perf_counter() - start,
            "source_hashes_after": after,
            "source_hashes_unchanged": before == after,
            "results": len(rows),
        },
    )
    if before != after or any(r["status"] == "failure" for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
