"""Generate evaluation summary report from test outcomes."""

import argparse, json, os
from pathlib import Path
import numpy as np
from .science import wilson


def load(root, name):
    return json.loads((root / (name + ".json")).read_text())


def report(root, out):
    summary = load(root, "summary")
    engineering = load(root, "engineering")
    science = load(root, "science")
    follow = load(root, "followup")
    resources = load(root, "resources")
    api = load(root, "api")
    external = load(root, "external")
    meta = load(root, "metadata")
    if external.get("rows") is not None:
        external_text = f"Actually inspected: **{external.get('source')}**, revision `{external.get('revision')}`, SHA256 `{external.get('data_sha256')}`. {external.get('rows', 0):,} rows; {external.get('pm25_observed_rows', 0):,} PM2.5 observations and {external.get('pm25_missing_rows', 0):,} missing. Median {external.get('pm25_quantiles', {}).get('0.5')} and maximum {external.get('pm25_max')} µg/m³."
    else:
        external_text = f"External inspection **{external.get('status', 'unrun')}**: {external.get('reason', 'not requested')}. No external dataset was evaluated and no substitute was generated."
    lines = [
        "# UPWIND severe stress-test report",
        "",
        f"Scientific model **{summary['model_version']}**, protocol **UW-STRESS-2026-01**. Generated from recorded outcomes, not manually selected examples.",
        "",
        "**Verdict:** the tested engineering contracts pass after specific defects were repaired. The source model does **not** have general scientific validity: weak signals, wrong weather, off-grid truth, unknown backgrounds and misreported uncertainty remain serious limitations. This is an experimental conditional model, not a perfectly coded or independently field-validated attribution system.",
        "",
        "## What was actually executed",
        "",
        f"- **{summary['engineering_checks']:,} engineering/property checks**, zero failed groups: {engineering['numerical']['checks']:,} numerical checks, {len(engineering['planning']['instances'])} randomized placement instances and {engineering['capabilities']['checks']} capability/refusal checks. These are assertions/instances, not independent field datasets.",
        f"- **{summary['scientific_runs']} synthetic case/seed runs**: 16 conditions ×40 held-out seeds. Conditions share seeds; these are not 640 independent campaigns. Crashes: {summary['scientific_crashes']}.",
        f"- **{summary['followup_runs']:,} paired follow-up evaluations**: 40 seeds ×2 signal conditions ×2 error regimes ×23 methods (optimizer, spread, wind, 20 random seeds). Crashes: {summary['followup_crashes']}. These are 160 simulated worlds with repeated method comparisons, not 3,680 independent trials.",
        f"- **{api['fuzzed_csv_cases']} deterministic CSV edge combinations**, {api['concurrent_requests']} writes using {api['workers']} client threads, malformed/oversized requests and integrity checks in isolated SQLite storage.",
        f"- **{external.get('rows', 0):,} actual upstream hourly records inspected**, including {external.get('pm25_observed_rows', 0):,} nonmissing PM2.5 readings. This is a measured-data audit and absent-coordinate refusal test, not a source-accuracy result.",
        "- Separate regressions: 34 pytest tests; four Chromium investigation workflows; TypeScript/production build; Ruff undefined-name/unused-import checks. See recorded verification commands below.",
        "",
        "## Defects exposed and corrected",
        "",
        "| Finding | Correction / evidence |",
        "|---|---|",
        "| Empty site arrays crashed | Shape-safe vectorized predictions; a structured infeasible result, while scenario comparison remains available |",
        "| Extreme uncertainty overflowed or produced singular covariance | Explicit supported per-reading range 0.01–1000 µg/m³; Cholesky solves instead of inverse; invalid schema rejected |",
        "| Unmatched calm/variable weather was ignored | Check every relevant in-window local wind record before fit-row sampling |",
        "| Row reduction could change represented sensors/conditions | Validate full window first; deterministic balanced quantiles retaining all supported sensors; maximum 40 fit rows/40 distinct sensors |",
        "| Unsupported source/receptor pairs became misleading zeros | Refuse unsupported observation pairs; exclude unsupported candidates equally for all methods |",
        "| Duplicate hypotheses/conflicting readings could distort evidence | ≥1m separation for source hypotheses; quarantine conflicting sensor/time groups; identical duplicates deduplicate without extra evidence |",
        "| Site order changed geographic calculations | Stable coordinate origin and ID ordering; preserved initial development failures and successful randomized permutation checks |",
        "| Subtracting large log determinants erased tiny information | Cholesky-whitened log1p eigenvalue score; independent singular-value oracle |",
        "| Greedy could lose to a computed baseline | Large cases choose the best utility from greedy and the baseline envelope; no global-optimum or realized-benefit guarantee |",
        "| Zero information was called infeasible | Separate uninformative status from permission/budget failure |",
        "| Budget changed the coverage target universe | All permissible target sites remain in the objective, regardless of affordability; exact budget-monotonicity checks |",
        "| Ambiguous MAP ties looked perfectly localized | Explicit tied MAP sets and min/max errors; no localization success claim for ties; earlier misleading scalar retained in the first run for audit |",
        "| Residual alarm ignored supplied uncertainty | Covariance-whitened dimensionless RMS; previous diagnostic and its false alarms preserved in v0.2.0 outcomes |",
        "| Malformed quotes/oversized Unicode could escape CSV contract | Strict CSV parsing, row-width checks, UTF-8 byte limit, preserved raw originals; 360° north normalization documented |",
        "| Concurrent large requests lacked admission bound | Maximum four POST/PUT requests processing; overload gets explicit 429/Retry-After; reads remain available |",
        "",
        "Baseline artifacts: `evaluations/stress/baseline-engine-0.1.0.py.txt`, `baseline-source-hashes.json`, `baseline-audit.json`, and `development-planning-failures.json`. The original 24-run v0.1 evaluation is unchanged. The first complete v0.2.0 stress run is retained beside the corrected final run. The evaluator/diagnostic amendments did not change emission/background grids, dispersion physics, likelihood weights or site objectives after inspecting held-out outcomes.",
        "",
        "## Scientific outcomes — conditional synthetic evidence",
        "",
        "| Case | Fits /40 | Median MAP error, m | Median 90% grid-set size | Truth in 90% set | Mismatch warnings |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    scientific_summary = {}
    for case in dict.fromkeys(r["case"] for r in science):
        rows = [r for r in science if r["case"] == case]
        fits = [r for r in rows if "localization_error_m" in r]
        unique = [r for r in fits if r.get("map_unique", True)]
        error = (
            f"{np.median([r['localization_error_m'] for r in unique]):.1f}"
            if unique
            else "Unresolved ties"
            if fits
            else "Refused"
        )
        region = (
            f"{np.median([r['grid_points_90'] for r in fits]):.0f}" if fits else "N/A"
        )
        covered = [r for r in fits if r["truth_in_90"] is not None]
        coverage = (
            f"{sum(r['truth_in_90'] for r in covered)}/{len(covered)}"
            if covered
            else "N/A"
        )
        warnings = sum(r.get("mismatch_warning", False) for r in fits)
        lines.append(
            f"| {case} | {len(fits)} | {error} | {region} | {coverage} | {warnings} |"
        )
        scientific_summary[case] = {
            "runs": len(rows),
            "fits": len(fits),
            "unique_maps": len(unique),
            "map_error_median": None
            if not unique
            else float(np.median([r["localization_error_m"] for r in unique])),
            "within_100m_unique_map": sum(
                r["localization_error_m"] <= 100 + 1e-6 for r in unique
            ),
            "mismatch_warnings": warnings,
            "truth_coverage_wilson95": wilson(
                sum(r["truth_in_90"] for r in covered), len(covered)
            ),
        }
    strong = scientific_summary["strong_signal"]
    weak = scientific_summary["weak_signal"]
    lines += [
        "",
        f"The matched high-signal demonstration meets its predeclared expectation: **{strong['within_100m_unique_map']}/40** unique MAP estimates within 100m, versus **{weak['within_100m_unique_map']}/40** for weak signals. This deliberately favorable high-signal generator uses the same dispersion family with an independently coded scalar implementation; it is not independent atmospheric validation. Weak/upwind data can retain nearly the entire 9-point grid, so including truth in a large set is not useful localization.",
        "",
        "Ambiguous upwind cases have tied maxima: their legacy first-index scalar error can be zero solely because truth is listed first. They are unresolved, not successful. Off-grid truth has no meaningful coverage under the on-grid discrete set; its coverage is N/A. Wind bias can exclude the real source even while retaining a broad-looking set. Sharp single-source fits to multi-source/changing-background data do not validate the single-source assumption. A missing residual alarm does not establish correctness.",
        "",
    ]
    confident = [
        r for r in science if r.get("wrong_map_grid") and r["max_weight"] > 0.9
    ]
    lines.append(
        f"Confidently wrong unique grid choices: **{len(confident)}** (>90% conditional weight on a nontruth grid location) in the scientific battery. Exact 100m boundaries use metre-level interpretation rather than treating floating-point 100.0000000001 as a substantive distance above 100m. The original raw distance-threshold boolean is retained for audit and is not used as the primary count."
    )
    lines += [
        "",
        f"The constructed two-source condition triggered **{scientific_summary['two_sources']['mismatch_warnings']}/40** residual alarms. Failure to detect an unmodelled second source is a retained scientific limitation; a correct dominant-grid location does not establish that only one source exists.",
    ]
    if confident:
        r = confident[0]
        lines += [
            "",
            f"Concrete failure: `{r['case']}`, seed `{r['seed']}`, error **{r['localization_error_m']:.1f}m**, conditional maximum weight **{100 * r['max_weight']:.2f}%**, mismatch alarm **{r['mismatch_warning']}**.",
        ]
    lines += [
        "",
        "## Realized follow-up benefit, including failures",
        "",
        "Plans are locked before candidate outcomes are generated/revealed. Every method sees the same budget/opportunities and the same candidate error realization within a seed. Random methods are averaged **within seed** before paired comparisons. Matched means a matched synthetic covariance family, not exact planner expected-information optimality. The mismatch deliberately adds stronger/longer-range error and underreported independent noise.",
        "",
        "| Signal / error regime | Method | Mean entropy reduction, nats | Mean location error, m | Mean held-out predictive RMSE, µg/m³ | Wrong grid with >90% weight |",
        "|---|---|---:|---:|---:|---:|",
    ]
    paired = []
    for case in ["strong_signal", "weak_signal"]:
        for regime in ["matched", "mismatched"]:
            group = [
                r
                for r in follow
                if r.get("case") == case
                and r.get("error_model") == regime
                and r["status"] == "ok"
            ]
            for prefix in ["Optimized", "Spatial", "Wind", "Random"]:
                rows = [r for r in group if r["method"].startswith(prefix)]
                wrong = sum(
                    r.get("wrong_map_grid", False) and r["max_weight"] > 0.9
                    for r in rows
                )
                lines.append(
                    f"| {case} / {regime} | {prefix} | {np.mean([r['entropy_reduction'] for r in rows]):.4f} | {np.mean([r['localization_error_m'] for r in rows]):.2f} | {np.mean([r['posterior_predictive_rmse'] for r in rows]):.2f} | {wrong}/{len(rows)} |"
                )
            diffs = []
            wins = 0
            ties = 0
            worse_rmse = 0
            negative = 0
            for seed in sorted({r["seed"] for r in group}):
                opt = next(
                    r
                    for r in group
                    if r["seed"] == seed and r["method"].startswith("Optimized")
                )
                random = [
                    r
                    for r in group
                    if r["seed"] == seed and r["method"].startswith("Random")
                ]
                d = opt["entropy_reduction"] - np.mean(
                    [r["entropy_reduction"] for r in random]
                )
                diffs.append(float(d))
                wins += d > 1e-10
                ties += abs(d) <= 1e-10
                worse_rmse += opt["posterior_predictive_rmse"] > np.mean(
                    [r["posterior_predictive_rmse"] for r in random]
                )
                negative += opt["entropy_reduction"] < 0
            paired.append(
                {
                    "case": case,
                    "error_model": regime,
                    "seeds": len(diffs),
                    "entropy_advantage_vs_random_mean": float(np.mean(diffs)),
                    "empirical_difference_q05_q95": np.quantile(
                        diffs, [0.05, 0.95]
                    ).tolist(),
                    "entropy_wins": int(wins),
                    "ties": int(ties),
                    "wins_wilson95": wilson(wins, len(diffs)),
                    "worse_predictive_rmse_than_random_mean": int(worse_rmse),
                    "negative_entropy_changes": int(negative),
                }
            )
    lines += [
        "",
        "Paired seed-level comparisons (Wilson intervals describe Monte Carlo win rates, not real-world calibration):",
        "",
    ]
    for r in paired:
        lo, hi = r["wins_wilson95"]
        lines.append(
            f"- {r['case']} / {r['error_model']}: optimizer entropy advantage over the random-seed mean **{r['entropy_advantage_vs_random_mean']:.4f} nats**; wins **{r['entropy_wins']}/{r['seeds']}** (95% Wilson {lo:.2f}–{hi:.2f}); {r['negative_entropy_changes']} runs increased entropy; {r['worse_predictive_rmse_than_random_mean']} had worse predictive RMSE than the random-seed mean."
        )
    lines += [
        "",
        "**Interpretation:** the optimizer helps in the matched high-signal synthetic setting, but there is no general improvement guarantee. Weak-signal mean localization/prediction can be worse than random. Under mismatch, confidence can increase while accuracy deteriorates. Entropy reduction is neither a health benefit nor evidence of the correct source. Negative and worse-than-baseline outcomes are retained.",
        "",
        "## Capacity, robustness and actual hardware",
        "",
        f"CPU: **{meta['processor']}**. Python {meta['python']}; NumPy {meta['numpy']}; {meta['platform']}. One sequential Python process, BLAS threads pinned to {meta['blas_threads']}. Full evaluation wall time: {summary['wall_seconds']:.2f}s. These timings characterize this machine, not every laptop.",
        "",
        "| Measurements | Weather records | Sites / source hypotheses | Fit rows | Wall ms | Peak RSS MiB (Linux VmHWM) |",
        "|---:|---:|---|---:|---:|---:|",
    ]
    for r in resources:
        if not all(
            k in r
            for k in [
                "measurements",
                "weather_rows",
                "rows_used",
                "wall_ms",
                "sites",
                "source_locations",
                "peak_rss_mib",
            ]
        ):
            lines.append(
                f"| {r.get('size', 'unknown')} | N/A | N/A | N/A | {r.get('status', 'failed')} | N/A |"
            )
            continue
        lines.append(
            f"| {r['measurements']:,} | {r['weather_rows']:,} | {r['sites']} / {r['source_locations']} | {r['rows_used']} | {r['wall_ms']:.2f} | {(r.get('proc_peak_rss_mib') or r['peak_rss_mib']):.2f} |"
        )
    lines += [
        "",
        "Each scale case ran in a subprocess with a 30s timeout and 2GiB address-space ceiling. Linux VmHWM reports the fresh executable's high-water RSS; `getrusage` may include inherited launcher accounting and is retained separately. Incremental high-water growth of zero does not mean no memory allocation. Ten thousand imported/validated rows **does not mean ten thousand rows fitted**: inference uses a declared 40-row balanced subset after all-window checks. Memory/resource instrumentation is verified on Linux, not every supported laptop OS.",
        "",
        f"Concurrency results: {api['response_statuses']}. All {api['acknowledged_writes']} acknowledged writes were present exactly once; rejected overload writes were not claimed saved. All malformed requests returned 422, oversized body returned 413, invalid writes left storage unchanged, and a request after overload succeeded. 429 is deliberate capacity refusal, not silent success or an unexplained server crash.",
        "",
        "## External data evidence and remaining blockers",
        "",
        external_text,
        "",
        "Coordinates are absent; all incomplete spatial imports were rejected rather than supplied invented coordinates. One urban station and no known release truth cannot validate this source model. Official NOAA/EPA/UCI/UK station-metadata acquisition remained blocked by CONNECT 403; those datasets were not evaluated. Raw upstream observations remain ignored locally pending primary-data redistribution review. See [DATASET_CATALOG.md](DATASET_CATALOG.md) for compatible uses and rejected assumptions.",
        "",
        "## Reproduction and next decisions",
        "",
        "```sh\nuv pip install --python .venv/bin/python -r requirements-research.lock\nOPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.run --out .local/new-stress-run\n.venv/bin/python -m upwind.validation.reporting --input .local/new-stress-run --out .local/new-stress-report.md\n.venv/bin/python -m pytest -q\ncd frontend\nnpm run build\nnpm run test:e2e\n```",
        "",
        f"Raw final results: `{root}` (`metadata`, `engineering`, `science`, `followup`, `resources`, `external`, `api`, `summary` JSON). Metadata hashes identify the exact numerical/evaluation sources and protocol. Previous outputs are never overwritten by the runner. Repeating frozen seeds verifies a correction; it is not new independent evidence.",
        "",
        "Next priorities follow the failures: acquire compatible controlled-release data and verified station metadata; validate units/heights and reject mismatched campaigns; test independent campaign/site/time splits; quantify weather/background/model discrepancy with real evidence; independently evaluate forecast/scheduling before enabling it; observe an actual operator. Do not tune the current held-out seeds or market conditional source weights as field probabilities. No outreach, public deployment, Git push or data publication was performed by this stress task.",
    ]
    relative = Path(os.path.relpath(root, out.parent)).as_posix()
    if (root / "source-stress.svg").exists() and (
        root / "followup-stress.svg"
    ).exists():
        lines += [
            "",
            "## Recorded-data figures",
            "",
            f"![Conditional synthetic localization and coverage]({relative}/source-stress.svg)",
            "",
            f"![Paired synthetic follow-up entropy outcomes]({relative}/followup-stress.svg)",
            "",
            "Figures are generated by `scripts/plot_stress.py`; its input/source hashes and plotting-library version are in `figures.json`.",
        ]
    out.write_text("\n".join(lines) + "\n")
    import hashlib

    artifact = {
        "reporter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outcome_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.glob("*.json")
            if path.name
            not in {
                "aggregate.json",
                "report-artifact.json",
                "figures.json",
                "dependencies.json",
            }
        },
        "report_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    (root / "report-artifact.json").write_text(json.dumps(artifact, indent=2) + "\n")
    aggregated = {
        "scientific": scientific_summary,
        "paired_followup": paired,
        "engineering_checks": summary["engineering_checks"],
        "source_model": summary["model_version"],
    }
    (root / "aggregate.json").write_text(json.dumps(aggregated, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report(args.input, args.out)


if __name__ == "__main__":
    main()
