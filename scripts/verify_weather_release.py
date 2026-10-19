"""Verify retained release evidence without rerunning or modifying the model."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/weather-bias"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    freeze = read(BASE / "final-source-freeze.json")["source_hashes"]
    for name, expected in freeze.items():
        assert digest(ROOT / name) == expected, name
    snapshots = {}
    for name, folder in [
        ("baseline-manifest.json", "baseline-source"),
        ("calibration-source-manifest.json", "calibration-source"),
        ("frozen-source-manifest.json", "frozen-source"),
    ]:
        manifest = read(BASE / name)
        files = manifest["files"]
        for relative, expected in files.items():
            assert digest(BASE / folder / relative) == expected, relative
        snapshots[folder] = len(files)
    counts = {}
    for split, expected in [("calibration", 448), ("final", 896)]:
        records = []
        planning = []
        for index in range(4):
            folder = BASE / f"{split}-part{index}"
            complete = read(folder / "completion.json")
            assert complete["source_unchanged"], str(folder)
            if split == "final":
                assert read(folder / "metadata.json")["source_hashes_before"] == freeze
            records += [
                json.loads(line)
                for line in (folder / "science.jsonl").read_text().splitlines()
            ]
            if (folder / "planning.jsonl").exists():
                planning += [
                    json.loads(line)
                    for line in (folder / "planning.jsonl").read_text().splitlines()
                ]
        assert len(records) == expected
        assert len({(r["family"], r["seed"], r["model"]) for r in records}) == expected
        assert all(r.get("status") in {"fitted", "refused"} for r in records)
        if split == "final":
            assert len(planning) == 360
            assert all(r.get("status") == "fitted" for r in planning)
            assert all(r["cost"] <= 250 and r["equipment"] <= 2 for r in planning)
        counts[split] = {
            "source_outcomes": len(records),
            "followup_fits": len(planning),
        }
    for name in ["report-manifest.json", "figure-manifest.json"]:
        manifest = read(BASE / name)
        entries = manifest.get("artifacts", manifest)
        for relative, expected in entries.items():
            assert digest(ROOT / relative) == expected, relative
    figure = read(BASE / "figure-manifest.json")
    assert digest(BASE / "final-summary.json") == figure["input_sha256"]
    assert digest(ROOT / "scripts/plot_weather_bias.py") == figure["script_sha256"]
    assert read(BASE / "resources-release/completion.json")["source_hashes_after"] == freeze
    result = {
        "passed": True,
        "model": "plume-weather-0.5.0",
        "protocol": "UW-WEATHER-2026-03",
        "source_freeze_sha256": digest(BASE / "final-source-freeze.json"),
        "frozen_files": len(freeze),
        "snapshots": snapshots,
        "counts": counts,
        "final_budget_checks": True,
        "report_and_figure_hashes": True,
        "scope": "Artifact integrity and declared counts; not physical validation or operational certification",
    }
    (BASE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
