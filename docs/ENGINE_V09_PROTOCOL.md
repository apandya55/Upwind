# UW-ENGINE-2026-09: feasibility and release-prior sensitivity

Candidate: `plume-robust-0.9.0`. This protocol follows the v0.8 conditional
background versus one steady-source model and its nested source/weather
quadrature. It adds two targeted changes justified by the feasibility audit:

1. Single-window and campaign fits use the same four-node tensor rule inside
   every supported source cell. Midpoint-only evaluation can miss a narrow
   plume inside a 20 m cell.
2. Every fit reweights the existing GLS source/weather components with release
   HalfNormal scale factors `0.1`, `1.0`, and `10.0`. A location shift greater
   than 100 m or source-cell total variation greater than 0.25 blocks
   `source_supported`. This is a prior-dependence diagnostic, not a fitted
   alternative or a calibrated interval.

The model and protocol identifiers change because the production semantics
changed. The old v0.8 source, configuration, results and hashes remain under
`evaluations/engine-v08/` and are not rerun or retuned by this protocol.

## Declared rules

The source prior remains uniform in the supported rectangle, and the emission
prior scale remains 30,000 µg/s for the fitted result. Sensitivity factors only
multiply that scale while holding observations, covariance, weather nodes and
source cells fixed. Each alternative reports source probability, posterior
mean, density mode, spatial RMS, cell-mass total variation from the fitted
scale, and posterior-mean movement. The largest material alternative blocks
support; the conditional posterior and all alternatives remain available.

The four tensor nodes are the Cartesian Gauss-Legendre points at ±1/√3 in each
cell. The existing nested quadrature convergence policy remains in force. A
converged integral is numerical stability, not physical adequacy or field
accuracy.

## Compact feasibility ladder

`scripts/feasibility_ladder_v09.py` creates a fresh, refuse-to-overwrite
directory containing metadata, public rows, private diagnostic truth and a
summary. It covers the weak current fixture, a strong source with a labeled
known-weather control, unknown strength, sensor offset, background shift,
weather bias, an additional monitor, source-free data, two sources and an
out-of-domain source. The strong controls use an independently coded scalar
Gaussian plume calculation and record its comparison with the production
primitive. Truth and oracle weather are used only after the production result
is serialized for diagnostic scoring.

```sh
PYTHONPATH=backend OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python scripts/feasibility_ladder_v09.py \
  --out evaluations/engine-v09/ladder
```

This ladder is a compact mechanism check, not a replacement for measured
validation or the held-out v0.8 campaign. Do not treat its synthetic errors,
acceptance counts, or source probabilities as field performance.
