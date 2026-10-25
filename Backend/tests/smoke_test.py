"""Run from backend: python tests/smoke_test.py. Uses a temporary database."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

with tempfile.TemporaryDirectory() as temp:
    os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(temp) / 'test.db')
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config import CHECKPOINT_PATH
    from app.database import engine
    from app.data.sample_dataset import video_index
    with TestClient(app) as client:
        signup = client.post('/api/auth/signup', json={'username':'testplayer','display_name':'Test Player','password':'test-password-123'})
        assert signup.status_code == 201, signup.text
        user = signup.json()
        items = client.get('/api/game/items?count=100').json()
        assert len(items) == len(video_index()) > 0
        for item in items:
            assert item['media_type'] == 'video'
            assert 'ground_truth' not in item
            assert '/real/' not in item['media_url'] and '/fake/' not in item['media_url']
            response = client.get(item['media_url'], headers={'Range': 'bytes=0-99'})
            assert response.status_code == 206, response.text
            assert len(response.content) == 100
        assert client.get('/api/dashboard/metrics').json()['total_evaluations'] == 0
        answer = client.post('/api/game/submit-round', json={'user_id':user['id'],'item_id':items[0]['id'],'ticket':items[0]['ticket'],'prediction':'Real','time_taken_ms':1000})
        assert answer.status_code == 200, answer.text
        result = client.post(f"/api/detector/analyze-preset/{items[0]['id']}")
        if CHECKPOINT_PATH.exists():
            assert result.status_code == 200, result.text
            data = result.json()
            assert data['model_checkpoint_loaded'] and 0 <= data['fake_probability'] <= 1
            assert len(data['temporal_scores']) == 16 or data.get('xai_error')
            assert answer.json()['ai_prediction'] in ('Real','Fake')
            print('Trained checkpoint inference: PASS (not an accuracy benchmark)')
        else:
            assert result.status_code == 503, result.text
            assert answer.json()['ai_prediction'] is None and answer.json()['ai_error']
            failed = client.post('/api/research/submit', json={'user_id':user['id'],'item_id':items[0]['id'],'human_prediction':'Real','human_confidence':3,'clue_tags':[],'reaction_time_ms':1000})
            assert failed.status_code == 403
            assert client.get('/api/dashboard/metrics').json()['total_evaluations'] == 0
            print('Missing-model handling: PASS. Trained inference: NOT TESTED.')
        assert client.get('/api/media/doesnotexist').status_code == 404
        assert client.post('/api/detector/upload', files={'file':('image.png',b'invalid','image/png')}).status_code == 415
    engine.dispose()
print('Video indexing, streaming, clean metrics and game submission: PASS')
