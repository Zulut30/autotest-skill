#!/usr/bin/env python3
"""Render shareable evidence from completed synthetic demonstration records."""

import hashlib
import html
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from autotest_skill.doctor import browser_path

ROOT = Path(__file__).resolve().parents[1]


def execute():
    data = json.loads((ROOT / "docs/evidence/demos.json").read_text())
    metrics = json.loads((ROOT / "docs/evidence/distribution.json").read_text())["wheel_probe"][
        "metrics"
    ]
    assert data["synthetic_demo_gate_passed"] and len(data["rows"]) == 6
    folder = ROOT / "docs/media"
    folder.mkdir(exist_ok=True)
    labels = {
        "web": ("Web", "Real Chromium · save/reopen"),
        "telegram": ("Telegram handlers", "aiogram FSM · recording transport"),
        "android": ("Android", "API26 · real APK + Appium"),
    }
    cards = []
    for target, (title, detail) in labels.items():
        rows = [r for r in data["rows"] if r["target"] == target]
        assert {r["mode"]: r["actual_status"] for r in rows} == {
            "clean": "passed",
            "broken": "failed",
        }
        cards.append(
            f'<article><h2>{html.escape(title)}</h2><p>{html.escape(detail)}</p><div><span>Clean control</span><strong class="pass">passed</strong></div><div><span>Seeded defect</span><strong class="fail">detected</strong></div></article>'
        )
    document = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Autotest Skill — executed evidence</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#0c1425;color:#edf5fc;font:18px Arial,sans-serif}}main{{padding:48px 56px;width:1200px;min-height:630px}}.tag{{color:#76e6bd;letter-spacing:3px;font-size:14px;font-weight:bold}}h1{{font-size:54px;margin:18px 0 12px;letter-spacing:-2px}}.lead{{font-size:22px;color:#b8c9dc;margin:0 0 32px}}section{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}article{{background:#152237;border:1px solid #31435a;border-radius:16px;padding:24px}}h2{{font-size:24px;margin:0 0 10px}}article p{{font-size:14px;color:#b8c9dc;min-height:26px;margin:0 0 20px}}article div{{display:flex;justify-content:space-between;gap:8px;margin:14px 0;font-size:16px}}strong{{font-size:16px}}.pass{{color:#76e6bd}}.fail{{color:#f6bf74}}.metric{{font-size:20px;margin-top:28px;color:#d1dfeb}}footer{{margin-top:20px;padding-top:18px;border-top:1px solid #31435a;display:flex;justify-content:space-between;color:#9eb2c9;font-size:14px}}
</style><main><div class="tag">AUTOTEST SKILL / 0.1.0a1 ALPHA</div><h1>Give AI tests it can prove.</h1><p class="lead">Declare the expectation. Execute the flow. Keep the evidence.</p><section>{"".join(cards)}</section><div class="metric">Bundled corpus: <b>{metrics["detected"]}/{metrics["known_defects"]} seeded defects detected</b> · {metrics["false_positives"]}/{metrics["clean_controls"]} clean-control false positives</div><footer><span>Small synthetic corpus · Live Telegram validation pending</span><span>github.com/Zulut30/autotest-skill</span></footer></main></html>"""
    (folder / "overview.html").write_text(document)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=browser_path(), headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        page.set_content(document)
        page.screenshot(path=str(folder / "overview.png"))
        browser.close()
    provenance = []
    for row in data["rows"]:
        if row["target"] != "android":
            continue
        source = Path(row["directory"]) / "native.saved-item.png"
        assert source.is_file()
        destination = folder / f"android-{row['mode']}.png"
        shutil.copyfile(source, destination)
        provenance.append(
            {
                "file": destination.name,
                "run_id": row["run_id"],
                "mode": row["mode"],
                "actual_status": row["actual_status"],
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            }
        )
    provenance.append(
        {
            "file": "overview.png",
            "source": "docs/evidence/demos.json and distribution.json",
            "sha256": hashlib.sha256((folder / "overview.png").read_bytes()).hexdigest(),
        }
    )
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "scope": "Synthetic owned demo data only; unedited native screenshots",
                "assets": provenance,
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"assets": str(folder), "provenance": str(folder / "manifest.json")}))


if __name__ == "__main__":
    execute()
