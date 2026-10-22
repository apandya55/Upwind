# Engine 0.9 feasibility and substantive repair

The v0.8 results showed stable numerical quadrature but little useful source
discrimination. Its median conditional region covered about 89% of the domain,
the source probability was near one half, and the weak fixture's 5,000 µg/s
signal was below roughly 0.1 µg/m³ against about 2 µg/m³ noise and broad nuisance
covariance. A strong three-sensor case can produce a narrow mode while still
having multiple plume geometries that fit the observations. Numerical
convergence therefore did not establish identifiability.

The repair targets the two code-level risks that can be addressed without
inventing information. `backend/upwind/inference.py` now evaluates each
continuous source cell at four tensor nodes for single windows as well as
campaigns. It also reuses the exact grouped GLS `norm` and `dot` terms to
recompute the source mixture under declared release-scale factors `[0.1, 1,
10]`. The result reports the alternative posterior summaries and blocks
`source_supported` when mean movement exceeds 100 m or cell-mass total
variation exceeds 0.25. `backend/upwind/engine.py` propagates this diagnostic
through `observability`, adds a fail-closed warning, and retains the posterior
for inspection.

The focused v0.9 tests verify four-node single-window integration, finite
sensitivity outputs, a deliberately prior-sensitive two-cell case, and the
public support gate. The existing cache-clearing regression remains covered.

The fresh ladder produced the following compact evidence. Point errors and the
domain-center baseline are evaluator-only diagnostics; they are not inputs to
the engine. Region fractions are conditional area summaries, not coverage
probabilities.

| Case | Public evidence | Source weight | Diagnostic mean error (m) | Domain-center error (m) | Region area fraction | Prior gate |
|---|---|---:|---:|---:|---:|---|
| weak current fixture | ambiguous | 0.487 | 87.8 | 178.9 | 0.892 | pass |
| strong, known weather | ambiguous | 0.921 | 209.8 | 178.9 | 0.611 | blocked |
| unknown strength | ambiguous | 0.921 | 209.8 | 178.9 | 0.611 | blocked |
| sensor offset | model mismatch | 1.000 | 311.2 | 178.9 | 0.219 | blocked |
| background shift | ambiguous | 0.924 | 211.2 | 178.9 | 0.606 | blocked |
| weather bias | ambiguous | 0.914 | 198.6 | 178.9 | 0.575 | blocked |
| additional sensor | ambiguous | 0.911 | 196.6 | 178.9 | 0.634 | blocked |
| source-free | ambiguous | 0.485 | — | — | 0.891 | pass |
| two sources | ambiguous | 0.483 | 90.7 | 178.9 | 0.891 | pass |
| out-of-domain source | ambiguous | 0.499 | 1,396.5 | 1,442.1 | 0.894 | pass |

No ladder case was publicly source-supported. The independent scalar plume
value was 0.2968437006 µg/m³ and differed from the production primitive by
0.0 at the checked point. The weak fixture's broad region and near-half source
weight remain after the repair. The strong controls demonstrate that a higher
source weight or a smaller conditional region does not imply correct location;
the release-prior gate correctly withholds those cases.

Run the compact ladder with:

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/feasibility_ladder_v09.py \
  --out evaluations/engine-v09/ladder
```

The ladder is synthetic and diagnostic. It includes a weak current fixture,
strong known-weather control, unknown strength, sensor/background/weather
perturbations, an extra sensor, source-free and two-source cases, and an
out-of-domain source. It also compares an independent scalar plume calculation
with the production primitive and records a declared-domain-center baseline.
Its private truth file is not an input to inference.

The product decision remains **C for the current inputs**: dependable source
localization is not established with the weak, noisy, sparsely placed inputs
that a community investigation can realistically provide. A monitoring-design
direction is worth considering only as a separate experiment after equal-budget
follow-up layouts show repeatable improvement against spatial and random
baselines. The concrete requirement is additional independent information:
measured source-strength constraints, multiple wind directions or temporal
variation, and enough spatially diverse monitors to separate plume geometries.
No synthetic ladder result establishes field accuracy, responsibility,
calibration, organizational demand or operational readiness.

## Sol feasibility audit and reproducible denominators

The v0.8 candidate was `plume-robust-0.8.0` under `UW-ENGINE-2026-08`;
its paired workspace baseline was the retained 0.7.1 snapshot. The final
split has 256/256 matching serialized inputs, 256/256 finite candidate fits,
and 256/256 numerical convergence passes. The reported 224/256 is **correct
source-count region inclusion**: the conditional 90% region contained the
simulated source count in 224 of 256 source-present worlds. It is neither an
acceptance rate nor a source-count probability. The split has no source-free
worlds. Candidate labels were 1 supported, 177 ambiguous and 78 mismatch;
median region area was 89.1% of the domain, median mean error 91.0 m, and
median mode error 484.4 m. The paired 0.7.1 comparison changed median mean
error by +0.0002 m and mode error by 0 m, while median runtime rose from
1.66 s to 3.49 s. Thus v0.8 convergence established stability of its finite
integral, not useful localization.

The v0.9 production path is: raw measurement quality and row selection in
`backend/upwind/quality.py`; WGS84 local projection and the neutral plume in
`backend/upwind/numerics.py`; UTC campaign assignment and coherent shared
weather evidence in `backend/upwind/campaign.py` and
`backend/upwind/weather_evidence.py`; GLS likelihood, analytic background
marginalization, positive HalfNormal release integration, and area-weighted
source/weather posterior in `backend/upwind/inference.py`; profile and
externality checks in `backend/upwind/identifiability.py`; and public support
classification in `backend/upwind/engine.py`. The continuous source prior is
uniform in supported area; each cell's four tensor Gauss nodes carry equal
within-cell quadrature mass. Background intercept/trend and sensor-persistent
bias are Gaussian nuisances. Wind speed scaling uses `Q_eff=Q/speed_scale`,
with the HalfNormal scale and normalization transformed consistently. The
`[0.1, 1, 10]` sensitivity values multiply the default 30,000 µg/s HalfNormal
scale, yielding 3,000, 30,000 and 300,000 µg/s; they do not scale observations
or the fitted strength. The v0.9 gate blocks support under a material
alternative posterior shift, but does not alter the posterior.

The six-case diagnosis in
[the detailed profile report](ENGINE_V09_STRENGTH_LOCATION_DIAGNOSIS.md)
compares optimized-Q/background GLS profile maps with marginalized posterior
locations, then fixes release, background, and weather in labeled diagnostic
controls. The clean strong-source truth is close to the best profile location
in likelihood units despite a distant profile minimum; fixing Q/background
does not remove that ridge. A sensor-specific offset is unmodeled mismatch.
An 18° weather perturbation leaves truth 14.5 profile-loss units above the
minimum; the matched true-weather oracle restores the clean geometry. These
controls show physical/nuisance ambiguity and two designed mismatch effects,
not a production likelihood arithmetic defect. The ideal off-grid control
uses eight sensors and two winds, with true source (-123.4, 87.6) m and
Q=500,000 µg/s. An independently coded scalar plume calculation agrees with
the production kernel at the checked receptor; its 121×121 known-Q/background
profile places the best point 3.40 m from truth (6.67 m grid spacing), while
the default marginalized mean is 33.9 m from truth. The default prior is
therefore consequential even in this recoverable construction.

The compact ten-case ladder has 10/10 finite fits, zero numerical convergence
failures, zero supported outputs, six prior-sensitivity blocks, one source-free
case, one two-source case and one out-of-domain case. Across its nine
source-present cases, median mean error is 209.8 m; the declared-domain-center
baseline has median error 178.9 m. At the 50/100/200 m thresholds, candidate
success is 0/9, 2/9 and 4/9, versus baseline 0/9, 0/9 and 8/9. The 90% region
area median is 61.1% among those source-present cases. Support is 0/10 overall;
source-free false support is 0/1 in this tiny challenge, not a calibrated
false-alarm estimate. The source-free output's conditional region occupies
89.1% of the domain and should not be interpreted as a located source. The
source-free, multiple-source, mismatch and out-of-domain cases remain in the
attempt denominators; evaluator truth is never given to production inference.

Reproduce the reporting summary without rerunning or modifying the frozen
inference runs:

```sh
PYTHONPATH=backend:. .venv/bin/python scripts/sol_feasibility_assessment_v09.py \
  --out evaluations/engine-v09/NEW-assessment.json
```

The checked artifact is
[`assessment.json`](../evaluations/engine-v09/sol-assessment/assessment.json).
The expensive six-case and off-grid diagnosis can be reproduced into a new
directory using the command in `ENGINE_V09_STRENGTH_LOCATION_DIAGNOSIS.md`.
The report generator joins evaluator-private truth only after serialized
production outcomes exist. V0.8 source hashes and all historic results remain
preserved. No additional production inference change is justified by these
diagnostics, and no acceptance relaxation is proposed.

The product decision is **Outcome C for the current feasible-input premise**.
Community investigators may use the system to inspect measurements,
provenance, weather assumptions and conditional hypotheses; the evidence does
not support presenting a source location as a dependable decision aid. A
monitoring-design research direction remains unproven: this ladder's one extra
colocated sensor does not materially resolve the ridge, and no equal-budget,
fresh-layout experiment here establishes benefit over random or spatial
baselines. A concrete next experiment needs genuinely spatially diverse
monitors plus independent local weather or a second steady wind direction,
with release/background measurements recorded where feasible and an equal
budget comparison against random and spread layouts on fresh held-out
geometries. Field tracer validation with verified units, wind/time metadata
and source truth remains required before any operational claim.
