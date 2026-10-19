"""Generate descriptive tables from frozen research outputs, never refit a model."""

import hashlib, json, re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/research"
NEW = "plume-campaign-0.4.0"


def read(path):
    return json.loads(path.read_text())


def show(x, d=1):
    return "—" if x is None else f"{x:.{d}f}"


def rate(x):
    if not x["n"]:
        return "—"
    lo, hi = x["wilson95"]
    return f"{x['count']}/{x['n']} ({100 * lo:.0f}–{100 * hi:.0f}%)"


def dist(r, key, stat="median"):
    return None if not r.get(key) else r[key][stat]


def fraction(x):
    return show(None if x is None else 100 * x)


def block_bootstrap(values):
    a = np.array(values)
    rng = np.random.default_rng(90211)
    return np.quantile(
        a[rng.integers(0, len(a), (5000, len(a)))].mean(axis=1), [0.025, 0.975]
    ).tolist()


def table(headers, rows):
    return (
        "| "
        + " | ".join(headers)
        + " |\n|"
        + "|".join("---" for _ in headers)
        + "|\n"
        + "".join("| " + " | ".join(map(str, row)) + " |\n" for row in rows)
    )


def main():
    meta = read(BASE / "final/metadata.json")
    summary = read(BASE / "final/summary.json")
    science = read(BASE / "final/science.json")
    plans = read(BASE / "final/followup.json")
    assert (
        meta["source_hashes_unchanged"]
        and len(meta["seeds"]) == 40
        and summary["science_results"] == 960
        and summary["followup_results"] == 1200
    )
    assert (
        meta["source_hashes_before"]
        == read(BASE / "final-source-freeze.json")["source_hashes"]
    )
    rows = [r for r in summary["conditions"] if r["model"] == NEW]
    lookup = {r["family"]: r for r in rows}
    inf = lookup["informative_campaign"]
    ind = lookup["independent_transport"]
    orig = lookup["single_window_original"]
    report = [
        f"""# Research results and capability decision

Model **{NEW}**, protocol **UW-RESEARCH-2026-02**. Synthetic evidence only. The redesigned campaign engine materially improves localization in a specifically supported synthetic measurement design, and the prediction planner is tested on actual withheld outcomes. **It is not reliable enough for organizational source attribution, enforcement, compliance or allegations.** Changed release, biased meteorology and transport outside the assumed model can remain confidently wrong; the warning screen does not reliably protect those decisions.

The supported-control campaign has median MAP error **{show(dist(inf, "map_error_m"))}m** against a no-data centroid median **{show(dist(inf, "prior_centroid_error_m"))}m**, with **{inf["region90_covered"]["count"]}/40** conditional-region coverage and mean region **{fraction(dist(inf, "region90_area_fraction", "mean"))}%** of the unchanged search domain. Its fixed interpretive rule accepts **{inf["accepted"]}/40**, with **{inf["accepted_region_misses"]}** accepted primary-location region misses. These are40 held-out synthetic seed blocks under compatible transport, not a field accuracy guarantee.

The control's MAP error90th percentile is **{show(dist(inf, "map_error_m", "p90"))}m** (maximum **{show(dist(inf, "map_error_m", "max"))}m**); the median is not an accuracy bound. In the biased-weather challenge, **{lookup["biased_met_campaign"]["accepted_region_misses"]}/{lookup["biased_met_campaign"]["accepted"]} accepted regions miss** and no warning is raised. The new prediction planner does not consistently outperform random placement across conditions. These failures prevent a trusted attribution or general recommendation claim.

On the independent advection/transverse-diffusion challenge, coverage is **{ind["region90_covered"]["count"]}/40** and **{ind["accepted_region_misses"]}/{ind["accepted"]}** accepted regions miss. On the original low-information single-window population, mean region remains **{fraction(dist(orig, "region90_area_fraction", "mean"))}%**, with **{orig["accepted"]}/40** accepted. The new data intervention does not demonstrate that the old measurements suddenly identify sources.

## What changed and why

[Root-cause evidence](RESEARCH_ROOT_CAUSES.md), [equations/code/owner handover](RESEARCH_IMPLEMENTATION.md), [scientific meaning](SCIENCE.md) and [commands/provenance](RESEARCH_REPRODUCTION.md) describe the implemented system. Main changes: explicit separately steady campaign periods with shared fixed source/constant release; per-period backgrounds with persistent instrument bias; declared weather uncertainty/heights; four-node spatial integration; exact positive-strength predictive density/sampling; joint withheld-sensor/period contrasts; global free-nuisance profiles; optional deterministic concentration-prediction design. No new runtime scientific dependency.

Four periods are **extra collected data**, with different winds and extra collection time. The source rectangle[-450,-80]×[-220,220]m, release strength18000–36000µg/s (weak150–450), six existing monitors,12 feasible candidates,250cost units and two added instruments are retained. The rectangle is never centered or shrunk around truth. The original population remains separate. User-declared3° met uncertainty is simulated study metadata, not inferred field calibration;25° bias intentionally violates it.

## Fresh final source results

Each condition has40 paired seed blocks. Wilson95% intervals accompany coverage; area is mean percent of the162,800m² supported domain. MAP/mean/centroid errors are medians in metres. Two-source coverage/error below refer to the **primary** release only, not correct identification of both sources. Background-only has no location truth; its location fields are deliberately absent. Unsupported inputs stay in the denominator and refuse rather than create data.
"""
    ]
    report.append(
        table(
            [
                "Condition",
                "Fit/refuse",
                "MAP / mean / centroid m",
                "90% coverage (95% CI)",
                "Mean area %",
                "Accepted / misses",
                "Warnings",
            ],
            [
                [
                    r["family"],
                    f"{r['statuses'].get('fitted', 0)}/{r['statuses'].get('refused', 0)}",
                    " / ".join(
                        show(dist(r, k))
                        for k in (
                            "map_error_m",
                            "mean_error_m",
                            "prior_centroid_error_m",
                        )
                    ),
                    rate(r["region90_covered"]),
                    fraction(dist(r, "region90_area_fraction", "mean")),
                    f"{r['accepted']} / {r['accepted_region_misses']}",
                    f"{r['warning']['count']}/{r['warning']['n']}",
                ]
                for r in rows
            ],
        )
    )
    report.append("""\nCoverage and area must be read together: a large covering region can be unhelpful, and a small wrong region can be dangerous. The rule remains P(source)≥.9, region<50%domain and no warning, fixed before final. An accepted mismatch case is not removed from the analysis. The label is research-only and uncalibrated.

## Presence, wrongly sharp results and held-sensor prediction

A source-presence Brier score measures the binary simulated presence indicator under this artificially chosen case mix. It does not calibrate facility responsibility or location. A miss means P(source)<.5; false-source alarm means P(source)>.9 when Q=0. A wrongly sharp region misses the primary truth while covering<25%domain and P(source)>.9. Concentration metrics hold out a whole sensor; rows within a world are not counted as independent campaigns. NLPD is mean negative marginal log density, not a product likelihood for correlated observations. New intervals use2048 scrambled Sobol draws from the exact truncated-strength predictive distribution.\n""")
    report.append(
        table(
            [
                "Condition",
                "Presence Brier mean",
                "Miss / false alarm",
                "Wrongly sharp",
                "Held-sensor RMSE median µg/m³",
                "NLPD median",
                "90% interval coverage / width median",
            ],
            [
                [
                    r["family"],
                    show(dist(r, "source_brier", "mean"), 3),
                    f"{r['source_miss']['count']}/{r['source_miss']['n']} ; {r['false_source_alarm']['count']}/{r['false_source_alarm']['n']}",
                    f"{r['sharp_wrong_region']['count']}/{r['sharp_wrong_region']['n']}",
                    show(dist(r, "prediction_rmse_ug_m3"), 3),
                    show(dist(r, "prediction_nlpd"), 3),
                    f"{fraction(dist(r, 'prediction_interval90_coverage'))}% / {show(dist(r, 'prediction_interval90_width'), 2)}",
                ]
                for r in rows
            ],
        )
    )
    report.append("""\nThe warning counts above include healthy controls (false warnings) and mismatch challenges (detections). A non-warning is not proof that source count, weather or release history is correct. Several failures are observationally similar under this layout. The full raw records expose unavailable checks and which sensor/period blocks were actually screened.

## Realized planner results

First12 final seed blocks in four conditions,25methods per world: prediction-risk, current information, spread, wind, old0.3 planner and20random seeds. All choices are locked before candidate outcomes are generated. Refits share the same realized outcomes at selected sites; the separate target instruments' outcomes stay withheld. Target geometry is known design information. All methods share costs, access, power, weather, equipment and timestamp. This is a retrospective hypothetical measurement comparison, not a future deployment/forecast guarantee.

Positive advantage means lower held-target RMSE than the mean of20 random placements in that same world. Intervals bootstrap12 paired seed blocks,5000resamples/RNG90211; they remain imprecise. Campaign inputs are unsupported by0.3: its empty/no-update records are **not applicable**, not a fair campaign planner win/loss. In the original single-window condition its chosen placements are applicable.\n""")
    planner_rows = []
    for r in summary["planner"]:
        if (
            r["method"] == "baseline_0.3_planner"
            and r["family"] != "single_window_original"
        ):
            continue
        lo, hi = r["mean_advantage_bootstrap95"]
        d = r["rmse_advantage_vs_random20"]
        planner_rows.append(
            [
                r["family"],
                r["method"],
                r["worlds"],
                show(r["posterior_rmse"]["mean"], 3),
                f"{d['mean']:.3f} [{lo:.3f},{hi:.3f}]",
                f"{r['worse_count']}/{r['worlds']}",
                show(d["min"], 3),
                show(r["mean_cost"], 1),
            ]
        )
    report.append(
        table(
            [
                "Condition",
                "Method",
                "Worlds",
                "Post RMSE mean",
                "Advantage mean [95%CI] µg/m³",
                "Loses to random",
                "Worst advantage",
                "Mean cost",
            ],
            planner_rows,
        )
    )
    additional = []
    for r in summary["planner"]:
        if (
            r["method"] == "baseline_0.3_planner"
            and r["family"] != "single_window_original"
        ):
            continue
        selected = [
            x
            for x in plans
            if x["family"] == r["family"]
            and x["method"] == r["method"]
            and x["status"] == "fitted"
        ]
        delta = []
        for x in selected:
            random = [
                a
                for a in plans
                if a["family"] == x["family"]
                and a["seed"] == x["seed"]
                and a["method"].startswith("random-")
                and a["status"] == "fitted"
            ]
            delta.append(
                float(np.mean([a["map_error_m"] for a in random])) - x["map_error_m"]
            )
        lo, hi = block_bootstrap(delta)
        additional.append(
            [
                r["family"],
                r["method"],
                show(np.mean(delta)),
                f"[{lo:.1f},{hi:.1f}]",
                show(np.mean([a["region90_area_fraction"] for a in selected]) * 100),
                f"{sum(a['region90_covered'] for a in selected)}/{len(selected)}",
            ]
        )
    report.append(
        "\nSource-localization outcomes are separate from prediction benefit. A positive MAP advantage below means lower primary-source MAP error than random; it is not the prediction objective.\n"
    )
    report.append(
        table(
            [
                "Condition",
                "Method",
                "MAP advantage m",
                "Paired95%CI m",
                "Post mean area %",
                "Post coverage",
            ],
            additional,
        )
    )
    risks = [r for r in summary["planner"] if r["method"] == "prediction_risk"]
    supported = [r["family"] for r in risks if r["mean_advantage_bootstrap95"][0] > 0]
    report.append(
        f"\nPrediction-risk's mean RMSE-advantage interval is entirely positive in: **{', '.join(supported) if supported else 'none of the four tested conditions'}**. Other intervals cross zero or indicate loss; report them rather than selecting only successful worlds. This is a specific synthetic concentration-prediction finding, not a universal planner or attribution guarantee. Spread and random remain explicit practical alternatives.\n"
    )
    report.append("""\n## Development ablations and original data

The12-seed paired material ablation keeps source/Q/domain/monitor/candidate geometry fixed. First-window0.3 also retains that engine's broad20° met assumption, so it is a full prior-version comparison; first-window0.4 uses declared3°. Do not attribute that entire difference to a new optimizer. Noiseless controls access evaluator truth only diagnostically; production never receives it.\n""")
    ab = read(BASE / "development-ablations/results.json")
    ar = []
    for family in ("informative_campaign", "same_wind_repetition"):
        for change in sorted({r["intervention"] for r in ab}):
            a = [
                r
                for r in ab
                if r["family"] == family
                and r["intervention"] == change
                and r["status"] == "fitted"
            ]
            ar.append(
                [
                    family,
                    change,
                    len(a),
                    show(np.median([r["map_error_m"] for r in a])),
                    show(np.mean([r["region90_area_fraction"] for r in a]) * 100),
                    sum(r["region90_covered"] for r in a),
                ]
            )
    report.append(
        table(
            ["Data design", "Ablation", "n", "Median MAP m", "Mean area %", "Covered"],
            ar,
        )
    )
    original = read(BASE / "original-development-comparison/science.json")
    orows = []
    for family in sorted({r["family"] for r in original}):
        for model in ("baseline-0.3.0", NEW):
            a = [r for r in original if r["family"] == family and r["model"] == model]
            f = [r for r in a if r["status"] == "fitted"]
            source = [r for r in f if r["source_present"]]
            orows.append(
                [
                    family,
                    model,
                    f"{len(f)}/{len(a) - len(f)}",
                    show(np.median([r["map_error_m"] for r in source]))
                    if source
                    else "—",
                    show(np.mean([r["region90_area_fraction"] for r in f]) * 100)
                    if f
                    else "—",
                    f"{sum(r['region90_covered'] for r in source)}/{len(source)}",
                    sum(r["warning"] for r in f),
                ]
            )
    report.append(
        "\nThe following400 previously inspected original-development worlds compare0.3 and0.4 with the same original single-window data/default assumptions. They are a regression population, not a fresh holdout. No data-intervention benefit is claimed here.\n"
    )
    report.append(
        table(
            [
                "Original condition",
                "Model",
                "Fit/refuse",
                "Median MAP m",
                "Mean area %",
                "Primary coverage",
                "Warnings",
            ],
            orows,
        )
    )
    report.append("""\n## Calibration and sensitivity

Calibration used24 distinct seed blocks/layout/wind and an independent stretched-profile mechanism. It was diagnostic: no posterior calibration transform or threshold was fitted, and no policy changed to rescue acceptance. The full calibration was repeated after pre-final valid-input/metadata corrections; its unchanged numerical results and source hashes are verified separately. Descriptive calibration acceptance/coverage tradeoffs are in `calibration-tradeoffs.json`, by condition. No final truth selected a threshold.

Final perturbations use the first four seeds/condition: reverse input lists,+3°wind,+5µg/m³ background,+2µg/m³ one sensor,10m/48-axis grid. Plan overlap is tested on the first seed with the prediction objective. These are sensitivity probes, not a guarantee that changed physical inputs leave an answer unchanged.\n""")
    stability = read(BASE / "final-stability/results.json")
    corrected_grid = read(BASE / "grid-plan-check/results.json")
    st = []
    for change in (
        "reverse_rows",
        "wind_plus3",
        "background_plus5",
        "one_sensor_plus2",
        "grid10m",
    ):
        a = [
            r
            for r in stability
            if r.get("change") == change and r["status"] == "fitted"
        ]
        st.append(
            [
                change,
                len(a),
                show(np.median([r["map_shift_m"] for r in a])),
                show(max(r["map_shift_m"] for r in a)),
                show(max(r["mean_shift_m"] for r in a)),
                show(
                    np.mean(
                        [
                            r["plan_jaccard"]
                            for r in corrected_grid
                            if r["split"] == "final" and r["status"] == "fitted"
                        ]
                    )
                    if change == "grid10m"
                    else np.mean([r["plan_jaccard"] for r in a if "plan_jaccard" in r]),
                    2,
                ),
            ]
        )
    report.append(
        table(
            [
                "Perturbation",
                "Fits",
                "MAP shift median m",
                "MAP shift max m",
                "Mean shift max m",
                "Mean plan Jaccard",
            ],
            st,
        )
    )
    report.append(
        "\n![Coverage and region area](../evaluations/research/final/figures/source-coverage-area.png)\n\n[Standalone PDF](../evaluations/research/final/figures/source-coverage-area.pdf) · [Planner outcome chart](../evaluations/research/final/figures/planner-realized-outcomes.png) · [Ablation chart](../evaluations/research/final/figures/development-ablations.png). SVG and PDF exports are retained alongside each PNG.\n"
    )
    report.append(
        "\nGrid-refinement source metrics use fresh direct fits. The original perturbation planner reused a cached baseline for the identical payload under a diagnostic CONFIG mutation; its grid plan-overlap field is invalid. A separate fresh-cache paired check, `grid-plan-check`, supplies the corrected overlap above for all three splits. Production configuration is fixed; no production/model change was made. All other perturbation overlap fields use their changed input payloads.\n"
    )
    sampled = read(BASE / "selected-full/results.json")
    report.append(
        "\nA separate development480-reading campaign compares64/128selected rows with all480 (limit512). This changes sampling only, keeping domain, Q, geometry and declared met fixed; it does not pretend the10,000-row resource import was fully inverted. A subset can change a mode even when its mean remains nearby.\n"
    )
    report.append(
        table(
            [
                "Seed",
                "Limit",
                "Fitted",
                "MAP error m",
                "Region area %",
                "Covered",
                "Location-mass TV vs full",
                "Mean shift vs full m",
            ],
            [
                [
                    r["seed"],
                    r["limit"],
                    r["fitted"],
                    show(r["map_error_m"]),
                    fraction(r["region90_area_fraction"]),
                    r["region90_covered"],
                    show(r["total_variation_location_mass_vs_full"], 3),
                    show(r["mean_location_shift_vs_full_m"]),
                ]
                for r in sampled
            ],
        )
    )
    resources = read(BASE / "resources-final/results.json")
    api = read(BASE / "api-live-final/results.json")
    report.append("""\n## Engineering and audit

Final scientific run:480 condition-worlds/40seed blocks,960old/new outcomes,1200follow-ups; unsupported0.3 campaigns remain explicit refusals. Current0.4 fits440cases and refuses40unsupported-weather cases; old0.3 fits40single-window cases and refuses440campaign inputs. These are960outcomes, not960successful fits. All generated cases, ambiguous outputs and failures stay in raw records. Final hashes before/after match the predeclared final source freeze. Baseline reproduction matches800/864/108 original0.3 outputs exactly excluding timings. Current verification:99pytest tests, seven Chromium workflows, production typecheck/build and RuffF401/F821. These checks verify software, not field science.

Fresh-child resource limits:60seconds,2GiB address space, one BLAS thread. Every probe loads10,000measurement and10,000weather rows,100sites/25anchors. Single-window has12,097components; six-period campaign48,385. Fitted rows are bounded; this is not a10,000-row inversion. Default128 cannot retain240sensor×period groups and returns a clear refusal.\n""")
    report.append(
        table(
            ["Campaign", "Limit", "Status", "Fitted", "Seconds", "Peak RSS MiB"],
            [
                [
                    r["campaign"],
                    r["inference_limit"],
                    r.get("analysis_status", r["status"]),
                    r.get("rows_fitted", "—"),
                    show(r.get("wall_seconds"), 2),
                    show(r.get("peak_rss_mib")),
                ]
                for r in resources
            ],
        )
    )
    report.append(
        f"\nIsolated live API stress:64writes/32clients produced{api['writes']}; all{api['acknowledged_writes_verified']}acknowledged writes were reopened/verified.16concurrent campaign analyses produced{api['analysis']}. Malformed JSON/boolean/numerical row-limit/8MB checks returned{api['malformed_boolean_oversize_rows_statuses']}; health recovered200. Explicit429responses are overload rejections, not successful requests. This is one local process, not a deployment SLA.\n"
    )
    report.append("""\nRetained failures: incorrect original auxiliary background-oracle subtraction (corrected separately); coarse pair-grid endpoints (bounded reference separately); initial diagnostic40-sensor budget refusal (corrected/reprobed); incorrect API-test refusal label and oversized-row test construction; browser test's missing tab action (fixed workflow); development source-hash drift. A preflight final attempt was stopped to fix a historical midpoint label found in the browser screenshot **before any performance/truth inspection**; incomplete directories are preserved. No final outcome motivated a model change. Frozen final is the complete rerun, not a selection among attempted performance results.

## Measured data and organizational capability

Official NOAA DATEM/Sagebrush retries failed at the egress proxy with CONNECT403. Actual release measurements, units, heights, source geometry/history, averaging and licensing remain unverified. Official NOAA parser source is not a measured campaign. London65,533rows support only an import/data-quality audit without source truth. There is **no measured localization or field planning validation**.

| Task | Decision after this work |
|---|---|
| Local records, UTC/quality review, provenance, constraints, save/export | Working and tested for private research review; raw evidence/origins remain distinct from inference. Keep backups and review exclusions/instrument metadata. |
| Source localization under the explicitly supported synthetic campaign | Material conditional improvement demonstrated, with coverage/area/errors and failures reported. Research exploration with a qualified reviewer; not reliable operational attribution. |
| Source count, variable release, inaccurate weather, urban PM2.5 | Unsupported inference or inadequately detected mismatch. Do not use accepted labels to assign responsibility. |
| Spatial concentration prediction / sensor placement | Specific synthetic predictive outcomes measured; gains/losses and uncertainty above. No demonstrated field advantage or general superiority. Simple spread/random options remain. |
| Government enforcement, corporate compliance, public source allegations | Not supported. Requires compatible held-out measured campaigns, independent review/calibration and operational governance. |
| Shared organizational production service | Not implemented: local unauthenticated loopback service, unencrypted private storage; no production access-control/operations assurance. No deployment or external write was performed. |

Attainable next evidence: acquire verified controlled-release campaigns, reserve entire campaigns before fitting, review transport/averaging and instrument calibration with an atmospheric scientist, test prospective added-monitor outcomes and include uncertainty in actual met accuracy. For current low-contrast cases, better independent wind coverage/monitor geometry is more plausible than forcing an optimizer to choose a location. See the owner handover before changing assumptions or thresholds.

[Full reproduction commands](RESEARCH_REPRODUCTION.md). Raw final inputs are reproducible from pinned generator hashes/seeds; `truth.json` remains evaluator-only. The repository has no preexisting commit and remains local/uncommitted; no GitHub push, deployment or data publication was performed.
""")
    report.append(
        "\n[Accepted/rejected case distributions and reliability bins](RESEARCH_ACCEPTANCE.md) retain errors, region usefulness and presence scores for both groups. Raw source/error distributions and Wilson intervals remain in the final summary; no claim depends solely on the median.\n"
    )
    prose = re.sub(r"(\d)(?!(?:th|st|nd|rd)\b)([A-Za-zµ])", r"\1 \2", "\n".join(report))
    prose = re.sub(r"\b([A-Za-z]{2,})(?=\d)", r"\1 ", prose)
    (ROOT / "docs/RESEARCH_RESULTS.md").write_text(prose)
    acceptance = []
    bins = []
    from upwind.validation.research.run import wilson, distribution

    for family in sorted(lookup):
        f = [
            r
            for r in science
            if r["model"] == NEW and r["family"] == family and r["status"] == "fitted"
        ]
        for accepted in (True, False):
            a = [r for r in f if r["accepted"] == accepted]
            source = [r for r in a if r["source_present"]]
            acceptance.append(
                {
                    "family": family,
                    "accepted": accepted,
                    "fitted": len(f),
                    "n": len(a),
                    "present": len(source),
                    "covered": sum(r["region90_covered"] for r in source),
                    "coverage_wilson95": wilson(
                        sum(r["region90_covered"] for r in source), len(source)
                    ),
                    **{
                        key: distribution([r[key] for r in a if r.get(key) is not None])
                        for key in [
                            "map_error_m",
                            "mean_error_m",
                            "region90_area_fraction",
                            "source_brier",
                        ]
                    },
                }
            )
        for lo, hi in zip([0, 0.2, 0.4, 0.6, 0.8], [0.2, 0.4, 0.6, 0.8, 1.00000001]):
            a = [r for r in f if lo <= r["source_probability"] < hi]
            bins.append(
                {
                    "family": family,
                    "bin": [lo, min(hi, 1.0)],
                    "n": len(a),
                    "mean_source_probability": float(
                        np.mean([r["source_probability"] for r in a])
                    )
                    if a
                    else None,
                    "source_present_count": sum(r["source_present"] for r in a),
                    "presence_wilson95": wilson(
                        sum(r["source_present"] for r in a), len(a)
                    ),
                }
            )
    (BASE / "acceptance-reliability.json").write_text(
        json.dumps(
            {
                "scope": "Descriptive final results; no policy tuning. Presence calibration is conditional on synthetic case construction and is not location/responsibility calibration. Conditions share seed blocks.",
                "acceptance": acceptance,
                "reliability_bins": bins,
            },
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    adoc = [
        "# Accepted/rejected final results\n\nForty paired seed blocks per condition; generated/refused counts are in the main report. Conditional coverage refers to a primary source where one exists. Interpret both groups and area/error jointly; an accepted label is not validated accuracy. All rates/intervals/distributions and per-condition source-presence reliability bins are retained in [the raw JSON](../evaluations/research/acceptance-reliability.json).\n"
    ]
    adoc.append(
        table(
            [
                "Condition",
                "Group",
                "n / fitted",
                "Present/covered",
                "MAP p10 / median / p90 m",
                "Mean area %",
                "Brier mean",
            ],
            [
                [
                    r["family"],
                    "accepted" if r["accepted"] else "rejected",
                    f"{r['n']}/{r['fitted']}",
                    f"{r['present']} / {r['covered']}",
                    " / ".join(
                        show(dist(r, "map_error_m", k))
                        for k in ["p10", "median", "p90"]
                    ),
                    fraction(dist(r, "region90_area_fraction", "mean")),
                    show(dist(r, "source_brier", "mean"), 3),
                ]
                for r in acceptance
            ],
        )
    )
    adoc.append(
        "\nPresence reliability bins do not demonstrate population calibration: the benchmark intentionally constructs conditions with different prevalence and reused seed blocks. Within-condition bins have small denominators and often all or no sources. They cannot identify a facility or justify source-location precision.\n"
    )
    (ROOT / "docs/RESEARCH_ACCEPTANCE.md").write_text("\n".join(adoc))
    # Descriptive policy curves: condition-specific denominators, never final-selected.
    cal = read(BASE / "calibration-confirmation/science.json")
    curves = []
    for family in sorted({r["family"] for r in cal}):
        eligible = [
            r
            for r in cal
            if r["family"] == family and r["model"] == NEW and r["status"] == "fitted"
        ]
        for p in (0.5, 0.9, 0.99):
            for area in (0.1, 0.25, 0.5, 0.75, 0.9):
                for warnings in (False, True):
                    a = [
                        r
                        for r in eligible
                        if r["source_probability"] >= p
                        and r["region90_area_fraction"] < area
                        and (not warnings or not r["warning"])
                    ]
                    present = [r for r in a if r["source_present"]]
                    curves.append(
                        {
                            "family": family,
                            "generated": 24,
                            "fitted": len(eligible),
                            "presence_threshold": p,
                            "max_area_fraction": area,
                            "exclude_warned": warnings,
                            "accepted": len(a),
                            "accepted_present": len(present),
                            "primary_location_misses": sum(
                                not r["region90_covered"] for r in present
                            ),
                            "no_source_accepted": sum(
                                not r["source_present"] for r in a
                            ),
                        }
                    )
    (BASE / "calibration-tradeoffs.json").write_text(
        json.dumps(
            {
                "purpose": "Descriptive calibration curves only. Policy not selected using these curves or final truth. Conditions reuse24seed blocks.",
                "curves": curves,
            },
            indent=2,
        )
        + "\n"
    )
    outputs = {
        "docs/RESEARCH_ACCEPTANCE.md": hashlib.sha256(
            (ROOT / "docs/RESEARCH_ACCEPTANCE.md").read_bytes()
        ).hexdigest(),
        "evaluations/research/acceptance-reliability.json": hashlib.sha256(
            (BASE / "acceptance-reliability.json").read_bytes()
        ).hexdigest(),
        "docs/RESEARCH_RESULTS.md": hashlib.sha256(
            (ROOT / "docs/RESEARCH_RESULTS.md").read_bytes()
        ).hexdigest(),
        "evaluations/research/calibration-tradeoffs.json": hashlib.sha256(
            (BASE / "calibration-tradeoffs.json").read_bytes()
        ).hexdigest(),
    }
    inputs = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            BASE / "final/summary.json",
            BASE / "final/science.json",
            BASE / "final/followup.json",
            BASE / "final-stability/results.json",
            BASE / "calibration-confirmation/science.json",
            BASE / "development-ablations/results.json",
            BASE / "original-development-comparison/science.json",
            BASE / "resources-final/results.json",
            BASE / "api-live-final/results.json",
            BASE / "grid-plan-check/results.json",
            BASE / "selected-full/results.json",
        ]
    }
    (BASE / "report-manifest.json").write_text(
        json.dumps(
            {
                "script_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "inputs": inputs,
                "outputs": outputs,
                "reporting_rng": 90211,
            },
            indent=2,
        )
        + "\n"
    )
    print("Wrote research report and calibration tradeoffs")


if __name__ == "__main__":
    main()
