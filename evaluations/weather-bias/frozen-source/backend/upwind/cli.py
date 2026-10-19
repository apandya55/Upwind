import argparse
import json
from pathlib import Path
from .fixtures import synthetic_case, CASES
from .engine import analyze
from .models import Investigation


def main():
    parser = argparse.ArgumentParser(
        description="Reproduce UPWIND analysis without the browser"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--case", choices=CASES, default="identifiable")
    demo.add_argument("--out", default=".local/demo-result.json")
    run = sub.add_parser("analyze")
    run.add_argument("investigation")
    run.add_argument("--out", default=".local/analysis.json")
    evaluation = sub.add_parser("evaluate")
    evaluation.add_argument("--out", default=".local/current-model-evaluation.json")
    args = parser.parse_args()
    if args.command == "evaluate":
        from .evaluation import evaluate

        result = evaluate()
    else:
        inv = (
            synthetic_case(args.case)[0]
            if args.command == "demo"
            else Investigation.model_validate_json(Path(args.investigation).read_text())
        )
        result = analyze(inv)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Saved {path}")
    print(
        json.dumps(
            result if args.command != "evaluate" else result["summary"], indent=2
        )
    )


if __name__ == "__main__":
    main()
