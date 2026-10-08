"""Paired experiments against a small, explicit synthetic defect corpus."""

import hashlib
import json
import time
from pathlib import Path
import yaml
from .artifacts import create_run,write_json
from .config import Config
from .demo import start_demo
from .runner import run_config
from .secrets import Redactor


CATALOG=Path(__file__).parent/'assets'/'benchmark'/'catalog.json'


def case_config(case,base,defects):
    shared={'project':case['id'],'allowed_origins':[base],'allow_mutations':True,'budgets':{'seconds':120,'retries':0}}
    if case['id']=='api-idor':
        checks=[{'id':'api.login','kind':'http','mutating':True,'requirement':'API-LOGIN','oracle':'Alice receives the authenticated session',
            'spec':{'base_url':base,'path':'/api/login','method':'POST','json_body':{'username':'alice','password':'demo-password'},'capture':{'auth':'authorization'}}},
            {'id':case['check'],'kind':'http','severity':case['severity'],'requirement':case['requirement'],'oracle':case['oracle'],
             'depends_on':['api.login'],'spec':{'base_url':base,'path':'/api/items/2','headers_from':{'Authorization':'auth'},'expected_status':403,'expected_json':{'error':'forbidden'}}}]
    elif case['id'].startswith('web-'):
        spec={'base_url':base,'expected_text':['Autotest demo'],'timeout':2}
        if case['id']=='web-false-save':
            spec['actions']=[{'action':'click','role':'button','name':'Sign in'},{'action':'expect_text','text':'Signed in as alice'},
                {'action':'fill','label':'Name','value':'Benchmark saved work'},{'action':'fill','label':'Quantity','value':'2'},
                {'action':'click','role':'button','name':'Save'},{'action':'expect_text','text':'Saved'},{'action':'reload'},
                {'action':'expect_text','text':'Benchmark saved work × 2'}]
        elif case['id']=='web-overflow':spec.update(viewport=[360,800],check_layout=True)
        elif case['id']=='web-missing-label':spec['accessibility']=True
        checks=[{'id':case['check'],'kind':'web','mutating':case['id']=='web-false-save','severity':case['severity'],
            'requirement':case['requirement'],'oracle':case['oracle'],'spec':spec}]
    else:
        checks=[{'id':case['check'],'kind':'telegram','severity':case['severity'],'requirement':case['requirement'],
            'oracle':case['oracle'],'spec':{'scenario':'isolation','defects':defects}}]
    return Config.model_validate({**shared,'checks':checks})


def score(rows):
    total=len(rows);found=sum(r['broken_status']=='failed' for r in rows)
    critical=[r for r in rows if r['severity']=='critical']
    critical_found=sum(r['broken_status']=='failed' for r in critical)
    fp=sum(r['clean_status']=='failed' for r in rows)
    high_fp=sum(r['clean_status']=='failed' and r['severity'] in {'critical','high'} for r in rows)
    incomplete=sum(r['clean_status'] not in {'passed','failed'} or r['broken_status'] not in {'passed','failed'} for r in rows)
    gates=bool(total and critical and critical_found==len(critical) and high_fp==0 and not incomplete)
    return {'detected':found,'known_defects':total,'missed':[r['id'] for r in rows if r['broken_status']!='failed'],
            'critical_detected':critical_found,'critical_known':len(critical),'false_positives':fp,'clean_controls':total,
            'critical_high_false_positives':high_fp,'incomplete_pairs':incomplete,'mandatory_benchmark_gates_passed':gates,
            'all_pairs_passed':bool(total and found==total and fp==0 and not incomplete)}


def run_benchmark(output,root=None):
    root=Path(root or Path.cwd()).resolve()
    run_id,folder=create_run(output);redactor=Redactor();catalog=json.loads(CATALOG.read_text());rows=[]
    started=time.monotonic()
    for case in catalog['measured_cases']:
        row={**case}
        for mode,defects in [('clean',False),('broken',True)]:
            with start_demo(defects=defects) as (base,_):
                config=case_config(case,base,defects)
                report,run_folder=run_config(config,root,folder/'runs')
                result=next(r for r in report.results if r.id==case['check'])
                row[mode+'_status']=result.status;row[mode+'_run']=str(run_folder.relative_to(folder))
                row[mode+'_reason']=result.reason;row[mode+'_elapsed_ms']=result.elapsed_ms
                row[mode+'_revision']=report.target_revision
                write_json(run_folder,'replay.config.json',config.model_dump(),redactor)
        rows.append(row)
    fingerprint=hashlib.sha256()
    for source in [CATALOG,Path(__file__).parent/'demo.py',Path(__file__).parent/'telegram_demo.py',Path(__file__).parent/'assets'/'demo.html']:
        fingerprint.update(source.name.encode());fingerprint.update(source.read_bytes())
    data={'schema_version':1,'run_id':run_id,'metrics':score(rows),'cases':rows,'not_measured':catalog['not_measured'],
        'fixture_sha256':fingerprint.hexdigest(),'elapsed_ms':(time.monotonic()-started)*1000,'limitations':catalog['limitations']}
    write_json(folder,'benchmark.json',data,redactor)
    return data,folder


def execute(args):
    data,folder=run_benchmark(args.output)
    print(json.dumps({'directory':str(folder),**data['metrics']},indent=2))
    return 0 if data['metrics']['all_pairs_passed'] else (2 if data['metrics']['incomplete_pairs'] else 1)
