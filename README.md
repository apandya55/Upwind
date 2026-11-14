<div align="center">

# Upwind

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24229463.svg)](https://doi.org/10.5281/zenodo.24229463)
[![Hugging Face Dataset](https://img.shields.io/badge/Hugging_Face-Dataset-FFD21E?logo=huggingface)](https://huggingface.co/datasets/epple0/upwind-nc-air-quality)

**A map of historical U.S. fine particulate matter ($\text{PM}_{2.5}$) pollution, with a local dispersion-modeling workspace.**

[![CI Release Checks](https://github.com/apandya55/Upwind/actions/workflows/ci.yml/badge.svg)](https://github.com/apandya55/Upwind/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Node 22+](https://img.shields.io/badge/Node-22%2B-5FA04E.svg?logo=nodedotjs&logoColor=white)](package.json)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](frontend/package.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](backend/upwind/api.py)
[![Vercel Deployment](https://img.shields.io/badge/Vercel-Deployed-black.svg?logo=vercel&logoColor=white)](https://upwind-explorer.vercel.app)

[🌐 Live Web Atlas](https://upwind-explorer.vercel.app) · [⚡ Live API](https://upwind-national-api.vercel.app/api/health) · [Architecture](#system-architecture) · [Quick Start](#quick-start) · [Data Pipeline](#data-pipeline--reproduction) · [Contributing](CONTRIBUTING.md)

<br />

<a href="https://upwind-explorer.vercel.app" target="_blank" rel="noopener noreferrer">
  <img src="docs/assets/explorer-overview.png" alt="Upwind National Explorer Overview" width="100%" style="border-radius: 8px; border: 1px solid #334155;" />
</a>

</div>

> [!TIP]
> **Live Production Deployment**:
> - **Interactive National Explorer**: [https://upwind-explorer.vercel.app](https://upwind-explorer.vercel.app)
> - **Public Read-Only REST API**: [https://upwind-national-api.vercel.app](https://upwind-national-api.vercel.app) (Health: [`/api/health`](https://upwind-national-api.vercel.app/api/health))

---

## Why Upwind?

UPWIND brings EPA monitor readings, annual place estimates, and emissions records together on a map. You can inspect the source behind each value and download the results.

The national release includes:

1. **31,000+ U.S. Census Places**: Modeled annual $\text{PM}_{2.5}$ estimates at Gazetteer internal points, with empirical $\pm 4.12\ \mu\text{g/m}^3$ 90% error bands. The release model sets the distance limit for publishing estimates.
2. **894 Physical EPA Reference Monitors**: Official Air Quality System (AQS) stations showing multi-year historical readings, monitor design values, and sampling event history.
3. **76,400+ Industrial Facilities**: The full EPA National Emissions Inventory (NEI) with reported annual filterable and primary $\text{PM}_{2.5}$ tonnages.

> [!IMPORTANT]
> **Proximity does not equal causation.** Seeing an industrial facility near a town does not prove that factory caused local air readings. Upwind keeps physical monitor measurements, place estimates, and emissions inventories visually and conceptually separate so they can be interpreted separately.

---

## What's in the App

### 1. National Explorer (`/`)
Search any U.S. Census town, borough, or city. Review its estimated annual $\text{PM}_{2.5}$ level, compare it with the nearest physical EPA reference monitor, inspect industrial emitters within a 50 km radius, and export community summary briefs as CSV, GeoJSON, or print-ready reports.

<div align="center">
  <img src="docs/assets/explorer-place.png" alt="Census Place Inspection" width="49%" style="border-radius: 6px; border: 1px solid #334155;" />
  <img src="docs/assets/explorer-sources.png" alt="Industrial Emissions Radius" width="49%" style="border-radius: 6px; border: 1px solid #334155;" />
</div>

### 2. Local Investigation Workspace (`/workspace`)
Run the workspace locally to import sensor CSVs and weather logs, fit Briggs Gaussian plume models, and compare possible source locations. The public site does not accept uploads.

### 3. Methodology & Scientific Notes (`/methodology`)
Data intake criteria, nearest-monitor spatial assignment, 5-fold cross-validation results, and empirical error bands.

---

## System Architecture

The Python pipeline prepares the data, FastAPI serves it, and the React frontend displays the map:

<div align="center">
  <img src="docs/assets/architecture.svg" alt="Upwind Architecture Diagram" width="100%" style="border-radius: 8px; border: 1px solid #334155;" />
</div>

- **Frontend**: React 19, TypeScript, Vite, and MapLibre GL.
- **Backend**: FastAPI with strict Pydantic schemas, spatial radius indexing, and Briggs Gaussian plume dispersion kernels.
- **Data Engine**: Python pipelines compiling EPA AQS, EPA NEI, U.S. Census Gazetteer, and OpenStreetMap road layers into compact release artifacts.

---

## Quick Start

### Prerequisites
- **Python 3.12**
- **Node.js 22.12+** or **Node 24**
- Optional: [`uv`](https://github.com/astral-sh/uv) for fast environment installation

### Installation

```bash
# Clone the repository
git clone https://github.com/apandya55/Upwind.git
cd Upwind

# Install backend virtual environment & build frontend bundle
bash scripts/setup.sh
```

### Running Locally

```bash
# Launch FastAPI backend (:8000) and Vite frontend (:5173) concurrently
bash scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Data Pipeline & Reproduction

Upwind builds its national dataset reproducibly from official government publications:

```bash
# 1. Fetch raw EPA AQS annual summaries and Census Gazetteer files
.venv/bin/python scripts/acquire_aqs.py
.venv/bin/python scripts/acquire_osm_roads.py

# 2. Build the national release dataset (monitors, places, facilities, manifests)
.venv/bin/python scripts/build_national_dataset.py

# 3. Execute spatial cross-validation and benchmark models
.venv/bin/python scripts/evaluate_national_v3.py
```

### Upstream Sources

| Dataset | Source Agency | Timeframe | Records |
| :--- | :--- | :--- | :--- |
| **AQS Annual Summaries** | U.S. EPA | 2018–2024 (provisional 2025) | 894 active eligible stations |
| **National Emissions Inventory (NEI)** | U.S. EPA | 2023 | 76,404 mapped facility records |
| **Gazetteer Place Files** | U.S. Census Bureau | 2024 | 32,333 places (internal points) |
| **Road Density Context** | OpenStreetMap | 2024–2026 snapshot | Major corridors across focus areas |

---

## Verification & Testing

Tests cover the model math, input validation, APIs, and browser workflows:

```bash
# Run backend tests
.venv/bin/python -m pytest backend/tests

# Typecheck and compile frontend bundle
cd frontend
npm run build

# Run Playwright end-to-end browser tests
npx playwright test
```

---

## Scientific Boundaries & Limitations

- **Annual retrospective view**: Upwind is designed for research, baseline comparisons, and historical investigations. It is not an active wildfire tracking tool or real-time emergency alert system.
- **Point-level approximations**: Census estimates represent Gazetteer internal points, not citywide averages. In geographically vast municipalities, conditions vary substantially across town limits.
- **Limited spatial coverage**: The release model sets a maximum supported distance to a monitor. Estimates outside that range are withheld.

---

## Contributing

Bug reports and contributions are welcome. Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before opening a pull request.

---

## Citation

If you use Upwind in academic work, policy research, or environmental analyses, please cite it using:

```bibtex
@software{pandya2026upwind,
  author = {Pandya, Arnav},
  title = {Upwind: An Open-Source National Atlas for Historical Air Pollution Exploration},
  year = {2026},
  url = {https://github.com/apandya55/Upwind},
  license = {Apache-2.0},
  doi = {10.5281/zenodo.24229463}
}
```

See [CITATION.cff](CITATION.cff) for complete citation metadata.

---

## License

Source code is released under the [Apache-2.0 License](LICENSE). Upstream public data records remain subject to their respective U.S. government open-data terms.

## Reproducible annual evidence release

The publication workflow exports 160 NC annual observations at 23 physical stations, evaluates spatial holdouts, generates the county report, and packages checksummed inputs, outputs, and source:

```sh
python -m pip install -r requirements-publication.lock
python scripts/publication_release.py
```

See [publication instructions](publication/README.md), [dataset dictionary](DATA_DICTIONARY.md), [benchmarks](BENCHMARKS.md), and [county evidence report](reports/nc-school-corridors-2026.html). The report documents annual observations and evidence gaps; it does not establish commute peaks, AQI spikes, or school-corridor exposure. Weather is absent from this snapshot. The public downloads live at `/research/` after deployment.

Published artifacts: [Zenodo software archive](https://doi.org/10.5281/zenodo.24229463) · [Hugging Face dataset](https://huggingface.co/datasets/epple0/upwind-nc-air-quality).
