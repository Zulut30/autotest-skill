from autotest_skill.config import Config
from autotest_skill.runner import run_config


def bot_config(scenario='start',**spec):
    return Config.model_validate({'project':'bot','checks':[{'id':'bot.scenario','kind':'telegram',
        'requirement':'TG-DIALOG','oracle':'Bot scenario matches documented replies, state and effects',
        'spec':{'scenario':scenario,**spec}}]})


def test_start_help_and_unknown_commands_use_real_handlers(tmp_path):
    report,_=run_config(bot_config(),tmp_path,tmp_path/'runs')
    assert report.exit_code()==0
    assert report.results[0].actual['events_executed']==3
    assert report.results[0].actual['live_telegram_validated'] is False
    assert report.results[0].actual['mode']=='local_recording_transport'
