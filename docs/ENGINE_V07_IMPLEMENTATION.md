# Engine 0.7 implementation

The candidate `plume-robust-0.7.1` is implemented on top of the reproducible
0.6 transport/weather integrator. Its protocol is
[`UW-ENGINE-2026-07A`](ENGINE_V07_PROTOCOL.md). The locked synthetic
development, calibration and final evaluations are complete; the post-final
numerical confirmation and its retained pre-repair result are documented in
`docs/PROGRESS.md` and `evaluations/engine-v07/`.

The observation covariance includes a sensor-specific latent humidity
coefficient. For row `i`, the design value is

```
h_i = max(0, (humidity_i - 70%) / 20%)
```

and the added covariance is

```
2.0² h_i h_j 1[sensor_i = sensor_j].
```

The scale and threshold are explicit research configuration. Missing humidity
is represented by `h=0`, so the engine never fabricates a correction. The
coefficient is marginalized rather than estimated from the same pollution
series.

The identifiability diagnostic first profiles the existing nonnegative
one-source signatures with per-window background and trend, using the same
row-level uncertainty covariance as the posterior fit. It then keeps at most
24 distinct cells and a bounded set of the best shared weather-offset
configurations, and solves every pair with bounded nonnegative least squares.
The two sources must use the same persistent weather offset; combining two
different weather alternatives would manufacture a false multi-source
improvement. A pair is material only when both strengths are positive, cells
are at least 50 m apart and the improvement exceeds the predeclared `9.21034`
profile-loss threshold. This is a sensitivity test, not a source-count
posterior.

Residual checks use the fitted covariance and retain their evidence: high vs
low humidity standardized contrast, per-sensor and global time correlation,
late-versus-early release contrast, nearby standardized residual products and
large standardized residual counts. Nearby products are compared with the full
model-implied off-diagonal covariance, including persistent instrument and
humidity terms. Any flag blocks the resolved label and is surfaced in
`observability.externalities` and the warnings list. If the secondary
diagnostic itself is numerically unavailable, the posterior is retained but
source support is withheld. The model continues to show the one-source
posterior region as a conditional explanation so users can inspect ambiguity.

All finite weather quadrature, positive-strength integration, adaptive area
integration, raw provenance and explicit unsupported-weather refusals are
unchanged. The candidate has no measured validation and must not be described
as a field-calibrated pollution attribution engine.
