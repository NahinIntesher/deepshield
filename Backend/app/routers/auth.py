import base64
import os
import hashlib
import hmac
import secrets
import time, threading
from collections import defaultdict, deque
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.db_models import User
from ..models.schemas import UserLoginRequest, UserResponse, UserSignupRequest, RoleUpdateRequest
from ..config import QUALIFICATION_ACCURACY_THRESHOLD

from ..security import current_user, admin_user, own_user, issue_session, qualify, COOKIE
from ..models.db_models import AuthSession

router = APIRouter(prefix="/api/auth", tags=["Authentication & User Management"])

_PASSWORD_HASH_ITERATIONS = 600_000
_attempts=defaultdict(deque)
_attempt_lock=threading.Lock()
def rate_limit(request: Request):
    key=request.client.host if request.client else "unknown"
    now=time.monotonic()
    with _attempt_lock:
        # Single-worker local limit; use edge rate limiting when publicly deployed.
        for stale in [k for k,v in _attempts.items() if not v or now-v[-1]>60]: _attempts.pop(stale,None)
        recent=_attempts[key]
        while recent and now-recent[0]>60: recent.popleft()
        if len(recent)>=15: raise HTTPException(429,"Too many attempts. Try again in a minute.",headers={"Retry-After":"60"})
        recent.append(now)



def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${_PASSWORD_HASH_ITERATIONS}${salt_text}${digest_text}"


def _verify_password(password: str, encoded_hash: str) -> bool:
    if not isinstance(password,str) or not isinstance(encoded_hash,str):return False
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations_text)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual_digest, expected_digest)


@router.post("/signup", status_code=202)
def signup(payload: UserSignupRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    if os.getenv('EMAIL_VERIFICATION_REQUIRED','false').lower()=='true':
        from ..services.email_verification import begin
        return begin(db,payload,_hash_password(payload.password))
    username=payload.username.strip().lower();name=payload.display_name.strip();email=str(payload.email).lower()
    if len(username)<2 or not name:raise HTTPException(422,'A username and display name are required.')
    user=User(username=username,display_name=name,email=email,password_hash=_hash_password(payload.password),role='participant',needs_profile=False)
    db.add(user)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'This username or email is already registered. Sign in instead.')
    return {'verification_required':False,'message':'Account created. Sign in with your username and password.'}


@router.post("/login", response_model=UserResponse)
def login(payload: UserLoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    username = payload.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    qualify(db,user)
    issue_session(db, response, user, request.cookies.get(COOKIE))
    return user


@router.get("/user/{user_id}", response_model=UserResponse)
def get_user_profile(user_id: int, user=Depends(current_user), db=Depends(get_db)):
    own_user(user, user_id)
    qualify(db,user)
    db.commit()
    return user

@router.post("/logout")
def logout(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        db.query(AuthSession).filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).delete()
        db.commit()
    response.delete_cookie(COOKIE)
    return {"ok":True}

@router.get("/qualification")
def qualification(user=Depends(current_user), db=Depends(get_db)):
    from ..config import QUALIFICATION_MIN_SCORE, QUALIFICATION_ACCURACY_THRESHOLD
    qualify(db,user)
    db.commit()
    raw_accuracy=100*user.total_correct/user.total_rounds_played if user.total_rounds_played else 0.0
    return {"required_score":QUALIFICATION_MIN_SCORE,"required_accuracy":QUALIFICATION_ACCURACY_THRESHOLD*100,"score":user.score,"rounds":user.total_rounds_played,"accuracy":raw_accuracy,"qualified":user.qualified_for_research}



class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8,max_length=128)
    new_password: str = Field(min_length=12,max_length=128)

@router.post("/password")
def change_password(payload:PasswordChange,request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    rate_limit(request)
    if not _verify_password(payload.current_password,user.password_hash): raise HTTPException(400,"Current password is incorrect")
    user.password_hash=_hash_password(payload.new_password)
    db.query(AuthSession).filter_by(user_id=user.id).delete()
    from ..product_models import ExtensionToken
    db.query(ExtensionToken).filter_by(user_id=user.id).delete()
    db.commit()
    response.delete_cookie(COOKIE)
    return {"ok":True,"message":"Password changed. Log in again on every device."}


@router.post("/admin/login", response_model=UserResponse)
def admin_login(payload: UserLoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user=db.query(User).filter_by(username=payload.username.strip().lower()).first()
    if not user or not user.password_hash or not _verify_password(payload.password,user.password_hash):
        raise HTTPException(401,"Invalid administrator credentials")
    if user.role != 'admin': raise HTTPException(403,"Administrator access required")
    from ..activity import audit
    audit(db,user.id,"admin_login",str(user.id))
    issue_session(db,response,user,request.cookies.get(COOKIE))
    return user

@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user),db=Depends(get_db)):
    qualify(db,user);db.commit();return user


from ..security import issue_mobile_session
# Native mobile authentication. Uses the same credential verification and session
# table as the browser; no existing web login route or model path is changed.
class MobileAuthResponse(BaseModel):
    token: str
    expires_in: int = 86400
    user: UserResponse


@router.post('/mobile/login', response_model=MobileAuthResponse)
def mobile_login(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = db.query(User).filter(User.username == payload.username.strip().lower()).first()
    if not user or not user.password_hash or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Invalid username or password')
    qualify(db, user)
    return {'token': issue_mobile_session(db, user), 'user': user}


@router.post('/mobile/signup', status_code=202)
def mobile_signup(payload: UserSignupRequest, request: Request, db: Session = Depends(get_db)):
    return signup(payload,request,db)


@router.post('/mobile/admin/login', response_model=MobileAuthResponse)
def mobile_admin_login(payload: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit(request)
    user = db.query(User).filter_by(username=payload.username.strip().lower()).first()
    if not user or not user.password_hash or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Invalid administrator credentials')
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required')
    from ..activity import audit
    audit(db, user.id, 'mobile_admin_login', str(user.id))
    return {'token': issue_mobile_session(db, user), 'user': user}


@router.post('/mobile/logout')
def mobile_logout(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get('authorization', '')
    if header.startswith('Bearer dsm_'):
        db.query(AuthSession).filter_by(token_hash=hashlib.sha256(header[7:].encode()).hexdigest()).delete()
        db.commit()
    return {'ok': True}


class VerificationInput(BaseModel):
    token: str = Field(min_length=40,max_length=128)

class ResendInput(BaseModel):
    email: EmailStr

@router.post('/verify-email')
def verify_email(payload:VerificationInput,request:Request,db=Depends(get_db)):
    rate_limit(request)
    from ..services.email_verification import verify
    return verify(db,payload.token)

@router.post('/resend-verification')
def resend_verification(payload:ResendInput,request:Request,db=Depends(get_db)):
    rate_limit(request)
    from ..services.email_verification import resend
    return resend(db,payload.email)

class ProfileCompletion(BaseModel):
    username: str = Field(min_length=2,max_length=50,pattern=r'^[A-Za-z0-9_.-]+$')
    display_name: str = Field(min_length=1,max_length=64)
    password: str | None = Field(default=None,min_length=12,max_length=128)

@router.post('/onboarding',response_model=UserResponse)
def complete_profile(payload:ProfileCompletion,request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    rate_limit(request)
    if not user.needs_profile:raise HTTPException(409,'Your profile is already complete.')
    name=payload.display_name.strip();username=payload.username.strip().lower()
    if not name:raise HTTPException(422,'Display name cannot be empty.')
    if username.startswith('google_'):raise HTTPException(422,'Choose a personal username without the google_ prefix.')
    if db.query(User).filter(User.username==username,User.id!=user.id).first():raise HTTPException(409,'That username is already registered')
    user.username=username;user.display_name=name;user.needs_profile=False
    if payload.password:user.password_hash=_hash_password(payload.password)
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'That username is already registered')
    issue_session(db,response,user,request.cookies.get(COOKIE))
    return user
