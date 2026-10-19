"""Reproducible summary of complete UW-STRESS-2026-04/04C evidence."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from upwind.models import Investigation
from upwind.quality import measurement_quality
from upwind.validation.research.cases import reveal
from upwind.validation.research.run import distribution, wilson
from severe_stress import FAMILIES, SEEDS, fingerprints

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/severe-stress"


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def validate_current_source(frozen):
    actual = fingerprints()
    if actual == frozen["source_hashes"]:
        return None
    # The only permitted post-campaign difference is a separately verified
    # request-boundary repair. Numerical/evaluator/protocol changes still fail.
    guard = read(BASE / "api-hardening.json")
    changed = {
        name
        for name in set(actual) | set(frozen["source_hashes"])
        if actual.get(name) != frozen["source_hashes"].get(name)
    }
    assert changed == {"backend/upwind/api.py"}, changed
    assert guard["applied_after_frozen_runs_and_resources_complete"]
    assert guard["before_sha256"] == frozen["source_hashes"]["backend/upwind/api.py"]
    assert guard["after_sha256"] == actual["backend/upwind/api.py"]
    assert (
        hashlib.sha256((BASE / "api-hardening-source/api.py").read_bytes()).hexdigest()
        == guard["after_sha256"]
    )
    return guard


def records(prefix, expected):
    rows = []
    freeze = read(BASE / "freeze.json")
    for index in range(4):
        folder = BASE / f"{prefix}-{index}"
        completion = read(folder / "completion.json")
        assert completion["source_unchanged"] and completion["configuration_unchanged"]
        assert (
            read(folder / "metadata.json")["source_hashes_before"]
            == freeze["source_hashes"]
        )
        if prefix == "nominal":
            assert completion["supplement_unchanged"]
        for line in (folder / "results.jsonl").read_text().splitlines():
            row = json.loads(line)
            row["input_path"] = str(
                (
                    folder
                    / (
                        f"input-{row['seed']}.json"
                        if prefix == "nominal"
                        else f"input-{row['family']}-{row['seed']}.json"
                    )
                ).relative_to(ROOT)
            )
            rows.append(row)
    assert len(rows) == expected
    assert len({(r["family"], r["seed"]) for r in rows}) == expected
    return rows


def rate(k, n):
    return {"count": int(k), "n": int(n), "wilson95": wilson(k, n)}


def summarize(rows):
    fitted = [r for r in rows if r["status"] == "fitted"]
    present = [r for r in fitted if r["source_present"]]
    accepted = [r for r in fitted if r["accepted"]]
    accepted_positive = [r for r in accepted if r["source_present"]]
    accepted_wrong = [r for r in accepted_positive if not r["region90_covered"]]
    background = [r for r in fitted if not r["source_present"]]
    scored = [
        r["prediction"]
        for r in fitted
        if r.get("prediction", {}).get("status") == "scored"
    ]
    return {
        "generated": len(rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "numeric_failures": sum(not r["numeric_ok"] for r in fitted),
        "acceptance": rate(len(accepted), len(rows)),
        "accepted_wrong_geography": rate(len(accepted_wrong), len(accepted_positive)),
        "accepted_wrong_per_generated": rate(len(accepted_wrong), len(rows)),
        "conditional_region_coverage": rate(
            sum(r["region90_covered"] for r in present), len(present)
        ),
        "predictive_warning": rate(sum(r["warning"] for r in fitted), len(fitted)),
        "weather_warning": rate(sum(r["weather_warning"] for r in fitted), len(fitted)),
        "unwarned_geographic_misses": rate(
            sum(
                not r["region90_covered"]
                and not r["warning"]
                and not r["weather_warning"]
                for r in present
            ),
            len(present),
        ),
        "source_misses": rate(sum(r["source_miss"] for r in present), len(present)),
        "background_source_false_alarm": rate(
            sum(r["false_source_alarm"] for r in background), len(background)
        ),
        "accepted_background_false_alarm": rate(
            sum(not r["source_present"] for r in accepted), len(background)
        ),
        "map_error_m": distribution([r["map_error_m"] for r in present]),
        "mean_error_m": distribution([r["mean_error_m"] for r in present]),
        "prior_centroid_error_m": distribution(
            [r["prior_centroid_error_m"] for r in present]
        ),
        "accepted_map_error_m": distribution(
            [r["map_error_m"] for r in accepted_positive]
        ),
        "region_area_fraction": distribution(
            [r["region90_area_fraction"] for r in fitted]
        ),
        "accepted_region_area_fraction": distribution(
            [r["region90_area_fraction"] for r in accepted]
        ),
        "region_area_m2": distribution([r["region90_area_m2"] for r in fitted]),
        "conditional_region_mass": distribution([r["region90_mass"] for r in fitted]),
        "source_brier": distribution([r["source_brier"] for r in fitted]),
        "analysis_wall_ms": distribution([r["analysis_wall_ms"] for r in fitted]),
        "scheduled_predictions": sum(r["prediction_scheduled"] for r in rows),
        "scored_predictions": len(scored),
        "prediction_crashes": sum(
            r.get("prediction", {}).get("status") == "crash" for r in rows
        ),
        "prediction_rmse_ug_m3": distribution([r["rmse_ug_m3"] for r in scored]),
        "prediction_nlpd": distribution([r["nlpd"] for r in scored]),
        "prediction_interval90_coverage": distribution(
            [r["interval90_coverage"] for r in scored]
        ),
        "prediction_interval90_width": distribution(
            [r["interval90_width"] for r in scored]
        ),
        "refusal_reasons": dict(
            Counter(r["reason"] for r in rows if r["status"] == "refused")
        ),
    }


def forecast_comparisons(rows):
    paired = []
    for row in rows:
        if row.get("prediction", {}).get("status") != "scored":
            continue
        raw = read(ROOT / row["input_path"])
        inv = Investigation.model_validate(raw["investigation"])
        truth = raw["private_evaluator_truth"]
        last = max(inv.study_windows, key=lambda window: window.end)
        usable, _ = measurement_quality(inv)
        readings = [
            m.pm25_ug_m3 for m in usable if last.start <= m.timestamp <= last.end
        ]
        if not readings:
            raise ValueError("No available-data comparator in a scored case")
        constant = float(np.mean(readings))
        reveal(truth)
        outcomes = np.asarray(truth["target_outcomes"])
        persistence_rmse = float(np.sqrt(np.mean((outcomes - constant) ** 2)))
        prior_rmse = float(np.sqrt(np.mean((outcomes - 10) ** 2)))
        paired.append(
            {
                "family": row["family"],
                "seed": row["seed"],
                "constant_from_available_data": constant,
                "model_rmse": row["prediction"]["rmse_ug_m3"],
                "last_period_mean_rmse": persistence_rmse,
                "prior10_rmse": prior_rmse,
            }
        )
    rng = np.random.default_rng(90311)
    comparisons = []
    for family in FAMILIES:
        group = [r for r in paired if r["family"] == family]
        if not group:
            continue
        for baseline in ["last_period_mean", "prior10"]:
            delta = np.array([r[baseline + "_rmse"] - r["model_rmse"] for r in group])
            draws = rng.integers(0, len(delta), (5000, len(delta)))
            comparisons.append(
                {
                    "family": family,
                    "comparator": baseline,
                    "worlds": len(group),
                    "mean_rmse_advantage_ug_m3": float(delta.mean()),
                    "paired_bootstrap95": np.quantile(
                        delta[draws].mean(axis=1), [0.025, 0.975]
                    ).tolist(),
                    "losses": int((delta < 0).sum()),
                    "worst_loss_ug_m3": float(max(0, -delta.min())),
                }
            )
    return paired, comparisons


def fraction(value):
    return f"{value['count']}/{value['n']}" if value["n"] else "0/0 (undefined)"


def interval(value):
    if not value["n"]:
        return "undefined"
    return f"{100 * value['wilson95'][0]:.1f}–{100 * value['wilson95'][1]:.1f}%"


def val(distribution, key="median", scale=1):
    return "—" if distribution is None else f"{scale * distribution[key]:.1f}"


def main():
    # Refuse partial runs before writing any derived report artifacts.
    for folder in ["engineering", "resources"]:
        read(BASE / folder / "completion.json")
    for filename, token in [
        ("pytest.log", "168 passed"),
        ("frontend-build.log", "built in"),
        ("playwright.log", "8 passed"),
    ]:
        assert token in (BASE / filename).read_text(), f"Incomplete check: {filename}"
    frozen = read(BASE / "freeze.json")
    api_guard = validate_current_source(frozen)
    if api_guard:
        assert "181 passed" in (BASE / "pytest-postfix.log").read_text()
    main_rows, nominal_rows = records("shard", 960), records("nominal", 480)
    assert {(r["seed"], r["family"]) for r in main_rows} == {
        (seed, family) for seed in SEEDS for family in FAMILIES
    }
    assert {r["seed"] for r in nominal_rows} == set(range(6400000, 6400480))
    conditions = [
        {"family": family, **summarize([r for r in main_rows if r["family"] == family])}
        for family in FAMILIES
    ]
    nominal = summarize(nominal_rows)
    error = nominal["accepted_wrong_geography"]
    criteria = {
        "median_map_le_50m": nominal["map_error_m"] is not None
        and nominal["map_error_m"]["median"] <= 50,
        "conditional_coverage_at_least_90_percent": nominal[
            "conditional_region_coverage"
        ]["n"]
        > 0
        and nominal["conditional_region_coverage"]["count"]
        / nominal["conditional_region_coverage"]["n"]
        >= 0.9,
        "zero_observed_accepted_geographic_errors": error["n"] > 0
        and error["count"] == 0,
        "accepted_error_wilson95_upper_at_most_5_percent": error["n"] > 0
        and error["wilson95"][1] <= 0.05,
    }
    paired, predictions = forecast_comparisons(main_rows)
    write(
        BASE / "summary.json",
        {
            "protocol": "UW-STRESS-2026-04/04C",
            "model": frozen["model"],
            "main": {"generated": len(main_rows), "conditions": conditions},
            "nominal_confirmation": nominal,
            "nominal_targets": criteria,
            "all_nominal_targets_pass": all(criteria.values()),
            "passive_prediction_comparisons": predictions,
            "scientific_source_unchanged_during_frozen_runs": True,
            "post_campaign_api_hardening": api_guard,
        },
    )
    write(BASE / "prediction-comparators.json", paired)
    failures = [
        {"cohort": name, **r}
        for name, rows in [("main", main_rows), ("nominal", nominal_rows)]
        for r in rows
        if r["status"] == "crash"
        or r.get("prediction", {}).get("status") == "crash"
        or r.get("numeric_ok") is False
        or r.get("accepted")
        and (not r["source_present"] or not r["region90_covered"])
    ]
    write(BASE / "failures.json", failures)
    target_labels = {
        "median_map_le_50m": "Median source-point error ≤50 m",
        "conditional_coverage_at_least_90_percent": "Conditional region coverage ≥90%",
        "zero_observed_accepted_geographic_errors": "No observed accepted-region misses",
        "accepted_error_wilson95_upper_at_most_5_percent": "Accepted-error Wilson95% upper bound ≤5%",
    }
    main_wrong = sum(
        r.get("accepted", False)
        and r.get("source_present", False)
        and not r.get("region90_covered", False)
        for r in main_rows
    )
    lines = [
        "# Severe stress results",
        "",
        "Model **plume-weather-0.5.0**, protocols **UW-STRESS-2026-04/04C**. Synthetic evidence only; no measured field accuracy or certification follows. Production source/configuration was unchanged throughout. The evaluated source and both protocols are retained with hashes. All preflight failures/refusals and every scheduled case remain visible.",
        "",
        f"The model {'passed all' if all(criteria.values()) else 'did not meet all'} predeclared nominal accuracy targets. The main mismatch campaign retained **{main_wrong} accepted geographic errors**. Software checks and the request-boundary repair are reported separately from those scientific failures.",
        "",
        "## Larger nominal confirmation: precision and reliability assessed separately",
        "",
        f"480 fixed fresh characterized-nominal worlds, with independent reference weather. Fitted/refused/crash: {nominal['statuses']}. Accepted {fraction(nominal['acceptance'])}; accepted geographic errors {fraction(error)}, Wilson95% interval {interval(error)}. Conditional region coverage {fraction(nominal['conditional_region_coverage'])}, interval {interval(nominal['conditional_region_coverage'])}.",
        "",
        f"MAP median/p90/max {val(nominal['map_error_m'])}/{val(nominal['map_error_m'], 'p90')}/{val(nominal['map_error_m'], 'max')}m. No-data source-domain-centroid median {val(nominal['prior_centroid_error_m'])}m. Accepted MAP median/p90 {val(nominal['accepted_map_error_m'])}/{val(nominal['accepted_map_error_m'], 'p90')}m. Mean conditional region area all/accepted {val(nominal['region_area_fraction'], 'mean', 100)}/{val(nominal['accepted_region_area_fraction'], 'mean', 100)}% domain. A covered region can still have a distant point estimate.",
        "",
        "| Predeclared nominal target | Outcome |",
        "|---|---|",
    ]
    lines += [
        f"|{target_labels[name]}|{'PASS' if passed else 'FAIL / not established'}|"
        for name, passed in criteria.items()
    ]
    lines += [
        "",
        "Passing a conditional error bound does not establish fine spatial precision or real-world accuracy. The full target set must be considered together. This cohort has favorable explicitly independent weather assumptions; hidden common bias and unsupported physics are challenged separately below.",
        "",
        "## Main stress matrix",
        "",
        "960 scheduled cases:48 fresh seed blocks×20conditions, continuously randomized monitor layouts and wind regimes. Seeds repeat across conditions; they are not960independent campaigns. Explicit refusals stay in generated denominators. All point/area statistics below describe fitted cases. Background-only has no geographic source truth.",
        "",
        "| Condition | Fit/refused/crash | Accepted | Wrong geography/accepted | Coverage/fitted source | MAP median/p90/max m | Area all/accepted % | Unwarned misses |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in conditions:
        counts = row["statuses"]
        lines.append(
            f"|{row['family']}|{counts.get('fitted', 0)}/{counts.get('refused', 0)}/{counts.get('crash', 0)}|{fraction(row['acceptance'])}|{fraction(row['accepted_wrong_geography'])}|{fraction(row['conditional_region_coverage'])}|{val(row['map_error_m'])}/{val(row['map_error_m'], 'p90')}/{val(row['map_error_m'], 'max')}|{val(row['region_area_fraction'], 'mean', 100)}/{val(row['accepted_region_area_fraction'], 'mean', 100)}|{fraction(row['unwarned_geographic_misses'])}|"
        )
    lines += [
        "",
        "### Warnings, presence errors and intervals",
        "",
        "| Condition | Accepted geography error95% interval | Coverage95% interval | Predictive / weather warnings | Missed sources | Background family false alarms / accepted false alarms |",
        "|---|---|---|---|---|---|",
    ]
    for row in conditions:
        lines.append(
            f"|{row['family']}|{interval(row['accepted_wrong_geography'])}|{interval(row['conditional_region_coverage'])}|{fraction(row['predictive_warning'])} / {fraction(row['weather_warning'])}|{fraction(row['source_misses'])}|{fraction(row['background_source_false_alarm'])} / {fraction(row['accepted_background_false_alarm'])}|"
        )
    lines += [
        "",
        "A warning-free fit is not a physical adequacy certificate. Hidden reference/primary bias deliberately violates an unverified independence claim; internal agreement cannot detect every shared error. The outside-domain case challenges a restricted source hypothesis family. Extreme-reading exclusion is recorded as a capability limit, not taken as evidence that a severe real event is impossible. Full distributions (including conditional mass, area, Brier, runtime and all denominators) are in [summary.json](../evaluations/severe-stress/summary.json). Every accepted error and software failure is retained in [failures.json](../evaluations/severe-stress/failures.json).",
        "",
        "## Passive unseen-sensor predictions",
        "",
        "240 scheduled worlds in the first12seed blocks per condition; unsupported-weather refusals remain unavailable. Twelve target readings within a world are correlated. Intervals below resample paired worlds 5,000 times, RNG 90311; positive advantage means comparator RMSE minus model RMSE. These are retrospective predictions at a recorded time, not forecasts or measurement-placement benefits.",
        "",
        "| Condition | Scored / scheduled | RMSE mean µg/m³ | Mean90% interval coverage / width | RMSE advantage vs last-period spatial mean [95%] | Losses |",
        "|---|---|---|---|---|---|",
    ]
    for row in conditions:
        comparison = next(
            (
                r
                for r in predictions
                if r["family"] == row["family"]
                and r["comparator"] == "last_period_mean"
            ),
            None,
        )
        advantage = (
            "unavailable"
            if comparison is None
            else f"{comparison['mean_rmse_advantage_ug_m3']:.3f} [{comparison['paired_bootstrap95'][0]:.3f},{comparison['paired_bootstrap95'][1]:.3f}]"
        )
        losses = (
            "—"
            if comparison is None
            else f"{comparison['losses']}/{comparison['worlds']}"
        )
        lines.append(
            f"|{row['family']}|{row['scored_predictions']}/{row['scheduled_predictions']}|{val(row['prediction_rmse_ug_m3'], 'mean')}|{val(row['prediction_interval90_coverage'], 'mean', 100)}% / {val(row['prediction_interval90_width'], 'mean')}|{advantage}|{losses}|"
        )
    lines += [
        "",
        "The comparator uses only quality-reviewed available monitoring measurements in the last study period; it never uses target outcomes to choose its constant. A fixed prior-mean 10 µg/m³ comparator is also retained in JSON. Point-prediction RMSE, geographic accuracy and conditional interval coverage are different capabilities; do not transfer success between them.",
        "",
        "## Post-hoc diagnosis: a retained accepted error",
        "",
        "The first observed accepted error in the hidden-common-weather-bias condition (seed 6100001) was repeated unchanged, then diagnosed in two separate variants. This is post-hoc explanation, not a held-out improvement experiment or a production repair. Main inputs and source remain unchanged. The oracle variant subtracts only the evaluator-known injected common bias; that truth is unavailable to ordinary users and never enters the main campaign.",
        "",
        "| Variant | Accepted | Region covers truth | MAP error m | Region area % domain | Predictive / weather warning |",
        "|---|---|---|---|---|---|",
    ]
    diagnosis = BASE / "posthoc-common-bias-diagnosis"
    assert read(diagnosis / "completion.json")["source_unchanged"]
    for name in ["original", "references_removed", "oracle_common_bias_removed"]:
        row = read(diagnosis / (name + ".json"))
        lines.append(
            f"|{name}|{row.get('accepted')}|{row.get('region90_covered')}|{row.get('map_error_m', float('nan')):.1f}|{100 * row.get('region90_area_fraction', float('nan')):.1f}|{row.get('warning')} / {row.get('weather_warning')}|"
        )
    lines += [
        "",
        "Removing reference data alone is not guaranteed to recover a displaced source: source/strength/background can compensate for wrong wind, and a finite bias prior can prefer a wrong geographic explanation. Agreement between two instruments cannot reveal every shared hidden error. Even evaluator-corrected weather does not guarantee a precise point estimate. These failures must not be reclassified as solved by a software-test pass or by knowing the injected truth after evaluation.",
        "",
        "Nominal simulations use the compatible physical kernel with separately specified synthetic noise/strength distributions; they are not an exact full-model prior-predictive calibration or a measured-data validation. Several layouts are weakly informative, so region area and abstention remain essential.",
        "",
        "## Engineering and resource stress",
        "",
    ]
    numerical = read(BASE / "engineering/numerical.json")
    placement = read(BASE / "engineering/placement.json")
    fuzz = read(BASE / "engineering/csv-fuzz.json")
    api = read(BASE / "engineering/api-rounds.json")
    lines += [
        f"Numerical checks: {numerical['checks']:,}, failed groups {numerical['failed_groups']}. Geographic placement checks: {placement['checks']}, failures {len(placement['failures'])} across 200 instances,100 independent exhaustive tiny optima and all-method constraints. These reproduce/extend deterministic property sequences; they are not empirical accuracy samples.",
        "",
        f"Adversarial CSV cases: {fuzz['cases']:,}; {fuzz['counts']}; unexpected failures {len(fuzz['unexpected_failures'])}. Original raw CSV and accepted/invalid accounting are checked. Explicit parser/schema refusals are correct outcomes. Four isolated API rounds total 256 write requests/32 clients per round: {sum(r['acknowledged_writes'] for r in api)}acknowledged writes, all preserved={all(r['all_acknowledged_writes_preserved'] for r in api)}; all round checks passed={all(r['passed'] for r in api)}. The existing500 CSV fixtures repeat inside API rounds; they are not 2,000 new unique cases.",
        "",
    ]
    resources = read(BASE / "resources/results.json")
    lines += [
        "Each fresh resource child had 60s/2GiB, after the scientific workers completed. Shapes loaded 10,000 concentrations + 10,000 weather rows, 100 sites and 25 anchors; fit limits are 128/512, not 10,000 inverted rows.",
        "",
        "| Campaign / compared weather | Limit / fitted | Status | Seconds | Peak MiB |",
        "|---|---|---|---|---|",
    ]
    for row in resources:
        seconds = f"{row['seconds']:.2f}" if "seconds" in row else "—"
        memory = f"{row['peak_rss_mib']:.1f}" if "peak_rss_mib" in row else "—"
        lines.append(
            f"|{row['campaign']} / {row['characterized']}|{row['limit']} / {row.get('rows_fitted', '—')}|{row.get('reason') or row.get('analysis_status') or row['status']}|{seconds}|{memory}|"
        )
    if api_guard:
        lines += [
            "",
            "### Request-boundary failure found and repaired after the frozen experiment",
            "",
            "An additional isolated JSON probe exposed a 500 response for 1200 nested levels and acceptance of nonstandard NaN metadata that was silently serialized as null. These failures were not caught by the earlier CSV/overload battery. Both original probes and the isolated prototype results are retained. After all scientific workers and resource probes completed, only backend/upwind/api.py was hardened: bounded-depth JSON, finite numbers and explicit 422 refusal before persistence. Valid finite JSON and quoted CSV text keep their previous semantics. No likelihood, prior, source-support rule, planner or generated outcome changed.",
            "",
            "The frozen-source suite passed 168 tests. The post-repair full suite passed 181 tests, including 13 new request-boundary regressions; eight Chromium workflows exercise the final API. The exact before/after API hashes and completion evidence are in [api-hardening.json](../evaluations/severe-stress/api-hardening.json). Historical weather-source verification uses `scripts/verify_weather_release.py --source evaluations/weather-bias/frozen-source`; the default current-tree check intentionally does not pretend the old API bytes are current.",
        ]
    lines += [
        "",
        "Actual test/build/browser outcomes are retained in pytest.log, frontend-build.log and playwright.log under evaluations/severe-stress. The automated release verifier checks their completion along with raw case counts, source/configuration hashes and artifacts. Initial workers shared CPU capacity; nominal workers were then paused/resumed to keep four active inversion workers. Their raw case/overall wall clocks include suspension and contention. See [scheduling.json](../evaluations/severe-stress/scheduling.json). Only the fresh unpaused resource children describe isolated timings; none is a shared-service SLA. Scheduling changed no input, model parameter or numerical algorithm.",
        "",
        "## Interpretation and reproduction",
        "",
        "This campaign can expose software or scientific failures; it cannot guarantee extreme field accuracy. The original organizational-attribution goal remains unvalidated without compatible independent measured data, documented physics and prospective outcomes. Primary data access remains an external prerequisite. No scientific thresholds, priors, warnings or failed-case inclusion were changed in response to these outcomes.",
        "",
        "[Main protocol](SEVERE_STRESS_PROTOCOL.md), [nominal supplement](STRESS_NOMINAL_CONFIRMATION.md), [reporting methods](STRESS_REPORTING_METHODS.md), [standalone figure](../evaluations/severe-stress/figures/stress-tradeoffs.png). Run `.venv/bin/python scripts/report_severe_stress.py` only after all runs complete; plot generation refuses existing output. Preserve previous artifacts on reproduction and choose a new run directory. All current seeds are now inspected and cannot serve as untouched tests for a repair.",
    ]
    (ROOT / "docs/SEVERE_STRESS_RESULTS.md").write_text("\n".join(lines) + "\n")
    write(
        BASE / "report-manifest.json",
        {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                ROOT / "docs/SEVERE_STRESS_RESULTS.md",
                BASE / "summary.json",
                BASE / "prediction-comparators.json",
                BASE / "failures.json",
                Path(__file__),
                ROOT / "docs/STRESS_REPORTING_METHODS.md",
            ]
        },
    )


if __name__ == "__main__":
    main()
