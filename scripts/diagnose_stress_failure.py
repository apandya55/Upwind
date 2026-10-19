"""Post-hoc explanation of a retained failure, never a production correction."""

import copy
import hashlib
import json
from pathlib import Path
import time

from upwind.models import Investigation
from severe_stress import evaluate, fingerprints, write

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evaluations/severe-stress"


def main():
    folder = BASE / "posthoc-common-bias-diagnosis"
    folder.mkdir(exist_ok=False)
    source = BASE / "shard-1/input-shared_reference_bias-6100001.json"
    original = json.loads(source.read_text())
    truth = original["private_evaluator_truth"]
    inv = Investigation.model_validate(original["investigation"])
    correction = truth["mutation"]["hidden_common_bias_deg"]
    before = fingerprints()
    write(
        folder / "metadata.json",
        {
            "role": "Post-hoc diagnosis of the first observed accepted error in hidden-common-bias stress; not a held-out improvement experiment",
            "case_input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_hashes_before": before,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "oracle_warning": "Known injected weather bias is evaluator truth. It is used ONLY in the separately labelled diagnostic variants, never in main inputs, model configuration, plans or field calibration.",
        },
    )
    started = time.perf_counter()
    results = []
    for name in ["original", "references_removed", "oracle_common_bias_removed"]:
        modified = inv.model_copy(deep=True)
        if name == "references_removed":
            modified.weather = [w for w in modified.weather if w.role == "primary"]
        if name == "oracle_common_bias_removed":
            for row in modified.weather:
                row.wind_from_deg = float((row.wind_from_deg - correction) % 360)
        result = evaluate(modified, copy.deepcopy(truth), prediction=False)
        result.update(variant=name, evaluator_oracle_used=name.startswith("oracle"))
        write(folder / (name + ".json"), result)
        results.append(result)
        print(
            name,
            result["status"],
            result.get("accepted"),
            result.get("region90_covered"),
            result.get("map_error_m"),
            flush=True,
        )
    assert original == json.loads(source.read_text()), "Main case changed"
    write(
        folder / "completion.json",
        {
            "source_unchanged": before == fingerprints(),
            "main_input_unchanged": True,
            "results": len(results),
            "seconds": time.perf_counter() - started,
        },
    )


if __name__ == "__main__":
    main()
