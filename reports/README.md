# NC annual evidence report

This is an annual evidence report, not a completed commute-window or school-corridor study. Do not describe it as showing highway-related AQI spikes.

Rebuild with `python scripts/build_nc_report.py` after installing the project export extra, matplotlib, reportlab, and pypdf. Run `scripts/export_and_benchmark.py` first if the Parquet input is absent. The generator uses `upwind.report.static_evidence_report`, writes exactly three PDF pages, and copies HTML/PDF/CSV into the frontend public directory. The HTML is self-contained and has no scripts or external image dependencies.

`manifest.json` records output SHA-256 checksums. The report records the input checksum. Summary CSV retains unrounded numeric values; displayed tables use six decimal places. SVG charts are supplied separately for reuse.

Before a Zenodo deposit, include the matching source revision, Parquet input, DATA_DICTIONARY.md, BENCHMARKS.md, report artifacts and manifest. Confirm authorship, dataset redistribution terms, version and license in the deposition metadata. No DOI or publication is claimed. Public hosting requires deployment of the frontend changes.
