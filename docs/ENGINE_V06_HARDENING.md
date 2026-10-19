# Final engine0.6 memory safeguards

Both final changes are complete. They were applied after all frozen scientific and supplementary runs. They bound engineering allocations without changing posterior/prior/support/planner rules. [Exact source record](../evaluations/engine-v06/post-campaign-hardening.json) preserves49before/after hashes; only `inference.py` and `identifiability.py` differ. Separate final source copies and unchanged original freeze are retained.

The512-reading single-window child originally failed under a2GiB address-space ceiling while expanding diagnostic signatures (294MiB residual allocation). The grouped GLS profile whitens a repeated-signature basis once and processes at most2048source columns per block, retaining the full observation covariance. Nuisance-space numerical nulls cannot acquire enormous fitted release strength from projection roundoff.

The8000-target/1GiB prediction probe originally raised MemoryError while allocating a977MiB pairwise displacement tensor. A quadratic target-covariance guard now refuses this query explicitly in about0.009s, before that allocation. Existing linear transport-work limits remain.

Validation: **209backend tests,8Chromium workflows and frontend build/typecheck pass**. Eight new regressions compare grouped profiles against dense GLS and independent constrained least squares up to512rows, check rank-null/chunk invariance, and exercise the three public prediction paths. Posterior weights/cells/source coordinates and ordinary moments/draws/log-densities are exactly equal to frozen source on two inspected constructed cases. `scripts/hardening_v06.py` proves exact hashes, unchanged configuration and AST scope. These constructed checks do not establish general scientific accuracy.

## Isolated resource repeat

Each child has60s/2GiB limits and runs sequentially after application checks ended.10,000loaded pollution and weather rows do not mean10,000inverted readings.

| Study | Requested fit rows | Characterized | Child / analysis | Seconds | Peak RSS MiB |
|---|---:|---|---|---:|---:|
| single window | 128 | False | finished / ok | 42.75 | 653.0 |
| single window | 512 | False | finished / ok | 42.66 | 697.7 |
| campaign | 128 | False | finished / insufficient_data | 1.71 | 211.9 |
| campaign | 512 | False | finished / insufficient_data | 1.73 | 214.1 |
| campaign | 512 | True | finished / insufficient_data | 1.82 | 214.2 |

Both single-window probes now finish, including the previously failing512-reading case. The three campaign probes explicitly refuse their supported numerical/steady-group workload; refusal is not a successful inference. In particular the characterized512campaign was fitted by0.5but is refused by0.6because richer alternatives exceed the design bound: a capability regression. Timing is specific to this machine/workload, not a service guarantee.

Original failures/resources and original201-test release logs remain under `resources-pre-hardening`, `pre-hardening-report` and `.pre-hardening` files. A mistakenly overlapping resource preflight was interrupted and retained with an explicit exclusion record; only the isolated repeat above is the final resource comparison.

Reproduce engineering integrity with `.venv/bin/python scripts/hardening_v06.py` and full evidence with `.venv/bin/python scripts/verify_v06.py`. Read [primary accuracy results](ENGINE_V06_RESULTS.md) and [supplementary observability](ENGINE_V06_OBSERVABILITY_RESULTS.md): primary50m point-error targets still fail, and accepted wrong regions remain. No field validation or organizational attribution reliability is established.
