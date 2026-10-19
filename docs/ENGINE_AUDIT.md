# Scientific engine baseline audit

Baseline: **plume-ensemble-0.2.1**, inspected and reproduced on 2026-10-18 before redesign. This document describes the preserved baseline, including its failures; it is not a claim about the replacement model. The previous stress cases are now development-used. No source-model field validation is established.

## Preservation and reproducibility

The checkout has no `HEAD` commit: the original project files are untracked on an unborn branch. No reset, cleanup, push or publication was performed. The baseline therefore uses file hashes rather than a fabricated commit identifier.

- Immutable source: `evaluations/overhaul/baseline-source/`, containing 37 scientific, API, test, protocol, dependency and documentation files copied before production edits.
- Manifest: `evaluations/overhaul/baseline-manifest.json`; initial SHA256 `365211bf9cdc7c61f874411818d8c5ae764cdd8996568deb169373be0cb3a8a7`.
- Baseline `engine.py` SHA256: `6949dffea3002ded8d7bf3cb8064d35746d84a7053b2792e860caf021d981fe5`.
- Baseline `numerics.py` SHA256: `d64a30504d559b003fb76a6c7f267f998399b26a7f2425d90f531c6feb1c2fd6`.
- Original stress protocol SHA256: `c7ec3b1a82417257c7f536732d8981c6147a7a384f54c9e01fcef34422e4672d`.
- Current reproduction: `evaluations/overhaul/baseline-reproduced/`. Original `evaluations/stress/v0.2.1-final/`, earlier stress runs, and the original v0.1 results remain intact.
- Exact packages: `baseline-reproduced/dependencies.json`; numerical/evaluation source hashes, host and configuration: `metadata.json`. Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, pyproj 3.7.2, Pydantic 2.13.4; Linux 6.18.55, AMD EPYC 9V45, one BLAS thread.

From the repository root:

```sh
# Use a fresh output folder on subsequent reproductions; the runner refuses overwrite.
PYTHONPATH=evaluations/overhaul/baseline-source/backend \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
.venv/bin/python -m upwind.validation.run \
  --out evaluations/overhaul/baseline-reproduced --skip-external

# Baseline-only independently checkable diagnostics, reading the immutable snapshot.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
.venv/bin/python evaluations/overhaul/baseline-diagnostics.py

PYTHONPATH=evaluations/overhaul/baseline-source/backend \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q \
  evaluations/overhaul/baseline-source/backend/tests \
  --junitxml=evaluations/overhaul/baseline-reproduced/pytest.xml
```

The snapshot-specific `PYTHONPATH` also reaches the runner's resource subprocesses. Consequently concurrent production edits cannot change this reproduction. The second command verifies every snapshot file against the initial manifest. Its saved `diagnostic-toys.json` includes its own script hash. Dependency lock files are included in the snapshot. The external audit was explicitly skipped in this rerun; previous measured-data metadata were inspected separately.

The runner completed in **16.41 seconds**: **72,167** engineering/property checks, zero failed groups; API battery passed; **640** source evaluations and **3,680** paired follow-up outcomes, zero crashes; all four resource subprocesses succeeded. A separate isolated baseline pytest run passed **34 tests**. `reproduction-comparison.json` confirms every scientific and follow-up output is identical to the previous final run after excluding timing fields: zero differing rows out of 640 and 3,680 respectively. This establishes repeatability of those computations, not scientific adequacy.

## What the baseline actually computes

### Transformations and units

Pydantic requires finite, strict JSON numbers. Timestamp inputs require an explicit offset and are normalized to UTC before weather matching, duplicate grouping or selection. CSV conversion handles units and timezone interpretation explicitly; raw imports, hashes and transformations remain stored. Naive daylight-saving ambiguities are refused. Meteorology uses integer UTC microseconds, so it is not matched by local display time.

WGS84 longitude/latitude project to local azimuthal-equidistant x-east/y-north metres using `always_xy=True`. The source-grid centroid defines the inference origin. Cardinal-wind and rotation tests agree with the meteorological convention: angle is **from**, clockwise from north; flow is `(-sin θ, -cos θ)`. Wind from 270° flows east. The audit toy projects longitude +0.001° at the equator to about 111.319 m east and verifies all four cardinal vectors. No degrees/radians, metre/kilometre or wind-from reversal defect was found in this path.

The ground-reflected neutral Gaussian kernel is:

```
μ = b + Q/(2πu σyσz) exp(-y²/(2σy²))
      × [exp(-(z-H)²/(2σz²)) + exp(-(z+H)²/(2σz²))]
σy = 0.08x / sqrt(1 + 0.0001x)
σz = 0.06x / sqrt(1 + 0.0015x)
H = 5 m, z = 2 m.
```

`Q` is µg/s, `u` m/s and dispersion lengths metres, giving µg/m³. The model has no release-duration parameter: it assumes an established steady plume. There is no humidity adjustment, atmospheric stability estimation, deposition, chemistry, terrain/canyon treatment or measured release/sensor height. Imported humidity is descriptive metadata. Fixed heights and neutral/open-terrain assertions do not establish compatibility with a real instrument or campaign.

The public kernel returns zero plume contribution for downwind distance below 20 m or radial distance beyond 3 km. Inference independently rejects any observation/source radial pair outside 20 m–3 km; it does not treat those pairs as observed zero pollution. Genuine upwind plume contribution is zero, with background still present. Sources lie within 1.5 km of their centroid and receptors within 3 km; source hypotheses must be at least 1 m apart. Candidate/source geometry is checked before planning.

### Likelihood, priors and selection

Each declared source point has uniform prior mass. The nuisance grid is `Q={1500,5000,12000}`, `b={4,10,18}`, wind offset `{-12,0,12}°`, speed multiplier `{0.85,1.15}`. Speed multipliers incompatible with the supported 0.8–8 m/s range are omitted. No continuous source location, zero-emission explanation, time-varying background or second source exists in this model. A truth between grid points has zero probability under its declared location support.

For usable selected readings, the covariance is

```
Σij = 1(i=j) σi² + 1(sensor_i = sensor_j)
      + noise_setting² exp(-distance(i,j)/150 m).
log L = -0.5 (y-μ)ᵀ Σ⁻¹ (y-μ).
```

Sensor bias has assumed variance 1 (µg/m³)². The spatial component is shared unchanged across the window, including repeated timestamps and readings; the independent reading term remains on the diagonal. **The baseline already models correlated observations.** Treating every row as independent is therefore not the confirmed explanation of these failures. Covariance parameters and the assumption of perfectly persistent spatial error remain uncalibrated physical assumptions. Different sensor drift, temporal background and humidity effects could still impersonate transport changes.

Cholesky solves and log-sum-exp normalization are stable in the independent numerical checks; covariance does not vary by scenario, so omitting its common normalization constant does not alter weights. Tiny likelihoods can legitimately underflow to zero after normalization; at least one normalized scenario remains. No evidence was found that numerical normalization, an optimizer fallback or hidden fixture recognition creates the reported sharp location weight. This does not prove every numerical input correct.

Negative, >500µg/m³ review-flagged and conflicting sensor/time groups are excluded from fitting but retained in the investigation. Identical duplicates are deduplicated. Full-window geometry, duration and weather are checked before sampling. At most 40 sensors are supported and **at most 40 rows are fitted**. The deterministic algorithm allocates one row per sensor, distributes remaining quotas round-robin by sorted sensor ID, then chooses evenly spaced timestamp indices within each sensor. This preserves sensor presence and first/last observations when a quota exceeds one; a quota of one selects its first reading. It does not preserve rare informative episodes deliberately. No random selection seed is involved.

Weather is nearest in time within ±30 minutes and 3 km, breaking ties by spatial distance then canonical record order. All local weather inside the observed window is checked, not just sampled rows. Observations span at most one hour, wind directional deviation at most 25°, speed ratio at most 2. The candidate prediction uses a representative observed-window wind, plus the same nuisance offsets. It is not a future forecast or travel schedule.

### Diagnostic and planner meanings

The residual alert tests RMS of Cholesky-whitened **same-fit posterior-mean residuals** against 3. It is neither a prospective test nor a calibrated test for number of sources. Marginalization over scenarios can fit observations better than any selected physical scenario, and the threshold is high relative to the observed residual distributions. A low in-sample residual cannot certify a correct source, correct wind or one-source adequacy.

The information score decomposes candidate predictive covariance into between-location `B` and within-location nuisance plus noise `R`, then calculates `0.5 logdet(I + R^-1/2 B R^-T/2)`. This Gaussian moment approximation is not the exact expected information gain of the discrete predictive mixtures. Noise includes spatial correlation and independent new-instrument bias. A confidently wrong posterior can recommend measurements around the wrong explanation. Weak candidate signal can give negligible true learning despite positive internal score.

Small problems (≤12 eligible sites) use exhaustive feasible subsets including the empty set. Larger problems take the best objective value of cost-normalized greedy, spread, wind and a 20-seed random envelope. This protects internal utility against those particular baselines, not realized localization or prediction. All methods share eligibility, budget and equipment limits; wind baseline uses the source-grid centroid, not hidden truth. Follow-up outcomes are generated only after choices are locked. The original follow-up experiment uses already available synthetic steady weather, not a forecast-oracle experiment establishing future scheduling.

The nominal 90% output is a cumulative conditional **set of grid points**, not a geographic confidence region. It has no area or between-point coverage definition. Naming it a 90% source region would be unsupported. Tied MAP indices must remain unresolved; a first-index argmax can otherwise report zero error on a completely uniform posterior.

## Reproduced findings and targeted diagnosis

| Condition | Reproduced baseline result | Meaning |
|---|---|---|
| Strong signal, matched scalar family |40/40 unique MAP within 100 m; median 0 m; true grid point in 90% set 40/40 |Useful on this favorable same-physics fixture; not independent transport validation |
| Weak signal |6/40 within 100 m; median 128.06 m; median 90% set contains all 9 grid points |Ambiguity is mostly preserved; low localization success alone is not a coding defect |
| Biased direction |True grid point in 90% set 10/40; median error 128.06 m; zero alarms |Truth uses 310° while available wind is 270° and prior reaches only ±12° |
| Biased speed, seed 220023 |Wrong grid point 100 m away has 0.9769725167 weight; no alarm; 90% set excludes truth |Speed is 4.6 m/s versus observed 2.3; magnitude/strength confounding and narrow discrete prior |
| Two sources |Zero alarms 40/40; residual standardized RMS range 0.996–2.167, median 1.632 |A diagnostic false-negative family; fitting dominant grid point is not source multiplicity detection |
| Off-grid source |Median MAP error 80.62 m; no calibrated region coverage reported |Truth is absent from location support; a set of grid IDs cannot cover it |
| Completely ambiguous/upwind layout |All 9 MAP points tied 40/40 |Zero first-index argmax error is meaningless; unique localization count is zero |
| Unsupported weather/data |160/160 source analyses refused, no crashes |Capability refusal, not successful localization |

The independently written scalar generator evaluates the same transport assumptions as inference. It checks implementation consistency but shares fixed heights, neutral dispersion and steady release; it does not remove inverse-crime concerns.

The weak-signal fixture's true plume increments are approximately `[0.000031, 0.000618, 0.010250, 0.000327]`µg/m³, against independent noise sigma 1 µg/m³ plus shared error. The direction-bias fixture's true plume increments at the four monitors are all ≤1.1×10^-20µg/m³. The latter is essentially a background-only observation pattern while every available source explanation assumes positive emission and a different wind. These are different causes: missing information versus missing model support.

At speed-bias seed 220023, fitted RMSE is 2.076 µg/m³ and standardized RMS 1.004 despite the wrong location's 97.7% conditional weight. This is not a floating-point alarm defect. The kernel depends on the ratio `Q/u`; an audit toy with `(Q,u)=(5000,2)` and `(10000,4)` gives exactly the same concentration. The finite strength/speed grid can force amplitude adjustments into a location shift. The 100 m error is stored as 100.000000000165 m; a strict `error>100` flag is sensitive to projection rounding. Wrong-grid identity, separately stored, confirms the scientific error without relying on that cutoff.

The second source adds approximately `[0.0011,7.9211,1.8376,6.9918]`µg/m³ at the monitors. Its contribution is not uniformly negligible. Yet the one-source nuisance mixture and assumed correlated error fit it well enough to evade the in-sample threshold. Lowering the threshold using these 40 cases would not establish multiplicity detection and would need a separate false-alarm analysis.

Selection toy: 240 validly stored readings across four sensors / 59 minutes contain an unselected 40 µg/m³ transient at 10:01 UTC. The 40-row subset produces standardized RMS 0.757 versus 2.578 under practical full 240-row inference. Both remain below the old alert threshold. The transient violates steady-release assumptions; this toy demonstrates loss of a potentially diagnostic episode, not recoverable source truth or a new valid operating regime. Full numerical outputs and both posterior vectors are saved in `diagnostic-toys.json`.

Paired follow-up findings also reproduce exactly. In matched strong signal, the optimizer improves entropy more than the 20-random-plan mean in 27/40 runs but gives worse held-out prediction RMSE in 13/40; six runs increase location entropy. In matched weak signal the mean entropy advantage is only 0.000702 nats and RMSE is worse in 16/40. Under the deliberately mismatched strong error model, 3/40 optimized outcomes assign >90% weight to a wrong grid point. These outcomes reject a general recommendation-benefit guarantee; they do not imply every optimized plan is useless.

The largest repeated workload loads 10,000 readings and 10,000 weather records, validates the full window, then fits 40 rows/1,350 scenarios. The reproduced resource timings/memory are in `resources.json`; loaded-row throughput must not be described as full 10,000-row inversion. Peak memory should use per-process `/proc/self/status` VmHWM, since inherited process high-water marks can inflate `getrusage` values.

## Ranked causes and what is still a hypothesis

1. **Confirmed model-support limitation:** no zero-source/background-only competitor, finite positive strength/background grid, narrow meteorological perturbations, no second source, and point-only source support. Consequences are visible in direction/speed/off-grid/no-source reasoning. Broader support and competing explanations require independent usefulness tests; merely widening every posterior is not a solution.
2. **Confirmed diagnostic limitation:** same-fit residual RMS and threshold 3 miss all constructed two-source cases and the wrong sharp speed case. Out-of-sensor/time predictions and explicit false-positive/miss-rate evaluation are necessary; no diagnostic can identify observationally indistinguishable physics.
3. **Confirmed low identifiability:** the weak fixture has effectively no concentration signal at its sensors. Better implementation cannot infer an absent signal. Recommendations must be evaluated by revealed outcomes and low-signal usefulness, rather than confident MAP reporting.
4. **Confirmed selection limitation:** deterministic time quantiles can omit a rare diagnostic episode. Compare selection with full inference and sample-size sensitivity; report loaded/excluded/fitted counts separately, and evaluate whether selection preserves weather/concentration events without consulting hidden truth.
5. **Confirmed objective/interpretation gap:** moment information, conditional scenario mass and a grid point set are not realized benefit, calibrated geographic responsibility or geographic coverage. Improve their definitions and product wording alongside independent outcome tests.
6. **Plausible, uncalibrated physical causes:** wrong noise correlation times/lengths, sensor offsets/drift/humidity response, background variation, stability/height errors and variable emissions. These were not individually identified from the existing observations. Strong model support under a false physical family remains possible.
7. **Not supported as present defects:** reversed wind convention, projection axis swap, unit scaling, timestamp offset loss, likelihood underflow/normalization failure, independent-row covariance, unconstrained budget violations, or future truth entering the current paired planner. Existing oracles and source inspection support their implementation, within tested cases.

## Measured-data status and interpretation

The preserved London audit actually inspected 65,533 openair Marylebone hourly records, including 56,758 nonmissing PM2.5 values; upstream revision and data hash are in the original external JSON. Coordinates and independent release truth were absent. All 65,533 incomplete-coordinate rows were rejected in bounded import batches. This supports a provenance/data-quality audit, **not source-localization accuracy**. Urban roadside monitoring also differs from neutral open-terrain point-release assumptions.

Official NOAA DATEM/Project Sagebrush and EPA routes were blocked by the environment's CONNECT 403 policy in the earlier acquisition attempt. Their current access status and any new files must be checked separately. No station coordinates, release truth, units or licenses may be invented; no acquired tracer success would automatically establish neighborhood PM2.5 attribution.

Baseline product judgment: a reproducible research prototype and functional investigation/import/geometry tool. It does not yet support unsupervised source-responsibility conclusions, calibrated geographic uncertainty, future sampling schedules or a general claim that recommended measurements improve source localization. The redesign's acceptance must depend on fresh campaign/layout/weather-family evaluation with prediction, region area/coverage, false alarms, misses, retention and realized planning outcomes reported together.
