"""Portable reproduction metadata and a whitelist of current-run evidence."""

import hashlib
import os
import zipfile
from pathlib import Path
from .artifacts import safe_file,write_json


def collect(config,report,root,folder,redactor):
    inputs=[]
    for check in config.checks:
        for field in ('apk','baseline','openapi_file'):
            name=getattr(check.spec,field,None)
            if name:
                path=safe_file(root,name)
                if path.is_file():inputs.append({'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    evidence=[]
    for result in report.results:
        names=set(result.evidence)
        for attempt in result.attempts:names.update(attempt.get('evidence',[]))
        for name in sorted(names):
            path=safe_file(folder,name)
            if path.is_file():evidence.append({'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'check':result.id})
    tool_hash=hashlib.sha256()
    for path in sorted(Path(__file__).parent.rglob('*.py')):
        tool_hash.update(str(path.relative_to(Path(__file__).parent)).encode());tool_hash.update(path.read_bytes())
    document={'schema_version':1,'run_id':report.run_id,'target_revision':report.target_revision,'target_dirty':report.target_dirty,
        'tool_version':report.tool_version,'tool_source_sha256':tool_hash.hexdigest(),'config_digest':report.config_digest,
        'profile':report.profile,'allowed_origins':config.allowed_origins,'input_fingerprints':inputs,'evidence':evidence,
        'configuration':config.model_dump(),'checks':[{'id':r.id,'requirement':r.requirement,'oracle':r.oracle,'status':r.status,
            'expected':r.expected,'actual':r.actual,'reason':r.reason,'attempts':r.attempts} for r in report.results],
        'replay_instructions':['Start the same test target and restore synthetic data/roles.',
            'Use the original reviewed configuration with secrets supplied by environment bindings. Redacted placeholders are not credentials.',
            'Run autotest plan CONFIG and autotest run CONFIG --profile '+report.profile+'. Compare the explicit oracle and current-run evidence.',
            'For the bundled defect corpus run autotest benchmark; it recreates healthy and broken targets.'],
        'privacy':'Archive contains referenced evidence only. Review screenshots and target-specific personal data before sharing.'}
    write_json(folder,'reproduction.json',document,redactor)
    archive=safe_file(folder,'reproduction.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as stream:
        for name in ['result.json','summary.json','reproduction.json',*[e['path'] for e in evidence]]:
            stream.write(safe_file(folder,name),arcname=name)
    os.chmod(archive,0o600)
    return document
