# UW-ENGINE-2026-08: nested quadrature convergence

Candidate: `plume-robust-0.8.0`. This protocol retains the 0.7.1 conditional
background versus one steady-source model, humidity random effect, coherent
weather alternatives, bounded two-source adequacy profile and residual screens.
The change is deterministic nested source-cell and weather quadrature with an
explicit numerical-convergence gate. It does not add a transport law, tune
acceptance, or convert the adequacy profile into a source-count probability.

## Predeclared numerical policy

The source prior remains uniform in supported area. Starting from the existing
20 m target grid (at most 24 cells per axis), later levels subdivide the
posterior-dense 90% of cells, up to 96 parents per level. The full cells and
area weights remain in every integral. Coherent campaign weather is integrated
at requested angular spacings 2°, 1°, and 0.5°, retaining the configured joint
speed/direction prior and common-mode alternative. Existing design-entry and
component bounds remain active; a level that exceeds them is recorded as
incomplete and cannot establish convergence.

Adjacent levels must satisfy all of these tolerances: absolute log-evidence
change ≤0.01; source-existence probability change ≤0.01; total-variation
distance of source mass mapped to the original parent cells ≤0.05; posterior
mean movement ≤10 m; relative Frobenius covariance change ≤0.05; change in the
selected 90% region mass ≤0.02; change in its area/domain fraction ≤0.05; and
weather marginal total-variation distance ≤0.05 on fixed 5° circular direction
bins with linearly interpolated mass from each grid node, and exact log-speed
node keys. This avoids nearest-bin alignment changes as spacing halves. These
are numerical stability criteria, not accuracy, coverage, or acceptance targets.
The finest completed finite posterior remains
available for inspection when they fail, while `source_supported` is withheld.

## Evaluation splits and comparator

The generator and eight scenario families match the prior 0.7 evaluation so
the dirty-workspace 0.7.1 baseline can be paired on identical serialized input.
The current 0.7.1 Python package, evaluator, and protocol were copied to
`evaluations/engine-v08/v07-baseline/` before candidate edits and hashed in its
source manifest. This is the exact current 0.7.1 workspace snapshot, including
the already-retained post-final numerical guard. It is not a reconstruction of
the original frozen 0.7.1 source.

Fresh split seeds (checked against seed values retained in prior JSON
artifacts):

| Split | Seeds | Worlds |
|---|---:|---:|
| development | 8,410,000–8,410,015 | 128 |
| calibration | 8,420,000–8,420,015 | 128 |
| final | 8,430,000–8,430,031 | 256 |
| separate resource pilot | 8,440,003 | 8 |

Each world contains one of nominal, humidity response, sensor drift, changing
release, two sources, spatial background, heavy tail, or weather error. The
pilot is development-only and separate. Truth is retained in a separate
evaluator-only file; it is never passed to either engine. Every candidate world
is paired with the workspace-frozen 0.7.1 engine on identical JSON input.
Refusals and crashes remain in attempt denominators. No split outcomes are
used to change the candidate policy.

Two earlier runner checks are retained append-only: seed 8,440,000 completed
engine calls but its report summarizer failed on crash rows; seed 8,440,001
completed engine calls but the wrapper incorrectly attempted to JSON-decode an
already-decoded result. Pilot seed 8,440,002 completed with the corrected
wrapper. Its nearest-bin weather comparison showed about 0.05 adjacent-level
TV despite stable source mass and moments, exposing angular-bin alignment
error. The final comparison linearly deposits mass to fixed 5° bins; this
changes only the numerical comparison metric, not posterior weights or
tolerances. Pilot seed 8,440,003 checks this corrected metric.

The 90% source region is a conditional area-quadrature set. Connected components
and centroid separation describe its geometry; they do not establish physical
source count. Source-existence weight, model adequacy, numerical convergence,
and location error are separate outcomes. Concentration holdout scores are
reported separately from localization. No measured-data validation is part of
this protocol.

## Commands

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/evaluate_v08.py --split development \
  --out evaluations/engine-v08/development
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/evaluate_v08.py --split calibration \
  --out evaluations/engine-v08/calibration
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/evaluate_v08.py --split final \
  --out evaluations/engine-v08/final
```

The runner refuses existing output directories. Store exact source/configuration
and environment hashes with each split. Preserve complete rows and per-family
denominators, including support, coverage, region area, point errors, numerical
level deltas, warnings, externality flags, held-out concentration metrics,
runtime, crashes and refusals. This synthetic evaluation cannot establish field
accuracy, calibration, attribution or operational readiness.
