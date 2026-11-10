# Contributing to Upwind

Thank you for your interest in contributing to Upwind. We welcome bug reports, documentation improvements, data pipeline enhancements, and UI polish from scientists, software engineers, and community advocates.

---

## Guiding Principles

1. **Scientific Integrity Over Optimism**
   - Never fabricate or interpolate values when data is absent. If an area lacks an eligible federal monitor within the empirical support threshold, Upwind withholds the estimate rather than guessing.
   - Proximity does not equal causation. Keep emissions inventories, reference monitor measurements, and community estimates visually and conceptually distinct.

2. **Reproducibility**
   - Every number displayed in the national atlas can be traced back to its raw EPA or Census source file through the build scripts in `scripts/`.
   - Any modification to model logic or data transformations must include validation tests.

3. **Human Craft & Clean Code**
   - Write clear, idiomatic code with concise, technical comments explaining *why* non-obvious mathematical or domain choices exist.
   - Avoid generic boilerplate or robotic docstrings.

---

## Development Setup

### Prerequisites

- **Python 3.12**
- **Node.js 22.12+** or **Node 24**
- **Git**
- Optional: [`uv`](https://github.com/astral-sh/uv) (recommended for fast Python environment management)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/apandya55/Upwind.git
cd Upwind

# Install dependencies and build frontend assets
bash scripts/setup.sh
```

### Running Locally

To start both the FastAPI backend (on `http://localhost:8000`) and the Vite development server (on `http://localhost:5173`):

```bash
bash scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running Tests

Before opening a pull request, ensure all test suites pass locally.

### Backend Tests

Run the full pytest suite (over 220 tests covering physics models, data ingestion, and API routes):

```bash
.venv/bin/python -m pytest backend/tests
```

To run a fast subset during feature iteration:

```bash
.venv/bin/python -m pytest backend/tests/test_national_api.py backend/tests/test_engine.py
```

### Frontend Typechecking & Production Build

```bash
cd frontend
npm run build
```

### Browser End-to-End Tests

```bash
cd frontend
npx playwright test
```

---

## Project Structure

```
Upwind/
├── backend/upwind/         # FastAPI application, data loaders & plume physics
│   ├── api.py              # REST API endpoints & route handling
│   ├── engine.py           # Atmospheric Gaussian plume dispersion calculations
│   ├── importers.py        # Sensor CSV parsing & time-series normalization
│   └── models.py           # Pydantic schemas and validation rules
├── frontend/               # React 19 + TypeScript + Vite + MapLibre GL
│   ├── src/
│   │   ├── national/       # National Explorer atlas, filters, and drawer UI
│   │   ├── Landing.tsx     # Homepage & project introduction
│   │   ├── AboutPage.tsx   # Project context & dataset summary
│   │   └── MethodologyPage.tsx # Scientific documentation
│   └── tests/              # Playwright browser end-to-end tests
├── scripts/                # Data acquisition, dataset building & validation scripts
│   ├── build_national_dataset.py  # Compiles EPA AQS + NEI + Census into release data
│   ├── evaluate_national_v2.py    # Spatial cross-validation benchmarks
│   ├── setup.sh                   # Environment setup script
│   └── dev.sh                     # Concurrent local dev server runner
├── data/                   # Release schemas, manifests & metadata
└── docs/                   # Visual architecture diagrams and documentation assets
```

---

## Submitting Pull Requests

1. **Create a topic branch**: `git checkout -b feature/your-feature-name`
2. **Make focused, atomic commits**: Follow standard commit message conventions (`feat: ...`, `fix: ...`, `docs: ...`, `perf: ...`).
3. **Verify locally**: Make sure `npm run build` in `frontend/` and `pytest backend/tests` succeed with zero errors.
4. **Open a Pull Request**: Detail the problem addressed, the solution implemented, and any visual or data changes.

---

## License

By contributing to Upwind, you agree that your contributions will be licensed under the [Apache-2.0 License](LICENSE).
