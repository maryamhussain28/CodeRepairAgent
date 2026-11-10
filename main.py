"""Command-line entry point: python main.py repair evals/<case> --provider scripted."""

import argparse
import sys

from bootstrap import build_repair_service
from core.repair_service import UnknownCaseError


def _print_trace(trace: list[dict]) -> None:
    for entry in trace:
        print(f"[{entry['event']}] {entry}")


def run_repair(eval_path: str, provider: str) -> int:
    """Run one repair attempt and print its trace, changed files, and final result."""
    try:
        service = build_repair_service(provider)
        result = service.repair(eval_path)
    except (UnknownCaseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    _print_trace(result.trace)
    print()
    print("Changed files:", result.changed_files or "(none)")
    if result.last_test_result is not None:
        print(f"Final test result: passed={result.last_test_result.passed}")
        print(result.last_test_result.output)
    print("Repair", "PASSED" if result.passed else "FAILED")

    return 0 if result.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="main.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    repair_parser = subparsers.add_parser("repair", help="Repair one evals/<case> project")
    repair_parser.add_argument("eval_path", help="Path to the selected project, e.g. evals/arithmetic")
    repair_parser.add_argument(
        "--provider", default="scripted", choices=["scripted"], help="Model provider to use"
    )

    subparsers.add_parser("ui", help="Start the local Gradio web page")

    args = parser.parse_args(argv)

    if args.command == "repair":
        return run_repair(args.eval_path, args.provider)

    if args.command == "ui":
        from adapters.gradio_ui import create_demo

        create_demo().launch()
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
