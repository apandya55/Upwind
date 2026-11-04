# Upwind v0.1.0 — Release Readiness Record

This document records the verification steps and test outcomes for the Upwind v0.1.0 release candidate (National Explorer 0.3.0).

---

## Overview

Upwind is structured as a monorepo containing:
1. **National Explorer**: Static React frontend (`frontend/`) displaying historical PM2.5 data across U.S. Census places.
2. **National API**: Read-only FastAPI service (`backend/upwind/api.py`) serving national place searches, nearest-monitor estimates, and emissions inventory context.
3. **Local Investigation Engine**: Downloadable scientific workspace (`/workspace`) for local sensor CSV imports and atmospheric dispersion modeling.

---

## Verified Checks

- **Data Pipeline & Packaging**
  - Downloaded and verified official source files from EPA AQS, EPA NEI (2023), and U.S. Census Bureau (2024 Gazetteer and population estimates).
  - Built national dataset: 32,333 searchable places, 31,523 supported estimates, 894 monitoring stations, and 76,404 industrial facilities.
  - Verified package bundle with `scripts/verify_vercel_bundle.py` and response sizes with `scripts/check_vercel_response_sizes.py` (all responses under the 4 MiB function ceiling).

- **Backend Test Suite**
  - All core unit and integration tests passing: API endpoints, data loading, spatial cross-validation, and report generation.
  - Public read-only guard (`UPWIND_PUBLIC_READONLY=1`) properly restricts write and workspace endpoints on public origins.

- **Frontend Build & Browser Tests**
  - Production build (`npm run build`) compiles cleanly without errors.
  - Playwright end-to-end tests verify place search, layer toggles, responsive viewports, and snapshot exports.
  - Public build mode (`npm run build:public`) prunes unneeded local assets and generates valid sitemap and metadata.

- **Dependency & Security Hygiene**
  - Dependencies pinned and audited (`npm audit` and `pip-audit`).
  - Source code licensed under Apache-2.0; upstream government open data properly attributed.

---

## Verification Commands

```bash
# Backend test suite
.venv/bin/python -m pytest backend/tests/test_national_api.py backend/tests/test_report_evidence.py backend/tests/test_national_dataset.py backend/tests/test_vercel_data_bundle.py backend/tests/test_local_pollution_investigation.py backend/tests/test_json_request_guard.py

# Frontend production build & tests
cd frontend
npm run build
npx playwright test
```
