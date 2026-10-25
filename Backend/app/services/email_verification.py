"""Single-use registration links. Only token hashes are persisted."""
import hashlib
import html
import os
import secrets
import time
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from ..models.db_models import User
from ..product_models import PendingRegistration

def configured():
 return bool(os.getenv('BREVO_API_KEY','').strip() and os.getenv('EMAIL_FROM','').strip() and os.getenv('PUBLIC_APP_URL','').strip())

def send_link(email,token,language):
 if not configured():raise HTTPException(503,'Email verification is being configured. Please try again later or use Google sign-in.')
 origin=os.environ['PUBLIC_APP_URL'].rstrip('/')
 parsed=urlsplit(origin)
 if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1')):
  raise HTTPException(503,'Email verification is temporarily unavailable.')
 link=origin+'/verify-email#token='+token
 bn=language=='bn'
 subject='DeepShield email যাচাই করুন' if bn else 'Verify your DeepShield email'
 text=('DeepShield-এ আপনার email যাচাই করতে নিচের লিংক খুলুন। লিংকটি ৩০ মিনিট কার্যকর থাকবে।\n' if bn else 'Open this link to verify your DeepShield email. It expires in 30 minutes.\n')+link
 text+=('\nআপনি account না খুলে থাকলে এই email উপেক্ষা করুন।' if bn else '\nIf you did not request an account, ignore this email.')
 try:
  response=httpx.post('https://api.brevo.com/v3/smtp/email',headers={'api-key':os.environ['BREVO_API_KEY']},json={
   'sender':{'name':'DeepShield','email':os.environ['EMAIL_FROM']},'to':[{'email':email}],
   'subject':subject,'textContent':text},timeout=20)
  response.raise_for_status()
 except httpx.HTTPError:
  raise HTTPException(503,'Verification email could not be sent. Please use Resend or try again later.') from None

def begin(db,payload,password_hash):
 if not configured():raise HTTPException(503,'Email verification is being configured. Please try again later or use Google sign-in.')
 username=payload.username.strip().lower();name=payload.display_name.strip();email=str(payload.email).lower()
 if len(username)<2 or not name:raise HTTPException(422,'A username and display name are required.')
 if db.query(User).filter((User.username==username)|(User.email==email)).first():raise HTTPException(409,'This username or email is already registered. Sign in instead.')
 now=time.time()
 db.query(PendingRegistration).filter(PendingRegistration.expires<now).delete()
 if db.query(PendingRegistration).filter((PendingRegistration.username==username)|(PendingRegistration.email==email)).first():
  raise HTTPException(409,'A verification is already pending. Check your inbox or use Resend.')
 token=secrets.token_urlsafe(32)
 db.add(PendingRegistration(token_hash=hashlib.sha256(token.encode()).hexdigest(),username=username,email=email,display_name=name,password_hash=password_hash,expires=now+1800,sent_at=now,language=payload.language))
 try:db.commit()
 except IntegrityError:
  db.rollback();raise HTTPException(409,'A registration is already pending. Check your inbox or use Resend.')
 send_link(email,token,payload.language)
 return {'verification_required':True,'message':'Check your email to verify your account.','resend_after':60}

def resend(db,email):
 row=db.query(PendingRegistration).filter_by(email=str(email).lower()).with_for_update().first()
 if row:
  now=time.time()
  if now-row.sent_at<60:raise HTTPException(429,'Wait 60 seconds before requesting another email.',headers={'Retry-After':str(max(1,int(60-now+row.sent_at)))})
  token=secrets.token_urlsafe(32)
  row.token_hash=hashlib.sha256(token.encode()).hexdigest();row.expires=now+1800;row.sent_at=now
  db.commit();send_link(row.email,token,row.language)
 return {'ok':True,'message':'If a registration is pending, a verification email has been sent.','resend_after':60}

def verify(db,token):
 import datetime as dt
 row=db.get(PendingRegistration,hashlib.sha256(token.encode()).hexdigest(),with_for_update=True)
 if not row or row.expires<time.time():raise HTTPException(400,'This verification link is invalid or expired. Request a new email.')
 user=User(username=row.username,display_name=row.display_name,password_hash=row.password_hash,email=row.email,email_verified_at=dt.datetime.utcnow(),role='participant',needs_profile=False)
 db.add(user);db.delete(row)
 try:db.commit()
 except IntegrityError:
  db.rollback();raise HTTPException(409,'This username or email is already registered. Sign in instead.')
 return {'ok':True,'message':'Email verified. You can now sign in.'}
