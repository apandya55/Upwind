"""Derive every weather-repair table from retained raw observations/results."""

import hashlib
import json
from pathlib import Path
import numpy as np
from upwind.validation.weather_bias import summary, write, MODEL_VERSION
from upwind.validation.research.run import distribution

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/weather-bias"


def jsonlines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def aggregate(prefix):
    science = []
    planning = []
    metadata = []
    for folder in sorted(BASE.glob(prefix + "-part*")):
        if not (folder / "completion.json").exists():
            raise ValueError("Incomplete run: " + str(folder))
        science += jsonlines(folder / "science.jsonl")
        if (folder / "planning.jsonl").exists():
            planning += jsonlines(folder / "planning.jsonl")
        metadata.append(
            dict(
                folder=str(folder.relative_to(ROOT)),
                metadata=json.loads((folder / "metadata.json").read_text()),
                completion=json.loads((folder / "completion.json").read_text()),
            )
        )
    keys = [(r["family"], r["seed"], r["model"]) for r in science]
    assert len(keys) == len(set(keys))
    if prefix == "final":
        assert len(science) == 32 * 14 * 2 and len(planning) == 8 * 3 * 15
        assert all(m["completion"]["source_unchanged"] for m in metadata)
        assert (
            len(
                {
                    json.dumps(m["metadata"]["source_hashes_before"], sort_keys=True)
                    for m in metadata
                }
            )
            == 1
        )
    result = summary(science, planning)
    write(BASE / (prefix + "-summary.json"), result)
    write(BASE / (prefix + "-run-records.json"), metadata)
    return science, planning, result


def pct(k, n):
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else "0/0 (undefined)"


def number(d, key="median"):
    return "—" if d is None else f"{d[key]:.1f}"


def planner_comparisons(planning):
    result = []
    rng = np.random.default_rng(90311)
    primary_intervals = {
        (r["family"], r["method"]): r["paired_bootstrap95"]
        for r in summary([], planning)["planning"]
    }
    families = sorted({r["family"] for r in planning})
    for family in families:
        for method in ["prediction_risk", "information"]:
            for baseline in ["random_mean", "spread", "wind", "baseline_0.4_planner"]:
                deltas = []
                loc = []
                cov = []
                area = []
                seeds = sorted({r["seed"] for r in planning if r["family"] == family})
                for seed in seeds:
                    rows = [
                        r
                        for r in planning
                        if r["family"] == family
                        and r["seed"] == seed
                        and r["status"] == "fitted"
                    ]
                    m = next((r for r in rows if r["method"] == method), None)
                    b = [
                        r
                        for r in rows
                        if (
                            r["method"].startswith("random-")
                            if baseline == "random_mean"
                            else r["method"] == baseline
                        )
                    ]
                    if not m or not b:
                        continue
                    deltas.append(
                        float(
                            np.mean([r["prediction"]["rmse_ug_m3"] for r in b])
                            - m["prediction"]["rmse_ug_m3"]
                        )
                    )
                    loc.append(
                        float(np.mean([r["map_error_m"] for r in b]) - m["map_error_m"])
                    )
                    cov.append(
                        float(
                            np.mean([r["region90_covered"] for r in b])
                            - m["region90_covered"]
                        )
                    )
                    area.append(
                        float(
                            np.mean([r["region90_area_fraction"] for r in b])
                            - m["region90_area_fraction"]
                        )
                    )
                if deltas:
                    bootstrap = np.mean(
                        rng.choice(deltas, size=(5000, len(deltas)), replace=True),
                        axis=1,
                    )
                    result.append(
                        dict(
                            family=family,
                            method=method,
                            baseline=baseline,
                            n=len(deltas),
                            prediction_advantage=distribution(deltas),
                            bootstrap95=primary_intervals[(family, method)]
                            if baseline == "random_mean"
                            else np.quantile(bootstrap, [0.025, 0.975]).tolist(),
                            prediction_losses=sum(d < 0 for d in deltas),
                            worst_prediction_loss=max(0, -min(deltas)),
                            localization_advantage=distribution(loc),
                            coverage_difference=distribution(cov),
                            area_difference=distribution(area),
                        )
                    )
    return result


def reliability_document(result):
    def rate(value):
        k, n = value["count"], value["n"]
        ci = value["wilson95"]
        return (
            f"{k}/{n}; undefined"
            if not n
            else f"{k}/{n}; {100 * k / n:.1f}% [{100 * ci[0]:.1f},{100 * ci[1]:.1f}]"
        )

    lines = [
        "# Acceptance, uncertainty and failure distributions",
        "",
        "Fresh final32worlds/condition. All rates include counts and Wilson95% intervals. Reused seeds across conditions are not independent campaigns. Accepted=source weight≥.9, region<half domain, no predictive or comparison mismatch. Abstained=fit but not accepted; refusals are separate. Wrong means the primary simulated source is outside the conditional region. A covered region can still have a distant MAP. Background-only has no geographic truth; source-family false alarms are separate.",
        "",
        "| Condition | Model | Acceptance/all generated [95%] | Wrong/accepted [95%] | Wrong/generated [95%] | Coverage/fitted [95%] |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["conditions"]:
        lines.append(
            f"|{r['family']}|{r['model']}|{rate(r['acceptance_rate'])}|{rate(r['wrong_given_accepted'])}|{rate(r['wrong_per_generated'])}|{rate(r['all']['region90_covered'])}|"
        )
    lines += [
        "",
        "## Diagnostic false alarms and missed failures",
        "",
        "The table records diagnostic mismatch screens, separate from the generic unknown-weather notice. No warning does not verify weather. Nominal characterized rows measure false warnings under compatible synthetic conditions. Unwarned geographic misses count covered=false even among abstentions. Unknown-direction/speed/clock/spatial errors can remain undetected; uncertainty integration is not a detector of physical bias. No false-positive/negative field calibration follows.",
        "",
        "| Condition | Model | Predictive warning [95%] | Comparison warning [95%] | Unwarned region misses | Source presence miss [95%] | False source alarm [95%] |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in result["conditions"]:
        a = r["all"]
        lines.append(
            f"|{r['family']}|{r['model']}|{rate(a['warning'])}|{rate(a['weather_warning'])}|{r['unwarned_wrong_regions']}|{rate(a['source_miss'])}|{rate(a['false_source_alarm'])}|"
        )
    lines += [
        "",
        "## All, accepted and rejected distributions",
        "",
        "Each error cell is p10 / median / p90 / maximum in metres. Area cells give mean and p10 / median / p90 / maximum as percentage of supported domain. Refusals have no fitted error/area and remain in generated rates above. Conditional-mean error and no-data centroid comparisons are retained in final-summary.json along with source Brier and runtime.",
        "",
        "| Condition | Model | Group (n) | MAP error m | Conditional mean error m | Region area % |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["conditions"]:
        for group in ["all", "accepted", "rejected"]:
            a = r[group]
            m = a["map_error_m"]
            mean = a["mean_error_m"]
            area = a["region90_area_fraction"]
            fmt = (
                lambda x: "—"
                if not x
                else " / ".join(f"{x[k]:.1f}" for k in ["p10", "median", "p90", "max"])
            )
            astr = (
                "—"
                if not area
                else f"mean {100 * area['mean']:.1f}; "
                + " / ".join(
                    f"{100 * area[k]:.1f}" for k in ["p10", "median", "p90", "max"]
                )
            )
            lines.append(
                f"|{r['family']}|{r['model']}|{group} ({0 if not area else area['n']})|{fmt(m)}|{fmt(mean)}|{astr}|"
            )
    (ROOT / "docs/WEATHER_BIAS_ACCEPTANCE.md").write_text("\n".join(lines) + "\n")


def main():
    science, planning, result = aggregate("final")
    cal, _, cal_summary = aggregate("calibration")
    regression = []
    for folder in sorted(BASE.glob("regression-part*")):
        regression += jsonlines(folder / "science.jsonl")
    assert len(regression) == 80
    old = json.loads((BASE / "reproduced/all40.json").read_text())
    old = {r["seed"]: r for r in old}
    original = [r for r in regression if r["family"] == "biased_met_campaign"]
    useful = [r for r in regression if r["family"] == "informative_campaign"]
    before_after = [
        dict(
            seed=r["seed"],
            before={
                k: old[r["seed"]][k]
                for k in (
                    "accepted",
                    "region90_covered",
                    "region90_area_fraction",
                    "map_error_m",
                )
            },
            after=r,
        )
        for r in original
    ]
    write(BASE / "original40-before-after.json", before_after)
    comparisons = planner_comparisons(planning)
    write(BASE / "planner-paired-comparisons.json", comparisons)
    reliability_document(result)
    lines = [
        "# Weather-bias repair results",
        "",
        f"Model **{MODEL_VERSION}**, protocol **UW-WEATHER-2026-03**. Synthetic research evidence only. The repair changes the error/usefulness tradeoff; it does not establish field reliability or universal weather-error detection.",
        "",
        "## Original failures: development-used regression",
        "",
        "| Seed | Old accepted/covered | New accepted/covered | MAP error old→new (m) | Region area old→new (% domain) |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(before_after, key=lambda x: x["seed"]):
        if not r["before"]["accepted"]:
            continue
        a = r["before"]
        b = r["after"]
        lines.append(
            f"|{r['seed']}|{a['accepted']}/{a['region90_covered']}|{b.get('accepted')}/{b.get('region90_covered')}|{a['map_error_m']:.1f}→{b.get('map_error_m', float('nan')):.1f}|{100 * a['region90_area_fraction']:.1f}→{100 * b.get('region90_area_fraction', float('nan')):.1f}|"
        )
    for title, rows in [
        ("All40 original biased cases", original),
        ("Previously supported40 campaigns", useful),
    ]:
        fitted = [r for r in rows if r["status"] == "fitted"]
        accepted = [r for r in fitted if r["accepted"]]
        wrong = sum(r["source_present"] and not r["region90_covered"] for r in accepted)
        lines += [
            "",
            f"{title}: {len(fitted)}/{len(rows)} fitted; accepted {len(accepted)}, wrong {pct(wrong, len(accepted))} of accepted and {pct(wrong, len(rows))} of generated; coverage {sum(r['region90_covered'] for r in fitted)}/{len(fitted)}. MAP median/p90 {np.median([r['map_error_m'] for r in fitted]):.1f}/{np.quantile([r['map_error_m'] for r in fitted], 0.9):.1f}m; mean region area {100 * np.mean([r['region90_area_fraction'] for r in fitted]):.1f}% domain.",
        ]
    lines += [
        "",
        "## Calibration and frozen decision",
        "",
        f"{len(cal) // 2} condition-worlds across16 seed blocks, {len(cal)} old/new outcomes. No numerical prior, threshold or acceptance transform was fitted. The predeclared conditional support rule was retained. Calibration already showed unresolved clock, spatial-wind, correlated-error and transport failures; final evaluation is a challenge of that frozen rule, not a claim these mechanisms were solved.",
        "",
        "| Condition | Old accepted / wrong | New accepted / wrong | New coverage (fitted) |",
        "|---|---|---|---|",
    ]
    for new in [
        r for r in cal_summary["conditions"] if not r["model"].startswith("baseline")
    ]:
        oldcal = next(
            r
            for r in cal_summary["conditions"]
            if r["family"] == new["family"] and r["model"].startswith("baseline")
        )
        cov = new["all"]["region90_covered"]
        lines.append(
            f"|{new['family']}|{oldcal['accepted_count']} / {oldcal['accepted_wrong']}|{new['accepted_count']} / {new['accepted_wrong']}|{cov['count']}/{cov['n']}|"
        )
    lines += [
        "",
        "After calibration, output-only changes list the actual comparison source/upstream/time/provenance used and correct generic mismatch wording to include weather checks. Two fixed calibration cases (with/without references) reproduce all numeric metrics and diagnostic checks exactly. No inference, planner, covariance, prior or rule changed. Exact identifiers are in [final-source-freeze.json](../evaluations/weather-bias/final-source-freeze.json); SHA256 source/configuration manifests identify the exact evaluated scientific source independently of later reporting and Git publication.",
    ]
    lines += [
        "",
        "## Fresh final holdout",
        "",
        f"{len(science) // 2} condition-worlds across32 paired seed blocks; {len(science)} old/new outcomes, {len(planning)} actual follow-up refits. Each condition has32 generated worlds. Conditions reuse seeds; do not pool them as independent campaigns. Final layouts, bias magnitude bands/signs, clock-lag range and nonlinear spatial/time weather mismatch differ from development/calibration. All frozen hashes match before/after every final shard. Refusals remain in generated denominators.",
        "",
        "| Condition | Model | Fit/refused/crash | Accepted | Wrong/accepted | Wrong/generated | Coverage (fitted) | MAP median/p90/max m | Area all/accepted % |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in result["conditions"]:
        all = r["all"]
        yes = r["accepted"]
        st = r["statuses"]
        cov = all["region90_covered"]
        err = all["map_error_m"]
        a = all["region90_area_fraction"]
        ya = yes["region90_area_fraction"]
        lines.append(
            f"|{r['family']}|{'0.4' if r['model'].startswith('baseline') else '0.5'}|{st.get('fitted', 0)}/{st.get('refused', 0)}/{st.get('crash', 0)}|{r['accepted_count']}|{pct(r['accepted_wrong'], r['accepted_count'])}|{pct(r['accepted_wrong'], r['generated'])}|{cov['count']}/{cov['n']}|{number(err)}/{number(err, 'p90')}/{number(err, 'max')}|{number(a, 'mean') if a is None else f'{100 * a["mean"]:.1f}'}/{number(ya, 'mean') if ya is None else f'{100 * ya["mean"]:.1f}'}|"
        )
    lines += [
        "",
        "[All/accepted/rejected distributions and confidence intervals](WEATHER_BIAS_ACCEPTANCE.md) include p10/median/p90/max and mean; geographic area in m²/fraction, conditional mass, source Brier, warning/false-alarm/miss counts, Wilson95% intervals and runtime are in [final-summary.json](../evaluations/weather-bias/final-summary.json). A zero observed error rate has a nonzero upper interval bound;0/0 is undefined. Nominal90% conditional regions are not calibrated coverage. Background-only has no location truth; false source alarms are reported separately.",
        "",
        "## Planner outcomes",
        "",
        "All choices were locked before candidate/target outcomes were revealed. Each plan uses at most two permitted pollution instruments, costs≤250 units, and the same recorded-time weather/data. Ten random policies per world form a seed-paired comparator. All follow-up inversions use0.5 so the0.4 planner comparison isolates site choice. Existing reference readings are already observed inputs; no new weather instrument is given for free.0.4 does not support the new paired-reference conditioning, an explicitly labeled capability difference.",
        "",
        "| Condition | Policy | Comparator | RMSE advantage mean [95% bootstrap] µg/m³ | Losses | Worst loss | MAP advantage mean m |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in comparisons:
        ci = r["bootstrap95"]
        lines.append(
            f"|{r['family']}|{r['method']}|{r['baseline']}|{r['prediction_advantage']['mean']:.3f} [{ci[0]:.3f},{ci[1]:.3f}]|{r['prediction_losses']}/{r['n']}|{r['worst_prediction_loss']:.3f}|{r['localization_advantage']['mean']:.1f}|"
        )
    lines += [
        "",
        "### Actual resources used",
        "",
        "Caps are equal; policies may choose fewer instruments or leave budget unused. This is a policy outcome, not hidden free data. Costs are synthetic units, not real deployment quotes.",
        "",
        "| Policy | Plans | Mean cost (min–max) | One / two instruments |",
        "|---|---|---|---|",
    ]
    for method in [
        "prediction_risk",
        "information",
        "baseline_0.4_planner",
        "spread",
        "wind",
        "random",
    ]:
        group = [
            r
            for r in planning
            if (
                r["method"].startswith("random-")
                if method == "random"
                else r["method"] == method
            )
        ]
        costs = [r["cost"] for r in group]
        lines.append(
            f"|{method}|{len(group)}|{np.mean(costs):.1f} ({min(costs):.0f}–{max(costs):.0f})|{sum(r['equipment'] == 1 for r in group)} / {sum(r['equipment'] == 2 for r in group)}|"
        )
    supplement = json.loads((BASE / "reference-control/results.json").read_text())
    assert (
        len(supplement) == 8
        and json.loads((BASE / "reference-control/completion.json").read_text())[
            "source_unchanged"
        ]
    )
    lines += [
        "",
        "### Supplementary control: old model uses observed reference weather",
        "",
        "The primary legacy adapter cannot interpret comparison fields and retains primary station data. To separate that capability difference from denying available observations to the old model, an additional control feeds qualified observed reference readings directly into0.4. It was declared after the primary freeze, before inspecting planner outcomes; it changes no production/evaluation rule. It uses noisy observed readings, never true weather. See [supplement protocol](WEATHER_BIAS_REFERENCE_CONTROL.md) and [raw results](../evaluations/weather-bias/reference-control/results.json). Eight worlds; equal250cost/equipment2 caps, actual spending may differ. All downstream fits still use0.5.",
        "",
        "| Comparator against0.4 reference-data planner | Mean RMSE advantage µg/m³ | Losses /8 | Mean MAP advantage m |",
        "|---|---|---|---|",
    ]
    controls = []
    for method in [
        "prediction_risk",
        "information",
        "baseline_0.4_planner",
        "spread",
        "wind",
    ]:
        delta = []
        loc = []
        for row in supplement:
            other = next(
                r
                for r in planning
                if r["family"] == "direction_characterized"
                and r["seed"] == row["seed"]
                and r["method"] == method
            )
            delta.append(
                row["prediction"]["rmse_ug_m3"] - other["prediction"]["rmse_ug_m3"]
            )
            loc.append(row["map_error_m"] - other["map_error_m"])
        controls.append(
            dict(
                method=method,
                rmse_advantage=distribution(delta),
                losses=sum(d < 0 for d in delta),
                map_advantage=distribution(loc),
            )
        )
        lines.append(
            f"|{method}|{np.mean(delta):.3f}|{sum(d < 0 for d in delta)}/8|{np.mean(loc):.1f}|"
        )
    prior = [r["legacy_reference_inference"] for r in supplement]
    lines += [
        "",
        f"Reference-only0.4 inference covers {sum(r['region90_covered'] for r in prior)}/8 sources; MAP median {np.median([r['map_error_m'] for r in prior]):.1f}m, mean area {100 * np.mean([r['region90_area_fraction'] for r in prior]):.1f}% domain. This small control prevents attributing all comparison-enabled improvements to new inversion logic; it is not an independent field validation.",
    ]
    write(BASE / "reference-control/comparisons.json", controls)
    lines += [
        "",
        "Intervals resample paired worlds5000times with RNG90311; eight worlds/condition give limited precision. Prediction improvement cannot establish localization improvement. Full per-plan errors, regions, costs, RMSE/density/interval scores and lock hashes remain in each final shard’s planning.jsonl. Paired coverage/area differences are in planner-paired-comparisons.json.",
        "",
        "## Sensitivity, engineering and remaining limits",
        "",
        "Development profiles and48 perturbation/oracle fits are in [sensitivity](../evaluations/weather-bias/sensitivity). Correct-weather oracles are diagnostic only. Several layouts retain broad or displaced alternatives even with true weather; same-wind repeats mostly leave≥75% area. Prior15° can miss a source retained by20°/30°, demonstrating prior dependence. No prior was tuned against final data.1° angular refinement, a requested10m cell target (the24-per-axis cap gives about15.4×18.3m cells here) and±5° coherent shifts are reported separately; stable arithmetic is not validated physics.",
        "",
        "The protocol, root cause, equations, exact compatibility contract and commands are in [WEATHER_BIAS_IMPLEMENTATION.md](WEATHER_BIAS_IMPLEMENTATION.md). Old source and all failed preflight probes remain retained. The first resource probes exposed two temporary-array memory failures; exact bounded column calculation and algebraic reduction repaired them before the freeze. Resource results show retained shape, fitted-row limits, refusals and actual memory/time;10,000 loaded readings do not imply10,000 inverted rows.",
        "",
        "Independent reference uncertainty/provenance claims remain user declared. A shared hidden reference/primary bias, wrong clock, spatially unrepresentative wind, unsupported transport, multiple sources, source outside the domain or prior tails can still defeat localization. Unknown weather is explicitly unknown. No universal “weather fixed” or organizational attribution readiness claim follows. Official NOAA measured-tracer requests failed proxy CONNECT403 again; [exact attempts](../evaluations/weather-bias/external-retry.json). Field validation remains unperformed.",
    ]
    resources = json.loads((BASE / "resources-release/results.json").read_text())
    lines += [
        "",
        "### Engineering verification on the frozen release",
        "",
        "115 pytest checks and eight Chromium workflows passed; the frontend production build/typecheck passed. Logs: pytest-release.log, playwright-final.log and frontend-build-complete.log under evaluations/weather-bias. These verify software behavior, not physical accuracy. The API stress probe retained all36 acknowledged writes among64 simultaneous requests (28 explicit429 responses), rejected malformed/oversized requests and recovered;500 CSV fuzz cases produced no unhandled error. See api-engineering.json.",
        "",
        "Resource children each had60seconds and2GiB limits. Every row loaded10,000 readings plus10,000 weather rows,100sites and25anchors. Time/memory are this machine's observations, not a shared-service guarantee.",
        "",
        "| Campaign | Compared weather | Fit limit / fitted | Outcome | Seconds | Peak MiB |",
        "|---|---|---|---|---|---|",
    ]
    for row in resources:
        lines.append(
            f"|{row['campaign']}|{row['characterized']}|{row['limit']} / {row.get('rows_fitted', '—')}|{row.get('reason') or row['analysis_status']}|{row['seconds']:.2f}|{row['peak_rss_mib']:.1f}|"
        )
    lines += [
        "",
        "The unknown-weather512-row campaign explicitly refuses excessive numerical workload;128-row campaigns cannot retain240sensor/window groups. These are retained capability limits. All child source hashes match the final freeze. Full records: [resources-release](../evaluations/weather-bias/resources-release/results.json).",
        "",
        "[Standalone tradeoff figure](../evaluations/weather-bias/figures/weather-tradeoffs.png) ([PDF](../evaluations/weather-bias/figures/weather-tradeoffs.pdf), [SVG](../evaluations/weather-bias/figures/weather-tradeoffs.svg)) shows coverage, acceptance and accepted errors together, with Wilson intervals. Broad regions can restore coverage while reducing usefulness; acceptance alone is not success.",
    ]
    (ROOT / "docs/WEATHER_BIAS_RESULTS.md").write_text("\n".join(lines) + "\n")
    write(
        BASE / "report-manifest.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                ROOT / "docs/WEATHER_BIAS_RESULTS.md",
                BASE / "final-summary.json",
                BASE / "calibration-summary.json",
                BASE / "original40-before-after.json",
                BASE / "planner-paired-comparisons.json",
                ROOT / "docs/WEATHER_BIAS_ACCEPTANCE.md",
            ]
        },
    )


if __name__ == "__main__":
    main()
