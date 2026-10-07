import json
import secrets
from autotest_skill.config import Config
from autotest_skill.runner import run_config


def security_config(tool,path='.',**options):
    return Config.model_validate({'project':'security','budgets':{'retries':0},'checks':[{
        'id':'security.scan','kind':'security','requirement':'SEC-SCAN','oracle':'Configured source scope has no matching unsafe patterns',
        'spec':{'tool':tool,'path':path,**options}}]})


def test_credential_control_is_found_without_leaking_value(tmp_path):
    value=secrets.token_hex(20)
    source=tmp_path/'app.py';source.write_text('api_key = "'+value+'"\n')
    report,folder=run_config(security_config('secrets','app.py'),tmp_path,tmp_path/'runs')
    assert report.results[0].status=='failed'
    assert report.results[0].actual['findings'][0]['line']==1
    assert value not in (folder/'result.json').read_text()
    assert value not in (folder/'security.scan.security.json').read_text()
    source.write_text('import os\napi_key = os.environ["API_KEY"]\n')
    clean,_=run_config(security_config('secrets','app.py'),tmp_path,tmp_path/'runs')
    assert clean.exit_code()==0


def test_real_pinned_dependency_advisory(tmp_path):
    pins=tmp_path/'requirements.txt';pins.write_text('urllib3==1.26.5\n')
    report,_=run_config(security_config('dependencies','requirements.txt'),tmp_path,tmp_path/'runs')
    assert report.results[0].status=='failed',report.results[0].reason
    actual=report.results[0].actual
    assert actual['audited_dependencies']==1 and actual['findings']
    assert actual['findings'][0]['classification']=='potential_issue'


def test_dependency_urls_are_not_executed(tmp_path):
    (tmp_path/'requirements.txt').write_text('danger @ https://example.com/file.whl\n')
    report,_=run_config(security_config('dependencies','requirements.txt'),tmp_path,tmp_path/'runs')
    assert report.results[0].status=='blocked'
