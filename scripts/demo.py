#!/usr/bin/env python3
"""Recreate clean/broken fixtures and keep the detector's real statuses."""

import argparse
import json
from pathlib import Path

import yaml

from autotest_skill.artifacts import create_run, write_json
from autotest_skill.benchmark import CATALOG, case_config
from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config
from autotest_skill.secrets import Redactor

ROOT = Path(__file__).resolve().parents[1]


def execute(args):
    _, folder = create_run(args.output)
    cases = {case["id"]: case for case in json.loads(CATALOG.read_text())["measured_cases"]}
    targets = ["web", "telegram", "android"] if args.module == "all" else [args.module]
    modes = ["clean", "broken"] if args.mode == "paired" else [args.mode]
    rows = []
    for target in targets:
        for mode in modes:
            defects = mode == "broken"
            with start_demo(
                defects=defects if target == "web" else False,
                port=8765 if target == "android" else 0,
            ) as (base, state):
                if target == "android":
                    data = yaml.safe_load((ROOT / "examples/android.yaml").read_text())
                    data["project_root"] = "."
                    data["checks"][0]["spec"].update(
                        fixture_defects=defects,
                        wait_timeout=5,
                        udid=args.udid,
                        reuse_runtime=args.reuse_runtime,
                    )
                    config = Config.model_validate(data)
                    check_id = "native.saved-item"
                else:
                    case = cases["web-false-save" if target == "web" else "telegram-state-leak"]
                    config = case_config(case, base, defects)
                    check_id = case["check"]
                report, run_folder = run_config(config, ROOT, folder / "runs")
                result = next(r for r in report.results if r.id == check_id)
                expected = "failed" if defects else "passed"
                matched = result.status == expected and report.exit_code() == (1 if defects else 0)
                native_items = (
                    [i for i in state.items.values() if i["name"] == "Native example work"]
                    if target == "android"
                    else None
                )
                if native_items is not None:
                    matched = matched and len(native_items) == (0 if defects else 1)
                rows.append(
                    {
                        "target": target,
                        "mode": mode,
                        "expected_detector_status": expected,
                        "actual_status": result.status,
                        "reason": result.reason,
                        "demonstration_matched": matched,
                        "run_id": report.run_id,
                        "directory": str(run_folder),
                        "backend_items": native_items,
                        "transport": "local aiogram recording transport"
                        if target == "telegram"
                        else "real browser/native UI and HTTP",
                    }
                )
    data = {
        "directory": str(folder),
        "synthetic_demo_gate_passed": bool(rows) and all(r["demonstration_matched"] for r in rows),
        "rows": rows,
        "live_telegram_validated": False,
    }
    write_json(folder, "demo.json", data, Redactor())
    print(json.dumps(data, indent=2))
    return 0 if data["synthetic_demo_gate_passed"] else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=["web", "telegram", "android", "all"], default="all")
    parser.add_argument("--mode", choices=["clean", "broken", "paired"], default="paired")
    parser.add_argument("--output", type=Path, default=ROOT / ".autotest/demos")
    parser.add_argument("--udid", default="emulator-5554")
    parser.add_argument(
        "--reuse-runtime",
        action="store_true",
        help="Only after Appium installed and verified its helper APKs",
    )
    raise SystemExit(execute(parser.parse_args()))
