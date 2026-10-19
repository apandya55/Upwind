# UPWIND continuation prompt — engine0.6 release

Continue work in `apandya55/Upwind` on GitHub `main`. Read `AGENTS.md`, `docs/PROGRESS.md`, `docs/SCIENCE.md`, `docs/ENGINE_V06_RESULTS.md`, `docs/ENGINE_V06_IMPLEMENTATION.md`, `docs/ENGINE_V06_HARDENING.md`, and the supplementary observability report before changes. Preserve user work and raw evidence. The existing checkout is isolated; do not create worktrees unless requested.

The user requested a stronger pollution inference/prediction engine, severe stress testing, completion of the final two memory changes, GitHub publication and this handoff. Engine **plume-robust-0.6.0**, protocol **UW-ENGINE-2026-06**, is implemented. Package version remains0.1.0. Work is a synthetic research prototype; it does not establish field accuracy, source responsibility, certification or reliability for organizational decisions. Do not claim that passing software tests makes it extremely accurate.

Implemented behavior: joint nominal/common-reference-weather-error mixture (75/25, uncalibrated extra20degree/0.2log-speed scales), area-preserving adaptive source subdivision, posterior mean/density-mode/RMS/domain-edge outputs, exact grouped transport GLS and speed-mixture predictive reductions, UI/HTML disclosure and lossless0.5 result migration. Every positive-prior alternative remains represented. Physical restrictions remain: neutral Gaussian plume, fixed one source/constant release, limited steady windows, Gaussian nuisance/error assumptions and finite weather/geographic quadrature. No multisource or resolved meteorological field model was added.

Primary evidence at `evaluations/engine-v06`: **960 paired model attempts**,480condition-worlds/24seed blocks/20conditions. Each engine432fits+48explicit weather refusals, zero inference crashes/numerical failures/unexpected refusals. Old0.5accepted15,3wrong; new0.6accepted12,1wrong. Source-present region coverage332/408→336/408; broad mean region area76.8%→78.4%domain. In nominal24worlds both accept2/24, median posterior-mean error137.2→141.1m, density-mode166.6→179.9m. **Both50m targets fail.** Common-bias primary accepted errors0→0also fails the strict improvement target. Lower acceptance and wider regions must not be marketed as a precision breakthrough.

Other retained evidence: calibration128fits; original18cases×2models36fits; planning48equal-budget downstream fits with choices locked before outcomes; supplementary passive mean controls; original0.4exact40-case reproduction (18accepted/allwrong); sensitivity/convergence diagnostics. The engineering battery repeats701,017numerical checks,900placement checks,5,000CSV cases and four API rounds; these are fixed software checks, not independent field samples.

A separate **post-primary64-fit** observability control uses16new paired seeds, near-monitor geometry and nominal/shared-bias conditions; it cannot replace the failed primary comparison. Near nominal old11/16accepted,0wrong, median mean28.7m; new7/16accepted,0wrong,35.9m. Shared bias old3/16accepted,3wrong, coverage6/16, median233.9m; new5/16accepted,1wrong, coverage13/16, median98.8m. This is conditional improvement with a remaining accepted wrong region. See `ENGINE_V06_OBSERVABILITY_RESULTS.md` and raw summary.

The user's final two changes are engineering only, applied **after all scientific fits**: bounded grouped/chunked nuisance GLS profiling (fixes a512-reading2GiB diagnostic allocation failure) and a quadratic target-covariance guard (8000targets previously MemoryError, now explicit ValueError). `post-campaign-hardening.json` records exactly two changed scientific paths, separate source copies and before/after hashes. `scripts/hardening_v06.py` verifies their exact hashes, unchanged configuration and AST scope; independent constrained-GLS tests cover up to512rows; ordinary posterior/prediction arrays exactly match frozen code on two inspected constructed cases. Frozen source/primary results were not retrospectively altered. Preserve the original resource failure, memory probe and interrupted concurrent-resource preflight; use the final isolated resource repeat as current evidence. Larger characterized campaigns can explicitly refuse workload that0.5previously fitted; that capability regression remains documented.

Final checks: **209backend tests,8Chromium workflows and frontend build/typecheck pass**. Known Starlette/httpx deprecation and frontend bundle-size warnings remain. Final resource outcomes and source/evidence integrity are in `verification.json`, `resources/results.json` and `ENGINE_V06_HARDENING.md`. Check actual logs if later work changes this state.

Useful commands from repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q
.venv/bin/python scripts/hardening_v06.py
.venv/bin/python scripts/verify_v06.py
cd frontend
npm ci
npm run build
npx playwright install chromium
npm run test:e2e
```

See README for server startup; browser tests own8001/5174 and isolated storage. Existing `.venv` and frontend dependencies may already be ready. Do not run release orchestration into existing exclusive output directories or overwrite frozen artifacts. `verify_v06.py` derives verification/manifests and should pass on this release; historical current-tree identity commands intentionally differ after later model changes. Use historical source archives for old exact-source checks.

All development7100000–3, calibration7200000–7, final7300000–23 and observability7700000–15 seeds are now inspected. Old6100000–6100047/6400000–6400479 and all other retained cases are also reproduction/development evidence, never untouched selection data. Further scientific changes require a documented hypothesis, new model/protocol, fresh untouched seeds and locked comparisons before review. Do not tune to these failures or hide refusals, broad regions or accepted misses.

Measured validation remains the largest missing evidence. Official NOAA/HARMO/Aarhus access returns proxyCONNECT403 (`primary-access.json`); a secondary Prairie Grass workbook has unverified primary provenance and incompatible units/release scale. No field fit was performed. Read `MEASURED_DATA_VALIDATION.md` and `MEASURED_READINESS_AUDIT.md`; distinguish measured observations, modelled workbook values, synthetic controls and evaluator truth. Acquisition helpers preserve raw imports, UTC, units, provenance and completion semantics. Do not guess data or fabricate field scores. If accessible compatible primary data become available, predeclare intake/validation before looking at outcomes.

This release is published to GitHub; determine the actual SHA with `git log -1` and `git ls-remote origin refs/heads/main`. Frozen scientific checkpoint is82bb5fed21c622d2f1378125b8c361108f9d5fe6, baseline2b1ac2186d64fa0f858396c13ab66ac665359d72. No deployment, outreach or investigation-data publication is authorized by a generic continuation. Use existing Git HTTPS proxy authentication; do not infer missing access solely from unset tokens or `gh auth` status. No forced push.
