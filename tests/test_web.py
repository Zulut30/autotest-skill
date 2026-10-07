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


def test_bounded_interface_map_inventories_without_submitting(tmp_path):
    with start_demo() as (base,state):
        report,_ = run_config(web_config(base,explore=True),tmp_path,tmp_path/'runs')
        assert report.exit_code() == 0
        mapping = report.results[0].actual['interface_map']
        assert len(mapping['elements']['forms']) == 2
        assert any(b['name']=='Save' for b in mapping['elements']['buttons'])
        assert mapping['visited_pages'][0]['url'].endswith('/health')
        assert not state.sessions
        assert len(state.items) == 2


def test_ambiguous_locator_blocks_before_clicking(tmp_path):
    with start_demo() as (base,state):
        report,_ = run_config(web_config(base,[{'action':'click','role':'button'}]),tmp_path,tmp_path/'runs')
        assert report.results[0].status == 'blocked'
        assert 'ambiguous' in report.results[0].reason
        assert not state.sessions


SAVE_ACTIONS = [
    {'action':'click','role':'button','name':'Sign in'},
    {'action':'expect_text','text':'Signed in as alice'},
    {'action':'fill','label':'Name','value':'Browser saved work'},
    {'action':'fill','label':'Quantity','value':'2'},
    {'action':'click','role':'button','name':'Save'},
    {'action':'expect_text','text':'Saved'},
    {'action':'reload'},
    {'action':'expect_text','text':'Browser saved work × 2'},
]


def test_save_reopen_flow_confirms_persisted_backend_state(tmp_path):
    with start_demo() as (base,state):
        report,_ = run_config(web_config(base,SAVE_ACTIONS),tmp_path,tmp_path/'runs')
        assert report.exit_code() == 0
        assert any(item['name']=='Browser saved work' and item['quantity']==2 for item in state.items.values())


def test_false_success_is_found_after_reopening(tmp_path):
    with start_demo(defects=True) as (base,state):
        report,_ = run_config(web_config(base,SAVE_ACTIONS,timeout=2),tmp_path,tmp_path/'runs')
        assert report.results[0].status == 'failed'
        assert len(report.results[0].attempts) == 1
        assert not any(item['name']=='Browser saved work' for item in state.items.values())
