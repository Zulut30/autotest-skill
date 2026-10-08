"""Automated WCAG checks are evidence, not complete accessibility certification."""

from pathlib import Path

from .errors import Blocked


def inspect(page):
    script = Path(__file__).parent / "assets" / "axe.min.js"
    if not script.is_file():
        raise Blocked("Verified axe-core bundle is unavailable")
    page.add_script_tag(path=str(script))
    result = page.evaluate("""async () => await axe.run(document, {
        runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa']},
        resultTypes: ['violations']
    })""")
    return {
        "engine": result["testEngine"],
        "violations": [
            {
                "id": v["id"],
                "impact": v["impact"],
                "description": v["description"],
                "help": v["helpUrl"],
                "nodes": [
                    {"target": node["target"], "summary": node.get("failureSummary", "")}
                    for node in v["nodes"]
                ],
            }
            for v in result["violations"]
        ],
        "limit": "Automated checks do not cover every WCAG requirement or human usability judgment.",
    }
