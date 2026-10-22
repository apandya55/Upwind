"""Verify the post-release data-integrity patch without rewriting frozen evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evaluations/engine-v06/post-release-integrity.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record = json.loads(RECORD.read_text())
    before = record["source_before"]
    after = record["source_after"]
    changed = {name for name in after if before[name] != after[name]}
    assert changed == set(record["changed_paths"])
    current = {name: digest(ROOT / name) for name in after}
    assert current == after
    assert record["scientific_configuration_unchanged"]
    print("Post-release integrity patch hashes verified")


if __name__ == "__main__":
    main()
