"""Stable CLI surface; handlers load only when their command is invoked."""

import argparse
import importlib
import json
import sys

from . import __version__


def build_parser():
    parser = argparse.ArgumentParser(prog="autotest", description="Evidence-based agent checks")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("skill", help="Locate the packaged agent skill and reference files")
    doctor = commands.add_parser("doctor", help="Inspect installed capabilities without secrets")
    doctor.add_argument("--probe-browser", action="store_true")
    discover = commands.add_parser("discover", help="Inspect repository metadata")
    discover.add_argument("path", nargs="?", default=".")
    validate = commands.add_parser("validate", help="Validate a configuration without executing it")
    validate.add_argument("config")
    for name in ("plan", "run"):
        command = commands.add_parser(name)
        command.add_argument("config")
        command.add_argument("--profile", choices=("smoke", "changed", "release"), default="smoke")
        command.add_argument("--changed-file", action="append", default=[])
        if name == "run":
            command.add_argument("--output", default=".autotest/runs")
    report = commands.add_parser("report", help="Render an existing current-run report")
    report.add_argument("run_directory")
    benchmark = commands.add_parser("benchmark", help="Exercise seeded defects and clean controls")
    benchmark.add_argument("--output", default=".autotest/benchmark")
    regression = commands.add_parser(
        "regression", help="Propose a regression test for a confirmed seeded case"
    )
    regression.add_argument("--case", required=True)
    regression.add_argument("--output", required=True)
    demo = commands.add_parser("demo", help="Start the isolated demonstration target")
    demo.add_argument("--port", type=int, default=8765)
    demo.add_argument("--defects", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "skill":
            from pathlib import Path

            bundled = Path(__file__).parent / "skill" / "SKILL.md"
            source = Path(__file__).resolve().parents[2] / "SKILL.md"
            path = bundled if bundled.is_file() else source
            if not path.is_file():
                raise ValueError("Skill resources missing")
            print(json.dumps({"skill": str(path), "resource_root": str(path.parent)}))
            return 0
        if args.command == "doctor":
            from .doctor import diagnose

            result = diagnose(args.probe_browser)
            print(json.dumps(result, indent=2))
            return 0 if result["core_ready"] else 2
        modules = {
            "discover": "discovery",
            "validate": "config",
            "plan": "planner",
            "run": "runner",
            "report": "reporting",
            "benchmark": "benchmark",
            "demo": "demo",
            "regression": "regression",
        }
        try:
            handler = importlib.import_module(f"autotest_skill.{modules[args.command]}")
        except ModuleNotFoundError as exc:
            if exc.name == f"autotest_skill.{modules[args.command]}":
                print(
                    f"Command {args.command} is not available in this development build.",
                    file=sys.stderr,
                )
                return 2
            raise
        return handler.execute(args)
    except KeyboardInterrupt:
        print("Interrupted; inspect any saved partial run before retrying.", file=sys.stderr)
        return 130
    except (ValueError, OSError) as exc:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            details = [".".join(map(str, e["loc"])) + ": " + e["type"] for e in exc.errors()]
            print("Invalid configuration: " + "; ".join(details), file=sys.stderr)
        else:
            print(f"Unable to execute command ({type(exc).__name__}).", file=sys.stderr)
        return 2
