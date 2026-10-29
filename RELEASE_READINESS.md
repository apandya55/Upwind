# UPWIND v1.0 candidate release readiness

Audit updated: 2026-10-29. This report records the source release candidate and the checks that were run locally. Commit `ce93183` is published on `main`; **UPWIND is not verified production-ready.** No public or production deployment was performed.

## Tonight's verdict

The source tree is ready to be reviewed and published as a **release candidate**. The public National Explorer is not ready to be called a live production service until a real API host/domain is wired, the generated data distribution terms are approved, and HTTPS staging passes. Publish the repository and a clearly labeled release candidate only after the final tree review; keep the public launch switch off until those external gates pass.

The product split is settled for the first release: one monorepo containing the local downloadable engine, the public Vercel Explorer, and the separate read-only National API. Do not split repositories tonight. Keep the engine and Explorer model identities separate in documentation, health responses, and exports.

### What to do now

1. Review the staged release tree and remove anything that is not intended for the public source release. Keep `deployment-data/`, raw upstream archives, local investigations, `.env` files, evaluation workspaces, and generated caches out of Git.
2. Approve the exact EPA/Census/OSM distribution model. The source `LICENSE` is Apache-2.0; that license does not clear upstream data redistribution or ODbL obligations.
3. Create the Vercel project with root `frontend`, then set the final `VITE_SITE_URL` and `VITE_API_BASE_URL`. The Vercel config includes an SPA rewrite for direct `/methodology`, `/about`, and `/local` visits.
4. Provision the selected small Linux VM and set its API DNS name. Prepare `deployment-data/`, set `UPWIND_API_DOMAIN`, set exact `UPWIND_CORS_ORIGINS`, run `compose.api.yaml`, and verify `/api/ready` over HTTPS.
5. Run the hosted smoke test: search a place, inspect monitor and inventory evidence, export JSON, confirm an unlisted origin has no CORS permission, and confirm legacy write/demo routes return 404.
6. Add provider-level rate limiting, logs/alerts, a data backup and restore test, and a rollback rehearsal before changing the public DNS or announcing availability.

After those checks, create the release commit/tag and deploy. Do not claim field accuracy, source responsibility, current conditions, or partner adoption in the launch copy.

The repeatable HTTP acceptance command is `python3 scripts/smoke_public_deployment.py --site https://... --api https://...`; it is provider-neutral because the VM provider and DNS names remain deployment inputs.

## Verified passes

- **Deployment shape:** two supported shapes are configured. The selected target is a Vercel static Explorer calling a separate container API on a small Linux VM with exact-origin CORS; the same-host Caddy stack remains available for private staging. No browser API credential is used.
- **Separate API host:** `compose.api.yaml` runs FastAPI with runtime-only dependencies, a read-only deployment-data mount, exact-origin CORS, and a Caddy HTTPS gateway. Only the gateway publishes ports 80/443.
- **Public API boundary:** `UPWIND_PUBLIC_READONLY=1` allows GET/HEAD only for national explorer and health paths. Legacy workspace, demo, analyze/import, investigation and other routes are hidden with 404. Public reads have endpoint-level result bounds and a 120-request/client/minute in-process limit. Caddy overwrites `X-Forwarded-For`; the API must stay private behind that proxy. The existing request-body limit remains 8 MB for local write routes, which public mode denies before they run.
- **Vercel API boundary:** the static build accepts `VITE_API_BASE_URL`; the API allows browser origins only from the exact comma-separated `UPWIND_CORS_ORIGINS` list. Public OPTIONS preflight is allowed only for those origins and GET/HEAD paths/methods. Same-origin builds leave CORS disabled.
- **Health checks:** `/api/health` reports process/model identity. `/api/ready` returns 503 unless all five runtime national JSON files and both Durham/Charlotte OSM plus metadata files exist and are nonempty. Compose uses `/api/ready` as its container health check.
- **Fresh data packaging:** the acquisition/build/evaluation/verification workflow ran against a clean temporary deployment directory. It downloaded and processed EPA AQS annual monitor summaries (2018–2025), the Census 2024 place Gazetteer and 2020–2024 population estimates, the EPA 2023 NEI facility summary, and fresh bounded Durham and Charlotte OSM API extracts. The evaluator's new `--release-dir` option allowed the built data to be evaluated outside the laptop's ignored release directory. The verified generated release has 32,333 searchable places, 31,523 supported 2024 estimates, 894 selected-year monitor sites and 76,404 EPA NEI facility records.
- **Supported public workflows:** the clean artifacts passed `scripts/verify_release_bundle.py`. A live FastAPI `TestClient` run using only those temporary artifacts returned Durham and Charlotte place estimates, 3 and 4 nearby 2024 monitor summaries, 162 and 164 nearby NEI summary rows, and available OSM road context. A two-place JSON snapshot export returned both places. Public mode returned 404 for legacy demo and write endpoints. These are release-data integration checks, not a network deployment.
- **OSM acquisition and attribution:** the bounded OSM acquisition script retrieved both documented extracts from the OpenStreetMap API, verified OSM XML bounds and recorded retrieval date, source, endpoint, SHA-256, ODbL 1.0 and © OpenStreetMap contributors attribution. Road coverage remains limited to the two supplied Census place points and is contextual only. The public OSM raster tile endpoint remains external and best-effort; its usage policy and lack of production service agreement still apply.
- **Frontend:** `cd frontend && npm run build` passed. The existing large MapLibre bundle advisory remains; it is not a build failure.
- **Public frontend surface:** `VITE_SITE_URL=https://upwind.example npm run build:public` passed and verified that the public output omits the local workspace route shell, investigation application chunk, and authoring-only/unused visual source assets. Screenshots are served as WebP; the public dist is 4.2 MB, down from 23 MB before asset pruning/conversion. Three Playwright checks against the built public site passed. The placeholder origin was used only for build testing, not a deployment.
- **Browser tests:** the full local Playwright suite passed **45 tests** against isolated test ports/storage. The compiled Vercel/public Playwright suite passed **3 tests**, including a request assertion against the configured API origin.
- **Backend tests:** the full supported Python 3.12.3 suite passed **274 tests** in 292 seconds with one existing Starlette/httpx deprecation warning. Focused public-mode, readiness, rate-limit, model-identity, lazy-engine-import, and exact-origin CORS/preflight tests passed. The installed `.venv` uses Python 3.14 and segfaulted in pinned pandas during AQS intake; Python 3.12 is the verified runtime.
- **License and citation:** owner-selected Apache-2.0 source license and `CITATION.cff` are present. This does not clear redistribution of upstream datasets.
- **Dependency audits:** `npm audit --omit=dev` and `pip-audit` against both locked Python files reported no known vulnerabilities. The API runtime lock has 13 packages and excludes the numerical engine, pytest, and test-only HTTP clients.
- **Local engine distribution:** a clean Python 3.12 environment installed `.[engine]` successfully, `upwind --help` returned the CLI commands, and `upwind demo` produced a labeled synthetic result with model/protocol metadata. A built wheel is also verified before publishing. Full `npm audit` (including development dependencies) also reported no known vulnerabilities.
- **Scientific scope:** model, dataset content and numerical results were preserved. The production workflow runs the existing nearest-monitor release evaluator. The deployed estimates remain Census-point assignments supported by historical monitor evidence; they are not place averages, current conditions, field validation, personal exposure or source attribution. Existing methodology and limitations remain in the release artifacts and UI.
- **Credentials:** the deployment configuration requires no application secrets or paid API credentials. `.env.example` contains only a domain and optional local path settings. No credentials have been added to the repository.
- **Configuration syntax:** both Compose YAML files, the GitHub workflow, and `frontend/vercel.json` parsed successfully. Docker Engine and the Compose plugin are absent in this environment, so image builds, Caddy configuration validation and a container health check could not be executed here. No API hosting provider or domain is configured, so Vercel has not been deployed or connected to a real API.
- **Continuous integration:** a GitHub Actions workflow now runs the Python, package artifact, frontend, browser, dependency-audit and Docker build gates on pull requests and main pushes. It has been syntax-parsed locally but has not yet run on GitHub.

## Remaining blockers

1. **Data distribution review.** EPA and Census provenance/terms are recorded in the generated manifest. The OSM bundle is identified as ODbL 1.0 with attribution, but no legal determination has been made that the generated bundle and served road-derived metrics meet all redistribution obligations. Keep generated data out of the source repository until the owner resolves the exact distribution model.
2. **No hosted staging verification.** `docker` is unavailable here, and the VM, DNS names, and Vercel project are not configured. The Vercel static build and separate API contract are prepared, but container images, HTTPS, exact host CORS, `/api/ready`, and real API browser traffic have not been verified on a host. Do not describe the candidate as deployed or staging-tested.
3. **Source RC is published; service release is not.** The reviewed source tree is committed as `ce93183` on `main`. The generated deployment bundle, hosted service, and production data distribution still require the external gates above.
4. **Production operations are unproven.** No production URL, monitoring/alerting, backup restore, load test, rollback rehearsal, host capacity test, or provider contract has been verified. The public OSM tile service has no project production agreement.

## Nonblocking warnings and boundaries

- Public API rate limiting is an in-process per-client ceiling and resets on restart. With direct browser-to-API requests and internet-facing Caddy, it uses the client address seen by Caddy. If a load balancer or proxy sits in front of Caddy, configure only that provider's verified client-IP chain. The limiter is not distributed; add provider-level rate limiting before production.
- The check of Durham and Charlotte does not establish nationwide OSM road coverage. Other locations return an explicit unsupported coverage state.
- Raster basemap tiles are third-party HTTP requests. Prior local desktop/mobile reload checks observed successful settled tile requests; transient aborted requests occurred while the camera moved. Availability remains external and best-effort.
- External dataset providers, OpenStreetMap, and the user's chosen hosting provider must be reachable during acquisition or deployment. Data acquisition fails visibly rather than filling gaps with fixtures.
- A clean data build is reproducible against the source files acquired on 2026-10-26; it is not a permanent immutable upstream snapshot. Retain the generated `deployment-data/` directory with the deployment and its source manifest/hashes.
- The backend test environment has an existing Starlette/httpx deprecation warning. The test suite passed in Python 3.12; Python 3.14 previously segfaulted in pinned pandas 2.2.3 and is not the release runtime.
- Vite reports the existing ~1.05 MB MapLibre chunk advisory. No performance failure was measured in the prior visual audit.
- This is not a full independent accessibility, penetration, security, or legal review. No measured local predictive accuracy or source-responsibility claim is made.

## Selected architecture

- **Frontend:** immutable Vite/React static Explorer hosted on Vercel; exact Vercel project/root/build settings are documented in `docs/VERCEL_DEPLOYMENT.md`.
- **API:** Python 3.12 FastAPI in a separate, single-worker container service on the selected small Linux VM. Vercel browser requests use `VITE_API_BASE_URL` and the exact-origin `UPWIND_CORS_ORIGINS` allowlist; the same-host Compose stack remains available for staging.
- **TLS:** Vercel HTTPS for the frontend and Caddy-managed HTTPS for the API. Caddy obtains automatic HTTPS when a real `UPWIND_DOMAIN` points to the VM and ports 80/443 are available.
- **Data:** generated read-only `deployment-data/release/` plus `deployment-data/osm_roads/raw/`, mounted into the API container. Raw upstream caches are retained outside the runtime volume for rebuilds.
- **Preparation:** exact clean install, acquisition and staging commands are in [DEPLOYMENT.md](DEPLOYMENT.md); Vercel settings are in [VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md). Vercel and the small Linux VM are selected; production domains and stable preview origins remain deployment inputs.

## Hosting and expected costs

The chosen split needs a small container-capable Linux VM with persistent storage, a Vercel project, API/frontend DNS origins, and outbound HTTPS. No paid API or tile credentials are configured. Provider pricing, capacity and traffic costs have not been checked. OSM tiles remain subject to their usage policy and have no service-level commitment here.

## Exact deployment instructions

1. Install Python 3.12, Node 22.12+, Docker Engine and the Docker Compose plugin.
2. From a clean checkout run `bash scripts/setup.sh`.
3. Run `UPWIND_PYTHON=.venv/bin/python bash scripts/prepare_deployment_data.sh`. This acquires/validates source archives, produces estimates, fetches the bounded road extracts and verifies Durham/Charlotte. It writes ignored `deployment-data/`.
4. Review the exact source-data distribution model before publishing or serving generated EPA/Census/OSM data.
5. For private local staging, copy `.env.example` to `.env`, set `UPWIND_DOMAIN=localhost` and `VITE_SITE_URL=https://localhost`. Run `docker compose build`, then `docker compose up -d`, and confirm `curl -k https://localhost/api/ready` returns `{"status":"ready",...}`.
6. On the selected VM, set `UPWIND_DOMAIN` only after DNS points to the host and TCP 80/443 are reachable. Build/start there and verify `/api/ready`, place search, the two city investigations, evidence layers and JSON snapshot export over HTTPS. No deployment has been done by this audit.

## Verification results

- Data pipeline, model release evaluation and `scripts/verify_release_bundle.py`: completed successfully from temporary data outside the repository release directory. Counts: 32,333 places, 31,523 estimates, 894 monitor sites, 76,404 EPA NEI facility records.
- FastAPI data integration: Durham and Charlotte estimate/context checks passed; snapshot JSON for both places returned 200. Legacy public demo and write routes returned 404.
- Full supported Python 3.12 backend suite: **274 passed**, one Starlette/httpx deprecation warning.
- Frontend production build: passed.
- Public Explorer build plus bundle verification: passed with `https://upwind.example`; Vercel build passed with `https://api.upwind.example` as a compile-time test origin; public-site Playwright: **3 passed**. Full local browser suite: **45 passed**.
- Docker image build, Caddy validation, container health, real API CORS/HTTPS, and staging URL: **not run** because Docker is unavailable and no API host/domain is configured.

The candidate has documented architecture, source licensing, a public-only frontend build, and locally verified data workflows, but it is **not production-ready** and has not been verified in a containerized or real staging deployment. Resolve data distribution terms, provision the selected VM and configure domains, run the container and HTTPS staging checks, and put operations controls in place before claiming a production service.
