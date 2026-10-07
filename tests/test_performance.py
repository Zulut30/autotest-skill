import pytest
from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config
from autotest_skill.tooling import binary
from autotest_skill.errors import Blocked


def perf_config(base, **options):
    return Config.model_validate({'project':'perf','allowed_origins':[base], 'budgets':{'retries':0}, 'checks':[{
        'id':'load.health','kind':'performance','requirement':'PERF-HEALTH','oracle':'All measured responses are 200 and p95 is bounded',
        'spec':{'base_url':base,'requests':6,'warmup':2,'concurrency':2,**options}}]})


@pytest.mark.parametrize('engine',['builtin','k6'])
def test_measured_load_and_negative_status(engine,tmp_path):
    if engine=='k6':
        try:binary('k6')
        except Blocked:pytest.skip('Optional installed k6 required; builtin remains executed')
    with start_demo() as (base,_):
        clean,_=run_config(perf_config(base,engine=engine),tmp_path,tmp_path/'runs')
        assert clean.exit_code()==0, clean.results[0].reason
        actual=clean.results[0].actual
        assert actual['measured_requests']==6 and actual['warmup_requests']==2
        assert actual['error_rate']==0 and actual['p95_ms']>=0
        broken,_=run_config(perf_config(base,engine=engine,path='/missing'),tmp_path,tmp_path/'runs')
        assert broken.results[0].status=='failed'
        assert broken.results[0].actual['error_rate']==1


def test_absolute_latency_oracle_is_enforced(tmp_path):
    with start_demo() as (base,_):
        report,_=run_config(perf_config(base,max_p95_ms=.00001),tmp_path,tmp_path/'runs')
        assert report.results[0].status=='failed'


def test_compatible_baseline_reproduces_regression_and_is_immutable(tmp_path):
    import json
    with start_demo() as (base,state):
        reference,_=run_config(perf_config(base),tmp_path,tmp_path/'runs')
        assert reference.exit_code()==0
        baseline=tmp_path/'approved.json';baseline.write_text(json.dumps(reference.results[0].actual))
        before=baseline.read_bytes()
        state.health_delay=.08
        broken,_=run_config(perf_config(base,baseline='approved.json',max_regression_ratio=1.1),tmp_path,tmp_path/'runs')
        assert broken.results[0].status=='failed'
        assert broken.results[0].actual['comparison']['replay_ratio']>1.1
        incompatible,_=run_config(perf_config(base,baseline='approved.json',concurrency=1),tmp_path,tmp_path/'runs')
        assert incompatible.results[0].status=='blocked'
        assert baseline.read_bytes()==before
