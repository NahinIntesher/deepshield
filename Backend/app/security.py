import hashlib, secrets, time
from fastapi import Request, HTTPException, Depends
from .database import get_db
from .models.db_models import AuthSession, User, VideoAttempt
from .config import COOKIE_SECURE, COOKIE_SAMESITE, QUALIFICATION_MIN_SCORE, QUALIFICATION_ACCURACY_THRESHOLD
COOKIE = "deepshield_session"

def session_user(db, token, allow_incomplete=False):
    if not token: return None
    row = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
    user=db.get(User, row.user_id) if row and row.expires > time.time() else None
    return user if user and (allow_incomplete or not user.needs_profile) else None

def issue_session(db, response, user, previous_token=None):
    db.query(AuthSession).filter(AuthSession.expires < time.time()).delete()
    if previous_token:
        db.query(AuthSession).filter_by(token_hash=hashlib.sha256(previous_token.encode()).hexdigest()).delete()
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.id, expires=time.time()+86400))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE, max_age=86400)

def issue_mobile_session(db, user):
    """Issue an opaque, revocable token backed by the existing AuthSession table."""
    db.query(AuthSession).filter(AuthSession.expires < time.time()).delete()
    token = 'dsm_' + secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                       user_id=user.id, expires=time.time()+86400))
    db.commit()
    return token


def bearer_mobile_user(db, header, allow_incomplete=False):
    if not header.startswith('Bearer dsm_'):
        return None
    return session_user(db, header[7:],allow_incomplete)


def current_user(request: Request, db=Depends(get_db)):
    auth = request.headers.get('authorization', '')
    user = bearer_mobile_user(db, auth,True) if auth.startswith('Bearer dsm_') else session_user(db, request.cookies.get(COOKIE),True)
    if not user: raise HTTPException(401, "Please log in again")
    if user.needs_profile and request.url.path not in ('/api/auth/me','/api/auth/onboarding','/api/auth/logout','/api/auth/mobile/logout'):
        raise HTTPException(403,'Complete your username and display name before continuing.')
    return user

def admin_user(user=Depends(current_user)):
    if user.role != 'admin': raise HTTPException(403, "Administrator access required")
    return user


def subscription_reviewer(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    return user

def own_user(user, user_id):
    if user.id != user_id: raise HTTPException(403, "This request belongs to another account")

def qualify(db, user):
    # Use the same aggregate history as the displayed account accuracy.
    accuracy = user.total_correct / user.total_rounds_played if user.total_rounds_played else 0.0
    user.qualified_for_research = accuracy >= QUALIFICATION_ACCURACY_THRESHOLD and user.score >= QUALIFICATION_MIN_SCORE
    return user.qualified_for_research


def record_attempt(db, user, item, correct):
    key = f"{user.id}:{item.id}"
    if not db.get(VideoAttempt, key):
        db.add(VideoAttempt(key=key,user_id=user.id,item_id=item.id,correct=correct))
        db.flush()
    qualify(db,user)
