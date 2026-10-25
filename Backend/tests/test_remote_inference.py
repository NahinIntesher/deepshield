"""Contract checks for hosted inference; never sends fixture data over the network."""
import sys
from types import SimpleNamespace
import pytest
from app.services import remote_inference as remote

@pytest.fixture
def setup_remote(monkeypatch,tmp_path):
    monkeypatch.setenv('MODEL_SPACE_ID','owner/private-fixture')
    monkeypatch.setenv('MODEL_SPACE_TOKEN','fixture-token')
    monkeypatch.setattr(remote,'_client',None)
    monkeypatch.setattr(remote,'_verified',False)
    file=tmp_path/'fixture.mp4';file.write_bytes(b'fixture only')
    result={'model_id':remote.expected_id(),'verdict':'Real','fake_probability':.1,'confidence_percentage':90.,
            'model_checkpoint_loaded':True,'model_name':'Fixture','temporal_scores':[],
            'detected_artifacts':[],'verification_tips':[]}
    job=SimpleNamespace(result=lambda timeout:result,cancel=lambda:None)
    calls=[]
    class Client:
        def __init__(self,space,**kwargs):assert space=='owner/private-fixture' and kwargs['token']=='fixture-token'
        def submit(self,file,explain,api_name):calls.append((file,explain,api_name));return job
    monkeypatch.setitem(sys.modules,'gradio_client',SimpleNamespace(Client=Client,handle_file=lambda p:p))
    return file,result,job,calls

def test_remote_result_requires_original_checkpoint(setup_remote):
    file,result,job,calls=setup_remote
    assert remote.analyze(file,False)['verdict']=='Real'
    assert calls==[(str(file),False,'/predict')]
    assert remote.status()['last_prediction_verified']
    result['model_id']='unverified-model'
    with pytest.raises(RuntimeError,match='checkpoint verification failed'):remote.analyze(file)

def test_bad_probabilities_are_not_accepted(setup_remote):
    file,result,job,calls=setup_remote
    result['confidence_percentage']=float('nan')
    with pytest.raises(RuntimeError,match='temporarily unavailable'):remote.analyze(file)

def test_remote_timeout_cancels_job_without_exposing_details(setup_remote):
    file,result,job,calls=setup_remote
    cancelled=[]
    job.cancel=lambda:cancelled.append(True)
    def timeout(**kwargs):raise TimeoutError('private diagnostics')
    job.result=timeout
    with pytest.raises(RuntimeError,match='took too long'):remote.analyze(file)
    assert cancelled==[True]

def test_remote_quota_error_is_clear_and_missing_file_never_uploads(setup_remote):
    file,result,job,calls=setup_remote
    def exhausted(**kwargs):raise RuntimeError('GPU quota exhausted hf_fixture_secret')
    job.result=exhausted
    with pytest.raises(RuntimeError,match='allowance is currently exhausted') as error:remote.analyze(file)
    assert 'secret' not in str(error.value)
    file.unlink()
    with pytest.raises(ValueError,match='no longer available'):remote.analyze(file)
    assert len(calls)==1
