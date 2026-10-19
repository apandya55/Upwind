# Science, algorithms and evidence status

Scientific identifier: **plume-mixture-0.3.0**. Application package remains 0.1.0. The implemented model is a research prototype; source weights and geographic regions have no demonstrated field calibration. Read [ENGINE_AUDIT.md](ENGINE_AUDIT.md), [ENGINE_EVALUATION_PROTOCOL.md](ENGINE_EVALUATION_PROTOCOL.md), and [ENGINE_DEVELOPMENT_COMPARISON.md](ENGINE_DEVELOPMENT_COMPARISON.md). The preserved `legacy.py` implements 0.2.1 for comparisons; previous reports remain historical evidence, not current performance claims.

## What is and is not established

Implementation correctness concerns whether code computes these equations. Model adequacy concerns whether these equations can represent a particular investigation. Identifiability concerns whether its readings distinguish the explanations. Empirical reliability requires independent predictive and geographic coverage evidence. Passing numerical tests establishes neither physical adequacy nor responsibility for pollution. PM2.5 mass alone cannot identify composition, an odor's cause, or a facility's responsibility.

Measured points, resident accounts and inferred explanations remain distinct. Instruments require independent calibration and representativeness review. CSV/provenance, constraints, geometric coverage and local save/export workflows are tested software capabilities. No controlled-release or real-neighborhood source accuracy has been validated. London records support only the documented data audit, not source localization. NOAA DATEM/Sagebrush acquisition is still blocked; exact routes, source documents, licenses and responses are in [ENGINE_RESEARCH.md](ENGINE_RESEARCH.md).

## Coordinates, time and transport

WGS 84 longitude/latitude are projected to a local azimuthal equidistant metric system at the coordinate-sorted anchor centroid, `always_xy=True`. x is east, y north, metres. Meteorological θ is degrees **from**, clockwise from north; the flow vector is `(-sin θ,-cos θ)`. Wind from 270° flows east; from 0° flows south. Timestamps require explicit offsets and normalize to UTC. Weather matching uses integer UTC microseconds; covariance uses elapsed seconds.

The transport kernel is unchanged from the audited ground-reflected neutral Gaussian baseline:

```
C = Q/(2π u σy σz) exp(-y²/(2σy²))
    [exp(-(2-5)²/(2σz²)) + exp(-(2+5)²/(2σz²))]
σy = .08 x / sqrt(1+.0001 x)
σz = .06 x / sqrt(1+.0015 x)
```

Concentration is µg/m³, Q µg/s, u m/s, fixed release height 5 m and receptor height 2 m. Heights are assumptions, not inferred metadata. Downwind x<20 m gives no plume contribution; a receptor must also lie 20–3000 m in radial distance from every supported source cell. Upwind zero plume is not zero total concentration. No deposition, chemistry, urban canyon, intermittent release or multi-source inverse model is implemented. The study is bounded to 3 km receptor radius and 1.5 km anchor radius. Changing release behavior is a mismatch challenge, not a supported forecast.

User assertions of steady release/wind, approximately neutral open terrain, and local representative weather remain required. They do not establish physical validity. Every usable reading needs measured weather within 30 minutes and 3 km; nearest time then spatial distance then canonical ordering breaks ties. No interpolation or substitute measurements are invented. All relevant local records in the full loaded time window, including those between fitted readings, must satisfy .8–8 m/s, direction deviation ≤25° and speed max/min ≤2. At most one hour is supported. Unsupported weather refuses reconstruction; geometric coverage can still operate.

## Competing explanations and nuisance integration

The prior assigns 0.5 each to background-only and one steady release. This is an explicit research prior, not field prevalence. A source-model weight compares only these explanations; a low weight does not prove no pollution, and a high weight does not rule out multiple sources.

Background intercept `b ~ Normal(10,20²)` µg/m³ and a centered linear trend `a ~ Normal(0,10²)` µg/m³ per hour are integrated analytically, not optimized and treated as known. Normal priors can include negative background tails; this is a local additive statistical approximation, not a physical assertion of negative concentration. Source strength `Q ~ HalfNormal(30000)` µg/s is also integrated, replacing the restrictive three-value strength/background grid.

A coherent wind offset shared across the window takes {−45,−30,−15,0,15,30,45}° with weights proportional to `exp(-offset²/(2·20²))`. Speed multipliers {.7,1,1.3} have prior {.25,.5,.25}; unsupported multipliers are removed and renormalized after checking every nominal speed. These are sensitivity priors, not an observed forecast or calibrated meteorological error distribution. No measured wind is clipped. All priors and constants are in `inference.CONFIG`.

Let R be measurement and discrepancy covariance, t centered time in hours, g the unit-strength plume at a location/weather component. Integrating intercept and trend gives:

```
C0 = R + 20² 11ᵀ + 10² ttᵀ
r = y - 10
A = 1/30000² + gᵀ C0⁻¹ g
m = (gᵀ C0⁻¹ r)/A; s²=1/A
log Lsource = log N(y;10,C0)
              -.5 log(A·30000²) + .5(m/s)² + log 2 + log Φ(m/s)
Lbackground = N(y;10,C0)
```

The truncation normalizer matters. Log determinants and Gaussian normalization are retained for comparisons; weights use log-sum-exp. Cholesky solves replace explicit inverses. Source posterior moments are those of `Normal(m,s²)` truncated at zero, with stable negative-tail formulas. Independent numerical integration checks evidence, weather weights, predictive means and covariance, including far-tail moments. These small checks verify computations only.

## Correlated readings and prediction

Before integrating background/trend:

```
Rij = measurement_sigma_i² δij + 1² I(sensor_i=sensor_j)
      + noise_setting² exp(-distance_ij/150 m - |time_i-time_j|/600 s)
```

Supplied reading uncertainty is used, otherwise the explicit setting (default 2 µg/m³). Sensor bias persists within the window. The separable space/time kernel is an assumed discrepancy model, not learned field calibration. Its 600 s timescale is a material assumption; persistent error, calibration offsets, humidity response and different correlation lengths are sensitivity challenges. No data-driven humidity correction is invented; recorded high humidity prompts instrument review.

Future/background error is conditioned on the observed residuals through its cross covariance, including shared instrument bias if an instrument ID recurs. The old planner omitted this conditioning. Conditional source strength has a truncated-normal posterior; production predictions moment-match each such component by a Gaussian. The overall prediction is a weighted Gaussian mixture. Its means and covariance match integrated moments, but its tails need not equal the exact truncated-strength predictive distribution. Predictive intervals, log scores, adequacy flags and acquisition therefore have this additional approximation.

Adequacy screening withholds entire sensors, refits on the others, and predicts the withheld readings. At least three usable sensors are required. Cost is bounded to six deterministically selected sensor blocks and up to 24 readings per block; unchecked counts and unavailable blocks are explicit. A 1% Bonferroni marginal-tail screen accounts for the number of screened readings without assuming independence. Its nominal threshold is a screening rule, not empirical field calibration. No warning is an absence of detected conflict, not an adequacy certificate. The in-sample standardized residual remains a descriptive compatibility field and no longer drives the warning. A single-source model can miss a second source that is observationally similar.

## Continuous search domain and region meaning

Marked locations now serve as **domain anchors**, not known facilities or equally likely responsibility candidates. Their local metric bounding rectangle defines the continuous location prior, uniform in area. It is divided into cells targeting 20 m side length, capped at 24 cells per axis. Midpoints approximate the spatial integral. The cap and midpoint approximation can miss narrow likelihood structure; this is a numerical limitation, not calibrated spatial resolution. Degenerate rectangles retain an explicitly discrete anchor model with zero geographic area.

Cells whose **whole extent** lies outside the radial 20 m–3 km transport support at any usable reading are excluded; near-field cells at declared sensor positions are also excluded so sensor-block holdout does not change the prior using withheld concentrations. Excluded area is reported and warnings identify it. A source outside supported cells has no coverage claim. Candidate receptors must satisfy the same support for every retained cell, consistently across placement methods. Such exclusions can remove sites that the old sparse-grid model allowed.

The region is the union of whole cells, sorted by conditional single-source posterior weight until accumulated mass is at least 0.9. It is conditional on one source inside the supported domain and the declared priors/physics. Report area, supported domain area, excluded area and cell side length together. Its nominal 90% label is **not** measured 90% geographic coverage. Independent continuous-truth tests measure actual coverage, including failures. Old sets of scenario IDs have no geographic area meaning.

Legacy-shaped `sources[].weight` now sums cell mass into nearest-anchor partitions, conditional on a single source. It is not weight at the anchor point. These partitions are only a coarse target for readable comparisons and acquisition. The UI removes point-probability map labels and displays domain anchors and region cells.

`evidence_status=source_supported` means source-family weight≥.9, conditional region<half supported domain, and no predictive-screen warning. This is an interpretive rule under the model, not a calibrated accuracy guarantee. A mismatch is displayed separately; all other cases remain ambiguous. Predictions and raw scores remain available for research rather than dropping difficult cases from evaluation. All placement results carry `recommendation_status=research_only`.

## Loaded, excluded and fitted rows

Raw imports/origins/hashes remain lossless. Negative, >500 µg/m³ review-flagged and contradictory duplicate rows are excluded from fitting; identical duplicates deduplicate. Extreme-value exclusion is a review heuristic, not proof severe pollution is impossible. Conflicts are order independent. Loaded, quality-excluded, usable and fitted counts are separate.

The default fitting limit is 128, configurable 40–512. All usable rows are fitted below the limit. Above it, round-robin per-sensor quotas retain every sensor. Within a quota the greatest departure from that sensor's median, first/last times and minimum/maximum values are prioritized; remaining slots use seeded chronological strata. Small quotas cannot retain every anchor or rare event, and an extreme observation can be noise. The sampler is reproducible and input-order independent, not an unbiased or sufficient approximation to full-data inference. All-window weather/geometry are checked before selection. The full 512 versus selected comparisons and rare-episode misses are reported; a 10,000-row workload is never labeled a 10,000-row inversion.

## Measurement design and baseline

Plans are simultaneous hypothetical measurements at the last usable timestamp of the selected **observed** window, with weather matched from its recorded data. New instrument IDs are `followup-{site ID}`. Appending outcomes at that timestamp with those IDs defines the update. This is retrospective design research, not scheduling, travel routing or use of future observed weather. The user must supply site access/permission/power/window feasibility; there is no inferred travel-time allowance.

The target is background-only versus nearest-anchor partitions. Unlike the old between-mean Gaussian logdet score, numerical mixture information can distinguish equal-mean distributions with different spread and cannot exceed its represented group entropy. It estimates prior group entropy minus expected posterior group entropy under the conditional Gaussian-component predictive mixture. Scrambled Sobol integration uses 128 draws per replicate and two replicates; at most 128 weighted-quantile representative components preserve every positive coarse group's total weight. Source-cell uncertainty within an anchor partition is not the acquisition target.

The score's finite component approximation can discard substantial original component mass. Metadata retains original/represented counts and mass, component total variation, group priors, numerical budgets, raw negative estimates and replicate disagreement. Replicate agreement does not bound systematic approximation error. Sensitivity tests measure plan changes at larger budgets. Numerical integration estimates may be negative; raw scores are preserved, including in archives, rather than clipped to imply precision.

Feasibility is shared across every method. Search all budget-feasible subsets when the combinatorial upper bound is≤256, including empty. Larger problems compare cost-normalized greedy with spread, wind and 20 random baselines; this is a heuristic, not global optimality or realized benefit. Canonical site/anchor ordering makes finite integration reproducible under reordered inputs. Geometry baseline remains mean `exp(-nearest monitor distance/400 m)` over all permissible targets independent of affordability. This transparent geometric heuristic needs no pollution model and establishes no exposure benefit.

Realized placement evaluation locks all methods before revealing candidate outcomes, appends the same realized readings for shared sites, refits, and scores independent target predictions and continuous-source errors. Perfect-weather oracle claims, expected health benefit and guaranteed percentage improvement are unsupported.

## Reproduction

Read [ENGINE_EVALUATION_PROTOCOL.md](ENGINE_EVALUATION_PROTOCOL.md) for splits, independent transport families and frozen metrics. Old examined cases are development-used. Primary source/evaluation hashes, dependency versions, commands and all refusals/failures are saved under `evaluations/overhaul`. Schema-canonical input JSON plus model identifier determines the analysis hash; an LRU 32 cache returns copied JSON results. No LLM or evaluator truth enters inference/planning. Reports, evidence labels and scientific product judgment must follow the saved numerical evidence.
