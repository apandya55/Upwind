"""Audit one pinned, secondary Prairie Grass workbook without running Excel.

This is a provenance/compatibility audit, not a measured-accuracy benchmark.
Only aggregate metadata are exported; raw observations stay in the local clone.
"""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import posixpath
import subprocess
import xml.etree.ElementTree as ET
import zipfile

REVISION = "6fd4a0892481e25171f3c4c6efe3114448bd4674"
REPOSITORY = "https://github.com/Reinenornormey/Gaussian-plume-model"
WORKBOOK = "Work Assignment Reine.xlsx"
NAMESPACE = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RELATIONSHIP = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def workbook_cells(raw):
    """Read stored cell types/values; a cached formula value is never evaluated."""
    if len(raw) > 4_000_000:
        raise ValueError("Candidate workbook exceeds4MB audit bound")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(info.file_size for info in archive.infolist()) > 32_000_000:
            raise ValueError("Candidate exceeds32MB expanded audit bound")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(node.itertext())
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(
                    "s:si", NAMESPACE
                )
            ]
        relationships = {}
        for relationship in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels")):
            if relationship.get("TargetMode") == "External":
                continue  # Never resolve external workbook/data connections.
            target = relationship.get("Target", "")
            path = posixpath.normpath(
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.join("xl", target)
            )
            if not path.startswith("xl/") or ".." in path.split("/"):
                raise ValueError("Invalid workbook relationship path")
            relationships[relationship.get("Id")] = path
        result = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).findall(
            "s:sheets/s:sheet", NAMESPACE
        ):
            path = relationships.get(sheet.get(RELATIONSHIP))
            if path is None:
                raise ValueError("Missing local worksheet relationship")
            cells = {}
            for cell in ET.fromstring(archive.read(path)).findall(
                "s:sheetData/s:row/s:c", NAMESPACE
            ):
                formula = cell.find("s:f", NAMESPACE)
                node = cell.find("s:v", NAMESPACE)
                text = node.text if node is not None else ""
                kind = cell.get("t", "n")
                if kind == "s":
                    text = strings[int(text)]
                elif kind == "inlineStr":
                    text = "".join(cell.find("s:is", NAMESPACE).itertext())
                cells[cell.get("r")] = {
                    "value": text,
                    "kind": kind,
                    "formula": formula is not None,
                }
            result[sheet.get("name")] = cells
        return result


def constant_number(cell):
    if cell is None or cell["formula"] or cell["kind"] != "n":
        return None
    try:
        number = float(cell["value"])
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def summarize(raw):
    sheets = workbook_cells(raw)
    arcs = []
    for name in ["Arc 50", "Arc 100", "Arc 200", "Arc 400", "Arc 800"]:
        if name not in sheets:
            raise ValueError(f"Missing expected worksheet: {name}")
        cells = sheets[name]
        headers = {
            column: cells.get(column + "1", {}).get("value", "")
            for column in ["A", "B", "C"]
        }
        numeric = {}
        formulas = {}
        for column in ["A", "B", "C"]:
            group = [
                cell
                for ref, cell in cells.items()
                if ref.startswith(column)
                and ref[len(column) :].isdigit()
                and int(ref[len(column) :]) > 1
            ]
            numeric[column] = sum(constant_number(cell) is not None for cell in group)
            formulas[column] = sum(cell["formula"] for cell in group)
        # Do not inherit units from another sheet, or call a stored constant a
        # measurement merely because it is not an Excel formula.
        explicit_unit = headers["B"] == "Concentration (g/m3)"
        arcs.append(
            {
                "sheet": name,
                "headers": headers,
                "numeric_constants_by_column": numeric,
                "formulas_by_column": formulas,
                "purported_observation_column": "B (unverified lineage)",
                "modelled_column_excluded": "C (never an observation)",
                "explicit_observation_unit": "g/m3" if explicit_unit else None,
                "above_app_500_ug_m3_review_threshold": sum(
                    constant_number(cell) > 0.0005
                    for ref, cell in cells.items()
                    if ref.startswith("B")
                    and ref[1:].isdigit()
                    and int(ref[1:]) > 1
                    and constant_number(cell) is not None
                )
                if explicit_unit
                else None,
            }
        )
    simulation = sheets.get("simulations", {})
    q = constant_number(simulation.get("C1"))
    return {
        "audit_type": "secondary-candidate compatibility; no accuracy fit",
        "workbook_sha256": hashlib.sha256(raw).hexdigest(),
        "sheets": list(sheets),
        "arc_columns": arcs,
        "release_constant_as_labelled_g_s": q,
        "release_constant_converted_ug_s": q * 1_000_000 if q is not None else None,
        "wind_at_source_height_workbook_constant_m_s": constant_number(
            simulation.get("C2")
        ),
        "release_height_workbook_constant_m": constant_number(simulation.get("C3")),
        "receptor_height_workbook_constant_m": constant_number(simulation.get("B7")),
        "field_value_status": "Workbook assertions/derived constants only; not independently verified measurements",
        "disposition": "not_ready_for_measured_validation",
        "blockers": [
            "No independently inspected primary archive or measurement-chain provenance",
            "No dataset redistribution license in the pinned two-file repository",
            "Observation units not explicitly stated on every arc sheet; no inherited conversion",
            "No verified UTC sampling date/time, source coordinate frame, wind direction or uncertainty supplied by this audit",
            "Source-height wind constant may be derived; workbook is a modelling assignment, not independent weather evidence",
            "One experiment is not a campaign-level held-out validation set; its inspected data are development-used",
            "SO2 tracer and high mass release are outside any demonstrated PM2.5 attribution validity",
            "Modelled/cached spreadsheet predictions cannot be substituted for measured observations",
        ],
        "observations_redistributed": False,
        "model_fit_performed": False,
        "source_truth_passed_to_inference": False,
    }


def audit(checkout):
    def read(path):
        return subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{REVISION}:{path}"]
        )

    tree = subprocess.check_output(
        ["git", "-C", str(checkout), "ls-tree", "-r", "--name-only", REVISION],
        text=True,
    ).splitlines()
    if set(tree) != {"README.md", WORKBOOK}:
        raise ValueError(
            "Pinned candidate tree differs from the audited two-file repository"
        )
    result = summarize(read(WORKBOOK))
    result.update(
        repository=REPOSITORY,
        revision=REVISION,
        files=tree,
        readme_sha256=hashlib.sha256(read("README.md")).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.checkout)
    # Never overwrite a prior audit or copy raw observations to the output.
    args.out.parent.mkdir(exist_ok=True, parents=True)
    with args.out.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"disposition": result["disposition"], "output": str(args.out)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
