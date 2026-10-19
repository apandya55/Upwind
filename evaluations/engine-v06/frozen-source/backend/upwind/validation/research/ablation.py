"""Development-only controlled measurement, met and integration ablations."""

import argparse
from pathlib import Path
import time
from ...inference import fit, CONFIG
from .cases import world, SPLITS
from .run import source_metrics, write, source_hashes, load_old, old_input


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error("Use a new directory")
    a.out.mkdir(parents=True)
    before = source_hashes()
    rows = []
    start = time.perf_counter()
    for seed in SPLITS["development"]:
        for family in ("informative_campaign", "same_wind_repetition"):
            inv, state = world(family, seed, "development")
            for intervention in (
                "four_windows",
                "first_window",
                "first_window_0.3",
                "broad_met",
                "midpoint",
                "dense10m",
            ):
                # Paired source, Q and domain never change. Only documented inputs/data differ.
                trial = inv.model_copy(deep=True)
                grid = (CONFIG["cell_target_m"], CONFIG["max_cells_axis"])
                if intervention.startswith("first_window"):
                    end = trial.study_windows[0].end
                    trial.study_windows = []
                    trial.measurements = [
                        m for m in trial.measurements if m.timestamp <= end
                    ]
                    trial.weather = [m for m in trial.weather if m.timestamp <= end]
                if intervention == "broad_met":
                    trial.settings.met_direction_sd_deg = 20.0
                    trial.settings.met_speed_fraction = 0.3
                if intervention == "dense10m":
                    CONFIG["cell_target_m"] = 10.0
                    CONFIG["max_cells_axis"] = 48
                row = {"seed": seed, "family": family, "intervention": intervention}
                try:
                    if intervention == "first_window_0.3":
                        mod, _, _ = load_old()
                        f = mod.fit(old_input(trial), diagnostics=False)
                    else:
                        f = fit(
                            trial,
                            diagnostics=False,
                            spatial_order=1 if intervention == "midpoint" else None,
                        )
                    row.update(status="fitted", **source_metrics(f, state))
                except Exception as exc:
                    row.update(status="failure", reason=f"{type(exc).__name__}: {exc}")
                finally:
                    CONFIG["cell_target_m"], CONFIG["max_cells_axis"] = grid
                rows.append(row)
        write(a.out / "results.json", rows)
        print(seed, flush=True)
    write(
        a.out / "metadata.json",
        {
            "source_hashes_before": before,
            "source_hashes_after": source_hashes(),
            "source_hashes_unchanged": before == source_hashes(),
            "wall_seconds": time.perf_counter() - start,
            "split": "development",
            "case_count": len(rows),
            "note": "No labels change production settings. Dense integration and broad met are ablations, not alternatives selected using final truth.",
        },
    )
    if any(r["status"] == "failure" for r in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
