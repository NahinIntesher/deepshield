import atexit,base64,hashlib,time
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal,engine
atexit.register(engine.dispose)
from app.models.db_models import User,AuthSession
from app.routers.auth import _hash_password,_attempts
from app.routers.mobile_bridge import handoff_hash

def test_pkce_handoff_is_bound_single_use_and_role_preserving():
    _attempts.clear()
    with SessionLocal() as db:
        user=User(username='bridge-test',display_name='Bridge test',role='participant',password_hash=_hash_password('test-password-123'))
        db.add(user);db.commit()
    with TestClient(app) as c:
        verifier='a'*43
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        assert c.post('/api/auth/mobile/handoff',json={'challenge':challenge}).status_code==401
        assert c.post('/api/auth/login',json={'username':'bridge-test','password':'test-password-123'}).status_code==200
        assert c.post('/api/auth/mobile/handoff',json={'challenge':'bad'}).status_code==422
        code=c.post('/api/auth/mobile/handoff',json={'challenge':challenge}).json()['code']
        assert c.post('/api/auth/mobile/exchange',json={'code':code,'verifier':'b'*43}).status_code==401
        assert c.get('/api/auth/me',headers={'Authorization':'Bearer dsm_'+code}).status_code==401
        with TestClient(app) as stranger:
            stranger.cookies.set('deepshield_session',f'mobile-handoff:{code}:{challenge}')
            assert stranger.get('/api/auth/me').status_code==401
        exchanged=c.post('/api/auth/mobile/exchange',json={'code':code,'verifier':verifier})
        assert exchanged.status_code==200,exchanged.text
        assert exchanged.json()['user']['role']=='participant'
        token=exchanged.json()['token']
        assert c.get('/api/auth/me',headers={'Authorization':'Bearer '+token}).status_code==200
        assert c.post('/api/auth/mobile/exchange',json={'code':code,'verifier':verifier}).status_code==401
        code=c.post('/api/auth/mobile/handoff',json={'challenge':challenge}).json()['code']
        with SessionLocal() as db:
            db.get(AuthSession,handoff_hash(code,challenge)).expires=time.time()-1;db.commit()
        assert c.post('/api/auth/mobile/exchange',json={'code':code,'verifier':verifier}).status_code==401
