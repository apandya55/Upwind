"""Verify retained stress source, counts and artifacts; not field certification."""

import hashlib
import json
from pathlib import Path

from severe_stress import FAMILIES, SEEDS, CONFIG
from report_severe_stress import validate_current_source

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/severe-stress"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen = read(BASE / "freeze.json")
    api_guard = validate_current_source(frozen)
    assert CONFIG == frozen["model_configuration"]
    for name, expected in frozen["source_hashes"].items():
        assert digest(BASE / "source" / name) == expected, name
    main_rows, nominal_rows = [], []
    for prefix, destination in [("shard", main_rows), ("nominal", nominal_rows)]:
        for index in range(4):
            folder = BASE / f"{prefix}-{index}"
            metadata, complete = (
                read(folder / "metadata.json"),
                read(folder / "completion.json"),
            )
            assert metadata["source_hashes_before"] == frozen["source_hashes"]
            assert complete["source_unchanged"] and complete["configuration_unchanged"]
            if prefix == "nominal":
                assert complete["supplement_unchanged"]
                for name, expected in metadata["supplement_hashes_before"].items():
                    assert digest(ROOT / name) == expected
                    assert digest(folder / "source" / name) == expected
            for line in (folder / "results.jsonl").read_text().splitlines():
                row = json.loads(line)
                filename = (
                    f"input-{row['seed']}.json"
                    if prefix == "nominal"
                    else f"input-{row['family']}-{row['seed']}.json"
                )
                raw = read(folder / filename)
                assert raw["private_evaluator_truth"]["family"] == row["family"]
                assert raw["private_evaluator_truth"]["seed"] == row["seed"]
                assert raw["investigation"]["synthetic"]
                assert all(
                    m["origin"] == "synthetic"
                    for m in raw["investigation"]["measurements"]
                )
                destination.append(row)
    assert len(main_rows) == 960 and len(nominal_rows) == 480
    assert len({(row["seed"], row["family"]) for row in main_rows}) == 960
    assert {(r["seed"], r["family"]) for r in main_rows} == {
        (seed, family) for seed in SEEDS for family in FAMILIES
    }
    assert {row["seed"] for row in nominal_rows} == set(range(6400000, 6400480))
    assert sum(row["prediction_scheduled"] for row in main_rows) == 240
    for name in ["report-manifest.json", "figure-manifest.json"]:
        manifest = read(BASE / name)
        for filename, expected in manifest.get("artifacts", manifest).items():
            assert digest(ROOT / filename) == expected, filename
    figure = read(BASE / "figure-manifest.json")
    assert digest(BASE / "summary.json") == figure["input_sha256"]
    assert digest(ROOT / "scripts/plot_severe_stress.py") == figure["script_sha256"]
    numerical = read(BASE / "engineering/numerical.json")
    placement = read(BASE / "engineering/placement.json")
    fuzz = read(BASE / "engineering/csv-fuzz.json")
    api = read(BASE / "engineering/api-rounds.json")
    assert read(BASE / "engineering/completion.json")["script_sha256"] == digest(
        ROOT / "scripts/stress_engineering.py"
    )
    assert numerical["failed_groups"] == 0
    assert placement["passed"] and fuzz["passed"] and all(row["passed"] for row in api)
    assert "168 passed" in (BASE / "pytest.log").read_text()
    if api_guard:
        assert "181 passed" in (BASE / "pytest-postfix.log").read_text()
    assert "8 passed" in (BASE / "playwright.log").read_text()
    assert "built in" in (BASE / "frontend-build.log").read_text()
    resources = read(BASE / "resources/completion.json")
    assert resources["source_hashes_after"] == {
        k: v
        for k, v in frozen["source_hashes"].items()
        if k not in {"scripts/severe_stress.py", "docs/SEVERE_STRESS_PROTOCOL.md"}
    }
    diagnosis = read(BASE / "posthoc-common-bias-diagnosis/completion.json")
    assert diagnosis["source_unchanged"] and diagnosis["main_input_unchanged"]
    assert read(BASE / "posthoc-common-bias-diagnosis/metadata.json")[
        "script_sha256"
    ] == digest(ROOT / "scripts/diagnose_stress_failure.py")
    result = {
        "integrity_passed": True,
        "main_attempts": len(main_rows),
        "nominal_confirmation_attempts": len(nominal_rows),
        "predictions_scheduled": 240,
        "inference_crashes": sum(
            row["status"] == "crash" for row in main_rows + nominal_rows
        ),
        "prediction_crashes": sum(
            row.get("prediction", {}).get("status") == "crash" for row in main_rows
        ),
        "numeric_failures": sum(
            row.get("numeric_ok") is False for row in main_rows + nominal_rows
        ),
        "all_nominal_accuracy_targets_pass": read(BASE / "summary.json")[
            "all_nominal_targets_pass"
        ],
        "backend_tests_frozen_source": 168,
        "backend_tests_after_api_repair": 181 if api_guard else None,
        "post_campaign_api_hardening": bool(api_guard),
        "browser_workflows": 8,
        "scientific_source_files_verified": len(frozen["source_hashes"]),
        "meaning": "Artifact/count/source integrity and engineering checks; scientific targets can fail. No measured-field or operational certification.",
    }
    (BASE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    # Full raw-evidence manifest identifies the exact published bytes. Use that
    # Git revision if later documentation or reporting scripts change.
    evidence = {
        str(path.relative_to(ROOT)): digest(path)
        for path in sorted(BASE.rglob("*"))
        if path.is_file() and path.name != "artifact-manifest.json"
    }
    (BASE / "artifact-manifest.json").write_text(
        json.dumps(
            {
                "scope": "Retained bytes at this published run; not all future working-tree documentation",
                "files": evidence,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
