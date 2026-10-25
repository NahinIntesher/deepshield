"""Opt-in extension and public-link analysis. The existing detector is reused as-is."""
import datetime
import hashlib
import secrets
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import current_user
from ..models.db_models import Subscription, ExtensionToken, User
from ..services.integration import platform_for_url,download_public_video,require_scan_quota,plan_info,MAX_UPLOAD_BYTES,MODEL_QUEUE
from ..services.inference import analyze_video
from .detector import save_detection
from ..activity import audit

router=APIRouter(prefix='/api/integrations',tags=['Public links and browser integration'])

class LinkPayload(BaseModel):
    url:str=Field(min_length=12,max_length=2048)

@router.post('/link')
def detect_link(payload:LinkPayload,user=Depends(current_user),db:Session=Depends(get_db)):
    platform=platform_for_url(payload.url)
    require_scan_quota(db,user)
    if not MODEL_QUEUE.acquire(blocking=False): raise HTTPException(503,'The detector is busy. Please retry shortly.')
    try:
        with tempfile.TemporaryDirectory(prefix='ds-link-') as temp:
            media=download_public_video(payload.url,Path(temp))
            output=analyze_video(media)
            return save_detection(db,user,f'Link: {platform} video',output)
    finally: MODEL_QUEUE.release()

@router.get('/subscription')
def subscription_status(user=Depends(current_user),db:Session=Depends(get_db)):
    return plan_info(db,user)

@router.post('/subscription/request')
def request_premium(user=Depends(current_user),db:Session=Depends(get_db)):
    existing=plan_info(db,user)
    if existing['plan']=='premium':raise HTTPException(409,'Premium already active')
    row=db.get(Subscription,user.id)
    if row and row.status=='pending':raise HTTPException(409,'Your request is already awaiting review')
    if not row:
        row=Subscription(user_id=user.id,plan='free',status='pending')
        db.add(row)
    else:
        row.plan='free';row.status='pending'
    row.requested_at=datetime.datetime.utcnow()
    audit(db,user.id,'premium_requested',str(user.id))
    db.commit()
    return {'status':'pending','message':'Request saved. No payment was charged. Activation requires administrative verification.'}

@router.post('/extension/token')
def issue_extension_token(user=Depends(current_user),db:Session=Depends(get_db)):
    db.query(ExtensionToken).filter(ExtensionToken.user_id==user.id,ExtensionToken.revoked_at.is_(None)).update({'revoked_at':datetime.datetime.utcnow()})
    token='dsx_'+secrets.token_urlsafe(36)
    expires=datetime.datetime.utcnow()+datetime.timedelta(days=7)
    db.add(ExtensionToken(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires_at=expires))
    db.commit()
    return {'token':token,'expires_at':expires.isoformat()+'Z','message':'Shown only once. Keep it private; generating a new token revokes older tokens.'}

@router.post('/extension/revoke')
def revoke_extension_token(user=Depends(current_user),db:Session=Depends(get_db)):
    db.query(ExtensionToken).filter(ExtensionToken.user_id==user.id,ExtensionToken.revoked_at.is_(None)).update({'revoked_at':datetime.datetime.utcnow()})
    db.commit();return {'ok':True}

def extension_user(request:Request,db:Session=Depends(get_db)):
    value=request.headers.get('authorization','')
    if not value.startswith('Bearer dsx_'):raise HTTPException(401,'Connect the extension using a token from your account')
    digest=hashlib.sha256(value[7:].encode()).hexdigest()
    row=db.get(ExtensionToken,digest)
    if not row or row.revoked_at or row.expires_at<=datetime.datetime.utcnow():
        raise HTTPException(401,'Extension token expired or revoked. Reconnect from DeepShield.')
    user=db.get(User,row.user_id)
    if not user:raise HTTPException(401,'Account no longer exists')
    return user

@router.get('/extension/status')
def extension_status(user=Depends(extension_user),db:Session=Depends(get_db)):
    return {'connected':True,'user':user.display_name,**plan_info(db,user)}

@router.post('/extension/analyze')
def extension_analyze(file:UploadFile=File(...),source:str='YouTube',user=Depends(extension_user),db:Session=Depends(get_db)):
    if source not in ('YouTube','Facebook','Instagram'):raise HTTPException(422,'Unsupported platform')
    if (file.content_type or '') not in ('video/webm','video/mp4','application/octet-stream'):
        raise HTTPException(415,'A recorded video is required')
    require_scan_quota(db,user)
    if not MODEL_QUEUE.acquire(blocking=False):raise HTTPException(503,'The detector is busy. Retry shortly.')
    try:
        with tempfile.TemporaryDirectory(prefix='ds-extension-') as folder:
            media=Path(folder)/'capture.webm'
            total=0
            with media.open('wb') as out:
                while chunk:=file.file.read(1024*1024):
                    total+=len(chunk)
                    if total>MAX_UPLOAD_BYTES:raise HTTPException(413,'Capture too large')
                    out.write(chunk)
            if total<512:raise HTTPException(422,'Capture contains no playable frames')
            result=analyze_video(media)
            return save_detection(db,user,f'Extension: {source} capture',result)
    finally:MODEL_QUEUE.release()
