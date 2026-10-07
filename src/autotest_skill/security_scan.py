"""Source scanning keeps locations, never secret values or source snippets."""

import os
import re
import signal
import subprocess
import tempfile
from pathlib import Path
from .errors import Blocked

EXCLUDE = {'.git','.venv','node_modules','.autotest','__pycache__','dist','build','.cache'}
TEXT = {'.py','.js','.ts','.tsx','.jsx','.json','.yaml','.yml','.toml','.sh','.env','.txt','.ini'}
RULES = {
    'literal-credential': re.compile(r'(?i)(?:password|passwd|api[_-]?key|token|secret)\s*[:=]\s*[\"\']([A-Za-z0-9_+/=.-]{16,})[\"\']'),
    'github-token': re.compile(r'(gh[pousr]_[A-Za-z0-9]{36,})'),
    'aws-access-key': re.compile(r'(AKIA[A-Z0-9]{16})'),
    'private-key': re.compile(r'(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)'),
}


def scan(root,target,redactor):
    files=[];excluded=0
    if target.is_file():files=[target]
    else:
        for directory,dirs,names in os.walk(target,followlinks=False):
            excluded+=sum(d in EXCLUDE for d in dirs)
            dirs[:]=[d for d in dirs if d not in EXCLUDE and not (Path(directory)/d).is_symlink()]
            for name in names:
                path=Path(directory)/name
                if path.suffix in TEXT or name=='.env':files.append(path)
                if len(files)>3000:raise Blocked('Source scan file budget exhausted')
    findings=[];total=0;scanned=0
    for path in files:
        if path.is_symlink() or not path.is_file():excluded+=1;continue
        if path.stat().st_size>1_000_000:excluded+=1;continue
        content=path.read_text(errors='replace');total+=len(content.encode());scanned+=1
        if total>10_000_000:raise Blocked('Source scan byte budget exhausted')
        for rule,pattern in RULES.items():
            for match in pattern.finditer(content):
                value=match.group(1);redactor.add(value)
                findings.append({'rule':rule,'file':str(path.relative_to(root)),'line':content.count('\n',0,match.start())+1,
                    'classification':'potential_issue','applicability':'Credential-shaped source literal; verify whether it is active. Value withheld.'})
    if not scanned:raise Blocked('No supported source files were scanned')
    return {'findings':findings,'scanned_files':scanned,'excluded_entries':excluded,'scope':'Bounded source files; not Git history or ignored build dependencies'}


def run_tool(argv,context,timeout,cwd=None):
    with tempfile.TemporaryFile() as stdout,tempfile.TemporaryFile() as stderr:
        process=subprocess.Popen(argv,cwd=cwd or context.root,stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=process.wait(timeout=min(timeout,context.remaining()))
        except BaseException:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            raise
        stdout.seek(0);payload=stdout.read(5_000_001)
        if len(payload)>5_000_000:raise Blocked('Tool output exceeds the safe parsing limit')
        return code,payload


def dependency_findings(data):
    skipped=[d['name'] for d in data.get('dependencies',[]) if d.get('skip_reason')]
    findings=[]
    for dependency in data.get('dependencies',[]):
        for vulnerability in dependency.get('vulns',[]):
            findings.append({'rule':vulnerability['id'],'package':dependency['name'],'version':dependency['version'],
                'fixed_versions':vulnerability.get('fix_versions',[]),'classification':'potential_issue',
                'applicability':'Known package advisory; exploitability depends on reachable usage and deployment.'})
    return {'findings':findings,'audited_dependencies':len(data.get('dependencies',[]))-len(skipped),'skipped_packages':skipped,
        'scope':'Explicit pinned Python dependencies; advisory presence does not prove exploitation'}
