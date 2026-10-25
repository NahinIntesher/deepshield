"""Google Identity Services login. Verify signed ID tokens on the server."""
import hmac
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from ..config import COOKIE_SECURE, COOKIE_SAMESITE, CORS_ORIGINS
from ..database import get_db
from ..models.db_models import User
from ..product_models import GoogleIdentity
from ..security import COOKIE, issue_session, qualify
from .auth import rate_limit

router=APIRouter(prefix='/api/auth',tags=['Google sign-in'])
NONCE_COOKIE='deepshield_google_nonce'

def client_id():return os.getenv('GOOGLE_CLIENT_ID','').strip()

@router.get('/providers')
def providers():return {'google':{'enabled':bool(client_id()),'client_id':client_id() or None}}

@router.post('/google/challenge')
def challenge(request:Request,response:Response):
 rate_limit(request)
 if not client_id():raise HTTPException(503,'Google sign-in has not been configured by the administrator.')
 if request.headers.get('origin') not in CORS_ORIGINS:raise HTTPException(403,'Open sign-in from the configured website.')
 nonce=secrets.token_urlsafe(32)
 response.set_cookie(NONCE_COOKIE,nonce,max_age=300,httponly=True,secure=COOKIE_SECURE,samesite=COOKIE_SAMESITE)
 return {'nonce':nonce}

def verify_credential(credential,audience):
 from google.oauth2.id_token import verify_oauth2_token
 from google.auth.transport.requests import Request as GoogleRequest
 return verify_oauth2_token(credential,GoogleRequest(),audience)

class GoogleLogin(BaseModel):credential:str=Field(min_length=100,max_length=16384)

@router.post('/google')
def login(payload:GoogleLogin,request:Request,response:Response,db=Depends(get_db)):
 rate_limit(request)
 audience=client_id()
 if not audience:raise HTTPException(503,'Google sign-in has not been configured by the administrator.')
 if request.headers.get('origin') not in CORS_ORIGINS:raise HTTPException(403,'Open sign-in from the configured website.')
 nonce=request.cookies.get(NONCE_COOKIE)
 if not nonce:raise HTTPException(401,'Google sign-in expired. Try again.')
 try:claims=verify_credential(payload.credential,audience)
 except ValueError:raise HTTPException(401,'Google could not verify this sign-in. Try again.')
 except Exception:raise HTTPException(503,'Google sign-in is temporarily unavailable. Try again later.')
 if not isinstance(claims.get('nonce'),str) or not hmac.compare_digest(claims['nonce'],nonce):raise HTTPException(401,'Google sign-in expired. Try again.')
 if claims.get('iss') not in ('accounts.google.com','https://accounts.google.com') or claims.get('aud')!=audience:raise HTTPException(401,'Invalid Google sign-in.')
 subject=claims.get('sub')
 if not isinstance(subject,str) or not subject or len(subject)>255 or claims.get('email_verified') is not True:raise HTTPException(401,'Use a verified Google account.')
 identity=db.get(GoogleIdentity,subject)
 if identity:user=db.get(User,identity.user_id)
 else:
  # Never merge accounts by email or accept role/identity fields from the browser.
  user=User(username='google_'+secrets.token_hex(8),display_name=str(claims.get('name') or 'Google member').strip()[:64] or 'Google member',role='participant',needs_profile=True)
  db.add(user);db.flush();db.add(GoogleIdentity(subject=subject,user_id=user.id))
  try:db.commit()
  except IntegrityError:
   db.rollback();identity=db.get(GoogleIdentity,subject)
   if not identity:raise HTTPException(409,'Please try signing in again.')
   user=db.get(User,identity.user_id)
 if not user:raise HTTPException(401,'This account is unavailable.')
 qualify(db,user)
 issue_session(db,response,user,request.cookies.get(COOKIE))
 response.delete_cookie(NONCE_COOKIE)
 from ..models.schemas import UserResponse
 return UserResponse.model_validate(user)
