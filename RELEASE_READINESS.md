# UPWIND source 0.1.0 / National Explorer 0.3.0 release readiness

Audit updated: 2026-10-29. This report records the source release candidate and checks run locally. Commit `e75ee2e` passed GitHub Actions run `40980151135`. **UPWIND is not verified production-ready.** No public or production deployment was performed.

## Tonight's verdict

The public source release is an early **release candidate**, not a production-ready service. The owner selected Vercel for both hosted projects and approved public hosting of the generated EPA/Census/OSM bundle with its required attribution. The tree has a verified static Vercel build, a fail-closed FastAPI entrypoint at `api/index.py`, and locally verified deterministic artifact packaging; the production data artifact, Vercel function build, and hosted preview remain unverified. This records the owner's distribution decision, not an independent legal opinion.

Keep one monorepo containing the local downloadable engine, the public Vercel Explorer, and the separate read-only National API. Do not split repositories for this release. Keep the engine and Explorer model identities separate in documentation, health responses, and exports.

### Release identities

- **Software/package and API:** `0.1.0`, as recorded by `pyproject.toml`, the frontend package metadata, and API health.
- **National Explorer release/data model:** `upwind-national-explorer-0.3.0`, model `upwind-nearest-monitor-annual-pm25-0.3.0`, protocol `UW-NATIONAL-SPATIAL-2026-04`.
- **Local engine science:** model `plume-robust-0.9.0`, protocol `UW-ENGINE-2026-09`; this is not the package version.

Keep these identifiers independent. The source prerelease tag is `v0.1.0-rc.1`; package artifacts report software version `0.1.0`. Data manifests and model outputs retain their own release and scientific identifiers.

### What to do now

Tonight's scope is a **source release candidate only**. With GitHub Actions green, publish tag `v0.1.0-rc.1` and attach the `0.1.0` Python wheel and source archive. Keep generated data, raw upstream archives, local investigations, `.env` files, evaluation workspaces, and caches out of Git and release assets.

The owner approved public hosting of the EPA/Census/OSM bundle with its required attribution. The hosted service is deferred: Vercel is logged out on this machine, its two projects and private Blob object do not exist, and no HTTPS preview has passed. When service work resumes, create the static project rooted at `frontend` and the read-only Python API project rooted at the repository; upload the pinned private artifact; verify `/api/ready`, exact-origin CORS, public route boundaries, place/evidence/export workflows, monitoring, rate limits, backup/restore, and rollback before launch.

Do not claim field accuracy, source responsibility, current conditions, partner adoption, or that the hosted National Explorer is live.

The repeatable HTTP acceptance command is `python3 scripts/smoke_public_deployment.py --site https://... --api https://...`; it is provider-neutral because Vercel project domains remain deployment inputs.

## Verified passes

- **Deployment shape:** the static Vercel Explorer is configured. The all-Vercel target uses a read-only FastAPI function and keeps the downloadable local engine separate. `tool.vercel.entrypoint = "api.index:app"` explicitly selects the FastAPI framework so its app receives all API paths; without it, Vercel's file-based Python mode would map `api/index.py` only to `/api`. The fail-closed entrypoint and config have local tests, but the authenticated Vercel build/runtime and hosted data packaging remain unverified. Docker/Caddy remains available as a private staging path. No browser API credential is used.
- **Container staging path:** `compose.api.yaml` runs FastAPI with runtime-only dependencies, a read-only deployment-data mount, exact-origin CORS, and a Caddy HTTPS gateway. This is a private staging/rollback path, not the selected public hosting target.
- **Public API boundary:** `UPWIND_PUBLIC_READONLY=1` allows GET/HEAD only for national explorer and health paths. Legacy workspace, demo, analyze/import, investigation and other routes are hidden with 404. Public reads have endpoint-level result bounds and a 120-request/client/minute in-process limit. Caddy overwrites `X-Forwarded-For`; the API must stay private behind that proxy. The existing request-body limit remains 8 MB for local write routes, which public mode denies before they run.
- **Vercel API boundary:** the static build accepts `VITE_API_BASE_URL`; the FastAPI API allows browser origins only from the exact comma-separated `UPWIND_CORS_ORIGINS` list. Public OPTIONS preflight is allowed only for those origins and GET/HEAD paths/methods. Same-origin builds leave CORS disabled. This proves the API policy in local tests, not a Vercel function deployment.
- **Vercel data gate:** the API project's root `vercel.json` runs `scripts/prepare_vercel_bundle.py`, then explicitly includes `deployment-data/**`. `scripts/package_vercel_bundle.py` creates a deterministic archive of the five national JSON files and four OSM/attribution files. The ignored local `deployment-data/` copy passes both bundle verifiers and packages as a 6,748,430-byte archive containing 84,901,481 bytes of release data. Its SHA-256 is `cad3f7b73b5156103a188344624003bc3ff8a90c4516424f8d24584d65cae738`. The build supports a private HTTPS artifact URL pinned by SHA-256, rejects synthetic data and unsafe archives, and caps data files at 400 MB to reserve Vercel's 500 MB function limit for runtime code. The archive remains local; it has not been uploaded to Blob.
- **Vercel response-size gate:** `/api/national/places` is capped at 2,000 rows per page and `/api/national/monitors` at 5,000 rows per page, with offset pagination preserved. `scripts/check_vercel_response_sizes.py` checks nine representative serialized API bodies against a 4 MiB ceiling. Against the generated release, the largest tested place search was 3.15 MB, all-year monitors 3.66 MB, and sources 3.12 MB; all nine passed with the largest body at 3,660,594 bytes. Hosted preview verification remains required.
- **Health checks:** `/api/health` reports process/model identity. `/api/ready` returns 503 unless all five runtime national JSON files and both Durham/Charlotte OSM plus metadata files exist and are nonempty. Compose uses `/api/ready` as its container health check.
- **Fresh data packaging:** the acquisition/build/evaluation/verification workflow ran against a clean temporary deployment directory. It downloaded and processed EPA AQS annual monitor summaries (2018–2025), the Census 2024 place Gazetteer and 2020–2024 population estimates, the EPA 2023 NEI facility summary, and fresh bounded Durham and Charlotte OSM API extracts. The evaluator's new `--release-dir` option allowed the built data to be evaluated outside the laptop's ignored release directory. The verified generated release has 32,333 searchable places, 31,523 supported 2024 estimates, 894 selected-year monitor sites and 76,404 EPA NEI facility records.
- **Supported public workflows:** the clean artifacts passed `scripts/verify_release_bundle.py`. A live FastAPI `TestClient` run using only those temporary artifacts returned Durham and Charlotte place estimates, 3 and 4 nearby 2024 monitor summaries, 162 and 164 nearby NEI summary rows, and available OSM road context. A two-place JSON snapshot export returned both places. Public mode returned 404 for legacy demo and write endpoints. These are release-data integration checks, not a network deployment.
- **OSM acquisition and attribution:** the bounded OSM acquisition script retrieved both documented extracts from the OpenStreetMap API, verified OSM XML bounds and recorded retrieval date, source, endpoint, SHA-256, ODbL 1.0 and © OpenStreetMap contributors attribution. Road coverage remains limited to the two supplied Census place points and is contextual only. The public OSM raster tile endpoint remains external and best-effort; its usage policy and lack of production service agreement still apply.
- **Frontend:** `cd frontend && npm run build` passed. The existing large MapLibre bundle advisory remains; it is not a build failure.
- **Public frontend surface:** `VITE_SITE_URL=https://upwind.example npm run build:public` passed and verified that the public output omits the local workspace route shell, investigation application chunk, and authoring-only/unused visual source assets. Screenshots are served as WebP; the public dist is 4.2 MB, down from 23 MB before asset pruning/conversion. Three Playwright checks against the built public site passed. The placeholder origin was used only for build testing, not a deployment.
- **Browser tests:** the full local Playwright suite passed **45 tests** against isolated test ports/storage. The compiled Vercel/public Playwright suite passed **3 tests**, including a request assertion against the configured API origin.
- **Backend tests:** the full supported Python 3.12.3 suite passed **286 tests** in 296 seconds with one existing Starlette/httpx deprecation warning. The bundle tests cover deterministic archives, digest mismatch, synthetic rejection, unsafe URLs/paths, public-mode entrypoint setup, the explicit FastAPI framework entrypoint, full `/api/national/...` route paths, and allowed/denied CORS preflight. Focused public-mode, readiness, rate-limit, model-identity, and lazy-engine-import tests passed. The pre-existing `.venv` uses Python 3.14 and segfaults in native-extension subprocess tests; the full suite was run in a clean Python 3.12.3 environment matching the release lock.
- **License and citation:** owner-selected Apache-2.0 source license and source-versioned `CITATION.cff` are present. The owner separately approved public hosting of the generated EPA/Census/OSM bundle with the required attribution; this is not an independent legal opinion.
- **Security reporting:** `SECURITY.md` defines the private vulnerability-reporting path and keeps public API reports free of credentials, private measurements, and raw upstream archives.
- **Dependency audits:** `npm audit --omit=dev` and `pip-audit` against both locked Python files reported no known vulnerabilities. The API runtime lock has 13 packages and excludes the numerical engine, pytest, and test-only HTTP clients.
- **Local engine distribution:** a clean Python 3.12 environment installed `.[engine]` successfully, `upwind --help` returned the CLI commands, and `upwind demo` produced a labeled synthetic result with model/protocol metadata. A built wheel is also verified before publishing. Full `npm audit` (including development dependencies) also reported no known vulnerabilities.
- **Scientific scope:** model, dataset content and numerical results were preserved. The production workflow runs the existing nearest-monitor release evaluator. The deployed estimates remain Census-point assignments supported by historical monitor evidence; they are not place averages, current conditions, field validation, personal exposure or source attribution. Existing methodology and limitations remain in the release artifacts and UI.
- **Credentials:** no browser-facing application key or paid API credential is required. Clean API builds that retrieve a private Blob artifact require a server-only bearer token plus the artifact URL and SHA-256. No credentials have been added to the repository.
- **Configuration syntax:** both Vercel JSON configs and the GitHub workflow parse successfully; `requirements.txt` matches the runtime lock. Vercel CLI 65.8.0 is available through `npx`, but the CLI is currently logged out, so the CLI build could not authenticate. Docker Engine and Docker Compose are absent, so container builds and Caddy validation could not be run. No Vercel projects, private Blob object, or domains are configured.
- **Continuous integration:** the previous release-surface runs on `ce931831` and `7527f219` failed because of legacy data paths and missing browser fixtures. Commit `e75ee2e` includes isolated fixture setup, the Vercel API boundary checks, and a slower-browser timeout. GitHub Actions run `40980151135` passed: backend 286 tests in 8m55s, frontend 45 local-engine and 3 public-surface browser tests, and the container build.

## Remaining blockers

1. **No hosted staging verification.** No Vercel projects, domains, private Blob object, or build credentials are configured. The static build and API entrypoint pass local checks, but the Vercel function build, HTTPS, exact-origin CORS, `/api/ready`, and real API browser traffic have not been verified on a host. Do not describe the candidate as deployed or staging-tested.
2. **Production operations are unproven.** No production URL, monitoring/alerting, backup restore, load test, rollback rehearsal, function-capacity test, or provider contract has been verified. The public OSM tile service has no project production agreement.

## Nonblocking warnings and boundaries

- Public API rate limiting is an in-process per-client ceiling and resets on restart. The Vercel deployment must add provider-level rate limiting before production; the local limiter is not distributed.
- The check of Durham and Charlotte does not establish nationwide OSM road coverage. Other locations return an explicit unsupported coverage state.
- Raster basemap tiles are third-party HTTP requests. Prior local desktop/mobile reload checks observed successful settled tile requests; transient aborted requests occurred while the camera moved. Availability remains external and best-effort.
- External dataset providers, OpenStreetMap, and the user's chosen hosting provider must be reachable during acquisition or deployment. Data acquisition fails visibly rather than filling gaps with fixtures.
- A clean data build is reproducible against the source files acquired on 2026-10-26; it is not a permanent immutable upstream snapshot. Retain the generated `deployment-data/` directory with the deployment and its source manifest/hashes.
- The backend test environment has an existing Starlette/httpx deprecation warning. The full suite passed in Python 3.12; the existing Python 3.14 environment is outside the supported release range and segfaults in a native-extension subprocess test.
- Vite reports the existing ~1.05 MB MapLibre chunk advisory. No performance failure was measured in the prior visual audit.
- This is not a full independent accessibility, penetration, security, or legal review. No measured local predictive accuracy or source-responsibility claim is made.

## Selected architecture

- **Frontend:** immutable Vite/React static Explorer hosted on Vercel; exact project/root/build settings are documented in `docs/VERCEL_DEPLOYMENT.md`.
- **API target:** Python 3.12 FastAPI as a separate Vercel function with `UPWIND_PUBLIC_READONLY=1`, exact-origin CORS, and an approved immutable data artifact. The local entrypoint exists; function deployment and data packaging are not verified.
- **TLS:** Vercel-managed HTTPS for both projects after real domains are attached and preview smoke tests pass.
- **Data:** a versioned archive is fetched from a private Vercel Blob store during the API build and bundled into the read-only function. The archive is not stored in Git or served directly to browsers. A verified local archive exists; owner approval includes required attribution, but no private Blob copy has been created.
- **Preparation:** exact clean install, acquisition, packaging, and staging commands are in [DEPLOYMENT.md](DEPLOYMENT.md) and [VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md). Production domains and stable preview origins remain deployment inputs.

## Hosting and expected costs

The chosen split needs two Vercel projects, API/frontend DNS origins, an approved immutable artifact in private Vercel Blob, and outbound HTTPS for external basemap tiles. No paid API or tile credentials are configured. Provider pricing, function capacity, cold starts, and traffic costs have not been checked. OSM tiles remain subject to their usage policy and have no service-level commitment here.

## Local container staging instructions

1. Install Python 3.12, Node 22.12+, Docker Engine and the Docker Compose plugin.
2. From a clean checkout run `bash scripts/setup.sh`.
3. Run `UPWIND_PYTHON=.venv/bin/python bash scripts/prepare_deployment_data.sh`. This acquires/validates source archives, produces estimates, fetches the bounded road extracts and verifies Durham/Charlotte. It writes ignored `deployment-data/`.
4. Preserve the approved EPA/Census/OSM attribution and source notices when packaging the public bundle; the owner's approval is recorded above.
5. For private local staging, copy `.env.example` to `.env`, set `UPWIND_DOMAIN=localhost` and `VITE_SITE_URL=https://localhost`. Run `docker compose build`, then `docker compose up -d`, and confirm `curl -k https://localhost/api/ready` returns `{"status":"ready",...}`.
6. For the all-Vercel target, package the approved data artifact, create preview projects, and verify `/api/ready`, place search, the two city investigations, evidence layers, and JSON snapshot export over HTTPS. No deployment has been done by this audit.

## Verification results

- Data pipeline, model release evaluation and `scripts/verify_release_bundle.py`: completed successfully from temporary data outside the repository release directory. Counts: 32,333 places, 31,523 estimates, 894 monitor sites, 76,404 EPA NEI facility records.
- FastAPI data integration: Durham and Charlotte estimate/context checks passed; snapshot JSON for both places returned 200. Legacy public demo and write routes returned 404.
- Vercel response-size preflight against the actual ignored production bundle: **9 representative responses passed** at a 4 MiB ceiling; maximum serialized body was 3,660,594 bytes.
- Full supported Python 3.12 backend suite: **286 passed**, one Starlette/httpx deprecation warning.
- Frontend production build: passed.
- Public Explorer build plus bundle verification: passed with `https://upwind.example`; Vercel build passed with `https://api.upwind.example` as a compile-time test origin; public-site Playwright: **3 passed**. Full local browser suite: **45 passed**.
- Vercel API function build, immutable data bundle, real API CORS/HTTPS, and staging URL: **not run** because the Vercel CLI is logged out and projects, domains, and private Blob artifact are not configured. Docker image build and Caddy validation are also unavailable locally.

The candidate has documented architecture, source licensing, a public-only frontend build, and locally verified data workflows, but it is **not production-ready** and has not been verified in a real staging deployment. Upload the approved artifact to private Vercel Blob, configure the two projects and domains, run the HTTPS smoke checks, and put operations controls in place before claiming a production service.
