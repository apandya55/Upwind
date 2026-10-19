# Science, algorithms and evidence status

Scientific identifier: **plume-campaign-0.4.0**; application package0.1.0. This is a research prototype with synthetic evaluation, not field-calibrated attribution. Current equations and implementation map: [RESEARCH_IMPLEMENTATION.md](RESEARCH_IMPLEMENTATION.md). Fresh evaluation design: [RESEARCH_EVALUATION_PROTOCOL.md](RESEARCH_EVALUATION_PROTOCOL.md). Historical0.3 equations are preserved [in the baseline snapshot](../evaluations/research/baseline-source/docs/SCIENCE.md); their results are not current performance claims.

## Scientific meaning

A correct calculation is not evidence that its physical assumptions describe a particular campaign. Identifiability asks whether the observations distinguish locations, release strengths, backgrounds and weather errors. Predictive accuracy asks whether withheld concentrations are predicted. Geographic coverage asks whether a conditional source region actually contains a simulated source. These are separate tasks. PM2.5 alone cannot identify chemical composition, an odor's cause, or responsibility for a release.

Source-family weights compare background-only with one steady release, with prior probability0.5 each. They are conditional on that restricted list and a declared search domain. The region is a union of whole quadrature cells accumulating at least90% of the **conditional single-source** mass. It is not an independently calibrated geographic confidence region. A source outside the domain, another source count, incorrect weather or changing release can produce misleadingly sharp results.

The unchanged interpretive label `source_supported` requires source-family weight≥.9, region<half the supported area and no detected predictive mismatch. This is an experimental model rule, not validated accuracy. Every measurement recommendation remains `research_only`. No warning means no detected disagreement in the checked blocks; it is not an adequacy certificate.

## Transport and declared inputs

Coordinates are WGS84, projected into a local azimuthal equidistant metric system with x east/y north and `always_xy=True`. Meteorological wind is degrees **from**, clockwise from north, giving flow(-sinθ,-cosθ). West wind270° flows east. Times require explicit offsets and normalize to UTC.

The ground-reflected neutral Gaussian approximation is

```
C = Q/(2π u σy σz) exp(-y²/(2σy²))
    [exp(-(z-H)²/(2σz²)) + exp(-(z+H)²/(2σz²))]
σy=.08x/sqrt(1+.0001x), σz=.06x/sqrt(1+.0015x).
```

Concentration isµg/m³; Qµg/s; um/s; distances/heights metres. H(default5m) and z(default2m) are declared assumptions, now editable. No validated deposition, chemistry, urban canyon, intermittent-release or multi-source inverse model is implemented. The kernel has zero plume for downwind x<20m; background still contributes. Every source/receptor pair must have radial separation20–3000m. Receptors are within3km and anchors within1.5km of the study projection origin. Unsupported pairs/cells are explicit exclusions, not evidence of impossible real sources.

Single-window studies retain the one-hour limit. Campaigns require2–6 explicit, nonoverlapping individually steady periods, each≤1hour, spanning≤14days, and an explicit fixed-location/constant-Q assumption across periods. There is no automatic splitting, transition transport or inferred release history. Each observed period requires≥2 usable sensors. Weather is checked separately within each period: measured records within30minutes/3km, speeds .8–8m/s, directional deviation≤25°, speed ratio≤2. Unsupported weather refuses physical inference; geometric coverage remains available. No future measured weather is used in plans.

Angular error is coherent across the campaign: seven offsets scaled by the declared direction standard deviation(default20°); three speed scenarios(default .7/1/1.3) scaled by a declared fraction(default.3). Documentation/provenance accompanies these inputs; small declared uncertainty is not an inferred calibration. Real meteorological errors outside this distribution can invalidate source regions even when predictive checks do not warn.

## Inference and numerical integration

Background intercept N(10,20²) and trend N(0,10²)µg/m³/hour are integrated analytically, independently by campaign period. Instrument bias N(0,1²) persists across all periods. Correlated model error has covariance noise² exp(-distance/150m-|Δt|/600s); independent reading variance uses supplied uncertainty or the explicit noise setting. Absolute elapsed time is preserved across periods. These are assumptions, not fitted instrument calibration.

Positive source strength has HalfNormal(scale30000µg/s) prior. Its marginal likelihood includes Gaussian normalization, determinant terms and the truncation normalizer. Source/weather weights use log-sum-exp. Because the kernel depends on Q/speed-scale, an exact change of variable integrates effective strength with prior scale30000/speed-scale; unique location/direction matrix columns are solved once. No speed scenario or posterior mass is discarded by this optimization.

Area-uniform location prior covers the rectangle spanned by anchors. Cells target20m, capped at24 per axis. Campaigns integrate four equal-weight tensor Gauss–Legendre nodes per cell; single-window studies retain midpoints. Report numerical resolution, excluded area, actual mass and region area. Refinement can change modes; these are finite integrals, not continuous optimization guarantees. Degenerate domains retain an explicitly discrete model and zero geographic area.

New predictive means/covariance integrate the exact truncated-strength mixture. Predictive marginal log densities use a Gaussian conditioning/truncation identity. Predictive intervals and joint checks use2048 scrambled Sobol draws from that distribution. Finite integration remains. The retained information planner uses Gaussian component moment matching; it is labeled as an approximation. See the implementation document for derivations and independent checks.

## Adequacy, observability and selection

Predictive screens withhold complete sensor blocks and, for campaigns with≥3 observed periods, complete periods' concentrations. Recorded weather remains available retrospectively. Held-period tests project out an unknown constant background and linear trend and compare joint spatial contrasts. Budget: at most six refits (single: six sensors; campaign: three sensors plus three periods), at most24 held readings/block. Above24 instruments, period checks sample24 evenly from sorted IDs; all held-period concentrations remain excluded from training. Checked/total counts and unavailable blocks are explicit. The1% familywise Bonferroni screen is an uncalibrated diagnostic under the model and finite integration, not a field false-alarm guarantee. Observationally equivalent sources cannot be reliably distinguished by this screen.

The nuisance-profile diagnostic independently fits unrestricted per-period background/trend and nonnegative effective strength over all source/direction grid configurations, using correlated residual covariance. Its Δχ²4.605 compatible-area fraction is a descriptive sensitivity diagnostic, not a p-value or confidence region. Huge profiled strengths can expose prior/geometry sensitivity. Local Fisher axes describe only local curvature; distant equivalent locations may remain.

Raw inputs and row origins are retained. Quality review excludes negative, contradictory duplicate and flagged extreme readings; identical duplicates deduplicate. Default inference uses at most128 rows, adjustable40–512. Campaign sampling balances sensor×period groups, retaining every group or explicitly asking for a larger limit; it retains departure/endpoints/extrema then seeded temporal strata. All usable geometry/weather are checked before sampling. A10,000-row import is not a10,000-row inversion. Severe real events require review of the existing >500µg/m³ exclusion heuristic rather than interpreting it as physical impossibility.

## Planning and supported decisions

The new optional `prediction_variance` objective maximizes mean Bayes-linear prediction-variance reduction C_TA C_AA^-1 C_AT at all permissible supported candidate receptors. Targets are separate instruments: independent observation noise/bias does not receive credit as learning. The target universe does not change with affordability or selected sites. All posterior mixture moments enter; there is no component reduction or Monte Carlo objective. Exact tiny-case subset search and an independent linear-prediction simulation check the objective. It is not exact nonlinear Bayes risk, a localization objective, or a promised field improvement.

The original information objective, geometric coverage, spatial spread, wind and random baselines remain named options under the same constraints. Plans refer to hypothetical simultaneous measurements at the last usable **recorded** timestamp, with IDs `followup-{site ID}`. Updating at a future timestamp, with another instrument or different weather is a different experiment. No future scheduling, movement/deployment optimization or guaranteed percentage gain is provided.

## Evidence and limitations

Prior results are preserved; the current protocol separates fresh development/calibration/final seed blocks and holds out layouts, wind regimes and an independent transverse-diffusion generator. Compatible-kernel controls test arithmetic under assumptions; synthetic mismatch tests expose conditional failures. They do not validate urban PM2.5 or regulatory attribution. Measured tracer validation remains blocked by NOAA CONNECT403; [the exact retry record](../evaluations/research/external-retry.json) contains the errors. London data without source truth remain import/data-audit evidence only. See [ENGINE_RESEARCH.md](ENGINE_RESEARCH.md) for actually inspected primary/official sources and licenses. No partner adoption or government certification is claimed.
