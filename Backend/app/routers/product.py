import csv,datetime as dt,hashlib,io,json,os,secrets,time,random
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Request
from fastapi.responses import FileResponse,StreamingResponse
from pydantic import BaseModel,Field,ConfigDict,model_validator
from ..database import get_db
from ..security import current_user,admin_user,subscription_reviewer,session_user,COOKIE
from ..product_models import Scan,Charge,Membership,Subscription,ExtensionToken,Ticket,Notice,Assessment,PaymentReceipt
from ..models.db_models import User,DetectionRecord,ResearchChallengeItem,GameRoundRecord,ResearchSubmission,CourseProgress
from ..services.scan_queue import ROOT,enqueue,view,membership,notify,lock,now,delete_source
from ..services.links import canonical
from ..data.sample_dataset import EXTENSIONS,available_items
from ..activity import audit
from .auth import rate_limit
from ..services.upload_validation import IMAGE_EXTENSIONS,IMAGE_MAX_BYTES,validate_image,validate_video
router=APIRouter(prefix='/api',tags=['DeepShield product'])
def scan_user(request:Request,db=Depends(get_db)):
 token=request.headers.get('authorization','')
 if token.startswith('Bearer dsm_'):
  from ..security import bearer_mobile_user
  user=bearer_mobile_user(db,token)
  if not user:raise HTTPException(401,'Mobile session expired. Please sign in again.')
  return user
 if token.startswith('Bearer '):
  row=db.get(ExtensionToken,hashlib.sha256(token[7:].encode()).hexdigest())
  if row and row.kind=='access' and row.expires>time.time():
   account=db.get(User,row.user_id)
   if account and not account.needs_profile:return account
  raise HTTPException(401,'Browser connection expired. Pair again from the web app.')
 user=session_user(db,request.cookies.get(COOKIE))
 if not user:raise HTTPException(401,'Please sign in')
 return user
class LinkInput(BaseModel):url:str=Field(min_length=10,max_length=2048)
@router.post('/scans/link',status_code=202)
def link(payload:LinkInput,user=Depends(scan_user),db=Depends(get_db)):
 url=canonical(payload.url);return enqueue(db,user,'link',url,url=url)
@router.post('/scans/upload',status_code=202)
def upload(file:UploadFile=File(...),user=Depends(scan_user),db=Depends(get_db)):
 suffix=Path(file.filename or '').suffix.lower()
 if suffix not in EXTENSIONS | IMAGE_EXTENSIONS:raise HTTPException(415,'Choose JPG, PNG, WebP, MP4, MOV, AVI, MKV or WebM.')
 is_image=suffix in IMAGE_EXTENSIONS
 maximum=IMAGE_MAX_BYTES if is_image else 50_000_000
 path=ROOT/(secrets.token_hex(16)+suffix)
 try:
  total=0
  with path.open('wb') as out:
   while chunk:=file.file.read(1024*1024):
    total+=len(chunk)
    if total>maximum:raise HTTPException(413,'Maximum image size is 20 MiB.' if is_image else 'Maximum video size is 50 MB.')
    out.write(chunk)
  if not total:raise HTTPException(422,'The uploaded file is empty.')
  (validate_image if is_image else validate_video)(path)
  return enqueue(db,user,'upload',Path(file.filename).name,path=path)
 except Exception:path.unlink(missing_ok=True);raise
 finally:file.file.close()
@router.get('/scans')
def scans(user=Depends(scan_user),db=Depends(get_db)):return [view(r) for r in db.query(Scan).filter_by(user_id=user.id).order_by(Scan.created_at.desc()).limit(100)]
@router.get('/scans/{scan_id}')
def get_scan(scan_id:str,user=Depends(scan_user),db=Depends(get_db)):
 row=db.get(Scan,scan_id)
 if not row or row.user_id!=user.id:raise HTTPException(404,'Scan not found')
 result=view(row)
 if row.result_id:
  saved=db.get(DetectionRecord,row.result_id)
  if saved:result['result']=json.loads(saved.result_json)
 return result
@router.delete('/scans/{scan_id}')
def remove(scan_id:str,user=Depends(current_user),db=Depends(get_db)):
 with lock:
  row=db.get(Scan,scan_id)
  if not row or row.user_id!=user.id:raise HTTPException(404,'Scan not found')
  if row.state in ('processing','downloading'):raise HTTPException(409,'Wait for processing to finish before deleting.')
  delete_source(row)
  if row.state!='completed':
   charge=db.get(Charge,scan_id)
   if charge:charge.charged=False
  record=db.get(DetectionRecord,row.result_id) if row.result_id else None
  db.delete(row);db.flush()
  if record:db.delete(record)
  db.commit();return {'ok':True}
@router.get('/billing')
def billing(user=Depends(current_user),db=Depends(get_db)):
 return {**membership(db,user.id),'price_bdt':int(os.getenv('PREMIUM_PRICE_BDT','299')),'payment':{'provider':'bKash','number':os.getenv('BKASH_PAYMENT_NUMBER','01815808291'),'verification':'manual'},'instructions':os.getenv('PAYMENT_INSTRUCTIONS','Pay the displayed amount to the bKash number, then submit the transaction ID. A reviewer must verify the payment before activation. Never share your PIN or OTP.'),'requests':[{'id':r.id,'status':r.status,'note':r.note,'reference':r.reference,'review':r.review,'created_at':r.created_at} for r in db.query(Subscription).filter_by(user_id=user.id).order_by(Subscription.id.desc())]}
class SubscriptionInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 reference:str=Field(default='',max_length=160)
 note:str=Field(min_length=5,max_length=1000)
 request_type:Literal['manual_payment','academic_demo']='academic_demo'
 @model_validator(mode='after')
 def valid_payment(self):
  self.reference=self.reference.upper()
  if self.request_type=='manual_payment':
   import re
   if not re.fullmatch(r'[A-Z0-9]{6,40}',self.reference):raise ValueError('Enter the bKash transaction ID (6–40 letters and numbers).')
  return self
@router.post('/billing/request',status_code=201)
def subscribe(payload:SubscriptionInput,user=Depends(current_user),db=Depends(get_db)):
 with lock:
  if membership(db,user.id)['plan']=='premium':raise HTTPException(409,'Premium is already active.')
  if db.query(Subscription).filter_by(user_id=user.id,status='pending').first():raise HTTPException(409,'Your request is already awaiting review.')
  if payload.reference and db.query(Subscription).filter(Subscription.reference==payload.reference,Subscription.status.in_(['pending','approved'])).first():raise HTTPException(409,'This transaction ID is already associated with a request. Contact support if this is an error.')
  if payload.reference and db.get(PaymentReceipt,hashlib.sha256(payload.reference.encode()).hexdigest()):raise HTTPException(409,'This transaction ID has already been used.')
  r=Subscription(user_id=user.id,reference=payload.reference.strip(),note=payload.note.strip());db.add(r);db.commit();return {'id':r.id,'status':r.status}
@router.get('/billing/export/scans')
def export(user=Depends(current_user),db=Depends(get_db)):
 if membership(db,user.id)['plan']!='premium':raise HTTPException(403,'Personal scan CSV export requires Premium.')
 text=io.StringIO();writer=csv.writer(text);writer.writerow(['id','video','prediction','model_score_percent','model_id','created_at_utc'])
 for r in db.query(DetectionRecord).filter_by(user_id=user.id):
  name=r.source_name
  if name.startswith(('=','+','-','@','\t','\r')):name="'"+name
  writer.writerow([r.id,name,r.verdict,r.confidence,r.model_id,r.created_at.isoformat()])
 return StreamingResponse(iter([text.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="deepshield-scans.csv"'})
@router.get('/extension/account')
def extension_account(user=Depends(scan_user),db=Depends(get_db)):return membership(db,user.id)
@router.post('/extension/pair')
def pair(user=Depends(current_user),db=Depends(get_db)):
 code=secrets.token_hex(12).upper();db.query(ExtensionToken).filter_by(user_id=user.id,kind='pair').delete();db.add(ExtensionToken(user_id=user.id,kind='pair',token_hash=hashlib.sha256(code.encode()).hexdigest(),expires=time.time()+300));db.commit();return {'code':code,'expires_in':300}
class PairInput(BaseModel):code:str=Field(min_length=24,max_length=24)
@router.post('/extension/redeem')
def redeem(payload:PairInput,request:Request,db=Depends(get_db)):
 rate_limit(request);key=hashlib.sha256(payload.code.strip().upper().encode()).hexdigest();r=db.get(ExtensionToken,key)
 if not r or r.kind!='pair' or r.expires<time.time():raise HTTPException(400,'Invalid or expired pairing code.')
 uid=r.user_id
 if db.query(ExtensionToken).filter(ExtensionToken.token_hash==key,ExtensionToken.expires>time.time()).delete(synchronize_session=False)!=1:db.rollback();raise HTTPException(409,'Code already used.')
 token=secrets.token_urlsafe(40);db.add(ExtensionToken(user_id=uid,token_hash=hashlib.sha256(token.encode()).hexdigest(),kind='access',expires=time.time()+30*86400));db.commit();return {'token':token}
@router.get('/extension/tokens')
def tokens(user=Depends(current_user),db=Depends(get_db)):return [{'id':r.token_hash,'expires':r.expires} for r in db.query(ExtensionToken).filter(ExtensionToken.user_id==user.id,ExtensionToken.kind=='access',ExtensionToken.expires>time.time())]
@router.delete('/extension/tokens/{token_id}')
def revoke(token_id:str,user=Depends(current_user),db=Depends(get_db)):
 db.query(ExtensionToken).filter_by(token_hash=token_id,user_id=user.id).delete();db.commit();return {'ok':True}
@router.get('/notifications')
def notices(user=Depends(current_user),db=Depends(get_db)):return [{'id':r.id,'title':r.title,'message':r.message,'read':r.read,'created_at':r.created_at} for r in db.query(Notice).filter_by(user_id=user.id).order_by(Notice.id.desc()).limit(50)]
@router.post('/notifications/read')
def read(user=Depends(current_user),db=Depends(get_db)):
 db.query(Notice).filter_by(user_id=user.id).update({'read':True});db.commit();return {'ok':True}
class TicketInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 subject:str=Field(min_length=4,max_length=160)
 message:str=Field(min_length=10,max_length=3000)
def ticket_view(r):return {'id':r.id,'user_id':r.user_id,'subject':r.subject,'message':r.message,'reply':r.reply,'status':r.status,'created_at':r.created_at}
@router.get('/support')
def tickets(user=Depends(current_user),db=Depends(get_db)):return [ticket_view(r) for r in db.query(Ticket).filter_by(user_id=user.id).order_by(Ticket.id.desc())]
@router.post('/support',status_code=201)
def ticket(payload:TicketInput,user=Depends(current_user),db=Depends(get_db)):
 if db.query(Ticket).filter_by(user_id=user.id,status='open').count()>=5:raise HTTPException(429,'Please wait for a reply to your open requests.')
 r=Ticket(user_id=user.id,subject=payload.subject.strip(),message=payload.message.strip());db.add(r);db.commit();return ticket_view(r)
@router.get('/operations',dependencies=[Depends(admin_user)])
def operations(db=Depends(get_db)):
 return {'subscriptions':[{'id':r.id,'user_id':r.user_id,'username':db.get(User,r.user_id).username,'status':r.status,'reference':r.reference,'note':r.note,'review':r.review,'created_at':r.created_at} for r in db.query(Subscription).order_by(Subscription.id.desc()).limit(100)],'tickets':[ticket_view(r) for r in db.query(Ticket).order_by(Ticket.id.desc()).limit(100)],'queue':[view(r) for r in db.query(Scan).order_by(Scan.created_at.desc()).limit(30)]}
class ReviewInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 decision:Literal['approved','rejected']
 activation:Literal['academic_demo','manual_payment']='academic_demo'
 note:str=Field(min_length=5,max_length=1000)
 payment_verified:bool=False
@router.post('/operations/subscriptions/{request_id}')
def review(request_id:int,payload:ReviewInput,admin=Depends(subscription_reviewer),db=Depends(get_db)):
 with lock:
  r=db.get(Subscription,request_id)
  if not r:raise HTTPException(404,'Request not found')
  if r.status!='pending':raise HTTPException(409,'Already reviewed.')
  if r.user_id==admin.id:raise HTTPException(403,'Another reviewer must decide your own membership request.')
  if payload.decision=='approved' and payload.activation=='manual_payment' and not r.reference:raise HTTPException(422,'Verified manual payments need a reference.')
  if payload.decision=='approved' and payload.activation=='manual_payment' and not payload.payment_verified:raise HTTPException(422,'Confirm that the bKash transaction, recipient and amount were independently verified.')
  if payload.decision=='approved' and payload.activation=='manual_payment' and db.query(Subscription).filter(Subscription.id!=r.id,Subscription.reference==r.reference,Subscription.status=='approved').first():raise HTTPException(409,'This transaction ID has already been used for an approved membership.')
  r.status=payload.decision;r.review=payload.note
  if r.status=='approved':
   if payload.activation=='manual_payment':
    key=hashlib.sha256(r.reference.strip().upper().encode()).hexdigest()
    if db.get(PaymentReceipt,key):raise HTTPException(409,'This transaction ID has already been used.')
    db.add(PaymentReceipt(reference_hash=key))
   m=db.get(Membership,r.user_id)
   if not m:m=Membership(user_id=r.user_id);db.add(m)
   m.expires=max(now(),m.expires or now())+dt.timedelta(days=30);m.activation=payload.activation
  notify(db,r.user_id,'Subscription request '+r.status,payload.note);audit(db,admin.id,'subscription_reviewed',str(r.id),{'decision':r.status,'activation':payload.activation,'payment_verified':payload.payment_verified,'reviewer_role':admin.role});db.commit();return {'ok':True}

@router.get('/membership-reviews')
def membership_reviews(reviewer=Depends(subscription_reviewer),db=Depends(get_db)):
 return {'payment':{'provider':'bKash','number':os.getenv('BKASH_PAYMENT_NUMBER','01815808291'),'price_bdt':int(os.getenv('PREMIUM_PRICE_BDT','299'))},'subscriptions':[{'id':r.id,'user_id':r.user_id,'username':db.get(User,r.user_id).username,'status':r.status,'reference':r.reference,'note':r.note,'review':r.review,'created_at':r.created_at} for r in db.query(Subscription).order_by(Subscription.id.desc()).limit(100)]}
class ReplyInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 reply:str=Field(min_length=5,max_length=3000)
@router.post('/operations/support/{ticket_id}')
def reply(ticket_id:int,payload:ReplyInput,admin=Depends(admin_user),db=Depends(get_db)):
 r=db.get(Ticket,ticket_id)
 if not r:raise HTTPException(404,'Request not found')
 r.reply=payload.reply;r.status='resolved';notify(db,r.user_id,'Reply: '+r.subject,payload.reply);audit(db,admin.id,'support_replied',str(r.id));db.commit();return {'ok':True}

def assessment_view(r,db):
 ids=json.loads(r.assignment)[r.state] if r.state in ('pre','post') else []
 return {'id':r.id,'state':r.state,'pre_score':r.pre_score,'post_score':r.post_score,'exposures':r.exposures,'items':[{'id':i,'media_path':db.get(ResearchChallengeItem,i).media_path} for i in ids]}
@router.get('/assessment')
def assessment(user=Depends(current_user),db=Depends(get_db)):
 r=db.query(Assessment).filter_by(user_id=user.id).first();return assessment_view(r,db) if r else None
class Consent(BaseModel):consent:Literal[True]
@router.post('/assessment/start',status_code=201)
def start(payload:Consent,user=Depends(current_user),db=Depends(get_db)):
 with lock:
  if db.query(Assessment).filter_by(user_id=user.id).first():raise HTTPException(409,'Continue your existing assessment.')
  items=available_items(db);real=[i.id for i in items if i.ground_truth=='Real'];fake=[i.id for i in items if i.ground_truth=='Fake']
  if min(len(real),len(fake))<4:raise HTTPException(409,'At least four Real and four Fake library videos are needed.')
  rng=random.SystemRandom();rng.shuffle(real);rng.shuffle(fake);pre=real[:2]+fake[:2];post=real[2:4]+fake[2:4];rng.shuffle(pre);rng.shuffle(post)
  seen={r.item_id for r in db.query(GameRoundRecord).filter_by(user_id=user.id)}|{r.item_id for r in db.query(ResearchSubmission).filter_by(user_id=user.id)}
  r=Assessment(id=secrets.token_hex(16),user_id=user.id,assignment=json.dumps({'pre':pre,'post':post}),exposures=len(set(pre+post)&seen));db.add(r);db.commit();return assessment_view(r,db)
class Choice(BaseModel):
 item_id:int
 prediction:Literal['Real','Fake']
class Answers(BaseModel):
 phase:Literal['pre','post']
 answers:list[Choice]
@router.post('/assessment/{assessment_id}/submit')
def submit(assessment_id:str,payload:Answers,user=Depends(current_user),db=Depends(get_db)):
 with lock:
  r=db.get(Assessment,assessment_id)
  if not r or r.user_id!=user.id:raise HTTPException(404,'Assessment not found')
  if r.state!=payload.phase:raise HTTPException(409,'Phase already submitted.')
  ids=json.loads(r.assignment)[r.state]
  if len(payload.answers)!=len(ids) or set(ids)!={a.item_id for a in payload.answers}:raise HTTPException(422,'Answer every assigned video exactly once.')
  if r.state=='post':
   practiced=db.query(GameRoundRecord).filter(GameRoundRecord.user_id==user.id,GameRoundRecord.created_at>=r.pre_at).first()
   studied=db.query(CourseProgress).filter(CourseProgress.user_id==user.id,CourseProgress.completed==True,CourseProgress.updated_at>=r.pre_at).first()
   if not practiced and not studied:raise HTTPException(409,'Complete a lesson or play a round after the first assessment before submitting the follow-up.')
  score=100*sum(a.prediction==db.get(ResearchChallengeItem,a.item_id).ground_truth for a in payload.answers)/len(ids)
  if r.state=='pre':r.pre_score=score;r.pre_answers=json.dumps([a.model_dump() for a in payload.answers]);r.pre_at=now();r.state='post'
  else:r.post_score=score;r.post_answers=json.dumps([a.model_dump() for a in payload.answers]);r.state='completed'
  db.commit();return assessment_view(r,db)
