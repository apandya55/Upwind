# v0.9 source strength and location diagnosis

This evaluator-only study investigates the six prior-sensitive synthetic
ladder cases. It changes no inference rule, prior, acceptance threshold, or
held-out seed. Raw generated observations and sensor layouts, fitted locations
under all three release-scale settings, profile maps, controlled nuisance
repeats, and the off-grid reference are in
[`strength-location-final2`](../evaluations/engine-v09/strength-location-final2/).
Earlier `strength-location*` directories are retained as exploratory
diagnostics; `final2` corrects two evaluator errors (stale truth coordinates
after replacing the synthetic source, and a shifted ideal-control domain).

## Diagnosis

The six cases are dominated by likelihood ambiguity and nuisance mismatch,
with the release prior selecting different points along broad likelihood
ridges. A separately constructed ideal off-grid case also demonstrates a
large prior effect: its known-strength/background likelihood map recovers the
source within one half of the 6.67 m grid spacing, while the default
marginalized posterior is displaced by about 34 m. No production numerical or
algebra defect was demonstrated, so production code and support rules were
left unchanged.

The production release prior is `Q ~ HalfNormal(30,000 µg/s)`. The sensitivity
settings `[0.1, 1, 10]` multiply that scale, yielding 3,000, 30,000 and
300,000 µg/s. They do not multiply observations, likelihood, or fitted Q.
Wind speed scale `s` is handled by the exact variable change `Q_eff=Q/s`, so
the effective HalfNormal scale is `tau/s`. Its normalization and positive-tail
normalizer are included in the marginal likelihood. The source-cell prior is
uniform in area; tensor Gauss nodes each carry one quarter of their cell's
area mass. Background intercept/trend are integrated as Gaussian nuisances.
The continuous profile maps instead optimize nonnegative Q and free background
by GLS under the same observation covariance. Their residual loss is a
chi-square-style GLS sum, not the marginalized posterior score.

## Six cases

Truth for the five strong-source variants is `(-83.3, 158.3) m` in the
production local projection and `250,000 µg/s`. The additional-sensor variant
uses the same source and adds one sensor. Locations below are posterior means;
the exact density modes, observations, sensors and all three means are retained
in `six_cases.json`. Region area is the finite 90% highest-density region as a
fraction of supported domain area. Errors are evaluator-only distance to the
synthetic source.

| Case | Mean location, factor 0.1 / 1 / 10 (m) | Default mean error | Mode error | Region area |
|---|---|---:|---:|---:|
| strong known weather | (-18, 84) / (111, 79) / (-57, 58) | 210 m | 402 m | 61.1% |
| unknown strength | (-18, 84) / (111, 79) / (-57, 58) | 210 m | 402 m | 61.1% |
| sensor offset | (278, 86) / (219, 84) / (-15, 82) | 311 m | 402 m | 21.9% |
| background shift | (-18, 84) / (112, 78) / (-58, 57) | 211 m | 402 m | 60.6% |
| weather bias | (-19, 90) / (115, 166) / (-41, 176) | 199 m | 393 m | 57.5% |
| additional sensor | (-17, 84) / (100, 88) / (-62, 79) | 197 m | 402 m | 63.4% |

For the clean strong-source case, the fully profiled map's best grid point is
about 300 m from truth, but truth is only 0.097 GLS loss above the minimum;
about 16.8% of the domain lies within the declared descriptive Δloss 4.605
contour. Fixing Q alone, background alone, or both leaves truth within 1.9,
0.2, and 2.5 loss units of the best point, respectively. These are all within
that contour. The extra sensor does not remove the ridge. The sensor-offset
case is model mismatch: its truth is near the unknown-Q/background profile
minimum, but fixing Q increases the truth loss by about 1.8; the single-sensor
offset is not represented in the model. For the +18° weather-bias case, using
biased weather leaves truth 14.5 loss units above the profile minimum; the
matched oracle-weather repeat returns the clean-case geometry. These results
separate location ambiguity from weather and sensor mismatch.

The supplied six-case artifact records per-case GLS minimum, truth loss, best
location, fitted strength, compatible-area fraction, observation records and
sensor coordinates. That detailed record is the source for the rounded table.

## Independent off-grid control

The ideal constructed case has eight spatially distributed sensors, two wind
directions, `Q=500,000 µg/s`, background `10 µg/m³`, and true source
`(-123.4, 87.6) m`, between production grid points. The independently coded
scalar plume equation agrees exactly with the vector kernel on a checked
reading. A 121×121 continuous diagnostic grid with known Q/background places
its best point 3.40 m from truth (grid spacing 6.67 m); truth attains the
minimum GLS loss. Leaving Q/background free gives the same best point and
location, with compatible-area fraction 0.041%. This verifies the transport,
projection and profile arithmetic independently at an off-grid location.

With the production marginalization, posterior mean error is 33.9 m and mode
error is 35.9 m, despite 4.0 m reported spatial RMS and 0.022% region area.
The `0.1` setting moves the mean to `(359.6, 59.6) m`; settings `1` and `10`
put it near `(-90, 90) m`. The release is far above the default prior scale,
and higher-concentration/low-Q locations receive more prior-integrated mass.
This is a prior specification effect, not a failed likelihood calculation.
The known-Q/background profile is a matched information control showing what
release assay and background measurement contribute; it is not a production
oracle or evidence that those values are available in a real investigation.

No production change is indicated by this evidence. Resolving the remaining
six-case ridge calls for information that raises directional/spatial diversity
or constrains nuisance parameters: independently measured wind at the site and
period, an independently characterized instrument offset, and an independently
measured background or release rate. The matched controls show known weather
removes the weather-bias displacement and known Q/background tightens the ideal
case. They do not establish that an added sensor alone resolves the six-case
geometry.

## Reproduction

```sh
PYTHONPATH=backend:. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/investigate_strength_location_v09.py \
  --out evaluations/engine-v09/NEW-strength-location
```

The script refuses an existing output path. It imports the existing fixed
ladder seed for diagnosis and must not be used to tune the model or claim fresh
held-out evaluation. All findings are synthetic and do not establish field
accuracy or source responsibility.
