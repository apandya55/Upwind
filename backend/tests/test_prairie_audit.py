"""Synthetic OOXML fixtures; no third-party measurements are redistributed."""

import importlib.util
import io
from pathlib import Path
import zipfile

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/audit_prairie_candidate.py"


@pytest.fixture
def auditor():
    spec = importlib.util.spec_from_file_location("prairie_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workbook(*, formula=False, units=True, external=False, bad_path=False):
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sheets = ["Arc 50", "Arc 100", "Arc 200", "Arc 400", "Arc 800", "simulations"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as source:
        source.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="{office}"><sheets>'
            + "".join(
                f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>'
                for i, name in enumerate(sheets, 1)
            )
            + "</sheets></workbook>",
        )
        targets = []
        for i, name in enumerate(sheets, 1):
            target = (
                "../escape.xml" if bad_path and i == 1 else f"worksheets/sheet{i}.xml"
            )
            extra = ' TargetMode="External"' if external and i == 1 else ""
            targets.append(f'<Relationship Id="rId{i}" Target="{target}"{extra}/>')
            if name == "simulations":
                data = '<row r="1"><c r="C1"><v>2</v></c></row><row r="2"><c r="C2"><v>3</v></c></row><row r="3"><c r="C3"><v>0.5</v></c></row><row r="7"><c r="B7"><v>1.5</v></c></row>'
            else:
                unit = "Concentration (g/m3)" if units and i != 1 else "Co"
                f = "<f>DO_NOT_EXECUTE_EXTERNAL_FUNCTION()</f>" if formula else ""
                data = f'<row r="1"><c r="A1" t="inlineStr"><is><t>y</t></is></c><c r="B1" t="inlineStr"><is><t>{unit}</t></is></c><c r="C1" t="inlineStr"><is><t>Cp</t></is></c></row><row r="2"><c r="A2"><v>0</v></c><c r="B2">{f}<v>0.001</v></c><c r="C2"><v>100000000</v></c></row>'
            source.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f'<worksheet xmlns="{main}"><sheetData>{data}</sheetData></worksheet>',
            )
        source.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(targets)
            + "</Relationships>",
        )
    return buffer.getvalue()


def test_observed_and_modelled_columns_never_merge(auditor):
    result = auditor.summarize(workbook())
    assert result["disposition"] == "not_ready_for_measured_validation"
    assert not result["model_fit_performed"]
    assert not result["observations_redistributed"]
    arc = result["arc_columns"][1]
    assert arc["numeric_constants_by_column"] == {"A": 1, "B": 1, "C": 1}
    assert arc["above_app_500_ug_m3_review_threshold"] == 1
    assert "never an observation" in arc["modelled_column_excluded"]
    # Release conversion is a unit calculation, not a fitted or verified truth.
    assert result["release_constant_converted_ug_s"] == 2_000_000
    assert "not independently verified" in result["field_value_status"]


def test_units_are_not_inherited_from_another_sheet(auditor):
    result = auditor.summarize(workbook())
    first, second = result["arc_columns"][:2]
    assert first["explicit_observation_unit"] is None
    assert first["above_app_500_ug_m3_review_threshold"] is None
    assert second["explicit_observation_unit"] == "g/m3"


def test_formula_cached_values_are_not_observation_constants(auditor):
    result = auditor.summarize(workbook(formula=True))
    arc = result["arc_columns"][1]
    assert arc["numeric_constants_by_column"]["B"] == 0
    assert arc["formulas_by_column"]["B"] == 1
    assert arc["above_app_500_ug_m3_review_threshold"] == 0


@pytest.mark.parametrize(
    "kind,value", [("n", "NaN"), ("n", "inf"), ("s", "123"), ("b", "1"), ("n", "bad")]
)
def test_non_numeric_or_nonfinite_cells_cannot_be_measurements(auditor, kind, value):
    assert (
        auditor.constant_number({"kind": kind, "value": value, "formula": False})
        is None
    )


@pytest.mark.parametrize("kwargs", [{"external": True}, {"bad_path": True}])
def test_external_or_escaping_relationships_are_refused(auditor, kwargs):
    with pytest.raises(ValueError):
        auditor.summarize(workbook(**kwargs))


def test_oversized_workbook_is_refused_before_decompression(auditor):
    with pytest.raises(ValueError, match="4MB"):
        auditor.workbook_cells(b"x" * 4_000_001)
