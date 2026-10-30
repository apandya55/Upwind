# Deployment and clean data packaging

The selected hosting direction is Vercel for both the static Explorer and the read-only National API, with the downloadable local engine kept as a separate product. This guide's Docker Compose setup remains a local/container staging path; `api/index.py` is the fail-closed Vercel FastAPI entrypoint, and deterministic private-artifact packaging is implemented, but no production artifact or hosted preview is configured. In public mode the API allows GET/HEAD on the national read API and health routes; local workspace, synthetic demo and write endpoints return 404.

## Requirements and configuration

- Python 3.12 for source-data acquisition and reproducible release generation; Node 22.12+ for the Explorer build.
- Two Vercel projects from this monorepo: `frontend/` for the static Explorer and the repository root for the read-only FastAPI API.
- A private Vercel Blob store for the immutable API build artifact when `deployment-data/` is not provided directly to the API build. Public hosting of the generated EPA/Census/OSM bundle was approved by the owner with required attribution; the generated local data directory and downloaded source archives remain ignored by Git.
- Docker Engine and the Compose plugin only for optional local/container staging. The public Vercel target does not require a VM, inbound ports, or an API-domain server.
- `UPWIND_DOMAIN` in `.env`. The default `localhost` is for local staging; Caddy obtains/renews public certificates when configured with a real DNS name and reachable ports 80/443.
- `VITE_SITE_URL` in `.env` must match `UPWIND_DOMAIN` for the Explorer-only container build. Use `https://localhost` for local Caddy staging and the final `https://` domain for public staging. The public build fails if this value is absent; local Vite development may omit it.
- The source `requirements.lock` includes development/test dependencies. The API image installs the runtime-only `requirements-runtime.lock`.

No browser-facing application key or third-party API credential is required. A clean Vercel API build that retrieves private Blob data needs its server-only build bearer token and pinned bundle URL/hash; keep them in Vercel project settings, never in Git or `VITE_*` variables. `UPWIND_DEPLOYMENT_DATA_DIR` optionally changes where the preparation script writes data; `UPWIND_PYTHON` selects its Python executable. At runtime Compose sets `UPWIND_NATIONAL_RELEASE_DIR`, `UPWIND_OSM_ROADS_DIR`, `UPWIND_DATA_DIR`, and `UPWIND_PUBLIC_READONLY=1` inside the API container. Do not turn off the public read-only setting on a public host.

## Acquire and build data

From a clean checkout with dependencies installed, run:

```sh
bash scripts/setup.sh
UPWIND_PYTHON=.venv/bin/python bash scripts/prepare_deployment_data.sh
```

This downloads EPA AQS annual summaries for 2018–2025, the 2024 Census place Gazetteer, 2020–2024 Census place population estimates, and the EPA 2023 NEI facility summary. It validates and hashes source archives, builds the national release, runs the existing nearest-monitor model release evaluator, then requests bounded Durham and Charlotte OpenStreetMap extracts and verifies both demonstration workflows. The model, protocol and calculations are unchanged. The script will stop on unavailable, malformed or incomplete inputs; it does not substitute mocked records.

The verified clean run built release `upwind-national-explorer-0.3.0`: 32,333 searchable places, 31,523 supported estimates, 894 selected-year monitor sites and 76,404 EPA NEI PM2.5 facility records. Durham and Charlotte each have a 2024 estimate, monitor and NEI context within 50 km, plus their bounded OSM extract. These are release coverage counts, not validation or impact claims. The generated `deployment-data/` directory is ignored by Git and is not committed to this repository. After terms approval, validate and package the Vercel API artifact as described in [VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md).

## Build and run private staging

```sh
cp .env.example .env
# For local Caddy staging set UPWIND_DOMAIN=localhost and VITE_SITE_URL=https://localhost.
docker compose build
docker compose up -d
docker compose ps
curl -k https://localhost/api/ready
curl -k 'https://localhost/api/national/places?q=Durham&state=North%20Carolina&year=2024'
```

Open `https://localhost` and accept/trust Caddy's local development certificate as appropriate for the test machine. `/api/ready` checks the five national release JSON files and both city OSM/metadata pairs. To test public HTTPS later, set both `UPWIND_DOMAIN` and `VITE_SITE_URL` to the DNS origin already pointed to the host, open 80/443, and repeat the build/start/check commands. No deployment, cloud account or DNS change is performed by this repository setup.

Use `docker compose logs -f api web` for logs, `docker compose down` to stop services, and preserve the `caddy_data` volume for certificate state. Back up `deployment-data/` before replacing it. For a rollback, stop the services, restore the previous `deployment-data/` snapshot and image revision, then start again.

## All-Vercel target

See [VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md) for the target topology
and unfinished implementation gates. Vercel supports Python FastAPI functions,
and `api/index.py` is the fail-closed entrypoint. The API project runs
`scripts/prepare_vercel_bundle.py` to validate a local bundle or fetch the
versioned private artifact using its pinned SHA-256. Keep the API read-only and
the local engine's user-upload workflow off the public API.

After the Vercel frontend and API preview are wired and HTTPS is live, run the
provider-neutral acceptance check from a machine that can reach both origins:

```sh
python3 scripts/smoke_public_deployment.py \
  --site https://your-site.example \
  --api https://api.your-site.example
```

It checks public model identity, `/api/ready`, an allowed and denied CORS
preflight, forbidden legacy routes, and direct Vercel loads of `/`,
`/methodology`, and `/about`.

## Source terms and public release decision

The bundle combines government datasets and OpenStreetMap-derived extracts. Census data are identified as U.S. Census Bureau public data; EPA AQS and NEI source notices, vintages and URLs are recorded in the generated manifest. The bounded OSM extracts retain source, retrieval time, SHA-256, © OpenStreetMap contributors attribution and ODbL 1.0 identification; show attribution in the interface and comply with ODbL obligations when distributing a derived database. OSM's public tile endpoint remains a separate external best-effort service and must not be bulk-downloaded or rehosted.

The owner approved public hosting of the generated EPA/Census/OSM bundle with its recorded attribution. This records the owner's distribution decision, not an independent legal determination that every proposed redistribution is cleared. UPWIND source uses Apache-2.0; that license does not apply to third-party datasets. Dataset and source notices remain required regardless of the project license.

## Hosting and cost considerations

Vercel pricing, function memory/duration, cold-start behavior, rate limiting, and data storage costs have not been evaluated for this workload. The public OSM raster tile service has usage rules but no production service agreement or availability guarantee in this project.
