# Severe model evaluation protocol — UW-STRESS-2026-01

Frozen before running new held-out statistical outcomes. The original v0.1.0 source, source hashes and 24 original outcomes are preserved; no tuning to seeds 101/202/303 or the new held-out seeds is permitted. This protocol distinguishes engineering correctness, conditional-model behavior, and independent external evidence. Passing one does not establish the others.

## Version and changes allowed

Audit hypotheses: v0.1.0 may crash on empty candidate lists or extreme per-reading uncertainty; subsampling may conceal unsupported weather/data; duplicated source coordinates alter prior mass; truncated near/far predictions can be mistaken for valid zero evidence; finite-difference log determinants can lose small information; and large-case greedy selection can underperform an available baseline. Demonstrate these on development/adversarial cases, preserve original failures, then correct contracts/numerics under model identifier `plume-ensemble-0.2.0`. Do not change emission/background grids, dispersion coefficients, or tune to held-out localization outcomes. Document any added model-error covariance as an assumption, not empirical calibration.

## Dataset compatibility gates

Inventory NOAA DATEM / Sagebrush, Prairie Grass, EPA AQS, UCI Beijing multi-site, and openair examples using actual accessible upstream files/documentation where possible. Record exact URLs, revisions, hashes, columns, units, missingness, release heights, timing, coordinate availability and license. Tracer datasets require compatible physics and unit conversion before inference; PM2.5 monitoring without independent source truth cannot measure attribution accuracy. Never synthesize missing coordinates/wind or rebrand another pollutant as PM2.5. Acquisition failures and incompatibilities remain visible. Do not run downloaded project code.

## Engineering battery

- At least 10,000 independent scalar-oracle and metamorphic plume comparisons: cardinal/rotated winds, ground reflection, emission and inverse-speed scaling, crosswind symmetry, translation, supported-range boundaries, finite outputs, and explicit invalid-input refusal.
- Adversarial contracts: empty sources/sites, duplicate/near-duplicate sources, unsupported pairs, calm/variable/remote/missing weather including records hidden between selected observations, unsorted/permuted imports, aliases/duplicates/conflicts, tiny/huge/NaN/infinite uncertainty, zero budget/cost, large coordinates/timezone boundaries, malformed CSV/JSON, oversized and Unicode payloads.
- At least 100 randomized tiny planning instances checked against an independent exhaustive oracle; at least 100 larger feasible constraint instances including random permission/cost/window patterns. Compare exact utility, budget, eligibility, equipment and deterministic round-trip/permutation behavior. Count checks executed rather than only pytest test-function count.
- Benchmark increasing problem sizes to schema maxima: 10,000 measurements, 10,000 weather rows, 100 sites, 25 source hypotheses, equipment 8; record wall time, peak RSS and hardware. Use a 30 s per-case subprocess timeout and 2 GiB incremental-memory target, not a claim of an absolute global limit. Probe rejection beyond documented input maxima without allocating unbounded data.
- API concurrency, repeat requests and SQLite save/reopen/rollback behavior in isolated test storage. Failed/malformed requests must not partially save investigations or erase originals.

## New scientific battery

Development seeds 110000–110009; **held-out seeds 220000–220039**. Sixteen predeclared cases (640 held-out runs): weak signal; strong on-grid signal; ambiguous/upwind; high noise; constant background shift within grid; changing background; two detectable sources; off-grid truth; direction bias; speed bias; clustered sensors; one missing sensor; calm; variable wind; absent weather; insufficient distinct sensors. True source Q/background and generated measurements are evaluator-only; inference gets the predeclared grid and actual measurement/met data only.

Use a separately coded scalar Gaussian generator, not `engine.plume`, with a declared high-signal geometry and unchanged physical units. High signal uses Q=12000 µg/s and receptors about 60–250 m downwind; weak signal reproduces long-distance detectability issues. Do not call a low localization error independent validation: this still shares a dispersion family. For mismatches retain confidently wrong predictions.

Report per case: status/refusal/crash/non-finite counts; MAP localization error; whether truth is on-grid; 90% **discrete conditional** set size/coverage only for on-grid truth; entropy; maximum weight; wrong-and-sharp count (error >100 m and max weight >0.9); mismatch-warning rate; held-out predictive error where feasible; wall time. Wilson intervals for event rates, empirical quantiles for errors; these are Monte Carlo uncertainty intervals, not atmospheric calibration.

## Follow-up planning experiment

Parameter detail recorded before the first new statistical run: matched strong transport uses a predeclared nuisance member (recorded 2.3 m/s ×1.15), Q=12000, b=10; the two-source mismatch adds Q=30000 at (-180,30) m so it produces detectable signal at multiple receptors. Strong-source demonstration expectation: ≥80% of seeds localize within 100 m; report failures without tuning. Future matched errors share the inference model's spatial field with initial observations; the deliberate mismatch uses a stronger, longer-range error field and underreported independent noise. The approximate planner is still not exact expected information gain.

For 40 held-out seeds, lock every method's plan using initial observations only, before generating/revealing follow-up outcomes. Compare optimized, spread, wind and all 20 random seeds on identical budgets/sites/opportunities. Same seed's instrument errors are shared by all methods; include the model's documented correlated site errors in the matched generator and a deliberate correlation mismatch separately. Weather is an already available synthetic steady scenario, not a future observation passed as a forecast. Compare realized posterior location entropy, localization error and held-out prediction, with negative improvements retained. Utility ranking is distinct from realized benefit. Repeat a weak-signal condition to expose vanishing practical benefit.

## Reporting and stopping

### Evaluation amendment after the preserved v0.2.0 run

The first complete run is retained in `evaluations/stress/v0.2.0`. Its ambiguous case revealed an evaluator defect: choosing the first index of a tied MAP set made an uninformative uniform posterior appear to have zero localization error. The corrected evaluator retains that legacy scalar for audit, adds tie count and minimum/maximum tied-location errors, and reports such cases as unresolved. Do not count tied maxima as successful localization.

The run also exposed a diagnostic defect: comparing raw residual RMSE to the default uncertainty ignored larger, explicitly supplied per-reading uncertainty. Model v0.2.1 uses RMS of Cholesky-whitened residuals under the already specified observation covariance, with the existing threshold 3. This is a heuristic, not a calibrated goodness-of-fit test. Emission/background grids, transport physics, likelihood/posterior and planner remain unchanged. Reuse of the frozen seeds here verifies corrections; it is not a second independent discovery set. Preserve both runs and report remaining scientific failures. Resource reporting also adds Linux VmHWM because inherited process-accounting high-water marks can overstate fresh-exec RSS.

Save raw machine-readable outcomes and a plain-language report with exact commands, source hashes and counts. Classify results as passed, refused as designed, failed scientific expectation, untested or blocked. Repair reproducible coding/logic defects and rerun affected checks, without deleting baseline failures. No claim of perfect code, real-world source validation, prospective forecasting skill, partner adoption, or an unlimited stress test is supported. Stop after the bounded protocol and relevant regressions, and list remaining demonstrated limitations.

A final JSON-contract check additionally found that default numeric coercion accepted boolean concentrations as 1.0. Strict schema quantities now refuse booleans/numeric strings in JSON (CSV converts declared numeric columns explicitly). This changes invalid-input acceptance only, not valid-input transport/posterior/planning computations. The `v0.2.1-final` rerun retains the same seed protocol and records the exact hardened source hashes.
