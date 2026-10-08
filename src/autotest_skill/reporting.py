"""Readable reports from validated persisted results, with escaped target content."""

import html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from .artifacts import safe_file
from .artifacts import write_json
from .results import RunReport
from .secrets import Redactor


def escape(value):
    return re.sub(r'([\\`*{}\[\]()#+.!|>_-])',r'\\\1',html.escape(str(value))).replace('\n',' ')


def render(report,folder):
    redactor=Redactor();report=RunReport.model_validate(redactor.clean(report.model_dump()))
    from .triage import analyze
    triage=analyze(report)
    write_json(folder,'triage.json',triage,redactor)
    lines=[f'# Autotest report: {escape(report.project)}','',f'Run `{escape(report.run_id)}` · profile `{escape(report.profile)}` · exit {report.exit_code()}',
        '',f'Version `{escape(report.tool_version)}` · target revision `{escape(report.target_revision or "unknown")}` · working tree dirty: {report.target_dirty}',
        '',f'Counts: {escape(json.dumps(report.counts(),sort_keys=True))}',
        '','Only executed declared oracles establish a result. Blocked/skipped checks remain unverified; observations require product review.',
        '','| Check | Status | Severity | Requirement | Reason |','| --- | --- | --- | --- | --- |']
    if triage['findings']:
        lines+=['',f"Prioritized finding groups: {len(triage['findings'])}. Inspect `triage.json` for impact and exact grouping.",'']
    for result in report.results:
        status=result.status+(' (flaky)' if result.flaky else '')
        lines.append('| '+' | '.join(escape(value) for value in (result.id,status,result.severity,result.requirement,result.reason))+' |')
    for result in report.results:
        lines += ['',f'## {escape(result.id)}','',f'Oracle: {escape(result.oracle)}','',f'Status: {escape(result.status)}; attempts: {len(result.attempts)}.']
        if result.actual is not None or result.expected is not None:
            detail=json.dumps({'expected':result.expected,'actual':result.actual},ensure_ascii=False,indent=2)
            lines+=['','```json',detail[:10000]+('\n... truncated for readability; inspect result.json' if len(detail)>10000 else ''),'```']
        for name in result.evidence:
            try:
                path=safe_file(folder,name)
                if not path.is_file():continue
                lines+=['',f'[{escape(name)}]({quote(name,safe="/")})']
            except ValueError:lines+=['','Invalid evidence path withheld.']
    lines += ['','Reproduction: `reproduction.json` and `reproduction.zip` (when generated). Review screenshots before sharing.','']
    path=safe_file(folder,'report.md');path.write_text('\n'.join(lines));os.chmod(path,0o600)
    return path


def execute(args):
    folder=Path(args.run_directory).resolve();source=safe_file(folder,'result.json')
    if not source.is_file() or source.stat().st_size>5_000_000:raise ValueError('Result file is missing or too large')
    report=RunReport.model_validate_json(source.read_text())
    path=render(report,folder)
    print(json.dumps({'report':str(path),'run_id':report.run_id,'counts':report.counts(),'exit_code':report.exit_code()},indent=2))
    return report.exit_code()
