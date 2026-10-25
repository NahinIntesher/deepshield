"""Additive mobile workspace. Shares Professional tables, or isolated tables on legacy releases."""
import datetime as dt, json, secrets, random, threading
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from ..database import get_db, Base, engine
from ..security import current_user, admin_user
from ..models.db_models import User, ResearchChallengeItem, GameRoundRecord, ResearchSubmission, CourseProgress
from ..data.sample_dataset import available_items
from ..activity import audit
try:
 from ..product_models import Ticket, Notice, Assessment
except ImportError:
 from sqlalchemy import Column,String,Integer,Text,DateTime,Float,Boolean,ForeignKey
 class Ticket(Base):
  __tablename__='mobile_support_tickets'
  id=Column(Integer,primary_key=True)
  user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
  subject=Column(String(160),nullable=False)
  message=Column(Text,nullable=False)
  reply=Column(Text,default='')
  status=Column(String(16),default='open')
  created_at=Column(DateTime,default=dt.datetime.utcnow)
 class Notice(Base):
  __tablename__='mobile_notifications'
  id=Column(Integer,primary_key=True)
  user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
  title=Column(String(160),nullable=False)
  message=Column(Text,nullable=False)
  read=Column(Boolean,default=False)
  created_at=Column(DateTime,default=dt.datetime.utcnow)
 class Assessment(Base):
  __tablename__='mobile_learning_assessments'
  id=Column(String(40),primary_key=True)
  user_id=Column(Integer,ForeignKey('users.id'),unique=True,nullable=False)
  state=Column(String(16),default='pre')
  assignment=Column(Text,nullable=False)
  pre_answers=Column(Text)
  post_answers=Column(Text)
  pre_score=Column(Float)
  post_score=Column(Float)
  exposures=Column(Integer,default=0)
  started_at=Column(DateTime,default=dt.datetime.utcnow)
  pre_at=Column(DateTime)

def initialize():
 # Create only the additive workspace tables; no legacy migration files or data are dropped.
 for model in (Ticket, Notice, Assessment): model.__table__.create(engine, checkfirst=True)
router=APIRouter(prefix='/api/mobile-workspace',tags=['Mobile workspace'])
lock=threading.RLock()
def now(): return dt.datetime.utcnow()
def notify(db,uid,title,message): db.add(Notice(user_id=uid,title=title,message=message))
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
class ReplyInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 reply:str=Field(min_length=5,max_length=3000)
@router.post('/admin/support/{ticket_id}')
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

@router.get('/admin/support',dependencies=[Depends(admin_user)])
def all_tickets(db=Depends(get_db)):
 return [ticket_view(r) for r in db.query(Ticket).order_by(Ticket.id.desc()).limit(100)]

@router.post('/extension/pair')
def extension_pair(user=Depends(current_user), db=Depends(get_db)):
 try: from .product import pair
 except ImportError: raise HTTPException(501, 'This legacy extension pairs from the web account. Open the existing web extension page, or install the Professional backend to pair here.')
 return pair(user,db)
@router.get('/extension/tokens')
def extension_tokens(user=Depends(current_user), db=Depends(get_db)):
 try: from .product import tokens
 except ImportError: return []
 return tokens(user,db)
@router.delete('/extension/tokens/{token_id}')
def extension_revoke(token_id:str,user=Depends(current_user),db=Depends(get_db)):
 try: from .product import revoke
 except ImportError: raise HTTPException(501,'Revoke this legacy extension from the web account.')
 return revoke(token_id,user,db)

@router.get('/capabilities')
def capabilities(user=Depends(current_user)):
 from pathlib import Path
 product=(Path(__file__).parent/'product.py').exists()
 return {'queued_scans':product,'screen_capture':'android_native','workspace_version':2}
