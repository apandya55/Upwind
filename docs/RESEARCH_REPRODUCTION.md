# Reproduce the research candidate

Run from the repository root after `bash scripts/setup.sh`. Python3.12.14, Node24.19 and the pinned runtime lock files were used. No new runtime dependency was introduced. Optional `requirements-research.lock` enables plots; it is separate from application dependencies. Use one BLAS thread for comparable timing. All output directories below must be new; never overwrite the preserved reports.

```sh
# Exact0.3 reproduction, isolated from current source:
PYTHONPATH=evaluations/research/baseline-source/backend \
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.overhaul --split final --out .local/reproduce-0.3

# Current model, development only:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.research.ablation --out .local/reproduce-ablations
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.research.run --split development --planner-seeds 4 \
  --out .local/reproduce-development

# Calibration assesses the fixed source/screen policy; planner not tuned here:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.research.run --split calibration --skip-planner \
  --out .local/reproduce-calibration

# Entire fixed final experiment:40 seed blocks,12 conditions;12 planner blocks/condition:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.research.run --split final --out .local/reproduce-final
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python \
  -m upwind.validation.research.stability --split final --out .local/reproduce-final-stability

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
cd frontend
npm run build
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 npm run test:e2e
```

The final command is a reproduction after inspection, not a fresh untouched validation set for a changed model. Scientific changes require new protocol/conditions and a new held-out split. Never choose thresholds using final truth. The same seed blocks repeat across conditions; they are not480 independent campaigns. Use condition-level Wilson intervals or seed-clustered uncertainty. Planner bootstrap resamples seed blocks with5000 repetitions and reporting RNG90211.

Artifacts under `evaluations/research/` include the baseline113-file source snapshot/hash manifest, exact reproduction comparisons, corrected developmental profiles and bounded two-source references, material/noiseless integration ablations, full development/calibration/final science/follow-ups, perturbation runs, resource probes, API stress, pytest XML and browser logs. Auxiliary executed scripts are retained beside their outputs as text. To rerun one, copy it to a new local script and change its output directory first; the saved script targets the original preserved directory and refuses replacement. They are diagnostic tools, not production pipeline dependencies.

`candidate-freeze.json` records the frozen production/evaluator/protocol/requirements hashes before calibration. Final metadata repeats hashes before and after execution and records allseeds/command/platform/configuration. The implementation/handover manifest records current UI/docs/tests and output hashes separately. A Git commit hash is unavailable: this inherited checkout is on an unborn branch with untracked project files. No hash is invented; no push or deployment was performed.

Resource probes run fresh children with a60-second timeout,2GiB address-space ceiling and one BLAS thread. They load10,000 readings/weather rows but invert at most128/512 selected rows. Campaign probes have six periods,40 instruments,100 total sites,25 anchors,576cells and48,385 raw mixture components. Default128 cannot retain240 sensor×period groups and explicitly refuses;512fits them. Peak RSS describes a single process, not multiuser capacity. Original failed diagnostic sampler probes are preserved beside their corrected rerun.

The local API probe uses isolated synthetic storage `.local/research-api-probe` and port8002. It does not write to the user's normal investigation database. Browser tests own8001/5174 and isolated browser storage. The normal application stays private on8000/5173. Request429 under overload is an explicit retry response; do not count rejected requests as successful writes.

Official measured tracer acquisition was retried with verified HTTPS and failed at the egress proxy, CONNECT403. No data adapter can supply missing release truth, heights, averaging or licensing. The exact routes and errors are preserved; no TLS/proxy bypass, simulated substitute or measured-validation claim is used.

Final-source clarification: `final-source-freeze.json` is the authoritative final hash set; `candidate-freeze.json` records initial calibration and `candidate-freeze-final.json` its subsequent preflight. Full calibration-confirmation reproduces all576outcomes exactly excluding timings under the final hash set. Its old default labels are unchanged; only tiny-fraction collisions, target-ID collisions and descriptive metadata were corrected before final. The incomplete preflight folders were stopped before performance/truth inspection to correct screenshot terminology.

The grid-plan supplementary check clears the fixed-model analysis cache around a diagnostic grid CONFIG mutation. Original grid-refinement source metrics remain valid; its cached plan-overlap field is replaced by `grid-plan-check`, which explicitly reruns the two planners with fresh caches. No production model was changed. The current API's actual probe storage is `.local/research-api-final`, as recorded in `api-live-final/server-metadata.json`; its script results contain an inherited descriptive storage label.
