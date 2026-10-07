from autotest_skill.config import Config
from autotest_skill.demo import start_demo
from autotest_skill.runner import run_config


def web_config(base, actions=None, **options):
    return Config.model_validate({'project':'web','allow_mutations':True,'allowed_origins':[base], 'checks':[{
        'id':'web.flow','kind':'web','mutating':True,'requirement':'WEB-SAVE','oracle':'Browser shows the documented target state',
        'spec':{'base_url':base,'expected_text':['Autotest demo'], 'actions':actions or [], **options}}]})


def test_real_browser_opens_target_and_captures_private_evidence(tmp_path):
    with start_demo() as (base, _):
        report, folder = run_config(web_config(base), tmp_path, tmp_path/'runs')
        assert report.exit_code() == 0
        assert (folder/'web.flow.png').stat().st_size > 1000
        assert report.results[0].actual['navigation_status'] == 200
        assert report.results[0].actual['browser_version']
