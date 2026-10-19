# Completed stress campaign — historical working log

All scientific jobs and checks below have finished. Do not resume the old PIDs/sessions. Read docs/SEVERE_STRESS_RESULTS.md and the completion note at the end; intermediate notes are retained as history.

---

# Active severe stress run — resume without restarting

User request: do a lot of stress testing and ensure accuracy/quality. Scientific claim remains unproven; complete all scheduled experiments and report failures honestly. Publishing remains authorized by prior user requests. Do not change backend/upwind, the main stress script/protocol or nominal supplement while running. No new agents were spawned.

Current source Git parent66ca670; production plume-weather-0.5.0 unchanged. Main protocol UW-STRESS-2026-04:48new seeds6100000–6100047×20conditions=960attempts,240scheduled passive predictions (first12seeds). Fixed nominal confirmation UW-STRESS-2026-04C:480seeds6400000–6400479. All inputs/truth retained separately. Main evaluator source/configuration archived/hash-frozen in evaluations/severe-stress/freeze.json and source/. Nominal supplement also archives its source. Never overwrite old artifacts or silently exclude cases.

## Live jobs

Main CLI: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/severe_stress.py run --shard I --out evaluations/severe-stress`.

- Main shard0session82871/PID15282; shard1session48782/PID15289; shard2session58471/PID15293; shard3session55337/PID15297.
- Nominal0session79457/PID15858; nominal1session54685/PID15860; nominal2session59203/PID15862; nominal3session99319/PID15866. Commands: scripts/confirm_nominal_accuracy.py --out evaluations/severe-stress --shard I.
- Nominal workers were SIGSTOP-paused to keep active inversion workers within four-CPU quota. **Controller session29789 automatically SIGCONT-resumes nominal workers when main workers finish, largest remaining job first.** Do not leave these workers paused or end the task early. Controller uses task-owned PID/cmdline checks, writes scheduling.json, polls five seconds. Normal main workers remain running. Verify current files/status rather than assuming PIDs survive.
- Main logs .local/severe-stress-I.log; nominal logs .local/stress-nominal-I.log. JSONL files append once per completed case; completion.json is written only at shard completion. Main has240rows/shard, nominal120/shard. Main source includes full held-sensor/period refits, making this a substantial CPU run.

## Completed evidence

- Disjoint preflight seeds6101000/6101001: six fits/six passive scores, all finite, unchanged source. Harness tests6pass.
- Full backend **168pass**, one preexistingStarlette/httpx deprecation,163.73s under contention. evaluations/severe-stress/pytest.log. Session27832 complete.
- Frontend production build/typecheck passed2.13s; existing large-bundle warning. frontend-build.log, session10087 complete. Do not npm ci during Vite/tests.
- Engineering session3620 complete:701,017numerical property checks, zero failed groups;900constraint/permutation/exhaustive checks across200placement instances, no failures;5,000seededCSVcases,2,814explicit refusals/2,186parsed,53accepted rows/2,133invalid, no unexpected exceptions. Four64write/32client API rounds:14/24/18/22acked writes (78total), all retained; all recovery/malformed/oversize checks pass. Existing500CSVfixtures repeat inside API rounds and must not count as2,000unique new inputs. Raw JSON under engineering/.
- First observed accepted geographic error in shared_reference_bias seed6100001: MAP175.1916m, region14.874%domain misses truth, sourceprob≈.99999991, no predictive/weather warning. Posthoc diagnosis complete(session7108): references_removed still accepted wrong177.644m/42.563%area; oracle injected common-bias removal accepted/covers, MAP86.495m/19.451%area. **Oracle is evaluator-only**, not a production fix or field calibration. Main input hash unchanged; source unchanged. Raw posthoc-common-bias-diagnosis files and scripts/diagnose_stress_failure.py retained. No production tuning from any outcome.

## Remaining work, do not skip

1. Let all960main and480nominal cases finish. Poll counts/progress; keep meaningful commentary updates. Controller should resume nominal processes when slots free. Capture any crashes/refusals without deletion. Do not claim completed results early.
2. **After scientific workers finish**, run fresh resource probes so CPU contention does not create misleading60s timeouts: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m upwind.validation.weather_aux resources --out evaluations/severe-stress/resources`. Five children60s/2GiB,10kloaded,128/512fit bounds. Preserve every result/refusal/failure. Usually ~2–3minutes.
3. Then `cd frontend && npm run test:e2e > ../evaluations/severe-stress/playwright.log` (Chromium /usr/bin/chromium; isolated8001/5174). Expect eight existing workflows; investigate failures, keep attempts. No frontend change. Do not interfere with user/private normal API storage.
4. Scripts prepared but not yet executed on final data: `.venv/bin/python scripts/report_severe_stress.py` requires all completions/resources/check logs; `MPLCONFIGDIR=.local/mplconfig .venv/bin/python scripts/plot_severe_stress.py` refuses existing figures; `.venv/bin/python scripts/verify_severe_stress.py` checks full evidence and writes artifact manifest. Run sequentially, inspect every error rather than silently patching results. View figure and fix only reporting if needed, retaining initial artifact if regenerating. Report/source semantics must stay distinct.
5. Reporter computes conditions, Wilson intervals, nominal targets, actual prediction scores, last-period spatial-mean and fixed10µg/m³ comparators (reporting methods predeclared before inspecting outcomes), paired5000-world bootstraps/RNG90311. Source model/noise assumptions are synthetic, not full prior-predictive or field calibration. Source point, conditional coverage/area, support label, presence and predictive tasks stay separate. All cases/background false alarms/unsupported refusals included.
6. Update README/PROGRESS and LLM continuation prompt with actual final results/limits/commands. Preserve old manifests as bytes at their original Git revisions; do not rehash historical claims into new ones. Check all links/hash manifests, nativeGit remote, staging excludes .local/credentials/private DB. Commit/push to origin main without force and verify remote SHA/clean checkout. Existing Git auth works through native proxy; gh token status is not authoritative.

Primary measured data access is still an independent pending prerequisite; saved Aarhus/HARMO network draft requires review/save/environment publication, no new evidence it was applied. Do not waste unchanged network retries or claim synthetic success proves field/government attribution readiness. User wants accuracy, not a perfect-sounding report: state failed/inconclusive targets plainly.

## Additional API defect / pending repair (do after all science+resources)

Isolated boundary probe found1200-levelJSON ->500/no writes; legacy result metadata NaN ->200 and silently null after save/reopen. Raw proof files json-boundary-probe.json/nonfinite-roundtrip-confirmation.json. No production file changed yet.

A tested isolated prototype exists in `.local/proposed_api_json_guard.py` (generated by `.local/prototype_json_guard.py`); production API oldSHA `8762f21ba05ae77263fd28631d96519b5381e0d47c5b4cea9a12b1bb05adc396`. Prototype rejects nonfinite JSON numbers/overflow and >64nesting with422 before persistence, preserves valid save/reopen and quotedNaN rawCSV. Seven probes pass (json-guard-prototype.json). **Do not apply until all eight scientific workers AND resources completion exist**; otherwise break the source freeze.

Prepared `backend/tests/test_json_request_guard.py` adds13regressions, not run against production yet (would expose the known defects). Current full-suite168log predates this test file. After applying API-only repair, expected full count181; actually run it, investigate failures and retain logs. Source API guard is a request parser only; inference inputs/physics/thresholds unchanged for valid existing payloads. Use apply_patch or verify oldAPIhash before applying the proposed file; Ruff format. If helper paths change, keep actual before/after hashes.

Write evaluations/severe-stress/api-hardening.json **after application**, with keys:
- applied_after_frozen_runs_and_resources_complete: true (verify all completions first)
- before_sha256: frozen APIsha above
- after_sha256: actual patched APIsha
- evidence of unchanged other44frozen source files / model CONFIG and completion hashes.
Copy final API to evaluations/severe-stress/api-hardening-source/api.py.

Reporter/strong verifier now explicitly permit ONLY this one post-campaign API file difference when matching the manifest; any numerical/evaluator/protocol change still fails. Reporter requires original pytest.log168 and postfix pytest-postfix.log181. Then run final eight browser workflows on the patched API, saving playwright.log. Re-run isolated API overload/boundary recovery if needed to verify parser/admission. Do not overwrite original failing probes or claim they initially passed.

Legacy scripts/verify_weather_release.py gained `--source ROOT` so historical exact source can be checked at evaluations/weather-bias/frozen-source after the API-only repair. Its persisted verification JSON stays byte-identical. Default current-tree identity is strict and should fail for an intentionally changed API; use the explicit archive path for historical checks. New severe verifier checks old archived45files plus exact currentAPI hardening hash; this distinguishes evaluated maths from a later API fix.

Current scientific run remains active (main ~559/960, nominal297/480 paused as of last check); controller29789 will resume nominal workers automatically as main workers finish. Continue all scheduled work; the final accuracy claim has already been disproved for at least one hidden-common-bias case, but do not stop early or tune/exclude it.

Resource watcher session53461 is already queued: it waits for all eight completion.json files, then automatically runs the five resource children and saves .local/severe-resources.log. Do not start a duplicate resource run. Wait for resources/completion.json before applying API patch.

After inserting the actual API guard, source provenance changes are intentionally limited to backend/upwind/api.py. `report_severe_stress.validate_current_source` verifies only that allowed post-campaign difference using api-hardening.json. The manifest must match current/archived API SHA and record all scientific+resource completions before application. New severe verifier imports that helper; it still checks all45original archived files and the unchanged model configuration. The original report log remains168pass, postfix log must actually show181pass (new test module collects13tests). Figure/report scripts are reporting only and may be fixed without changing frozen evidence.

Latest progress: main651/960, nominal297/480paused. Main statuses586fit/65refused, zero source/prediction crashes observed so far. Accepted geography errors seen so far in independent_transport(3), shared_reference_bias(3), source_outside_domain(2), two_sources(1); these are preliminary counts, not final denominators. Do not tune or stop early. Current case files continue to append.

## Completion — all live jobs ended

All960main and480nominal attempts completed; no source/prediction crashes or numeric failures. Both source/configuration freezes verify. Nominal82/480accepted,0accepted region misses (Wilson95% upper4.475%),477/480coverage, medianMAP117.33m overall/35.19m accepted; mean region area63.0%all/18.5%accepted. The50moverall precision target FAILED. Main17accepted geographic errors across correlated(1/4accepted), independenttransport(4/17), sharedlineage(1/8), sharedreferencebias(6/6), sourceoutsidedomain(4/4), twosources(1/9). No general extreme-accuracy/field-readiness claim.

All resource children completed under60s/2GiB: single12826.39s/966.5MiB, single51250.52s/1796.8MiB, characterizedcampaign51227.88s/1160.3MiB;128campaign and unknown512campaign explicitly refuse. Five raw rows/sourcehashes retained.

API-only repair applied AFTER all those completions. `api-hardening.json` and api-hardening-source/api.py retain exact hashes; other44frozen paths/configuration unchanged. Focused13APIregressions pass; finalfull181pass79.36s and8Chromiumworkflows54.7s. Postfixoverload64requests17acked/47explicit429, all acknowledged data retained. All jobs/sessionIDs above are historical, not live services.

Reports/summary/PNG-SVG-PDF now generated. Plot preflight failed on a tiny negative errorbar length from Wilson endpoint roundoff; original script/error retained in figure-preflight/, fixed only rendering with nonnegative lengths. Statistical JSON/data unchanged. Figure visually inspected. `scripts/verify_severe_stress.py` passes source/count/artifact/guard checks; all_nominal_accuracy_targets_pass=false (precision criterion). Original source verified explicitly using `scripts/verify_weather_release.py --source evaluations/weather-bias/frozen-source`.

Remaining: final README/PROGRESS/export prompt/doc status, integrity/link/staging checks, commit/push/remote verification and honest user report. Do not leave work unpushed. No deployment, outreach or measured-data claim. Historical log above intentionally retains intermediate failures/scheduler label correction; scheduling.json has actual PID→shard labels and correction record. No paused workers remain.

Final staging checks: source/document whitespace checks pass; Matplotlib-generated SVG path whitespace is retained as emitted and excluded from source-style checking so figure hashes stay exact. Credential-pattern and private-storage filename scans found no staged matches. Raw generated experiment files are synthetic.
