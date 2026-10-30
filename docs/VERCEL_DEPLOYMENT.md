# Vercel deployment target

The release target is one monorepo with three distinct surfaces:

- `frontend/`: the public National Explorer, built as an immutable Vite site;
- the National API: a read-only FastAPI function for the Explorer;
- the local engine: a downloadable Python package for user-owned data and local workflows.

Keep the engine and Explorer model identities separate in health responses,
methodology, exports, and release notes. The public site must never expose the
local upload, analysis, investigation-storage, or synthetic-demo routes.

## Current state

The frontend Vercel build is configured and verified locally:

- project root `frontend`;
- build command `npm run build:vercel`;
- output directory `dist`;
- required variables `VITE_SITE_URL` and `VITE_API_BASE_URL`;
- direct client routes rewrite to `index.html`;
- exact configured API origins are used by browser requests.

The API project's root `vercel.json` runs
`python scripts/prepare_vercel_bundle.py` before the function is built, then
includes only `deployment-data/**` as function data. A missing, malformed,
synthetic, oversized, hash-mismatched, or attribution-incomplete bundle fails
the build instead of producing an unhealthy preview.

The API is packaged for Docker Compose (`compose.api.yaml`) and now has a
fail-closed Vercel FastAPI entrypoint at `api/index.py`. A local import and
synthetic-fixture boundary check pass, but the Vercel build/runtime has not
been preview-tested. Do not claim that an all-Vercel API deployment exists
until the function and data artifact are deployed and the smoke checks below
pass.

## API implementation gate

Create the API Vercel project with the repository root as its project root.
`pyproject.toml` sets `tool.vercel.entrypoint = "api.index:app"` so Vercel
detects the FastAPI framework and sends all request paths through the ASGI
application. Without the framework entrypoint, file-based Python mode would
map `api/index.py` only to `/api`, leaving `/api/national/...` and health paths
unserved. The `api/index.py` entrypoint exposes the existing `upwind.api:app`, forces
`UPWIND_PUBLIC_READONLY=1`, and sets the immutable data paths to `deployment-data`
by default. The root `vercel.json` excludes evaluation, frontend, documentation,
and test trees from the Python function bundle. Use Python 3.12 and the
runtime-only dependency set. The root `requirements.txt` is Vercel's dependency
discovery file and is checked in CI against `requirements-runtime.lock`.
The root `.vercelignore` excludes the frontend, research workspaces, tests, raw
source caches, and local artifacts from the API upload while retaining the
approved `deployment-data/` directory.

The function bundle needs five national release JSON files and four bounded OSM
metadata/extract files required by `/api/ready`. Generated data stays ignored by
Git. The supported clean-checkout path uses a private Vercel Blob object as a
build input; the build retrieves it over HTTPS with a server-only bearer token,
checks a pinned SHA-256, validates its exact file list and metadata, and stages
it under `deployment-data/` before Vercel packages the function. The archive is
not served directly to browsers. The National API serves the approved public
Explorer responses. The owner approved public hosting of the EPA/Census/OSM
bundle with its recorded attribution; no independent legal opinion is implied.

Vercel's current Python limits are relevant to this design: Python function
bundles are limited to 500 MB uncompressed, and a function request or response
is limited to 4.5 MB. The local verifier caps data files at 400 MB to reserve
room for the runtime and application; Vercel's actual function build is the
final size check. The row-oriented API pages are capped below that response
limit: `/api/national/places` returns at most 2,000 rows and
`/api/national/monitors` at most 5,000 rows. Both endpoints retain
`offset`/`next_offset` pagination, and viewport, member, context, and snapshot
responses have their own bounded shapes. A local probe of the generated
release measured 3.15 MB for the broadest tested place search, 3.66 MB for
all-year monitors, and 3.12 MB for sources; repeat these checks after every
release-data change with `python scripts/check_vercel_response_sizes.py` and
again in a hosted preview. The script fails above 4 MiB, leaving headroom below
Vercel's 4.5 MB response ceiling.

## Data artifact

Build and validate the approved production data locally before uploading it
to private Blob:

```bash
UPWIND_PYTHON=.venv/bin/python bash scripts/prepare_deployment_data.sh
python scripts/verify_vercel_bundle.py --data-root deployment-data
python scripts/check_vercel_response_sizes.py
python scripts/package_vercel_bundle.py \
  --data-root deployment-data \
  --output .local/vercel-data-bundle.tar.gz
```

The owner approved public hosting of the generated EPA/Census/OSM bundle with
the attribution recorded in its metadata. Keep the archive itself in a
**private** Vercel Blob store and publish only the approved Explorer API
responses. Record the exact Blob URL and SHA-256 printed by the packager.
Configure the API project's build environment with:

- `UPWIND_VERCEL_BUNDLE_URL`: the private Blob delivery URL;
- `UPWIND_VERCEL_BUNDLE_SHA256`: the recorded archive SHA-256;
- `VERCEL_OIDC_TOKEN` or `UPWIND_VERCEL_BUNDLE_TOKEN`: server-only build access
  to the private object. `BLOB_READ_WRITE_TOKEN` is also recognized when the
  private Blob store provides it.

The build accepts only an HTTPS host ending in
`.private.blob.vercel-storage.com` and refuses redirects, missing digests, token/hash mismatch,
unexpected archive members, traversal paths, test fixtures, missing OSM
attribution, and data larger than 400 MB. Never expose the bearer token through
`VITE_*` variables or add it to the repository. A clean local API project build
without a local `deployment-data/` directory or these variables intentionally
fails closed.

The isolated test fixture may use `--roads-dir ... --allow-synthetic` when
testing the packager in CI. Never pass `--allow-synthetic` for an upload or
deployable preview.

## Web project settings

Create a Vercel project with root `frontend`:

- Install command: `npm ci --no-audit --no-fund`
- Build command: `npm run build:vercel`
- Output directory: `dist`
- `VITE_SITE_URL`: the final public HTTPS site origin
- `VITE_API_BASE_URL`: the final public HTTPS API origin

The frontend `.vercelignore` excludes local tests, the authoring sandbox, and
generated artifacts from the static-site upload.

Create two Vercel projects from the same repository:

- Explorer project root: `frontend`.
- National API project root: repository root, using the root `vercel.json`.

This keeps the product boundary clear without splitting the repository: the
Explorer is static, the API is read-only, and the local engine is distributed
from the Python package/release artifacts. Configure the API function with:

- `UPWIND_PUBLIC_READONLY=1`;
- `UPWIND_CORS_ORIGINS` containing only the exact production site origin and
  explicitly approved preview origins;
- `UPWIND_NATIONAL_RELEASE_DIR` and `UPWIND_OSM_ROADS_DIR` pointing at the
  packaged immutable data paths when the function bundle includes the data;
- no browser-facing API secret.

Do not use wildcard CORS. Do not expose a write-capable API function publicly.

## Preview acceptance

Run the static checks locally with the same compile-time origins:

```sh
cd frontend
VITE_SITE_URL=https://site.example \
VITE_API_BASE_URL=https://api.site.example \
npm run build:vercel
EXPECTED_PUBLIC_API_ORIGIN=https://api.site.example npm run test:e2e:public
```

After both Vercel previews exist, run:

```sh
python3 scripts/smoke_public_deployment.py \
  --site https://site.example \
  --api https://api.site.example
```

The acceptance run must confirm `/api/health`, `/api/ready`, Durham search,
evidence layers, JSON snapshot export, allowed and denied CORS preflight, 404s
for `/api/demo`, `/api/analyze`, `/api/import/csv`, and `/api/investigations`,
and direct loads of `/`, `/methodology`, and `/about`.

## Release gates

Do not switch the public domain or announce availability until all of these are
true:

1. EPA/Census/OSM redistribution terms and attribution are approved.
2. The API function entrypoint and immutable data artifact are deployed.
3. `/api/ready` is healthy in a Vercel preview.
4. The hosted smoke test passes from outside the build environment.
5. Provider-level rate limiting, logs/alerts, backup/restore, and rollback are
   configured.

The local Docker/Caddy stack remains useful for private staging and as a
rollback path, but it is not evidence that the Vercel API is production-ready.

## Vercel references

- [Python functions](https://vercel.com/docs/functions/runtimes/python)
- [Python functions in `/api` and route mapping](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [FastAPI framework entrypoint](https://vercel.com/docs/frameworks/backend/fastapi)
- [Private Blob storage](https://vercel.com/docs/vercel-blob/private-storage)
- [Python Blob SDK](https://vercel.com/docs/vercel-blob/python-sdk-reference)
