"""Explicit safe scanners with conservative scope and sanitized findings."""

import json
import re
from ..artifacts import safe_file,write_json
from ..errors import Blocked
from ..security_scan import scan,run_tool,dependency_findings
from ..tooling import binary


def run(check,context):
    spec=check.spec
    target=safe_file(context.root,spec.path)
    if not target.exists():raise Blocked('Configured scan target does not exist')
    if spec.tool=='secrets':actual=scan(context.root,target,context.redactor)
    elif spec.tool=='dependencies':
        if not target.is_file() or target.stat().st_size>100_000:
            raise Blocked('Dependency audit needs a small file of explicit name==version pins')
        lines=[line.strip() for line in target.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        if not lines or any(not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+',line) for line in lines):
            raise Blocked('Dependency audit only accepts explicit pins, without URLs, commands or implicit resolution')
        context.consume('requests',len(lines))
        code,payload=run_tool([binary('pip-audit'),'-r',str(target),'--disable-pip','--no-deps','--strict','-f','json',
            '--progress-spinner','off','--timeout','10','--cache-dir',str(context.folder/'audit-cache')],context,spec.timeout)
        if code not in {0,1}:raise Blocked(f'Dependency advisory audit could not finish (exit {code})')
        try:actual=dependency_findings(json.loads(payload))
        except (ValueError,KeyError,TypeError) as exc:raise Blocked('Dependency audit returned an invalid result') from exc
        if actual['skipped_packages'] or not actual['audited_dependencies']:
            raise Blocked('Some pinned dependencies could not be audited')
    else:raise Blocked('Requested security tool is not implemented yet')
    actual['tool']=spec.tool
    artifact=f'{check.id}.security.json';write_json(context.folder,artifact,actual,context.redactor)
    return context.result(check,'failed' if actual['findings'] else 'passed',actual=actual,
        expected={'findings':0},reason='Potential security issues require applicability review' if actual['findings'] else '',evidence=[artifact])
