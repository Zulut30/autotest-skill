from autotest_skill.config import Config
from autotest_skill.runner import run_config


def test_missing_native_server_is_blocked_and_other_checks_can_continue(tmp_path):
    config=Config.model_validate({'project':'native','allowed_origins':['http://127.0.0.1:1'],'checks':[{
        'id':'native','kind':'android','requirement':'APP-SAVE','oracle':'Native app shows its saved state',
        'spec':{'server_url':'http://127.0.0.1:1','udid':'emulator-5554','package':'com.autotest.demo','activity':'.MainActivity','actions':[{'action':'expect_text','text':'Autotest Demo'}]}}]})
    report,_=run_config(config,tmp_path,tmp_path/'runs')
    assert report.results[0].status=='blocked'
    assert report.exit_code()==2
