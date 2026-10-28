import atexit,io
import cv2
import numpy as np
import pytest
from PIL import Image
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine,SessionLocal
from app.models.db_models import User
from app.routers.auth import _hash_password,_attempts
from app.routers.mobile_overlay import _decode_frames,_temporary_video
atexit.register(engine.dispose)

def jpeg():
    image=Image.fromarray(np.random.default_rng(123).integers(0,256,(112,112,3),dtype=np.uint8))
    out=io.BytesIO();image.save(out,format='JPEG');return out.getvalue()

def test_capture_batch_requires_sixteen_valid_jpegs():
    data=jpeg()
    assert len(_decode_frames([data]*16))==16
    for batch in ([data]*15,[b'bad']*16):
        with pytest.raises(HTTPException):_decode_frames(batch)
    out=io.BytesIO();Image.new('RGB',(112,112)).save(out,format='PNG')
    with pytest.raises(HTTPException):_decode_frames([out.getvalue()]*16)


def test_only_fake_capture_notifies_its_owner(monkeypatch):
    from types import SimpleNamespace
    from app.routers import mobile_overlay
    sent=[];committed=[]
    monkeypatch.setattr(mobile_overlay,'PRODUCT_BACKEND',True)
    monkeypatch.setattr(mobile_overlay,'notify',lambda db,uid,title,message:sent.append((uid,title,message)))
    db=SimpleNamespace(commit=lambda:committed.append(True));user=SimpleNamespace(id=42)
    mobile_overlay._notify_fake_result(db,user,'YouTube',{'verdict':'Real'})
    assert not sent and not committed
    mobile_overlay._notify_fake_result(db,user,'YouTube',{'verdict':'Fake'})
    assert sent==[(42,'Possible deepfake','YouTube: Check the original before trusting or sharing.')]
    assert committed==[True]

def test_capture_video_preserves_sampling_time(tmp_path):
    decoded=_decode_frames([jpeg()]*16)
    path=tmp_path/'capture.avi';_temporary_video(decoded,path,500)
    video=cv2.VideoCapture(str(path))
    try:
        assert video.isOpened()
        assert video.get(cv2.CAP_PROP_FRAME_COUNT)==16
        assert video.get(cv2.CAP_PROP_FPS)==pytest.approx(2)
        success,frame=video.read()
        assert success and np.array_equal(frame,decoded[0])
    finally:video.release()

def test_overlay_auth_validation_and_daily_quota(monkeypatch):
    _attempts.clear()
    with SessionLocal() as db:
        db.add(User(username='overlay-fixture',display_name='Overlay fixture',role='participant',password_hash=_hash_password('test-password-123')));db.commit()
    with TestClient(app) as c:
        files=[('frames',('frame.jpg',jpeg(),'image/jpeg'))]*16
        endpoint='/api/integrations/mobile-overlay/analyze?source=YouTube'
        assert c.post(endpoint,files=files).status_code==401
        login=c.post('/api/auth/mobile/login',json={'username':'overlay-fixture','password':'test-password-123'});assert login.status_code==200
        c.headers['Authorization']='Bearer '+login.json()['token']
        assert c.post(endpoint+'&sample_interval_ms=1',files=files).status_code==422
        monkeypatch.setenv('FREE_DAILY_SCANS','0')
        assert c.post(endpoint,files=files).status_code==429
