# Planner audit: source-learning objective and follow-up experiment

This audit inspects `plume-ensemble-0.2.1`. Its findings establish individual mathematical properties, not field validation. The existing stress cases have been inspected and are now development-used.

## Confirmed properties

- The production planner consumes investigation readings, local observed weather, candidate locations, access flags, equipment and budget. It does not read the evaluator's separate hidden truth object, withheld candidate concentrations or future observed weather.
- Existing follow-up experiments lock every method's selected sites before candidate outcomes are generated. Methods share the same candidate outcomes within each simulated investigation. This supports paired comparisons and avoids outcome-aware site selection.
- Predictions use the mean supported weather of an already observed steady window. This is a same-window retrospective experiment, not a forecast-informed future deployment. No travel time, travel path, sampling-duration or forecast uncertainty is represented. The UI must continue to say so.
- Exhaustive search on at most 12 feasible candidates verifies optimality for the supplied objective only. The larger heuristic's best-baseline envelope guarantees no worse internal score than computed comparison plans; it does not guarantee better source localization or predictive performance.

## Confirmed discrepancies

### Gaussian-moment score is not discrete-location expected information

The current objective replaces location-conditioned predictive mixtures by a between-location mean covariance and averaged within-location covariance. This loses distinctions in mixture shape and variance. It can exceed the entropy of the discrete unknown location, which no actual information gain about that location can do.

Independent scalar integration using only normal densities, adaptive quadrature and finite mixture identities gives:

| Equally weighted location-conditioned predictive means | Independent noise SD | True location information (nats) | Current Gaussian moment score (nats) |
|---|---:|---:|---:|
| Location A: -3 or +3; location B: -0.5 or +0.5 | 0.3 | 0.693101 | 0 |
| Location A: -10; location B: +10 | 0.1 | 0.693147 | 4.605220 |
| Identical locations: both 0 | 1 | approximately 0 | 0 |

Two equally weighted locations have entropy `log(2) = 0.693147` nats. The first case isolates lost predictive-shape information; the second proves that the moment score is not the actual entropy reduction. Its use as a documented approximation was transparent, but its magnitude cannot be read as expected learning.

The independent calculation and numeric results are `.local/overhaul/planner_exact_checks.py` and `.local/overhaul/planner_exact_checks.json`. Exact command from repository root:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python .local/overhaul/planner_exact_checks.py
```

These development-only prototype files are intentionally local. Any permanent replacement needs equivalent regression checks independent of its implementation.

### Future discrepancy is unconditioned in acquisition but conditioned during update

The fitting likelihood shares a spatial discrepancy across the steady window. Appending observations uses one joint covariance, so new readings are correlated with old readings. However, the current acquisition computes candidate means directly from the plume scenarios and uses the marginal future covariance. It omits the Gaussian conditional terms from past residuals:

```
future_mean(s) = plume_future(s) + K_future,past C_past^-1 (y_past - plume_past(s))
future_cov = C_future - K_future,past C_past^-1 K_past,future
```

This is a confirmed inconsistency between the scoring model and the subsequent update under the documented shared-discrepancy assumptions. In a toy with old/future marginal variance 6, cross-covariance 4 and scenario means -1/+1 at both locations, conditioning gives future means -1/3,+1/3 and variance 10/3. The corresponding moment scores are 0.077075 unconditioned and 0.016395 conditioned. This is a factor of approximately 4.7 in one toy, not a prediction of application-wide improvement.

### Entropy change alone does not measure usefulness

An individual realized entropy reduction may be negative even under a correct Bayesian model; expected reduction is nonnegative. Conversely, entropy may fall because an inadequate model becomes sharply wrong. The previous stress experiment already reports these failures. Required comparisons remain localization-error distributions, geographic region area and coverage, proper predictive scores, wrong-and-sharp frequency and after-measurement performance under shared hidden outcomes. Weak-signal error and prediction changes can be worse than random despite a higher internal score.

## Implementation alternatives and priorities

1. Correct conditional future means/covariance if shared discrepancy remains in the redesign. Reuse stable Cholesky solves and validate the joint-to-conditional update against a small direct normal calculation.
2. A finite-mixture expected-information objective can evaluate location-conditioned predictive densities directly, using deterministic quadrature for tiny scalar checks and documented common-random-number integration for general subsets. Record integration resolution and convergence sensitivity. Do not silently call a Monte Carlo estimate exact, clamp substantial negative values or cap the previous moment score and relabel it expected information.
3. Additional complexity is justified only by paired after-outcome evaluation. Compare the old moment planner, corrected conditional planner, spatial spread, random seeds and the applicable observed-wind plan on the same feasible sites/noise/cost/time assumptions.
4. Offer spatial spread transparently when source-learning recommendations are not supported. It is a geometric sampling baseline, not a validated pollution-exposure or health objective. Do not invent an expected percentage benefit or assert universal dominance.
5. No-source, uncertain meteorology and mixture families must feed both acquisition and update consistently. Averaging only their means hides predictive multimodality. A robust minimum-across-model score may sacrifice useful learning; evaluate that tradeoff before adopting it.

## Remaining limits

Correct expected information under an internal model is conditional on that model. It cannot create identifiability, field calibration, source responsibility evidence or forecast feasibility. Under unsupported weather or unknown release patterns, retain measured data and fall back to appropriately labelled descriptive sampling rather than substituting invented observations.

## Implemented replacement and independent checks

`backend/upwind/design.py` now provides a standalone discrete-mixture acquisition calculation. The engine supplies joint posterior-predictive Gaussian components **already conditional on the existing observations**. The target is background-only versus coarse source regions tied to user anchors; fine spatial cells and nuisance parameters are marginalized. The engine remains responsible for the scientific adequacy of that predictive distribution.

The default numerical budget is 128 posterior components and 128 group-stratified normal draws in each of two scrambled Sobol replicates. Component reduction preserves every positive target group's prior mass; it approximates nuisance variation within each group. Stable caller-supplied component keys make that reduction invariant to mixture input permutation. Metadata reports represented original component mass, component-distribution total variation, component counts, target entropy, numerical resolution, score calls and replicate disagreement. A diffuse 5,400-component toy can retain only about 2.4% of the original individual-component mass at this budget; preservation of coarse group mass does not remove that approximation. This is explicitly a finite-model numerical research score.

Scores are prior group entropy minus estimated expected posterior group entropy. They cannot exceed prior entropy, but integration error can produce a small negative value; raw values are retained, and an empty plan has zero score. No clipping, noise inflation, probability tempering or invented percentage improvement is applied. Per-group Sobol arrays are generated at the next power of two and truncated to the allocated count; strict power-of-two balance is therefore not promised for each group. Replicate disagreement is a diagnostic, not a rigorous error bound. Increasing resolution is not guaranteed to move every estimate monotonically toward the answer.

Eight tests in `backend/tests/test_design.py` pass, including independent adaptive density quadrature, equal-mean/dispersed-mixture discrimination, the discrete entropy bound, identical-distribution zero information, correlated measurement redundancy, exact preservation of group priors, full-mixture preservation when the budget permits, stable component permutation, and invalid covariance contracts. Commands:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest backend/tests/test_design.py -q
```

Saved independent scalar results at three resolutions are `evaluations/overhaul/planner-math-checks.json`, with source hashes for the calculator and check implementation. At the default resolution the equal-mean separated mixture yields 0.693102 nats against an independently integrated 0.693101; the variance-only case yields 0.492466 against 0.492455. These favorable tiny cases verify specific properties only. They do not establish recommendation benefit across the application problem class. The two replicate estimates may agree more closely than their error from adaptive quadrature, so their spread must not be presented as a calibrated numerical confidence interval.

## Development sensitivity probes

`scripts/overhaul_ablations.py` provides append-only, explicitly development-only model, row-selection, numerical planner-budget and fresh-process resource probes. It cannot select final/calibration worlds. The first complete planner probe is `evaluations/overhaul/ablations-planner-dev-canonical/`: six worlds (two development seeds each for strong, weak and wind-biased signal), six numerical budgets each, all feasible subsets under the same constraints, with choices locked before candidate outcomes are exposed. Component budgets are 128/256/512 and integration budgets 128/512 per replicate. Candidate predictions use the declared last observed timestamp, instrument identifiers and nominal uncertainty rather than future realized uncertainty or weather.

This **pre-freeze** run changed four of six selected plans when moving from 128 components/128 draws to 512/512. Of those four changes, two improved the held-out-target RMSE and two worsened it; all six worlds retained the same source MAP error across those two plans. Minimum subset-ranking correlations were 0.354 for weak signal, 0.819 for strong signal and 0.671 under wind bias. No general recommendation dominance follows. Production inference/orchestration and evaluator files changed while this development probe ran; its metadata explicitly records `sources_unchanged=false`. It is a preserved developmental numerical-sensitivity result, not validation of a subsequently frozen implementation. The interrupted earlier ordinal-component-key probe is retained with its reason rather than overwritten.

Exact phase commands (use a new output directory each time):

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/overhaul_ablations.py --phase planner --limit-seeds 2 --out .local/planner-budget-probe
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/overhaul_ablations.py --phase resources --out .local/resource-probe
```

The complete resource probe is `evaluations/overhaul/ablations-resources-dev/`. All six fresh-process children succeeded with finite plan scores below the 30-second timeout and 2 GiB address-space ceiling. At 10,000 loaded readings and 10,000 weather rows, 100 sites and 25 anchors, the model had 4,621 mixture components. Default 128-row inference took 12.67 seconds and 357.51 MiB peak RSS; the explicit 512-row limit took 14.72 seconds and 660.62 MiB. Both include sensor-block diagnostic refits and candidate search. This is bounded inference, not a full 10,000-row inversion. The recorded machine is an AMD EPYC 9V45 with one BLAS thread. Production source hashes remained unchanged during these resource children; the evaluator source changed concurrently, which is separately recorded rather than presented as a fully frozen repository. Timings under this shared cloud workload do not guarantee a universal laptop runtime.

After the production/evaluator freeze, the complete budget study was rerun in a fresh process at `evaluations/overhaul/ablations-planner-dev-frozen-v2/`; **all recorded source hashes remained unchanged**. It uses the same six development worlds and 36 numerical-budget plans, with candidate outcomes now explicitly realized by the evaluator only after all choices are locked. Moving from 128/128 to 512/512 again changes four of six plans. Two changed plans improve held-out-target RMSE and two worsen it. Source MAP error improves in one world (230.6 to 162.7 m) and stays unchanged in the other five. The minimum subset-ranking correlations are 0.564 for weak signal, 0.862 for strong signal and 0.674 for direction bias. Maximum disagreement between two integration replicates is 0.0378 nats across all tested subsets/budgets. These six worlds demonstrate numerical sensitivity; they cannot establish a generally superior budget or recommendation method. The frozen default remains 128/128, and rankings must be presented as experimental. A failed intervening harness run, caused by the evaluator's newly deferred-outcome contract, is retained with its `KeyError` explanation; no final cases were used or altered.
