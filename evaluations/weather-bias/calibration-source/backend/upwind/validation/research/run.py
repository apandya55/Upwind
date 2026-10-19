"""Append-only UW-RESEARCH-2026-02 experiments. Truth never reaches production."""

import argparse, hashlib, importlib, importlib.util, json, os, platform, sys, time
from pathlib import Path
from collections import Counter
import numpy as np
from ...inference import fit, MODEL_VERSION, CONFIG
from ...identifiability import diagnose_fit
from ...models import Measurement
from ...engine import analyze, eligible_indices, select_plan
from ..overhaul import predictive_scores
from .cases import world, reveal, point, SPLITS, FAMILIES

ROOT = Path(__file__).resolve().parents[4]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def source_hashes():
    paths = list((ROOT / "backend/upwind").rglob("*.py")) + [
        ROOT / "docs/RESEARCH_EVALUATION_PROTOCOL.md",
        ROOT / "requirements.lock",
    ]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def load_old():
    name = "_upwind_research_baseline"
    if name not in sys.modules:
        p = ROOT / "evaluations/research/baseline-source/backend/upwind"
        spec = importlib.util.spec_from_file_location(
            name, p / "__init__.py", submodule_search_locations=[str(p)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return (
        importlib.import_module(name + ".inference"),
        importlib.import_module(name + ".models"),
        importlib.import_module(name + ".engine"),
    )


def old_input(inv):
    _, models, _ = load_old()
    data = inv.model_dump()
    data = {k: v for k, v in data.items() if k in models.Investigation.model_fields}
    data["settings"] = {
        k: v for k, v in data["settings"].items() if k in models.Settings.model_fields
    }
    data["settings"]["objective"] = "scenario_information"
    data["assumptions"] = {
        k: v
        for k, v in data["assumptions"].items()
        if k in models.Assumptions.model_fields
    }
    return models.Investigation.model_validate_json(json.dumps(data))


def truth_point(state):
    if "previous" in state:
        from ..overhaul import lonlat

        return lonlat(state["source_xy"], state["previous"]["split"])
    return point(state["source_xy"], state["split"])


def source_metrics(f, state):
    p = truth_point(state)
    truth = np.array(f["projection"].transform(p["longitude"], p["latitude"]))
    w = f["cell_weights"]
    cells = f["cells_xy"]
    order = np.argsort(-w, kind="stable")
    mode = int(order[0])
    chosen = order[: min(len(w), int(np.searchsorted(np.cumsum(w[order]), 0.9)) + 1)]
    area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    inside = np.all((truth >= cells[:, :2]) & (truth <= cells[:, 2:]), axis=1)
    coverage = bool(inside[chosen].any())
    fraction = float(area[chosen].sum() / area.sum())
    probability = f["source_probability"]
    present = state["source_present"]
    return {
        "source_probability": probability,
        "source_present": present,
        "source_brier": float((probability - present) ** 2),
        "map_error_m": float(np.linalg.norm(f["source_xy"][mode] - truth))
        if present
        else None,
        "mean_error_m": float(np.linalg.norm(w @ f["source_xy"] - truth))
        if present
        else None,
        "prior_centroid_error_m": float(
            np.linalg.norm(np.average(f["source_xy"], weights=area, axis=0) - truth)
        )
        if present
        else None,
        "region90_covered": coverage if present else None,
        "region90_area_m2": float(area[chosen].sum()),
        "region90_area_fraction": fraction,
        "region90_mass": float(w[chosen].sum()),
        "source_miss": bool(present and probability < 0.5),
        "false_source_alarm": bool(not present and probability > 0.9),
        "narrow_wrong_region": bool(present and not coverage and fraction < 0.25),
        "sharp_wrong_region": bool(
            present and not coverage and fraction < 0.25 and probability > 0.9
        ),
    }


def predict(f, points):
    return f["predictive"](
        points,
        [p.timestamp for p in points],
        [p.sensor_id for p in points],
        uncertainties=[p.uncertainty_ug_m3 for p in points],
    )


def score_prediction(f, points, observed, old=False):
    if old:
        means, covs = predict(f, points)
        return predictive_scores(f["weights"], means, covs, observed)
    args = (points, [p.timestamp for p in points], [p.sensor_id for p in points])
    kwargs = {"uncertainties": [p.uncertainty_ug_m3 for p in points]}
    mean, _ = f["prediction_moments"](*args, **kwargs)
    draws = f["predictive_draws"](*args, **kwargs, samples=2048, seed=90211)
    lo, hi = np.quantile(draws, [0.05, 0.95], axis=0)
    values = np.asarray(observed)
    return {
        "rmse_ug_m3": float(np.sqrt(np.mean((mean - values) ** 2))),
        "nlpd": float(-np.mean(f["predictive_log_density"](values, *args, **kwargs))),
        "interval90_coverage": float(np.mean((values >= lo) & (values <= hi))),
        "interval90_width": float(np.mean(hi - lo)),
        "interval_method": "2048 scrambled Sobol draws of exact truncated-strength mixture; numerical quantiles",
    }


def evaluate(inv, state, old=False):
    start = time.perf_counter()
    row = {
        "family": state["family"],
        "seed": state["seed"],
        "model": "baseline-0.3.0" if old else MODEL_VERSION,
        "rows_loaded": len(inv.measurements),
    }
    try:
        if old:
            mod, _, _ = load_old()
            study = old_input(inv)
            f = mod.fit(study, diagnostics=True)
        else:
            study = inv
            f = fit(inv, diagnostics=True)
        row.update(
            status="fitted",
            **source_metrics(f, state),
            rows_fitted=f["rows_used"],
            rows_usable=f["rows_input"],
            warning=bool(f["diagnostics"]["predictive_warning"]),
            diagnostics=f["diagnostics"],
        )
        if not old:
            row["observability"] = diagnose_fit(f, inv.settings.noise_ug_m3)
        row["accepted"] = bool(
            row["source_probability"] >= 0.9
            and row["region90_area_fraction"] < 0.5
            and not row["warning"]
        )
        sensor_ids = sorted({p.sensor_id for p in study.measurements})
        held_id = sensor_ids[
            (state["seed"] - SPLITS[state["split"]].start) % len(sensor_ids)
        ]
        held = [p for p in study.measurements if p.sensor_id == held_id]
        train = study.model_copy(deep=True)
        train.measurements = [p for p in study.measurements if p.sensor_id != held_id]
        try:
            trained = (
                mod.fit(train, diagnostics=False)
                if old
                else fit(train, diagnostics=False)
            )
            row["prediction"] = score_prediction(
                trained, held, [p.pm25_ug_m3 for p in held], old
            )
        except ValueError as exc:
            row["prediction_unavailable"] = str(exc)
    except (ValueError, OverflowError) as exc:
        row.update(status="refused", reason=str(exc))
    except Exception as exc:
        row.update(status="crash", reason=f"{type(exc).__name__}: {exc}")
    row["wall_ms"] = (time.perf_counter() - start) * 1000
    return row


def plans(inv):
    locked = []
    new = inv.model_copy(deep=True)
    new.settings.objective = "prediction_variance"
    risk = analyze(new)
    locked.append(
        ("prediction_risk", list(risk["plans"][0]["site_ids"]) if risk["plans"] else [])
    )
    information = inv.model_copy(deep=True)
    information.settings.objective = "scenario_information"
    old_score = analyze(information)
    locked.append(
        (
            "information",
            list(old_score["plans"][0]["site_ids"]) if old_score["plans"] else [],
        )
    )
    for name, prefix in [("spread", "Spatial"), ("wind", "Wind")]:
        plan = next(
            (p for p in risk.get("plans", []) if p["method"].startswith(prefix)), None
        )
        locked.append((name, plan["site_ids"] if plan else []))
    _, _, old_engine = load_old()
    try:
        prior = old_engine.analyze(old_input(inv))
        selected = prior["plans"][0]["site_ids"] if prior.get("plans") else []
    except ValueError:
        selected = []
    locked.append(("baseline_0.3_planner", selected))
    eligible = eligible_indices(inv)
    # Same supported geometry and constraints for every applicable policy.
    supported = fit(inv, diagnostics=False)["candidate_supported"]
    eligible = [i for i in eligible if supported[i]]
    for seed in range(7000, 7020):
        indices = select_plan(
            inv, "random", lambda s: 0, eligible, np.random.default_rng(seed)
        )
        locked.append((f"random-{seed}", [inv.sites[i].id for i in indices]))
    return locked


def followup(inv, state):
    locked = plans(inv)
    locked_hash = hashlib.sha256(
        json.dumps(locked, sort_keys=True).encode()
    ).hexdigest()
    # NO outcome realization occurs above this point.
    reveal(state)
    if "previous" in state:
        old = state["previous"]
        outcomes = old["candidate_outcomes"]
        sigma = old["candidate_sigma"]
        target_xy = old["target_xy"]
        target_values = old["target_outcomes"]
        target_sigma = old["target_sigma"]
        timestamp = old["stamps"][-1]
        from ..overhaul import lonlat

        target_points = [lonlat(xy, old["split"]) for xy in target_xy]
    else:
        outcomes = state["candidate_outcomes"]
        sigma = state["future_sigma"][:12]
        target_points = [point(xy, state["split"]) for xy in state["target_xy"]]
        target_values = state["target_outcomes"]
        target_sigma = state["future_sigma"][12:]
        timestamp = state["last_timestamp"]
    targets = [
        Measurement(
            sensor_id=f"target-{i}",
            timestamp=timestamp,
            pm25_ug_m3=float(value),
            uncertainty_ug_m3=float(s),
            origin="synthetic",
            **p,
        )
        for i, (p, value, s) in enumerate(
            zip(target_points, target_values, target_sigma)
        )
    ]
    baseline = fit(inv, diagnostics=False)
    prior = score_prediction(baseline, targets, target_values)
    rows = []
    for method, selected in locked:
        updated = inv.model_copy(deep=True)
        cost = 0
        for id in selected:
            site = next(s for s in inv.sites if s.id == id)
            j = int(id[1:])
            cost += site.cost
            updated.measurements.append(
                Measurement(
                    sensor_id="followup-" + id,
                    timestamp=timestamp,
                    pm25_ug_m3=float(outcomes[j]),
                    uncertainty_ug_m3=float(sigma[j]),
                    origin="synthetic",
                    latitude=site.latitude,
                    longitude=site.longitude,
                )
            )
        assert (
            cost <= inv.settings.budget + 1e-9
            and len(selected) <= inv.settings.equipment_limit
        )
        row = {
            "family": state["family"],
            "seed": state["seed"],
            "method": method,
            "site_ids": selected,
            "cost": cost,
            "equipment": len(selected),
            "locked_plan_sha256": locked_hash,
            "prior_prediction": prior,
        }
        try:
            fitted = fit(updated, diagnostics=False)
            row.update(
                status="fitted",
                prediction=score_prediction(fitted, targets, target_values),
                **source_metrics(fitted, state),
            )
        except Exception as exc:
            row.update(status="crash", reason=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    return rows


def distribution(values):
    values = [float(v) for v in values if v is not None]
    return (
        None
        if not values
        else {
            "n": len(values),
            "mean": float(np.mean(values)),
            "min": min(values),
            "p10": float(np.quantile(values, 0.1)),
            "median": float(np.median(values)),
            "p90": float(np.quantile(values, 0.9)),
            "max": max(values),
        }
    )


def wilson(k, n):
    if not n:
        return None
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0, float(center - half)), min(1, float(center + half))]


def summary(science, planning):
    conditions = []
    for family in FAMILIES:
        for model in ("baseline-0.3.0", MODEL_VERSION):
            rows = [r for r in science if r["family"] == family and r["model"] == model]
            if not rows:
                continue
            fitted = [r for r in rows if r["status"] == "fitted"]
            accepted = [r for r in fitted if r["accepted"]]
            row = {
                "family": family,
                "model": model,
                "generated": len(rows),
                "statuses": dict(Counter(r["status"] for r in rows)),
                "accepted": len(accepted),
                "accepted_region_misses": sum(
                    r["source_present"] and not r["region90_covered"] for r in accepted
                ),
            }
            for key in (
                "map_error_m",
                "mean_error_m",
                "prior_centroid_error_m",
                "region90_area_fraction",
                "region90_area_m2",
                "source_probability",
                "source_brier",
                "wall_ms",
            ):
                row[key] = distribution([r.get(key) for r in fitted])
            for key in (
                "region90_covered",
                "source_miss",
                "false_source_alarm",
                "narrow_wrong_region",
                "sharp_wrong_region",
                "warning",
            ):
                eligible = [
                    r
                    for r in fitted
                    if r.get(key) is not None
                    and (key != "source_miss" or r["source_present"])
                    and (key != "false_source_alarm" or not r["source_present"])
                ]
                k = sum(bool(r[key]) for r in eligible)
                n = len(eligible)
                row[key] = {"count": k, "n": n, "wilson95": wilson(k, n)}
            for key in (
                "rmse_ug_m3",
                "nlpd",
                "interval90_coverage",
                "interval90_width",
            ):
                row["prediction_" + key] = distribution(
                    [r["prediction"][key] for r in fitted if "prediction" in r]
                )
            conditions.append(row)
    paired = []
    rng = np.random.default_rng(90211)
    for family in sorted(set(r["family"] for r in planning)):
        for method in (
            "prediction_risk",
            "information",
            "spread",
            "wind",
            "baseline_0.3_planner",
        ):
            rows = [
                r
                for r in planning
                if r["family"] == family
                and r["method"] == method
                and r["status"] == "fitted"
            ]
            delta = []
            for r in rows:
                random = [
                    x["prediction"]["rmse_ug_m3"]
                    for x in planning
                    if x["family"] == family
                    and x["seed"] == r["seed"]
                    and x["method"].startswith("random-")
                    and x["status"] == "fitted"
                ]
                assert len(random) == 20
                delta.append(float(np.mean(random)) - r["prediction"]["rmse_ug_m3"])
            if not delta:
                continue
            x = np.array(delta)
            boot = x[rng.integers(0, len(x), (5000, len(x)))].mean(axis=1)
            paired.append(
                {
                    "family": family,
                    "method": method,
                    "worlds": len(x),
                    "rmse_advantage_vs_random20": distribution(x),
                    "mean_advantage_bootstrap95": np.quantile(
                        boot, [0.025, 0.975]
                    ).tolist(),
                    "worse_count": int(np.sum(x < 0)),
                    "worse_wilson95": wilson(int(np.sum(x < 0)), len(x)),
                    "posterior_rmse": distribution(
                        [r["prediction"]["rmse_ug_m3"] for r in rows]
                    ),
                    "mean_cost": float(np.mean([r["cost"] for r in rows])),
                }
            )
    return {
        "model": MODEL_VERSION,
        "science_results": len(science),
        "followup_results": len(planning),
        "crashes": sum(r["status"] == "crash" for r in science + planning),
        "conditions": conditions,
        "planner": paired,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split", choices=SPLITS, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit-seeds", type=int)
    p.add_argument("--skip-planner", action="store_true")
    p.add_argument("--planner-seeds", type=int, default=None)
    args = p.parse_args()
    if args.split == "final" and (args.limit_seeds or args.planner_seeds is not None):
        p.error("Final experiments cannot be partial")
    if args.out.exists() and any(args.out.iterdir()):
        p.error("Use a new output directory")
    args.out.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    seeds = list(SPLITS[args.split])
    seeds = seeds[: args.limit_seeds] if args.limit_seeds else seeds
    planner_count = (
        12
        if args.split == "final"
        else (args.planner_seeds if args.planner_seeds is not None else 4)
    )
    metadata = {
        "protocol": "UW-RESEARCH-2026-02",
        "model": MODEL_VERSION,
        "split": args.split,
        "seeds": seeds,
        "planner_seed_count": planner_count,
        "planner_skipped": args.skip_planner,
        "command": sys.argv,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
        "configuration": CONFIG,
        "source_hashes_before": before,
    }
    write(args.out / "metadata.json", metadata)
    start = time.perf_counter()
    science = []
    planning = []
    truth = []
    for family in FAMILIES:
        for j, seed in enumerate(seeds):
            inv, state = world(family, seed, args.split)
            truth.append(state)
            science.append(evaluate(inv, state))
            science.append(evaluate(inv, state, old=True))
            if (
                not args.skip_planner
                and j < planner_count
                and family
                in (
                    "single_window_original",
                    "informative_campaign",
                    "weak_campaign",
                    "biased_met_campaign",
                )
            ):
                try:
                    planning.extend(followup(inv, state))
                except Exception as exc:
                    planning.append(
                        {
                            "family": family,
                            "seed": seed,
                            "method": "all",
                            "status": "crash",
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
        write(args.out / "science.json", science)
        write(args.out / "followup.json", planning)
        write(args.out / "truth.json", truth)
        print(
            f"{family}: {len(seeds)} seed blocks; {len(science)} model outcomes; {len(planning)} followups",
            flush=True,
        )
    result = summary(science, planning)
    result["wall_seconds"] = time.perf_counter() - start
    after = source_hashes()
    metadata.update(source_hashes_after=after, source_hashes_unchanged=before == after)
    write(args.out / "summary.json", result)
    write(args.out / "metadata.json", metadata)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "science_results",
                    "followup_results",
                    "crashes",
                    "wall_seconds",
                )
            }
        ),
        flush=True,
    )
    if result["crashes"] or before != after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
