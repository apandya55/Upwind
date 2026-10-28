"""Validation runner for plume dispersion models."""

import argparse, hashlib, json, os, platform, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .engineering import numerical_battery, planning_battery, capability_battery
from .api_checks import api_battery
from .science import scientific_runs, followup_runs
from .external import external_check
from ..engine import MODEL_VERSION


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--skip-external",
        action="store_true",
        help="Explicitly record external inspection as skipped",
    )
    args = p.parse_args()
    if MODEL_VERSION != "plume-ensemble-0.2.1":
        p.error(
            "UW-STRESS-2026-01 is an archived discrete-model protocol. "
            "Reproduce it with PYTHONPATH=evaluations/overhaul/baseline-source/backend "
            "before this command. For the current engine use python -m "
            "upwind.validation.overhaul."
        )
    if args.out.exists() and any(args.out.iterdir()):
        p.error(
            "Output folder is not empty; use a new name to preserve previous results"
        )
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    cpu = (
        next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            platform.processor(),
        )
        if Path("/proc/cpuinfo").exists()
        else platform.processor()
    )
    source_root = Path(__file__).resolve().parents[1]
    metadata = {
        "protocol": "UW-STRESS-2026-01",
        "model_version": MODEL_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": cpu,
        "numpy": np.__version__,
        "sequential_python_processes": 1,
        "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS", "not pinned"),
        "source_hashes": {
            str(path.relative_to(source_root)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(source_root.rglob("*.py"))
        },
        "protocol_sha256": hashlib.sha256(
            Path("pyproject.toml").read_bytes()
        ).hexdigest(),
    }
    write(args.out / "metadata.json", metadata)
    print("Running numerical and independent planning oracles", flush=True)
    engineering = {
        "numerical": numerical_battery(),
        "planning": planning_battery(100),
        "capabilities": capability_battery(),
    }
    write(args.out / "engineering.json", engineering)
    print(
        "Engineering checks:",
        sum(v["checks"] for v in engineering.values()),
        "failed groups:",
        sum(v["failed_groups"] for v in engineering.values()),
        flush=True,
    )
    if any(v["failed_groups"] for v in engineering.values()):
        raise SystemExit(
            "Engineering failures retained; correct them before held-out statistical evaluation"
        )
    api = api_battery()
    write(args.out / "api.json", api)
    print("API battery passed:", api["passed"], flush=True)
    resources = []
    for size in [100, 1000, 5000, 10000]:
        try:
            child = subprocess.run(
                [sys.executable, "-m", "upwind.validation.resources", str(size)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            result = (
                json.loads(child.stdout)
                if child.returncode == 0
                else {
                    "size": size,
                    "status": "failed",
                    "exit_code": child.returncode,
                    "stderr": child.stderr[-2000:],
                }
            )
        except subprocess.TimeoutExpired:
            result = {"size": size, "status": "timeout", "limit_seconds": 30}
        resources.append(result)
        print("resource:", result, flush=True)
    write(args.out / "resources.json", resources)
    if args.skip_external:
        external = {"status": "explicitly skipped", "assertions_passed": False}
    else:
        try:
            external = external_check()
        except Exception as e:
            external = {
                "status": "blocked",
                "reason": str(e),
                "assertions_passed": False,
            }
    write(args.out / "external.json", external)
    print("external:", external["status"], flush=True)
    science = scientific_runs()
    write(args.out / "science.json", science)
    followup = followup_runs()
    write(args.out / "followup.json", followup)
    summary = {
        "model_version": MODEL_VERSION,
        "engineering_checks": sum(v["checks"] for v in engineering.values()),
        "engineering_failed_groups": 0,
        "api_passed": api["passed"],
        "scientific_runs": len(science),
        "scientific_crashes": sum(r["status"] == "crash" for r in science),
        "followup_runs": len(followup),
        "followup_crashes": sum(r["status"] == "crash" for r in followup),
        "external_status": external["status"],
        "resource_successes": sum(
            r.get("status") in ["ok", "uninformative"] and r.get("finite", False)
            for r in resources
        ),
        "wall_seconds": round(time.perf_counter() - started, 2),
    }
    write(args.out / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    if (
        not api["passed"]
        or summary["scientific_crashes"]
        or summary["followup_crashes"]
        or summary["resource_successes"] != 4
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
