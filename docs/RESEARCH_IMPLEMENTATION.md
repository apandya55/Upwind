# Research implementation and owner handover

Model `plume-campaign-0.4.0`, protocol `UW-RESEARCH-2026-02`. [SCIENCE.md](SCIENCE.md) defines capability limits. The application is a private local research workspace. Government, company or activist use does not change what its measurements can identify. Scientific validation and deployment authorization are separate requirements.

## Changes and review map

| Code | Change and purpose | Evidence |
|---|---|---|
| `backend/upwind/campaign.py`, `models.py` | Explicit individually steady periods, UTC/overlap/span validation and fixed-source/constant-release assertion; reject unsupported periods | Campaign schema/weather/assumption and API checks; data-collection ablations |
| `inference.py` | Independent regional background/trend per period; persistent instrument bias; coherent declared weather error; editable physical heights | Covariance tests; existing independent marginal-likelihood tests; fresh synthetic evaluation |
| `inference.py`, `numerics.py` | Four-node area integration for campaigns; exact Q/speed variable substitution and shared solves | Original math tests, moment/density oracle, dense/noiseless comparisons and resource probes |
| `predictive_checks.py` | Joint sensor/period spatial-contrast checks; exact positive-strength sampling; explicit check budgets/unavailability | Independent known-Gaussian discrepancy check, exact predictive-density oracle, 40-sensor regression, false-warning/missed-failure evaluation |
| `identifiability.py` | Global free-nuisance profile and local/global sensitivity tools | Independent NNLS comparisons, rank-deficient/observational-equivalence examples, dense oracle experiments |
| `prediction_design.py`, `engine.py` | Optional deterministic prediction-variance objective over a fixed target universe; same feasibility/search | Scalar closed form, exhaustive tiny subset comparison, 100,000 independent linear-prediction draws, realized held-out follow-ups |
| `campaign_fixture.py`, `api.py`, `frontend/src/App.tsx`, `report.py` | Clearly synthetic campaign, visible assumptions/settings/profile/cross-period checks, study save/export | API round trip, escaped reports, seven browser workflows and build |
| `validation/research/` | Truth-isolated split generators, paired old/new evaluation, locked plans, perturbations and ablations | Source/seed/configuration manifests and retained raw outputs |

No runtime scientific dependency was added. No neural network, LLM, automatic facility lookup, future meteorology service or field calibration was added. The old information and geometric planners remain named choices; they have separate purposes.

## Campaign model

For source location r and coherent weather scenario k, observed concentrations satisfy

```
y_i = b_window(i) + d_window(i) t_centered(i)/3600
      + Q g_i(r,k,H,z) + a_sensor(i) + e_i + epsilon_i
Q ~ HalfNormal(tau=30000 µg/s)
b_w ~ N(10,20²); d_w ~ N(0,10²)
a_j ~ N(0,1²)
Cov(e_i,e_j) = noise² exp(-distance/150 - |absolute Δt|/600)
Var(epsilon_i) = supplied_sigma_i² (else noise²).
```

Backgrounds/trends are independent between periods, while a given instrument's bias persists. The discrepancy kernel uses absolute time rather than resetting clocks in each period. Wind offset/speed scale are shared across periods. This is a limited uncertainty representation: independent unrecorded period-specific met errors are a mismatch, not a capability implied by adding periods.

After integrating the Gaussian nuisance terms, let C be their covariance plus measurement variance, v=y-10, h the unit-release signature. For speed scale s, the kernel is h/s. Define effective strength q=Q/s with prior scale tau/s. Then

```
precision = 1/(tau/s)² + hᵀ C⁻¹ h
sd = precision^(-1/2); m = hᵀ C⁻¹ v / precision
log evidence_source = log N(y;10,C)
  - log(precision*(tau/s)²)/2 + (m/sd)²/2
  + log(2) + log Φ(m/sd).
```

This identity reduces repeated columns/solves without reducing the weather mixture. The positive normal moments and evidence normalizers remain essential. Location prior mass is proportional to area. Four tensor two-point Gauss–Legendre nodes inside a cell have equal area weights; node posterior mass is summed to the geographic cell. This improves numerical integration in controls but does not prove all narrow/multimodal likelihoods are resolved. The 20m/24-axis cap and 10m/5m comparisons remain documented.

## Exact predictive distribution and screens

Conditioning Gaussian nuisance terms on history gives a base mean a, residual signature h and base covariance V independent of source component. Within a component, future Y=a+hq+Z, with q~Normal(m,sd²) restricted to q>0 and Z~N(0,V). All means and covariance use the exact truncated-normal moments. Sobol draws choose a posterior component, draw the positive strength via inverse truncated-normal CDF and add Gaussian residuals. This removes the former Gaussian moment approximation to predictive tails. The retained information objective still uses that approximation explicitly.

For one future observation, define T=V+h²sd², mu=a+hm, and the Gaussian conditional strength m_c,sd_c after seeing Y. Its exact marginal density is

```
p(Y | q>0) = Normal(Y;mu,T) * Φ(m_c/sd_c) / Φ(m/sd).
```

The test integrates the independent joint train-plus-future likelihood over positive strength and divides by the independent training evidence; agreement is checked at several future values. Marginal log scores are not a product joint likelihood for correlated readings.

For a held sensor/period, D=(Y-EY)ᵀ Cov(Y)⁻¹(Y-EY). Its tail is integrated against draws of the full non-Gaussian predictive mixture rather than a chi-square approximation. For held periods, SVD removes the span of constant background and linear time trend before this calculation. The sample tail is `(1+#D_draw>=D_observed)/2049`. At most six blocks use a familywise threshold `.01/blocks_checked`. This is finite numerical integration under an assumed model; it has no field p-value guarantee. Periods with more than24 instruments explicitly check a subset. At least three observed periods are needed to withhold one and still assess a shared release from the others.

The mathematical distribution check does not guarantee the screen catches incorrect release/transport. Development already demonstrated missed confidently wrong cases. Its actual false-warning/detection rates, acceptance and accepted errors must be read together.

## Nuisance profiles and diagnosis

`whiten_profile` Cholesky-whitens y, source signatures and nuisance design; an SVD removes the nuisance column space including rank deficiencies. For residual signature h, the free nonnegative strength is max(hᵀy,0)/(hᵀh). Direct residual norms avoid cancellation in noiseless examples. Every source/direction node is searched, with minimum loss aggregated into each cell. Source speed is redundant for this unbounded-strength profile. Profiled strength therefore denotes effective Q/speed-scale, not independently identified emitted mass.

The displayed compatible-area statistic uses minimum loss+4.605, an explicitly uncalibrated reference. It can expose a broad likelihood despite a prior-concentrated posterior. It is not a geographic confidence set or a second source probability. Local Fisher axes project out strength and background and describe infinitesimal sensitivity only; they do not rule out distant modes.

## Prediction design and practical update

The new target is **concentration at independent instruments** at all accessible, powered, permitted and supported candidate coordinates, uniformly weighted independent of price/budget. Let C_AA be candidate-observation covariance and C_TA target/observation cross-covariance, integrating all mixture moments. Score a selected subset A by

```
score(A) = trace(C_TA C_AA^-1 C_AT) / number_of_targets.
```

This is the optimal linear predictor's expected mean-squared-error reduction, even when the mixture is non-Gaussian. It is not the exact nonlinear refit risk or source information. Candidate and target instrument IDs differ; measurement noise and instrument bias are independent, while the modeled ambient field at the same location can be shared. A test verifies the formula against independently drawn predictions. Correlated or redundant observations get less incremental credit through the covariance inverse.

All methods use identical static site feasibility, costs, equipment limit and observed window. Exhaustive search handles small feasible spaces; larger spaces report greedy/heuristic status. Deployment duration/travel/forecast wind are not optimized. Follow-up instruments use IDs `followup-{candidate ID}` at the last usable recorded timestamp. New studies must explicitly account for actual relocation/setup and changed weather; the retrospective benchmark is not a future deployment schedule.

The evaluator locks prediction-risk, information, spread, wind, old0.3 and20 random choices before generating any follow-up readings. Candidate outcomes are common across methods; independent target-instrument outcomes are withheld. Campaign inputs exceed0.3's one-window capability: its empty plan is recorded as **not applicable/no update**, not an equal-capability planner competitor. Reports must not claim a campaign victory over0.3's unsupported input.

## Alternatives deliberately limited

- Puff/transition transport needs release histories, independently validated transport and compatible measured averaging periods. A new unvalidated simulator would not repair missing observations. This release instead supports explicit individually steady windows and refuses unsupported transitions.
- Sparse multi-source inference was not added simply to raise source-count labels. Correct-count/wind/physics/covariance oracle searches on noisy old cases still have distant nearly equivalent solutions. A non-identifiable two-source model could create confident arbitrary assignments.
- Background/discrepancy inflation was not used to make every result cover. Coverage, area and accepted-case errors remain explicit. Fixed priors remain research choices and can underdetect weak sources.
- Narrow met uncertainty is accepted only as a declared input with provenance, not estimated from known benchmark errors. Biased-weather challenges intentionally violate it and remain failures.
- More aggressive truth-centered grids/domains, bigger release strengths and dropping difficult cases were not used. Four periods are extra data and are labeled as an instrumentation intervention.

## What the owner should understand before changing code

1. Review the assumptions and covariance first. Changing the prior, wind support, temporal correlation or source domain changes scientific claims, even when unit tests pass.
2. Read source weights, conditional regions and predictive warnings together. Never turn a source marker into facility-responsibility probability. A low source weight is not proof of clean air.
3. Keep all raw/provenance/time transformations and row origins. Imports, resident observations and model output are different evidence types.
4. Preserve published experiment folders and their failures. Any evaluation used to select a new model becomes development-used. Declare fresh conditions/splits and freeze hashes before another final evaluation.
5. Run the independent math/API tests and browser workflow after changes. Recheck resource shapes when altering quadrature, diagnostics or maximum rows; the512-row campaign probe peaks around1.5GiB in one process, not a multiuser capacity guarantee.
6. Obtain compatible controlled-release data and independent atmospheric/statistical review before operational attribution. Verify units, source/receptor heights, emission schedule, coordinates, local weather, averaging and licenses. Set aside entire campaigns before tuning. Prospective added-sensor outcomes are needed before claiming field planning benefit.

The API is unauthenticated loopback software with local, unencrypted private storage. Shared government/company production service would additionally need an authorized deployment design, access controls, retention/audit policy and operations support. None is implied by these scientific changes or by passing local tests.
