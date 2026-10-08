"""Generate reviewable seeded regression checks; never modify or publish app code."""

import json
from pathlib import Path

from .benchmark import CATALOG


def propose(case_id, output):
    catalog = json.loads(CATALOG.read_text())
    case = next((c for c in catalog["measured_cases"] if c["id"] == case_id), None)
    if not case:
        raise ValueError("Unknown confirmed corpus case")
    path = Path(output).resolve()
    if path.exists():
        raise ValueError("Refusing to overwrite an existing regression proposal")
    path.parent.mkdir(parents=True, exist_ok=True)
    source = '''"""Generated proposal: inspect the requirement/oracle before adopting in a project."""
import json
import os
from pathlib import Path
from autotest_skill.benchmark import case_config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config

CASE = json.loads(CASE_JSON)

def test_declared_regression(tmp_path):
    defects = os.environ.get('AUTOTEST_REGRESSION_DEFECTS') == '1'
    with start_demo(defects=defects) as (base, _):
        config = case_config(CASE, base, defects)
        report, folder = run_config(config, Path.cwd(), tmp_path/'runs')
        result = next(r for r in report.results if r.id == CASE['check'])
        assert result.status == 'passed', (result.reason, str(folder))
'''.replace("CASE_JSON", repr(json.dumps(case)))
    path.write_text(source)
    return path


def execute(args):
    path = propose(args.case, args.output)
    print(
        json.dumps({"proposal": str(path), "case": args.case, "application_code_modified": False})
    )
    return 0
