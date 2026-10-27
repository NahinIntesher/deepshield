import numpy as np
import pytest
from app.services.shap_explanation import explain_game,region_masks,probability

def test_spatial_regions_partition_the_input_without_overlap():
    masks=region_masks()
    assert masks.shape==(4,224,224)
    assert np.all(masks.sum(0)==1)
    assert masks[0,90,70] and masks[0,90,154]
    assert masks[1,130,112] and masks[2,170,112]

def test_exact_shap_attributes_an_interaction_and_preserves_the_original_score():
    # An analytical game verifies the explainer implementation, not classifier accuracy.
    def score(m):return 5+2*m[:,0]-3*m[:,1]+4*m[:,0]*m[:,1]
    result=explain_game(score,['first','second'])
    assert result['algorithm']=='exact'
    assert result['base_value']==pytest.approx(5)
    assert result['values']==pytest.approx([4,-1])
    assert result['output_value']==pytest.approx(8)
    assert result['additivity_error']<1e-8

def test_frame_permutation_preserves_additivity_and_signed_effects():
    coefficients=np.arange(16)-8
    result=explain_game(lambda m:1+m@coefficients,[str(i) for i in range(16)],exact=False)
    assert result['values']==pytest.approx(coefficients)
    assert result['algorithm']=='permutation' and result['seed']==0
    assert result['base_value']+sum(result['values'])==pytest.approx(result['output_value'])

def test_two_class_margin_matches_softmax_probability():
    assert probability(0)==.5
    assert probability(np.log(9))==pytest.approx(.9)
    assert 0<=probability(-10000)<=1
from types import SimpleNamespace
import numpy as np
import torch
from PIL import Image
from app.services.model_manager import ModelManager
from app.services import shap_explanation

class TinyClassifier(torch.nn.Module):
    def __init__(self):
        super().__init__();self.rgb=torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1),torch.nn.Flatten());self.freq=self.rgb;self.rgb_proj=torch.nn.Identity();self.temporal=torch.nn.Identity();self.pos=torch.zeros(1,16,3);self.cls=torch.nn.Linear(3,2,bias=False)
        with torch.no_grad():self.cls.weight.copy_(torch.tensor([[1.,0.,0.],[0.,1.,0.]]))
    def fusion(self,r,f,t):return (r+f+t)/3,torch.full((r.shape[0],3),1/3)

def test_shap_failure_preserves_the_classifier_prediction_and_gradient_map(monkeypatch):
    manager=ModelManager();manager.device=torch.device('cpu');manager.model=TinyClassifier().eval();manager.checkpoint_sha256='isolated-fixture';manager.checkpoint_epoch=1
    monkeypatch.setattr(manager,'ensure_loaded',lambda:None)
    monkeypatch.setattr(shap_explanation,'explain_prediction',lambda *a:(_ for _ in ()).throw(RuntimeError('controlled test failure')))
    data=np.zeros((16,3,224,224),dtype=np.float32);data[:,1]=1
    prepared=SimpleNamespace(tensors=data,frames=[Image.new('RGB',(224,224),'green')]*16,source_indices=list(range(16)),fps=2.,media_type='video',detected_frames=16,repeated_frames=0)
    ordinary=manager.predict(prepared,explain=False)
    explained=manager.predict(prepared,explain=True)
    assert explained['verdict']==ordinary['verdict']=='Fake'
    assert explained['confidence_percentage']==ordinary['confidence_percentage']
    assert explained['shap_explanation'] is None and 'controlled test failure' in explained['shap_error']
    assert explained['xai_error'] is None and len(explained['frame_details'])==16
