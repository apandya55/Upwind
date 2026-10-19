# Science, algorithms and evidence status

Current scientific identifier: `plume-ensemble-0.2.1`. See [STRESS_REPORT.md](STRESS_REPORT.md) and [STRESS_PROTOCOL.md](STRESS_PROTOCOL.md) for measured results and preserved failures; application package version remains 0.1.0.

## Evidence levels

| Capability | Current evidence |
|---|---|
| CSV validation, projection/wind conventions, budget and eligibility | Automated contract/numerical checks |
| Measured-point map and arithmetic-mean timeline | Functional browser checks; instrument validity remains the user's responsibility |
| Spatial coverage planning | Deterministic geometric objective; not validated as pollution-exposure benefit |
| Steady single-source scenario engine | Synthetic only; nominal identifiable fixture failed reliable localization |
| Information-based planning | Approximate utility comparisons; prospective or independent follow-up benefit untested |
| NOAA tracer / real PM2.5 source accuracy | Unavailable; external acquisition blocked and no independent source truth |
| Partner usability or adoption | Unperformed |

Conditional model weights can be broad, or confidently wrong under mismatch. No facility proximity is used as causal evidence. PM2.5 concentration does not identify chemical composition or an odor's cause.

## Units and coordinates

WGS84 longitude/latitude are transformed with `pyproj`, `always_xy=True`, to a local azimuthal equidistant metric system centered on the source-grid centroid. x=east, y=north, distance=metres. Geometry is bounded to source radius 1.5 km and receptor radius 3 km; the approximation is deliberately local. The map's degree grid is for navigation, not physics.

Meteorological angle θ is **from** clockwise from north. Downwind unit vector is `f=(-sin θ,-cos θ)`. Thus wind from 270° flows east, and wind from 0° flows south. Downwind distance is `(receptor-source)·f`, crosswind is the projection onto `(-f_y,f_x)`. Upwind predictions are zero plume contribution, not zero total concentration. Independent tests check cardinal directions, length scales, linear emission scaling, inverse wind scaling, and a direct equation calculation.

All concentrations µg/m³, release Q µg/s, speed u m/s, fixed release height H=5 m, receptor height z=2 m. These heights are assumptions, not inferred facility data.

## Educational Gaussian baseline

For downwind distance x ≥20 m, total prediction is background b plus:

```
C = Q/(2π u σy σz) × exp(-y²/(2σy²))
    × [exp(-(z-H)²/(2σz²)) + exp(-(z+H)²/(2σz²))]
σy = 0.08x / sqrt(1+0.0001x)
σz = 0.06x / sqrt(1+0.0015x)
```

These are commonly used rural neutral dispersion approximations, not new physics or a regulatory implementation. Outside 20 m downwind or 3 km Euclidean range, plume contribution is zero by the **bounded model**, not a claim that physical pollution vanishes. Source grids or candidate sites near these boundaries need review. The current engine refuses receptor/source study extents outside its supported range; candidate sites outside 3 km cannot receive meaningful source information. No street canyon, deposition, chemistry, intermittent emissions, stability transitions or multiple-source inversion is modelled.

Required user assertions: steady wind/release, open approximately neutral terrain, and representative local weather. Each retained reading needs a weather record within 30 minutes and 3 km. The nearest in time qualifying record is used, breaking ties by spatial distance and canonical record order, with no interpolation. Every relevant local wind record within the full observed window is checked, including records between selected readings. Conflicting duplicate meteorology is refused. Nominal wind must be 0.8–8 m/s, circular directional deviation ≤25°, speed max/min ≤2, and selected readings must span ≤1 hour. A distant station is not silently substituted. Assertions and recorded weather do not establish neutral stability; independent meteorological judgment is required. This is a conditional experiment.

## Ensemble and likelihood

A uniform prior over each declared location and nuisance grid:

- Q ∈ {1500, 5000, 12000} µg/s;
- b ∈ {4, 10, 18} µg/m³;
- wind offset ∈ {-12, 0, 12} degrees;
- wind-speed multiplier ∈ {0.85, 1.15}.

At most 25 locations ×54 =1350 scenarios. Nuisance parameters are shared within a scenario, not independently fitted at every monitor. The uncertainty grid is a declared sensitivity approximation, not a weather forecast; its speed multipliers are retained only when all relevant nominal speeds remain inside supported bounds (truncation of the scenario prior, not clipping measured wind). The release range is deliberately limited and may exclude reality.

For observation vector y and scenario predictions μ, `log L=-0.5(y-μ)ᵀΣ⁻¹(y-μ)`. Σ has per-reading supplied uncertainty (otherwise the explicit user setting, default 2 µg/m³) squared on the diagonal, a shared 1 (µg/m³)² instrument-bias covariance within each sensor, and `default_noise² exp(-distance/150m)` spatial model-error covariance shared over the window. This spatial kernel is an assumption, not field calibration. Supplied per-reading uncertainty is supported between 0.01 and 1000 µg/m³; more extreme values are rejected rather than silently floored or overflowed. Thus repeated readings are not independent instrument calibrations. Weights use log-sum-exp normalization. Location weights sum over all nuisance combinations. No fitted background or strength is silently treated as known source location.

At most 40 balanced, time-quantile rows are used for bounded inference, retaining every sensor (at most 40 distinct sensors); full-window geometry/weather/time consistency is checked before sampling; all originals remain in the investigation. Negative, duplicate and >500 µg/m³ review-flagged rows are excluded from fitting, never erased. Out-of-order rows are flagged and retained. The extreme-value threshold is a review heuristic, not a claim that severe pollution is impossible. Identical duplicate sensor/time pairs are deduplicated for inference; conflicting valid concentration/location/uncertainty/origin groups are quarantined, independently of file order, while every raw row remains preserved. Hypothesized source locations must be at least 1 m apart. Every observation/source pair must be 20 m–3 km; unsupported pairs refuse reconstruction, and unsupported candidate sites are excluded consistently for every planning method. Dates are stored UTC; ambiguous/nonexistent daylight-saving naive times require explicit offsets.

RMS of Cholesky-whitened in-sample residuals >3 adds a mismatch warning, using the supplied observation uncertainty and correlated covariance. Raw RMSE remains reported in µg/m³. The previous default-noise-only diagnostic incorrectly warned on legitimate larger reported uncertainty; its first-run outcomes are preserved. This heuristic cannot detect all wrong models; particularly weak-signal multiple-source cases can fit without a warning. A mixture mean's fit is not independent predictive validation.

## Planning objectives

Only candidate sites with permission, power/battery, safe access, the supported observed window, and affordable cost are eligible. Existing monitors are never purchased again. Equipment limit ≤8; sites ≤100. Plans use the same feasible set across methods.

For source-location utility, obtain candidate predictions under posterior scenarios. Decompose their moment covariance into between-location B and within-location nuisance W. Future instrument/model error is:

`N_ij = noise² [I_ij + exp(-distance(i,j)/150m)] + I_ij × 1 (µg/m³)²`

The last term represents independent new-instrument bias; the spatial component reduces pseudoreplication of adjacent sites. The score uses Cholesky whitening and `log1p` eigenvalues, avoiding subtracting two large log determinants.

For selected subset A, the **Gaussian-moment location-information approximation** is:

`U(A)=0.5[log det((B+W+N)_A) - log det((W+N)_A)]`, in nats.

This is an approximation to discrimination between discrete location-conditioned predictive mixtures, not exact expected information gain. Nuisance covariance competes with location signal; model-error correlation reduces credit for nearby sites. Tests ensure identical-site observations do not earn twice the independent score. This covariance is assumed, not empirically calibrated. Non-Gaussian mixtures may be badly represented by moments.

For spatial coverage, with all permissible candidates as geometric targets, independently of the current budget and existing monitors as anchors, use mean `exp(-distance_to_nearest_monitor/400m)`. Utility is its increment from adding selected sites. The 400 m length is an explicit design heuristic, not an air-quality representativeness standard or exposure model. It needs no weather, readings, or source grid.

Search all budget-feasible subsets for ≤12 candidates, including empty, up to the equipment limit; report ties within 1e-10. Larger cases take the best planning utility among cost-normalized greedy selection and the supplied spread/wind/20-seed random baseline envelope, with deterministic ID ordering and no global optimality claim. This guarantees no lower utility than those computed baselines up to the numerical tie tolerance, not better realized outcomes. The empty set may be optimal when no information gain exceeds the 1e-10 tie tolerance; this is reported as `uninformative`, separately from infeasible constraints. Spatial coordinates are centered independently of input site order. Source-grid MAP ties are explicitly unresolved sets; choosing the first tied index is not localization evidence. Baselines: shuffled affordable sequential selection across 20 recorded seeds; maximin separation from existing/selected monitors; and rank by downwind minus absolute crosswind distance from the **unweighted** source-grid centroid. Wind baseline is available only with supported weather. Random result shows seed 42's plan plus mean/min/max across 20 seeds, not a fabricated average plan.

## Reproducibility and evaluation

Schema-normalized input JSON + model version determine a SHA256 analysis hash (numeric defaults are canonicalized across archive round-trips); an in-process LRU holds 32 analyses. Changes to imports/settings/constraints invalidate it. Cached result runtime describes the original computation. There is no LLM in the numerical path. Synthetic noise uses NumPy seeds; hidden truth is a separate evaluator object. All scenarios and fixtures are simulated, including source coordinates.

Read [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md) for metrics chosen before evaluation, [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md) for results, and the full JSON in `evaluations/`. The nominal identifiable fixture's plume increments are small relative to noise; its failure is retained, not fixed by tuning to the held-out outcomes. A high-signal benchmark and independent real-world benchmark remain future work and require a new protocol/version. No broad weights or truth-containing set is evidence of useful real-world localization.
