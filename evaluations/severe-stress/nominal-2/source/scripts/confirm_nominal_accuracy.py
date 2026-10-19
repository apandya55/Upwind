"""Fixed-size nominal confirmation; no optional stopping or model changes."""

import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import time

from severe_stress import case, evaluate, fingerprints, write, CONFIG, ROOT

SEEDS = tuple(range(6400000, 6400480))


def supplement_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [Path(__file__), ROOT / "docs/STRESS_NOMINAL_CONFIRMATION.md"]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shard", type=int, required=True, choices=range(4))
    args = parser.parse_args()
    frozen = json.loads((args.out / "freeze.json").read_text())
    before = fingerprints()
    supplemental = supplement_hashes()
    assert before == frozen["source_hashes"] and CONFIG == frozen["model_configuration"]
    folder = args.out / f"nominal-{args.shard}"
    folder.mkdir(parents=True, exist_ok=False)
    write(
        folder / "metadata.json",
        {
            "protocol": "UW-STRESS-2026-04C",
            "seeds": list(SEEDS[args.shard :: 4]),
            "source_hashes_before": before,
            "supplement_hashes_before": supplemental,
            "model_configuration": CONFIG,
        },
    )
    for name in supplemental:
        destination = folder / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    counts = Counter()
    started = time.perf_counter()
    for seed in SEEDS[args.shard :: 4]:
        inv, truth = case("characterized_nominal", seed)
        write(
            folder / f"input-{seed}.json",
            {"investigation": inv.model_dump(), "private_evaluator_truth": truth},
        )
        row = evaluate(inv, truth)
        with (folder / "results.jsonl").open("a") as output:
            output.write(json.dumps(row, allow_nan=False) + "\n")
        counts[row["status"]] += 1
        print(seed, row["status"], row.get("accepted"), flush=True)
        del inv, truth, row
        gc.collect()
    write(
        folder / "completion.json",
        {
            "counts": dict(counts),
            "seconds": time.perf_counter() - started,
            "source_unchanged": before == fingerprints(),
            "supplement_unchanged": supplemental == supplement_hashes(),
            "configuration_unchanged": CONFIG == frozen["model_configuration"],
        },
    )


if __name__ == "__main__":
    main()
