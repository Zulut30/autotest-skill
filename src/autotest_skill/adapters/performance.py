"""Bounded HTTP/k6 experiments. No redirects, generated remote code or uploads."""

import json
import math
import os
import platform
import signal
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from ..artifacts import safe_file, write_json
from ..errors import Blocked
from ..policy import request_url
from ..tooling import binary


def conditions(spec, url):
    return {'engine': spec.engine, 'url': url, 'requests': spec.requests,
            'concurrency': spec.concurrency, 'warmup': spec.warmup, 'timeout': spec.timeout,
            'expected_status': 200, 'platform': platform.system(), 'machine': platform.machine(),
            'cpu_count': os.cpu_count(), 'python': platform.python_version()}


def builtin(spec, context, url):
    def sample(_):
        began = time.monotonic()
        try:
            with httpx.Client(timeout=min(spec.timeout, context.remaining()), follow_redirects=False) as client:
                with client.stream('GET', url) as response:
                    status = response.status_code
            return {'ms': (time.monotonic() - began) * 1000, 'status': status, 'error': status != 200}
        except httpx.HTTPError:
            return {'ms': (time.monotonic() - began) * 1000, 'status': None, 'error': True}
    for i in range(spec.warmup):
        context.consume('requests'); sample(i)
    context.consume('requests', spec.requests)
    with ThreadPoolExecutor(max_workers=spec.concurrency) as pool:
        samples = list(pool.map(sample, range(spec.requests)))
    context.remaining()
    values = sorted(sample['ms'] for sample in samples)
    return {'samples': samples, 'p50_ms': values[math.ceil(len(values)*.5)-1],
            'p95_ms': values[math.ceil(len(values)*.95)-1],
            'error_rate': sum(sample['error'] for sample in samples)/len(samples),
            'measured_requests': len(samples), 'warmup_requests': spec.warmup,
            'tool_version': httpx.__version__, 'percentile_scope': 'Exploratory laboratory samples'}


def k6(spec, context, url, check_id):
    executable = binary('k6')
    context.consume('requests', spec.warmup + spec.requests)
    summary = safe_file(context.folder, f'{check_id}.k6-summary.json')
    script = '''import http from 'k6/http';
import { Counter, Trend, Rate } from 'k6/metrics';
const latency=new Trend('measured_latency',true), errors=new Rate('measured_errors');
const count=new Counter('measured_requests');
export const options=OPTIONS;
export function setup(){for(let i=0;i<WARMUP;i++) http.get(URL,{redirects:0,timeout:TIMEOUT});}
export default function(){const r=http.get(URL,{redirects:0,timeout:TIMEOUT});latency.add(r.timings.duration);errors.add(r.status!==200);count.add(1);}
'''.replace('OPTIONS', json.dumps({'scenarios': {'bounded': {'executor': 'shared-iterations',
        'vus': spec.concurrency, 'iterations': spec.requests, 'maxDuration': f'{int(context.remaining())}s'}},
        'summaryTrendStats': ['p(50)', 'p(95)', 'count']})).replace('WARMUP',str(spec.warmup)).replace('TIMEOUT',json.dumps(f'{spec.timeout}s')).replace('URL',json.dumps(url))
    script_file = safe_file(context.folder, f'{check_id}.k6.js')
    script_file.write_text(script); script_file.chmod(0o600)
    config = safe_file(context.folder, f'{check_id}.k6-config.json')
    config.write_text('{}'); config.chmod(0o600)
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen([executable,'run','--quiet','--no-usage-report','--config',str(config),
            '--summary-export',str(summary),str(script_file)], stdout=stdout,stderr=stderr,start_new_session=True)
        try:
            code=process.wait(timeout=context.remaining())
        except (subprocess.TimeoutExpired,BaseException):
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            raise
        if code or not summary.is_file():
            raise Blocked(f'k6 did not complete all iterations (exit {code})')
    summary.chmod(0o600)
    data=json.loads(summary.read_text()); metrics=data['metrics']
    values=metrics['measured_latency']; errors=metrics['measured_errors']
    actual_count=metrics['measured_requests']['count']
    if actual_count != spec.requests:
        raise Blocked('k6 completed fewer measured requests than configured')
    version=subprocess.run([executable,'version'],capture_output=True,text=True,timeout=min(5,context.remaining())).stdout.strip()
    return {'p50_ms':values['p(50)'],'p95_ms':values['p(95)'], 'error_rate':errors['value'],
            'measured_requests':actual_count,'warmup_requests':spec.warmup,'tool_version':version,
            'percentile_scope':'Exploratory laboratory samples'}


def run(check, context):
    spec=check.spec; url=request_url(context.config,spec.base_url,spec.path)
    began=time.monotonic()
    actual = (k6(spec,context,url,check.id) if spec.engine=='k6' else builtin(spec,context,url))
    actual.update({'conditions':conditions(spec,url),'elapsed_ms':(time.monotonic()-began)*1000})
    failures=[]
    if actual['p95_ms'] > spec.max_p95_ms: failures.append('p95 exceeds the configured threshold')
    if actual['error_rate'] > spec.max_error_rate: failures.append('error rate exceeds the configured threshold')
    flaky=False
    if spec.baseline:
        baseline_path=safe_file(context.root,spec.baseline)
        if not baseline_path.is_file() or baseline_path.stat().st_size>1_000_000:
            raise Blocked('Approved performance baseline is missing or too large')
        baseline=json.loads(baseline_path.read_text())
        if baseline.get('conditions')!=actual['conditions'] or baseline.get('tool_version')!=actual['tool_version']:
            raise Blocked('Performance baseline conditions or tool version are incompatible')
        reference=baseline.get('p95_ms')
        if not isinstance(reference,(int,float)) or not math.isfinite(reference) or reference<=0:
            raise Blocked('Approved baseline p95 is invalid')
        ratio=actual['p95_ms']/reference
        actual['comparison']={'baseline':spec.baseline,'baseline_p95_ms':reference,'ratio':ratio}
        if ratio>spec.max_regression_ratio:
            replay=(k6(spec,context,url,check.id+'.replay') if spec.engine=='k6' else builtin(spec,context,url))
            actual['comparison']['replay']=replay
            replay_ratio=replay['p95_ms']/reference
            actual['comparison']['replay_ratio']=replay_ratio
            if replay['error_rate']>spec.max_error_rate:
                failures.append('Replay error rate exceeds the configured threshold')
            if replay_ratio>spec.max_regression_ratio:
                failures.append('Compatible performance regression reproduced in an independent replay')
            else:
                flaky=True
    artifact=f'{check.id}.performance.json';write_json(context.folder,artifact,actual,context.redactor)
    return context.result(check,'failed' if failures else 'passed',actual=actual,
        expected={'max_p95_ms':spec.max_p95_ms,'max_error_rate':spec.max_error_rate},
        reason='; '.join(failures),evidence=[artifact],flaky=flaky)
