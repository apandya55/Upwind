# Engine overhaul: inspected research and external-data status

Audit date: 2026-10-18 UTC. [external-access.json](../evaluations/overhaul/external-access.json) contains acquisition requests, exact errors, pinned repositories, inspected-file SHA256 values, license findings and reproduction commands. This document distinguishes recommendations from measured performance; the engine evaluation report determines whether an implemented change actually helps.

## Measured-data validation remains unperformed

No compatible controlled-release observation archive was obtained in this overhaul. The following official starting routes were requested using verified HTTPS and the environment's configured proxy:

| Official route | Result |
|---|---|
| [NOAA DATEM programme index](https://www.arl.noaa.gov/research/atmospheric-transport-and-dispersion/atd-programs-datem/) | Proxy refused CONNECT: `403 Forbidden` |
| [NOAA DATEM legacy index](https://www.arl.noaa.gov/datem/) | Same proxy refusal |
| [NOAA local-dispersion/Project Sagebrush tutorial](https://ready.arl.noaa.gov/documents/Tutorial_2021/html/conc_local.html) | Same proxy refusal |

Python reported `URLError: <urlopen error Tunnel connection failed: 403 Forbidden>`. The `curl --fail` retry exited 22 with HTTP 403; a second curl request inspecting headers reported `server: envoy`, exited 56 and printed `curl: (56) CONNECT tunnel failed, response 403`. All exact outputs and commands are retained. The explicit tunnel errors identify the egress proxy blocker; a NOAA file-level response was not established. These failures do not establish that authentication, payment or a different scientific dataset is necessary. Prior draft domain settings do not demonstrate current runtime access. No TLS verification, proxy policy or authentication was bypassed.

Consequently, campaign release histories, source/receptor heights and coordinates, tracer concentration units, sampling periods, local meteorology/stability, missing-value codes, timezone and dataset redistribution terms remain unverified. There is no tracer-localization error, coverage or calibration result to report. A Sagebrush result, if later acquired, would still require a documented compatibility assessment and would not establish PM2.5 source accuracy in a built-up neighborhood.

The earlier [London/openair audit](DATASET_CATALOG.md) remains evidence for the documented import/data-quality tasks. Its single station has no verified source truth in the acquired file; it cannot become an attribution benchmark by relabelling it. This research task did not refit those records or invent station coordinates.

## Official DATEM format source actually inspected

The permitted official GitHub route supplied NOAA ARL's [utilhysplit](https://github.com/noaa-oar-arl/utilhysplit/tree/8df38a0c4d6066bc2631db80ca0fa3c468f8ae61), revision `8df38a0c4d6066bc2631db80ca0fa3c468f8ae61`. Inspected `README.md`, `setup.py` and [`utilhysplit/evaluation/datem.py`](https://github.com/noaa-oar-arl/utilhysplit/blob/8df38a0c4d6066bc2631db80ca0fa3c468f8ae61/utilhysplit/evaluation/datem.py). No upstream Python was executed or imported.

The writer's docstring names year/month/day/hour, duration, latitude/longitude, concentration with units, station ID and height. Its reader exposes additional source ID, level and thickness fields. The code treats hour as HHMM, and the writer obtains units from a dataset column. Thus neither a filename nor a bare numeric concentration column establishes scientific compatibility; metadata must resolve the concentration convention, averaging period, height and time basis. The generic reader alone does not supply a verified timezone or Sagebrush release geometry. No Sagebrush campaign measurements were found in this checkout, and no format adapter or real-data validation was claimed.

`setup.py` declares MIT, while the inspected checkout has no standalone license file. The README contains NOAA's as-is/no-endorsement disclaimer. These source-code declarations do not establish the license of externally hosted campaign measurements. UPWIND uses the source as a reference and copies no code.

## Primary research actually inspected

Gabry, J., Simpson, D., Vehtari, A., Betancourt, M. and Gelman, A. (2019), *Visualization in Bayesian workflow*, JRSS A 182:389–402, [DOI 10.1111/rssa.12378](https://doi.org/10.1111/rssa.12378). The [author repository](https://github.com/jgabry/bayes-vis-paper/tree/3214d1b7905869b5388bf33e8d1d9e230b61e8a4) was acquired at revision `3214d1b7905869b5388bf33e8d1d9e230b61e8a4`; the README and actual `bayes-vis.tex` manuscript were inspected, including sections on prior predictive checks, posterior predictive checks, cross-validation, influential observations and overfitting. No R code or bundled data were run. No repository-wide license was located; the manuscript and data remain in ignored research storage, with only citations and our own methodological conclusions recorded here.

Relevant findings and their limits:

- A normalized posterior alone is not a model evaluation. The paper separates prior predictive plausibility, computational checks, predictive checks and model comparison. UPWIND should make the same distinction between arithmetic correctness, model adequacy, identifiability and empirical reliability.
- A posterior predictive check reuses fitted data. Statistics closely related to fitted parameters can have low power to expose conflict. An in-sample mean or residual threshold is therefore not a certificate that there is one source. Predicting a withheld sensor or episode is a useful separate diagnostic, provided the split prevents correlated observations from leaking across it.
- The paper uses predictive distributions and pointwise log predictive density to compare models and examines influential observations. A useful UPWIND diagnostic records predictive spread, held-out errors and log scores, and shows which groups fail. A single favorable global RMSE can conceal a failing sensor.
- Its calibration examples explicitly diagnose overly broad predictions as well as overly narrow ones. Increasing every noise scale or returning the entire map can damage usefulness; coverage needs region area and retained-case rates alongside it.
- Model criticism is iterative and can overfit the criticism dataset. Existing stress cases become development-used after inspection. An evaluation that motivates a change must be replaced or explicitly cease to be called untouched.

This paper studies a different PM2.5 statistical model. Its workflow supports these evaluation choices; it supplies no field validation of UPWIND's atmospheric kernel, priors, wind distribution, planner or attribution claims.

## Official mathematical documentation actually inspected

The official [Stan documentation source](https://github.com/stan-dev/docs/tree/235171991f7040b0b0ebb59e974d1299af5a049b) was acquired at revision `235171991f7040b0b0ebb59e974d1299af5a049b`. These are method references; UPWIND does not add Stan or an MCMC dependency.

| Inspected source chapter | Relevant check or decision | Limit |
|---|---|---|
| [Posterior and Prior Predictive Checks](https://github.com/stan-dev/docs/blob/235171991f7040b0b0ebb59e974d1299af5a049b/src/stan-users-guide/posterior-predictive-checks.qmd) | Replicate observations under the fitted distribution and compare specified features; inspect prior-predictive plausibility | Posterior predictive tail areas are not generally classically calibrated p-values; a non-alarm does not establish adequate physics |
| [Simulation-Based Calibration](https://github.com/stan-dev/docs/blob/235171991f7040b0b0ebb59e974d1299af5a049b/src/stan-users-guide/simulation-based-calibration.qmd) | Generate parameters from the declared prior, then data, then inspect inference calibration/ranks | A matched-model computational check does not validate wind mismatch, an omitted source family or a real campaign |
| [Held-Out Evaluation and Cross-Validation](https://github.com/stan-dev/docs/blob/235171991f7040b0b0ebb59e974d1299af5a049b/src/stan-users-guide/cross-validation.qmd) | Evaluate the predictive mixture on withheld observations using stable log-sum-exp; keep test outcomes out of fitting | UPWIND's sensor/time correlations require group or episode splits; exchangeable row splitting alone would overstate independence |
| [Finite Mixtures](https://github.com/stan-dev/docs/blob/235171991f7040b0b0ebb59e974d1299af5a049b/src/stan-users-guide/finite-mixtures.qmd) | Marginalize discrete model/location alternatives with their declared prior weights and retain stable normalization | Conditional support among listed models is not the probability that the model list contains physical truth |

The inspected bibliography identifies the original SBC paper as Talts et al. (2018), arXiv **1804.06788**; the direct request was blocked, so this audit relies on the inspected official exposition and does not claim to have read that full paper. Direct Stan-site, arXiv and EPA AERMOD documentation requests were also blocked and are retained in the access record. An initial unverified arXiv identifier and two missing repository candidates are marked unused in that record; they are not cited as scientific evidence.

Stan's inspected `LICENSE` distinguishes BSD-3-Clause code from CC BY-ND 4.0 text/images. This document provides original analysis and links; it does not redistribute modified manual text or images. No source copy was incorporated into application code. The full local checkout is research storage rather than an installation requirement.

## Implications to evaluate in the redesign

These are hypotheses and design constraints, not success claims:

1. **Background-only comparison:** allow an observation vector to be explained without a localized plume. Report its model support separately from source-location weights conditional on a release. Comparing models needs explicit priors and all likelihood normalizing terms when covariances differ. Better background flexibility can also absorb a weak plume, so measure lost localization and false negatives.
2. **Predictive adequacy:** withhold whole sensors or separated episodes, integrate nuisance uncertainty, and predict the held-out group without its outcomes. Report unavailable diagnostics when too few independent groups exist. Test no-source cases and matched cases for false alarms as well as multiple-source/weather mismatch for missed failures. Observationally equivalent physical situations remain undetectable.
3. **Coherent nuisance uncertainty:** background, instrument offsets and wind uncertainty can impersonate movement of a source. A wind perturbation represents a shared meteorological error over the stated steady window, rather than independent random directions at every monitor. Uncertainty magnitudes require declared assumptions and independent evaluation; enlarging them until known failures disappear is not calibration.
4. **Geographic meaning:** a selected set of point-source IDs is a conditional discrete set, with zero geographic area as points. A geographic region requires an explicit partition or continuous model, prior measure, boundary treatment and construction rule. Assess off-grid truth coverage and area together; never call the original IDs a calibrated geographic confidence region.
5. **Selection and planning:** a deterministic subset can suppress rare informative observations. Compare full and selected inference and preserve the discarded rows. Test realized post-measurement benefit against the same feasible baselines, under noise/weather uncertainty, before promising improved recommendations. These sources provide no evidence that a particular UPWIND acquisition score already wins.

The existing fixed-height rural-neutral Gaussian approximation should remain explicitly conditional unless an atmospheric formulation and compatible observations justify changing it. The blocked EPA formulation was not inspected, so this audit does not validate the existing dispersion coefficients or extend them to urban, intermittent or elevated-release conditions.

## Reproducing acquisition and completing field validation

From the repository root, the following retries use the same official entry points. The curl failures are expected in the currently recorded environment:

```sh
mkdir -p .local/overhaul-research
curl --fail --show-error --location --connect-timeout 20 --max-time 60 \
  https://www.arl.noaa.gov/research/atmospheric-transport-and-dispersion/atd-programs-datem/ \
  --output .local/overhaul-research/datem-index.html
curl --fail --show-error --location --connect-timeout 20 --max-time 60 \
  https://ready.arl.noaa.gov/documents/Tutorial_2021/html/conc_local.html \
  --output .local/overhaul-research/sagebrush-tutorial.html
```

The access artifact records exact Git clone commands and revisions; checkout the recorded revision after cloning if a remote HEAD has moved. Scientific-source content hashes let an operator verify the inspected files. An existing checkout must be preserved rather than cloned over or reset destructively.

After official access is available, inspect the returned index/tutorial hyperlinks before downloading a campaign file; no archive URL was invented here. Retain raw archives and their SHA256 manifests, original documentation and terms. Verify release schedule and mass rate, tracer/mass or mixing-ratio conversion, source/receptor heights and locations, observation averaging period, meteorological conventions/stability and clock alignment. Establish campaign-level development/calibration/final separation before model tuning, and keep release truth solely in the evaluator. Implement a bounded adapter that rejects missing essential metadata. Only then run and report measured-data comparisons, with explicit acceptance and compatibility limits.
