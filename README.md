# Upwind

Upwind is an interactive national map and exploration tool for historical fine particulate matter (PM2.5) air pollution across the United States. Built to make federal environmental records accessible, transparent, and easy for anyone to explore place by place.

Most online air quality tools only show real-time AQI widgets or broad county averages. County averages often hide local differences, while raw federal environmental archives are spread across massive spreadsheets that are tough to work with. Upwind brings three distinct public records together on a single map:

1. **Census Place Estimates** — Annual PM2.5 estimates mapped to 31,000+ U.S. Census places.
2. **EPA Monitoring Stations** — Physical federal reference monitors with real historical readings and sampling event history.
3. **Industrial Facility Emissions** — Over 76,000 facilities from the EPA National Emissions Inventory (NEI) with reported PM2.5 tons per year.

Proximity to an industrial facility does not mean it's causing the pollution you breathe. Upwind keeps modeled estimates, physical monitor measurements, and factory inventories visually distinct so you can see what the data actually says—and where its limits are.

---

## What's in the App

- **National Explorer (`/`)**
  Search any U.S. Census town or city, check its estimated annual PM2.5 levels, compare it against the nearest reference monitor, inspect nearby industrial emissions within 50 km, and export community summary briefs (as CSV, GeoJSON, or printable reports).

- **Local Investigation Workspace (`/workspace`)**
  A local playground for importing personal sensor CSVs (like PurpleAir or custom monitors) alongside weather logs to experiment with atmospheric plume dispersion models directly in your browser.

- **Methodology & Science Notes (`/methodology`)**
  Complete documentation of data cleaning choices, nearest-monitor spatial assignment, error bands, and validation checks.

---

## Quick Start

You will need **Python 3.12+** and **Node 22+** (tested on Node 22 and 24).

```bash
# Clone the repository
git clone https://github.com/apandya55/Upwind.git
cd Upwind

# Install Python and Node dependencies
bash scripts/setup.sh

# Start development servers (frontend on :5173, backend API on :8000)
bash scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Data Pipeline

The national dataset is compiled reproducibly from official public government records:

```bash
# Build the national release from EPA and Census sources
.venv/bin/python scripts/build_national_dataset.py

# Run spatial evaluation and benchmark checks
.venv/bin/python scripts/evaluate_national_v3.py
```

### Data Sources
- **EPA Air Quality System (AQS)**: Annual PM2.5 summaries (2018–2024, plus provisional 2025).
- **EPA National Emissions Inventory (NEI)**: 2023 PM2.5-PRI facility emission summaries.
- **U.S. Census Bureau**: 2024 national Gazetteer place internal points and 2020–2024 population estimates.
- **OpenStreetMap contributors**: Local road network context for selected focus areas.

---

## Testing

```bash
# Run core backend tests
.venv/bin/python -m pytest backend/tests/test_national_api.py backend/tests/test_report_evidence.py backend/tests/test_national_dataset.py backend/tests/test_vercel_data_bundle.py backend/tests/test_local_pollution_investigation.py backend/tests/test_json_request_guard.py

# Build frontend and run browser tests
cd frontend
npm run build
npx playwright test
```

---

## Project Structure

```
Upwind/
├── frontend/               # React 19 + TypeScript + Vite + MapLibre GL
│   ├── src/
│   │   ├── national/       # National Explorer components & state
│   │   ├── Landing.tsx     # Homepage & project introduction
│   │   ├── AboutPage.tsx   # Project context & dataset summary
│   │   └── MethodologyPage.tsx # Scientific documentation
│   └── tests/              # Playwright browser end-to-end tests
├── backend/upwind/         # FastAPI backend, data loaders & dispersion math
│   ├── api.py              # REST API endpoints
│   ├── engine.py           # Atmospheric plume model
│   └── importers.py        # CSV parsing & normalization
├── scripts/                # Data download & dataset building scripts
├── data/                   # Release schemas, manifests & metadata
└── evaluations/            # Spatial fold benchmarks & model outputs
```

---

## Limitations

- **Retrospective, not real-time**: Upwind uses annual historical summaries. It is designed for community research and historical perspective, not active wildfire smoke warnings or daily health advisories.
- **Estimates have uncertainty**: The deployed national estimate assigns the nearest eligible monitoring station's reading to each Census place's internal point, with an empirical error band of ±4.123 µg/m³. Places located far from any physical monitor are withheld rather than guessed.
- **Proximity does not equal causation**: Seeing an industrial site near a city on the map does not establish that the facility caused specific ambient readings. Complex winds, stack heights, and atmospheric chemistry all affect transport.

---

## License

Source code is available under the [Apache-2.0 License](LICENSE). Upstream public data records remain subject to their respective government open-data terms.
