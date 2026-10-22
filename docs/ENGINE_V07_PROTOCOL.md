# UW-ENGINE-2026-07A — externality-aware source adequacy

Candidate model identifier: `plume-robust-0.7.1`. This revised protocol was
written before the 0.7.1 development, calibration or final result. The 0.6 release and
its evidence remain reproducible under `UW-ENGINE-2026-06`.

## Hypothesis and scope

The 0.6 posterior can be sharply concentrated while an unmodelled sensor
response, changing release, residual spatial process or second source produces
the same readings. A stronger localization result should therefore make those
competing explanations explicit and withhold a resolved label when one is
materially supported.

The candidate adds four guarded pieces:

1. High humidity is retained as a recorded covariate. An unknown,
   sensor-persistent humidity response is integrated as a zero-mean random
   coefficient in the observation covariance. No PM2.5 correction is inferred
   from humidity alone, and missing humidity contributes no invented signal.
2. A bounded nonnegative two-source GLS profile tests the best 24 distinct
   source cells after nuisance projection. Candidate pairs share one persistent
   weather-offset configuration; mixing offsets would create a false pair
   improvement. It is an adequacy diagnostic, not a two-source posterior or a
   responsibility claim.
3. Residual structure checks flag sensor drift or changing release, unresolved
   nearby background, heavy tails/events, and high-humidity response artifacts.
   A bounded two-half release profile is also checked against the same plume
   shape. Flags are evidence of model discrepancy and block
   `source_supported`.
4. Existing weather alternatives, background-only competition, predictive
   checks, domain-edge checks and finite quadrature remain in force. The model
   still does not solve chemistry, deposition, urban flow, arbitrary wind
   fields, source responsibility or future scheduling.

The candidate does not rewrite raw values, timestamps, origins, weather,
provenance or resident accounts. An externality flag is not a diagnosis of a
real emitter; it is a reason to obtain independent evidence.

## Locked evaluation design

Fresh seed families are disjoint from every 0.6 and earlier seed and from the
pre-revision 0.7 development smoke family (`8,100,000`):

| split | seeds | role |
|---|---:|---|
| development | 8,110,000–8,110,015 | implementation and mathematical checks only |
| calibration | 8,210,000–8,210,015 | assess predeclared thresholds and refusal rates |
| final | 8,310,000–8,310,031 | untouched held-out comparison |

Every split contains characterized nominal worlds and independently randomized
externalities: high-humidity sensor response, sensor drift, changing release
by window, sparse two-source releases, spatially correlated background,
heavy-tailed events, weather direction/speed errors, source-outside-domain
cases and combinations. Externalities are generated independently and jointly;
the final generator and source are frozen before final outcomes are read.

The primary comparison keeps the 0.6 observable inputs and adds the same
externality worlds to both engines. Report all attempts, refusals, acceptance,
accepted wrong regions, conditional region coverage and area, posterior-mean
and density-mode errors, source-family scores, predictive log scores and every
externality flag. A refusal stays in its denominator. No threshold, prior,
humidity scale or pair-improvement cutoff may be selected from final outcomes.

The candidate is not considered successful merely because it emits fewer
resolved labels. A useful result must reduce accepted wrong regions without
destroying characterized nominal coverage, and must expose unsupported worlds
instead of creating measurements. The predeclared nominal point-error target
remains 50 m, with failure reported if it is not met.

## Acceptance and limitations

`source_supported` requires the existing source/weather/predictive/domain
rules plus no blocking externality flag and no material two-source profile. A
non-blocking diagnostic still appears in the result. The pair profile uses a
finite candidate set and an uncalibrated delta-chi-square threshold; it cannot
prove a source count. The humidity coefficient is an uncalibrated research
prior, not an instrument calibration. No field or controlled-release
validation is currently available, so this protocol cannot support an
operational accuracy, attribution, regulatory or organizational claim.

The append-only harness is `scripts/evaluate_v07.py`. A development smoke run
is:

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/evaluate_v07.py \
  --split development --limit 1 --out .local/engine-v07-development-smoke
```

It refuses an existing output directory and records the source hash/config.
The calibration and final splits were run only after the generator and source
were frozen and reviewed. The original final output is retained under the
pre-repair result directory. A post-final engineering confirmation reran the
same locked worlds after a numerical serialization guard; it is not an
independent accuracy sample and does not change the predeclared scientific
selection.
