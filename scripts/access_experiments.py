#!/usr/bin/env python3
"""Execute paired owned API and aiogram access-control fixtures."""

import argparse
import json
from pathlib import Path

from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config

ROOT = Path(__file__).resolve().parents[1]


def config(target, guard, base, defects):
    identity = f"{target}.{guard}"
    common = {
        "project": identity,
        "allow_mutations": True,
        "allowed_origins": [base],
        "budgets": {"seconds": 120, "retries": 0},
    }
    check = {
        "id": identity,
        "kind": target,
        "severity": "critical",
        "requirement": f"ACCESS-{guard.upper()}",
        "oracle": "Ordinary users cannot use admin access or read another user/chat's object",
    }
    if target == "http":
        login = {
            "id": "api.login",
            "kind": "http",
            "mutating": True,
            "requirement": "ACCESS-LOGIN",
            "oracle": "Alice authenticates for a bounded owned-fixture test",
            "spec": {
                "base_url": base,
                "path": "/api/login",
                "method": "POST",
                "json_body": {"username": "alice", "password": "demo-password"},
                "capture": {"auth": "authorization"},
            },
        }
        check["depends_on"] = ["api.login"]
        check["spec"] = {
            "base_url": base,
            "path": "/api/admin" if guard == "role" else "/api/items/2",
            "headers_from": {"Authorization": "auth"},
            "expected_status": 403,
            "expected_json": {"allowed": False} if guard == "role" else {"error": "forbidden"},
        }
        checks = [login, check]
    else:
        events = [{"text": "/admin", "user_id": 501}, {"text": "/admin", "user_id": 9001}]
        replies = [
            {"chat_id": 501, "text": "Admin denied"},
            {"chat_id": 9001, "text": "Admin allowed"},
        ]
        if guard == "ownership":
            events = [
                {"text": "/new"},
                {"text": "Widget"},
                {"callback": "confirm"},
                {"text": "/item 1", "user_id": 502},
                {"text": "/item 1", "chat_id": -100501},
                {"text": "/item 1"},
                {"text": "/item 1", "user_id": 9001},
            ]
            replies = [
                {"chat_id": 502, "text": "Item denied"},
                {"chat_id": -100501, "text": "Item denied"},
                {"chat_id": 501, "text": "Item: Widget"},
                {"chat_id": 9001, "text": "Item: Widget"},
            ]
        check["spec"] = {"events": events, "expected_replies": replies, "defects": defects}
        checks = [check]
    return Config.model_validate({**common, "checks": checks})


def execute(output):
    rows = []
    for target in ("http", "telegram"):
        for guard in ("role", "ownership"):
            for mode, defects in (("clean", False), ("broken", True)):
                with start_demo(defects=defects) as (base, _):
                    report, folder = run_config(config(target, guard, base, defects), ROOT, output)
                result = next(r for r in report.results if r.id == f"{target}.{guard}")
                expected = "failed" if defects else "passed"
                assert result.status == expected, (
                    target,
                    guard,
                    mode,
                    result.status,
                    result.reason,
                )
                assert report.exit_code() == (1 if defects else 0)
                rows.append(
                    {
                        "target": target,
                        "guard": guard,
                        "mode": mode,
                        "status": result.status,
                        "run_id": report.run_id,
                        "actual": result.actual,
                        "directory": str(folder),
                    }
                )
    data = {
        "scope": "Owned API and local aiogram handler pairs; live Telegram unvalidated",
        "rows": rows,
    }
    (ROOT / "docs/evidence/access-matrix.json").write_text(json.dumps(data, indent=2) + "\n")
    print(
        json.dumps(
            {"experiments": len(rows), "clean_controls_passed": 4, "seeded_bypasses_detected": 4},
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".autotest/access-runs")
    execute(parser.parse_args().output)
