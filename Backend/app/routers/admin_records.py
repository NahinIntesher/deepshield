"""Record metadata CRUD; computed predictions and original research answers stay immutable."""
import json
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field
from ..database import get_db
from ..security import admin_user
from ..activity import audit
from ..models.db_models import User,DetectionRecord,ResearchSubmission,LearningSample,TrainingJob
from ..product_models import Scan,Ticket,Subscription
from .product import remove

router=APIRouter(prefix='/api/admin/records',tags=['Record management'],dependencies=[Depends(admin_user)])
Resource=Literal['scans','research','support','subscriptions']

@router.get('/{resource}')
def records(resource:Resource,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),db=Depends(get_db)):
 model={'scans':Scan,'research':ResearchSubmission,'support':Ticket,'subscriptions':Subscription}[resource]
 query=db.query(model);total=query.count();rows=query.order_by(model.created_at.desc()).offset(offset).limit(limit).all()
 users={u.id:u.username for u in db.query(User)}
 result=[]
 for r in rows:
  base={'id':r.id,'user_id':r.user_id,'username':users.get(r.user_id,'Deleted account'),'created_at':r.created_at}
  if resource=='scans':base.update(title=r.name,status=r.state,note=r.message)
  elif resource=='research':base.update(title=f'Research #{r.id}',status=r.disagreement_quadrant,note=r.admin_note,human_prediction=r.human_prediction,ai_prediction=r.ai_prediction,item_id=r.item_id)
  elif resource=='support':base.update(title=r.subject,status=r.status,note=r.message,reply=r.reply)
  else:base.update(title=f'Premium #{r.id}',status=r.status,note=r.note,reference=r.reference,review=r.review)
  result.append(base)
 return {'rows':result,'total':total,'offset':offset,'limit':limit}

class RecordEdit(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
 title:str|None=Field(default=None,min_length=2,max_length=160)
 note:str|None=Field(default=None,min_length=5,max_length=3000)
 reference:str|None=Field(default=None,min_length=6,max_length=40,pattern=r'^[A-Za-z0-9]+$')

@router.patch('/{resource}/{ident}')
def update(resource:Resource,ident:str,payload:RecordEdit,actor=Depends(admin_user),db=Depends(get_db)):
 model={'scans':Scan,'research':ResearchSubmission,'support':Ticket,'subscriptions':Subscription}[resource]
 try:key=ident if resource=='scans' else int(ident)
 except ValueError:raise HTTPException(422,'Invalid record ID')
 row=db.get(model,key)
 if not row:raise HTTPException(404,'Record not found')
 if resource=='scans':
  if payload.title is None or payload.note is not None or payload.reference is not None:raise HTTPException(422,'Only the scan title can be edited.')
  row.name=payload.title
  if row.result_id:
   saved=db.get(DetectionRecord,row.result_id)
   if saved:
    saved.source_name=payload.title;result=json.loads(saved.result_json);result['source_name']=payload.title;saved.result_json=json.dumps(result)
 elif resource=='research':
  if payload.note is None or payload.title is not None or payload.reference is not None:raise HTTPException(422,'Only the review note can be edited. Predictions and original answers are immutable.')
  row.admin_note=payload.note
 elif resource=='support':
  if payload.reference is not None:raise HTTPException(422,'Invalid support fields')
  if payload.title is not None:row.subject=payload.title
  if payload.note is not None:row.message=payload.note
 else:
  if row.status!='pending':raise HTTPException(409,'Only pending subscription requests can be edited.')
  if payload.title is not None:raise HTTPException(422,'The subscription title is generated automatically.')
  if payload.note is not None:row.note=payload.note
  if payload.reference is not None:
   from .product import SubscriptionInput
   from ..product_models import PaymentReceipt
   import hashlib
   reference=payload.reference.upper()
   if db.get(PaymentReceipt,hashlib.sha256(reference.encode()).hexdigest()) or db.query(Subscription).filter(Subscription.id!=row.id,Subscription.reference==reference,Subscription.status.in_(['pending','approved'])).first():raise HTTPException(409,'This transaction ID has already been used.')
   row.reference=reference
 audit(db,actor.id,resource+'_record_updated',str(ident),{'fields':list(payload.model_fields_set)});db.commit();return {'ok':True}

class ConfirmDelete(BaseModel):confirm_id:str

@router.delete('/{resource}/{ident}')
def delete(resource:Resource,ident:str,payload:ConfirmDelete,actor=Depends(admin_user),db=Depends(get_db)):
 if payload.confirm_id!=ident:raise HTTPException(422,'Enter the record ID to confirm deletion.')
 if resource=='scans':
  row=db.get(Scan,ident)
  if not row:raise HTTPException(404,'Record not found')
  owner=db.get(User,row.user_id)
  audit(db,actor.id,'scan_deleted_by_admin',ident)
  return remove(ident,owner,db)
 try:key=int(ident)
 except ValueError:raise HTTPException(422,'Invalid record ID')
 model={'research':ResearchSubmission,'support':Ticket,'subscriptions':Subscription}[resource]
 row=db.get(model,key)
 if not row:raise HTTPException(404,'Record not found')
 if resource=='research':
  if db.query(TrainingJob).filter_by(status='running').first():raise HTTPException(409,'Wait for the current training job to finish before deleting research records.')
  db.query(LearningSample).filter_by(submission_id=key).delete(synchronize_session=False)
 audit(db,actor.id,resource+'_record_deleted',ident,{'user_id':row.user_id})
 db.delete(row);db.commit();return {'ok':True}
