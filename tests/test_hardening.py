import copy
import json
import pytest
from pydantic import ValidationError
from autotest_skill.config import Config
from autotest_skill.secrets import Redactor
from autotest_skill.demo import start_demo
from autotest_skill.context import Context
from autotest_skill.adapters.http import run


@pytest.mark.parametrize('host',['169.254.169.254','[fe80::1]','metadata.google.internal','100.100.100.200','2130706433'])
def test_metadata_and_ambiguous_hosts_are_rejected(host):
    url='http://'+host
    with pytest.raises(ValidationError):
        Config.model_validate({'project':'unsafe','allowed_origins':[url],'checks':[{'id':'unsafe','kind':'http','requirement':'BOUNDARY','oracle':'Explicit configured boundary is enforced','spec':{'base_url':url}}]})


def test_sensitive_queries_and_escaping_input_files_are_rejected():
    for spec in ({'path':'/health?token=must-never-persist'},{'openapi_file':'../outside.json'}):
        with pytest.raises(ValidationError):
            Config.model_validate({'project':'unsafe','allowed_origins':['http://localhost:8000'],'checks':[{'id':'unsafe','kind':'http','requirement':'BOUNDARY','oracle':'Explicit configured boundary is enforced','spec':{'base_url':'http://localhost:8000',**spec}}]})


def test_query_and_jwt_values_are_removed_before_serialization(monkeypatch):
    monkeypatch.setenv('CUSTOM_JWT','signed-private-value')
    text=json.dumps(Redactor().clean({'url':'https://local/path?token=private-from-page&ok=1','message':'signed-private-value'}))
    assert 'signed-private-value' not in text and 'private-from-page' not in text


def test_capture_is_transactional_on_failed_extraction(tmp_path):
    with start_demo() as (base,_):
        config=Config.model_validate({'project':'capture','allowed_origins':[base],'allow_mutations':True,'checks':[{
            'id':'login','kind':'http','mutating':True,'requirement':'AUTH','oracle':'Login captures every required field atomically',
            'spec':{'base_url':base,'path':'/api/login','method':'POST','json_body':{'username':'alice','password':'demo-password'},'capture':{'auth':'authorization','missing':'does-not-exist'}}}]})
        context=Context(config,tmp_path,tmp_path)
        result=run(config.checks[0],context)
        assert result.status=='failed' and context.variables=={}
        assert 'Bearer demo-' not in (tmp_path/'login.http.json').read_text()


def test_native_empty_or_undeclared_mutation_is_rejected():
    base={'project':'native','allowed_origins':['http://localhost:4723'],'checks':[{'id':'native','kind':'android','requirement':'APP','oracle':'Native screen visibly displays its expected state','spec':{'udid':'emulator-5554','server_url':'http://localhost:4723','package':'com.demo.app','activity':'.MainActivity'}}]}
    with pytest.raises(ValidationError):Config.model_validate(base)
    base['checks'][0]['spec']['actions']=[{'action':'click','accessibility_id':'Save'},{'action':'expect_text','text':'Saved'}]
    with pytest.raises(ValidationError):Config.model_validate(base)
