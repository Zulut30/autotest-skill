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


def test_buttons_callback_ack_tampering_and_stale_confirmation(tmp_path):
    report,_=run_config(bot_config('callback'),tmp_path,tmp_path/'runs')
    assert report.exit_code()==0
    actual=report.results[0].actual
    buttons=[button for call in actual['calls'] for button in call.get('buttons',[])]
    assert {'text':'Confirm','data':'confirm'} in buttons
    assert {'text':'Cancel','data':'cancel'} in buttons
    answers=[call for call in actual['calls'] if call['method']=='answerCallbackQuery']
    assert len(answers)==3
    assert len(actual['items'])==1
    assert actual['states']['user_a'] is None


def test_conversation_completion_invalid_input_and_cancel(tmp_path):
    for scenario in ('dialog','invalid','cancel'):
        report,_=run_config(bot_config(scenario),tmp_path,tmp_path/'runs')
        assert report.exit_code()==0,scenario
    events=[{'text':'/new'},{'text':'x'*101}]
    report,_=run_config(bot_config('invalid',events=events),tmp_path,tmp_path/'runs')
    assert report.exit_code()==0
    assert report.results[0].actual['states']['user_a']=='Collect:name'
