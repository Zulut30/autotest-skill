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


def test_form_validation_does_not_persist_bad_input(tmp_path):
    actions = SAVE_ACTIONS[:2] + [
        {'action':'click','role':'button','name':'Save'},
        {'action':'expect_text','text':'Name is required.'},
        {'action':'fill','label':'Name','value':'Invalid quantity'},
        {'action':'fill','label':'Quantity','value':'0'},
        {'action':'click','role':'button','name':'Save'},
        {'action':'expect_text','text':'Quantity must be between 1 and 100.'},
    ]
    with start_demo() as (base,state):
        report,_=run_config(web_config(base,actions),tmp_path,tmp_path/'runs')
        assert report.exit_code()==0
        assert len(state.items)==2


def test_expected_login_error_is_checked_not_disabled(tmp_path):
    actions=[{'action':'fill','label':'Password','value':'wrong'},
             {'action':'click','role':'button','name':'Sign in'},
             {'action':'expect_text','text':'Sign in failed. Check your credentials.'}]
    with start_demo() as (base,state):
        report,_=run_config(web_config(base,actions,allowed_http_errors={'/api/login':[401]}),tmp_path,tmp_path/'runs')
        assert report.exit_code()==0
        assert report.results[0].actual['expected_http_errors'][0]['status']==401
        assert not state.sessions


def test_double_click_creates_at_most_one_object(tmp_path):
    actions=SAVE_ACTIONS[:4]+[{'action':'double_click','role':'button','name':'Save'}, {'action':'expect_text','text':'Saved'}]
    with start_demo() as (base,state):
        report,_=run_config(web_config(base,actions),tmp_path,tmp_path/'runs')
        assert report.exit_code()==0
        assert len([i for i in state.items.values() if i['name']=='Browser saved work'])==1


def test_unexpected_server_failure_is_reported_with_context(tmp_path):
    with start_demo() as (base,state):
        state.dependency_down=True
        actions=[{'action':'click','role':'button','name':'Check service'}, {'action':'expect_text','text':'Service unavailable. Try again.'}]
        report,_=run_config(web_config(base,actions),tmp_path,tmp_path/'runs')
        assert report.results[0].status=='failed'
        assert report.results[0].actual['http_errors'][0]['status']==503
        report,_=run_config(web_config(base,actions,allowed_http_errors={'/api/dependent':[503]}),tmp_path,tmp_path/'runs')
        assert report.exit_code()==0


def test_mobile_and_desktop_layout_and_seeded_overflow(tmp_path):
    for width in (360,1440):
        with start_demo() as (base,_):
            report,_=run_config(web_config(base,viewport=[width,800],check_layout=True),tmp_path,tmp_path/'runs')
            assert report.exit_code()==0
            assert report.results[0].actual['layout']['document'] <= width
    with start_demo(defects=True) as (base,_):
        report,_=run_config(web_config(base,viewport=[360,800],check_layout=True),tmp_path,tmp_path/'runs')
        assert report.results[0].status=='failed'
        assert 'overflows' in report.results[0].reason


def test_visual_comparison_preserves_approved_baseline(tmp_path):
    import json, shutil
    with start_demo() as (base,_):
        initial,folder=run_config(web_config(base),tmp_path,tmp_path/'runs')
        shutil.copyfile(folder/'web.flow.png',tmp_path/'approved.png')
        (tmp_path/'approved.png.json').write_text(json.dumps(initial.results[0].actual['visual_conditions']))
        clean,_=run_config(web_config(base,baseline='approved.png'),tmp_path,tmp_path/'runs')
        assert clean.exit_code()==0
    before=(tmp_path/'approved.png').read_bytes()
    with start_demo(defects=True) as (base,_):
        broken,_=run_config(web_config(base,baseline='approved.png'),tmp_path,tmp_path/'runs')
        assert broken.results[0].status=='failed'
        assert broken.results[0].actual['visual']['difference_ratio']>.01
    assert (tmp_path/'approved.png').read_bytes()==before
