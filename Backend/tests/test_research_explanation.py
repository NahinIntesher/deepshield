"""Transport and provenance tests with an explicit small model-result fixture.
These tests do not evaluate model prediction or attribution accuracy.
"""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models.db_models import User,ResearchChallengeItem,ResearchSubmission
from app.models.schemas import ResearchSubmissionRequest
from app.routers import research
from app import product_models



def test_research_reveals_analysis_after_submission_and_stores_numeric_provenance(monkeypatch):
    isolated_engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(isolated_engine)
    result={'verdict':'Real','confidence_percentage':98.1,'model_id':'fixture-checkpoint','model_name':'Test transport fixture','checkpoint_epoch':1,'spatial_heatmap_base64':None,'temporal_scores':[], 'frame_indices':[0], 'detected_frames':1,'repeated_frames':15,'fusion_gates':[.3,.3,.4],'xai_error':None,'explanation_method':'input_gradient_and_shap','shap_error':None,'shap_explanation':{'method':'SHAP','target_class':'Real','spatial':{'preview':{'original':'private-face-preview'},'regions':[{'id':'eyes','shap_value':.2,'preview':'private-blurred-preview'}]}}}
    monkeypatch.setattr(research,'item_path',lambda item:Path('transport-fixture.mp4'))
    monkeypatch.setattr(research,'analyze_video',lambda path:result)
    with Session(isolated_engine) as db:
        user=User(username='research_transport_fixture',display_name='Research transport',password_hash='unused-test-only',role='researcher',score=5000,total_correct=90,total_rounds_played=100)
        item=ResearchChallengeItem(title='Transport fixture',media_path='/api/media/transport-fixture',ground_truth='Real')
        db.add_all([user,item]);db.commit();db.refresh(user);db.refresh(item)
        payload=ResearchSubmissionRequest(user_id=user.id,item_id=item.id,human_prediction='Real',human_confidence=3,clue_tags=[],reaction_time_ms=1000)
        response=research.submit_research_evaluation(payload,actor=user,db=db)
        assert response.analysis==result
        assert response.disagreement_quadrant=='Q1'
        row=db.get(ResearchSubmission,response.submission_id)
        metadata=json.loads(row.inference_metadata)
        assert metadata['shap_explanation']['spatial']['regions'][0]['shap_value']==.2
        assert 'private-face-preview' not in row.inference_metadata
        assert 'private-blurred-preview' not in row.inference_metadata
        assert result['shap_explanation']['spatial']['preview']['original']=='private-face-preview'
        assert result['shap_explanation']['spatial']['regions'][0]['preview']=='private-blurred-preview'
    isolated_engine.dispose()
