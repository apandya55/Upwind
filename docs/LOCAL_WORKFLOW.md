# Local sensor workflow

The `/local` page links to the workspace, a CSV template, and a small synthetic import fixture. The template is one PM2.5 record with an explicit UTC offset. Use one row per station reading and preserve the original file. Required columns are `sensor_id,timestamp,latitude,longitude,pm25_ug_m3`; concentration units are `ug/m3`. Optional importer fields include `uncertainty_ug_m3`, `humidity_percent`, and `temperature_c`. Metadata such as instrument model and calibration notes should be retained with the investigation notes and source file.

In the workspace, create an investigation, choose **Import data**, select the CSV, map required columns if their names differ, and set an IANA timezone if timestamps have no offsets. The preview reports accepted, invalid, and flagged rows before append. Duplicate station/time pairs and out-of-order readings are flagged for review. Each import is limited to10,000 rows and2 MB. Split larger files into chronological, manageable files while retaining the unmodified source. Imports append to the local investigation and keep the raw text and hash. They are not uploaded to EPA, a tile provider, or another external service.

Use the station map and timeline in the workspace to inspect records and gaps. Export the normalized CSV or self-contained report from **Export evidence**. The private JSON archive includes raw imported content and exact coordinates; handle it as sensitive data. Sparse station data do not support neighborhood interpolation or source attribution merely because a map can draw the stations.

## Install and run

The repository remote is `https://github.com/apandya55/Upwind.git`; `git ls-remote --heads origin main` returned main revision `356beac35434b1dbed3ed75705cc96c384aa402c` during this check. The tested setup commands are for macOS and Linux:

```sh
git clone https://github.com/apandya55/Upwind.git
cd Upwind
bash scripts/setup.sh
bash scripts/dev.sh
```

Open `http://127.0.0.1:5173`. `scripts/setup.sh` requires Python3.12+ and Node22.12+ with npm, creates `.venv`, installs the locked backend requirements, and runs `npm ci` and a frontend build. `scripts/dev.sh` starts the API on loopback port8000 and the frontend on5173. Windows is not tested; use WSL2 with the Linux commands. The single-process API alternative and local data directory are described in the root README.

Local file validation, station/time inspection, analysis, and saving run on the same machine. The national Explorer requires internet for its released datasets and map tiles. No account or paid credential is required for the local CSV workflow. Local database files are not encrypted.

## Import resource probe

On an Apple Mac17,3 with10 CPU cores and16 GiB RAM, macOS Darwin27.0.0, the existing CSV validation function was run in a fresh Python3.14 process with one or100 synthetic station IDs. Peak RSS includes Python, NumPy, Pydantic, the in-memory CSV string, and validated row objects; it excludes the API server, SQLite persistence, browser, and frontend. This is an import-parser probe, not a total application or inference benchmark.

| Stations | Input readings | Accepted | Parse time | Process peak RSS |
|---:|---:|---:|---:|---:|
| 1 | 100 | 100 | 0.001 s | 42.2 MiB |
| 100 | 10,000 | 10,000 | 0.048 s | 59.9 MiB |

The larger fixture is close to the current per-file row ceiling. Actual browser/API memory and longer-running inference depend on retained investigations and selected analysis size; this probe does not establish a whole-app2–3 GiB guarantee. The API request limit is2 MB, and the browser, server, SQLite, and the analysis process can coexist, so split multi-million-row archives before import and retain a copy of the originals.
