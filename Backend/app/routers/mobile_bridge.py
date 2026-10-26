"""Single-use, short-lived PKCE exchange for the native browser login."""
import base64
import hashlib
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete
from ..database import get_db
from ..models.db_models import AuthSession, User
from ..security import current_user, issue_mobile_session
from .auth import MobileAuthResponse, rate_limit

router = APIRouter(prefix='/api/auth/mobile', tags=['Native browser sign-in'])

class HandoffInput(BaseModel):
    challenge: str = Field(pattern=r'^[A-Za-z0-9_-]{43}$')

class ExchangeInput(BaseModel):
    code: str = Field(pattern=r'^[A-Za-z0-9_-]{54}$')
    verifier: str = Field(pattern=r'^[A-Za-z0-9._~-]{43,128}$')

def handoff_hash(code, challenge):
    return hashlib.sha256(f'mobile-handoff:{code}:{challenge}'.encode()).hexdigest()

@router.post('/handoff')
def handoff(payload: HandoffInput, request: Request, user=Depends(current_user), db=Depends(get_db)):
    rate_limit(request)
    code = secrets.token_urlsafe(40)
    db.add(AuthSession(token_hash=handoff_hash(code, payload.challenge), user_id=user.id, expires=time.time()+60))
    db.commit()
    return {'code': code, 'expires_in': 60}

@router.post('/exchange', response_model=MobileAuthResponse)
def exchange(payload: ExchangeInput, request: Request, db=Depends(get_db)):
    rate_limit(request)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(payload.verifier.encode()).digest()).decode().rstrip('=')
    key = handoff_hash(payload.code, challenge)
    row = db.get(AuthSession, key)
    user = db.get(User, row.user_id) if row and row.expires > time.time() else None
    if not user or user.needs_profile:
        raise HTTPException(401, 'Sign-in expired. Please start again from the app.')
    consumed = db.execute(delete(AuthSession).where(AuthSession.token_hash == key, AuthSession.expires > time.time()))
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, 'Sign-in expired. Please start again from the app.')
    return {'token': issue_mobile_session(db, user), 'user': user}
