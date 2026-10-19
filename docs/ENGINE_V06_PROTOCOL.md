# UW-ENGINE-2026-06 — robust weather and adaptive source integration

Written before candidate implementation or new outcomes. Baseline is exact
`plume-weather-0.5.0` at `2b1ac218`, retained in
`evaluations/engine-v06/baseline-source` with a hash manifest. Candidate identifier:
`plume-robust-0.6.0`. Previously inspected weather/stress seeds are development
regressions only, including the original 18 failures. Historical files stay intact.

## Hypotheses and scope

1. Explicit model averaging over nominal reference calibration and a common-mode
   reference error prevents the comparison metadata from eliminating plausible
   coherent weather alternatives. Both explanations must enter prediction and
   design. The extra component is a research prior, not measured calibration.
2. Posterior-directed subdivision, retaining every unrefined cell and its area
   prior, reduces finite-grid localization/prediction error. One refinement stage,
   at most 96 parents, targeting 90% of coarse source mass, halves their widths.
   Refinement is skipped when the model's declared numerical workload would be
   exceeded; the original integral and explicit limitation remain available.
3. The conditional posterior mean minimizes squared position loss under the
   model. Report it alongside the density mode, spatial RMS and region. Neither
   estimator nor a fine numerical grid guarantees physical accuracy.
4. A large posterior fraction in the outer 10% strip of a declared domain means
   the answer depends on its extent. Report it; at least 50% edge mass withholds
   supported localization. This cannot detect every out-of-domain source.

No threshold or prior is selected on final outcomes. Initial common-mode mixture
probability 0.25; additional direction/log-speed SD 20 degrees/0.2. It is coherent
across the campaign and shared across references. Independence claims are not
verified. All existing raw/provenance handling, transport restrictions and
positive-strength/background integration remain. This is not a city-flow,
multiple-source or future-weather model.

## Separation and experiments

Development: seeds 7100000–7100003. Calibration: 7200000–7200007. Final:
7300000–7300023 (24 paired blocks), all 20 severe-stress families. Generator uses
the existing archived weather simulator, with separately declared layout/wind
bands: development six monitors x 10–700/y ±170m, calibration x 50–850/y ±200m,
final x 15–950/y ±235m; development wind bases 220/255/285/315, calibration
210/245/295/325, final 198/238/302/342 degrees, independent ±8 degree jitter.
Direction-error magnitudes and independent diffusion/spatial/clock/multi-source
conditions retain the original generator's split bands. Final layouts, end wind
regimes and nonlinear spatial/time cases have not been used for selection.

Original-18 and first severe common-bias/outside-domain cases are labelled
regressions, never fresh validation. Development can inform implementation;
record any departures here before calibration/final. Calibration is a locked
candidate assessment; any scientific changes after calibration require a new
candidate and a disclosed reclassification. Before final, freeze every production
and evaluation Python file, this protocol, dependency locks and CONFIG. Archive
the exact bytes. No source/configuration changes while final workers run.

Final attempts: 480 condition-worlds, both models on identical observable inputs
(960 scheduled source fits). A refusal/crash remains in its denominator. Score
passive unseen concentration predictions in the first four seed blocks for every
condition (80 per model, with refusals explicit). Evaluate equal-budget pollution
plans on characterized nominal, shared-reference bias and independent transport
for the first four blocks, four methods (prediction variance, spatial spread,
fixed random seed, observed-wind ordering): 48 downstream candidate fits, using the same downstream
engine, identical historical weather, budget 250/equipment 2. Choices are locked
before reveal. Weather instrumentation is not supplied for free. No planned
pollution improvement is evidence of weather verification or attribution benefit.

## Outcomes and reporting

Primary comparison: accepted wrong / accepted, and / all attempts; acceptance;
conditional 90% geographic coverage together with occupied area; median/p90
MAP and posterior-mean Euclidean errors, all and accepted. MAP is maximum
posterior *density*, not largest mass in an unequal-area adaptive cell. Disclose
this distinction alongside the archived baseline's original cell-mass MAP.
Report per-condition counts and Wilson intervals. Source probability is evaluated
against background/source presence separately from geographic coverage.

Report paired squared/absolute location losses, concentration RMSE/NLPD/interval
coverage, and planner outcomes/actual cost/loss frequency to each baseline.
Bootstrap paired seed blocks (5000 resamples, fixed seed 90606); repeated methods,
conditions and target rows are not independent campaigns. At 24 blocks the tails
remain uncertain. No single aggregate percentage is operational accuracy.

Success requires lower common-bias accepted-error count AND useful nominal
acceptance, without claiming a global improvement if other conditions worsen.
The precision aspiration remains nominal overall median point error ≤50m; report
failure if it fails. Software targets: no unexpected exceptions/nonfinite output,
all existing and new independent numerical/API tests pass, build/typecheck and
focused browser workflows pass. Bound memory/work explicitly. Repeat engineering
property/placement/CSV stress without counting them as field observations.

No compatible primary measured tracer files are currently present. Existing
network/access and Prairie Grass provenance/unit blockers remain; this campaign
provides synthetic evidence only. Do not imply measured or organizational
attribution readiness. Retain raw inputs, private evaluator truth separately,
timings, refused cases, failed preflights, exact hashes and all negative outcomes.

## Development implementation record (before calibration)

The initial four-seed/four-family prototype is retained in `development-*` and
`prototype-source`. Production/helper files changed while these explicitly
non-frozen development workers were finishing; completion flags correctly record
source drift. No such run is labelled frozen validation. Shared-bias coverage can
improve while its most likely point remains badly displaced, so point accuracy
continues to be reported. No outcome selected a new scientific threshold/prior.

Initial runtime was excessive. Exact repeated-signature sufficient statistics
and exact aggregation of speed-mixture strength moments were added, with direct
full-covariance/strength-integral oracles. Zero-prior joint tensor entries are
omitted (zero mass only; no posterior pruning). Predictive means/covariance/draws
avoid materializing the full component covariance tensor. A centered variance
calculation avoids cancellation. Work bounds now measure the actual compressed
transport design, retain the existing 28-million-entry limit, add a 2-million
nonzero-component limit and bound predictive target/component designs. All raw
readings remain in the full observation covariance and marginal normalization.
The first compressed development recheck is also retained, not relabelled final.

Calibration will use all eight declared seeds on these eight predeclared families:
characterized_nominal, shared_reference_bias, source_outside_domain,
unknown_nominal, direction_characterized, spatial_winds, correlated,
independent_transport. Final remains all twenty families and all 24 blocks.
