# Vercel web deployment

The National Explorer can run on Vercel as a static Vite build. The FastAPI
National API remains a separate container service because it reads the pinned
release volume and performs readiness, bounded-query, and operational checks.

## Required project settings

- Root directory: `frontend`
- Build command: configured by `frontend/vercel.json` (`npm run build:vercel`)
- Output directory: `dist`
- Install command: `npm ci --no-audit --no-fund`
- `VITE_SITE_URL`: the final public `https://` origin
- `VITE_API_BASE_URL`: the public National API origin

The Vercel config rewrites direct client-side routes to `index.html`, so links
to `/methodology`, `/about`, and `/local` load on a fresh browser request. The
public build prunes unused design sources and ships optimized WebP screenshots.

The Vercel build fails if either URL is missing. The browser calls the API
origin directly, so configure `UPWIND_CORS_ORIGINS` on the API host with the
exact production Vercel custom domain and any explicitly approved preview
origins, comma-separated. Do not use `*`. No browser-side API secret is used.
Set `UPWIND_PUBLIC_READONLY=1`. Set `UPWIND_TRUST_PROXY=1` only when the API
host's reverse proxy overwrites `X-Forwarded-For` correctly.

## API host requirements

The API service needs Python 3.12, the runtime-only `requirements-runtime.lock`,
the generated `deployment-data/` release mounted read-only, and the bounded
Durham/Charlotte OSM extracts. It must expose `/api/health` and `/api/ready`
over HTTPS and keep port 8000 private. Put a distributed or provider-level
rate limit in front of the in-process 120 requests/client/minute ceiling.

For a Linux VM behind Caddy, use `compose.api.yaml`, `deploy/Caddyfile.api`,
and `deploy/api.env.example`. Copy `deploy/api.env.example` to the API host's
`.env`, set the exact API hostname and Vercel origin(s), point the hostname at
the VM, prepare `deployment-data/`, then run:

```sh
docker compose -f compose.api.yaml config
docker compose -f compose.api.yaml build
docker compose -f compose.api.yaml up -d
curl https://api.your-domain.example/api/ready
```

Only Caddy publishes ports 80/443; FastAPI remains private on the Compose
network. The API volume is read-only. Browser requests go directly to the API
origin, and Caddy overwrites `X-Forwarded-For` with its socket peer. When Caddy
is internet-facing, this is the client address seen by Caddy, not a Vercel edge
address. If the host places a load balancer or proxy in front of Caddy, configure
only that provider's documented client-IP chain and retain provider-level
rate limiting.

## Verification after wiring the origin

1. Build the Vercel preview and confirm `/`, `/landing`, `/methodology`, and `/about` load.
2. Confirm `/api/health` reports `product: national-explorer`, model `upwind-nearest-monitor-annual-pm25-0.3.0`, and protocol `UW-NATIONAL-SPATIAL-2026-04`.
3. Search Durham, open its evidence panel, and export the JSON snapshot.
4. Confirm browser requests from the configured Vercel origin succeed and an unlisted origin receives no `Access-Control-Allow-Origin` header.
5. Confirm `/api/demo`, `/api/analyze`, `/api/import/csv`, and `/api/investigations` return 404 through the API origin.
6. Confirm `/api/ready` is healthy before switching the production domain.
