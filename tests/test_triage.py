from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config
from autotest_skill.triage import analyze


def test_exact_duplicates_group_without_hiding_distinct_requirements(tmp_path):
    with start_demo() as (base,_):
        checks=[{'id':name,'kind':'http','severity':severity,'impact':'Release readiness state differs from requirement',
            'requirement':requirement,'oracle':'Health reports expected ready false','spec':{'base_url':base,'path':'/health','expected_json':{'ready':False}}}
            for name,severity,requirement in [('first','high','READY'),('duplicate','medium','READY'),('other','critical','OTHER')]]
        config=Config.model_validate({'project':'triage','allowed_origins':[base],'budgets':{'retries':0},'checks':checks})
        report,_=run_config(config,tmp_path,tmp_path/'runs')
        data=analyze(report)
        assert len(data['findings'])==2
        assert data['findings'][0]['severity']=='critical'
        assert data['findings'][1]['checks']==['first','duplicate']
        assert len(data['findings'][1]['evidence'])==2
        assert data['findings'][1]['classification']=='confirmed_deviation'
