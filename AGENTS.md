# Working on UPWIND

Read `docs/PROGRESS.md` and `docs/SCIENCE.md` before changing scientific behavior. Preserve local investigation files and existing user edits. The current checkout is already isolated; do not create a worktree unless explicitly requested.

Keep raw imports, UTC/timezone transformations, synthetic row origins, and instrument/provenance metadata. Measurements, resident accounts, model predictions and inferred explanations must stay distinct in UI and exports. No source-responsibility, real-world calibration, partner adoption or field accuracy claim is supported by this release.

Do not tune to the existing held-out evaluation seeds. Scientific changes need a documented hypothesis, revised model/protocol identifier and new held-out development/evaluation separation. Keep failures visible. Unsupported weather must reduce capability rather than create or substitute measurements.

Run relevant existing pytest checks for numerical/API changes. For frontend changes run `cd frontend && npm run build`; use focused Playwright workflows for functional changes. Browser tests own ports 8001/5174 and isolated local storage. Setup/run commands and important limitations are in README. Do not send outreach, publish data, deploy, or push commits without user authorization.
