"""Compatibility endpoints for the Professional backend only. No alternate prediction logic."""
import json,time
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from ..database import get_db
from ..security import current_user,admin_user
from ..product_models import Scan,Subscription
from ..models.db_models import DetectionRecord,User
from . import product
router=APIRouter(tags=['Mobile compatibility'])
@router.get('/api/integrations/subscription')
def subscription(user=Depends(current_user),db=Depends(get_db)):
 v=product.billing(user,db);pending=next((r for r in v['requests'] if r['status']=='pending'),None)
 return {**v,'status':'active' if v['plan']=='premium' else 'pending' if pending else 'active','used_today':v['used'],'remaining':max(0,v['limit']-v['used']),'expires_at':v['expires']}
class PlanRequest(BaseModel):
 reference:str=Field(default='',max_length=160)
 note:str=Field(default='Please activate Premium for my mobile account.',min_length=5,max_length=1000)
@router.post('/api/integrations/subscription/request')
def subscribe(payload:PlanRequest,user=Depends(current_user),db=Depends(get_db)):
 v=product.subscribe(product.SubscriptionInput(**payload.model_dump()),user,db)
 return {**v,'message':'Your Premium request is awaiting administrator review.'}
@router.get('/api/admin/subscriptions',dependencies=[Depends(admin_user)])
def subscriptions(db=Depends(get_db)):
 return [{'request_id':r.id,'user_id':r.user_id,'username':db.get(User,r.user_id).username,'plan':'premium','status':r.status} for r in db.query(Subscription).order_by(Subscription.id.desc()).limit(100)]
class Decision(BaseModel):
 action:str
 days:int=30
@router.post('/api/admin/subscriptions/{user_id}')
def review(user_id:int,payload:Decision,admin=Depends(admin_user),db=Depends(get_db)):
 row=db.query(Subscription).filter_by(user_id=user_id,status='pending').order_by(Subscription.id.desc()).first()
 if not row:raise HTTPException(409,'No pending request. Refresh this list.')
 if payload.action not in ('activate','reject'):raise HTTPException(422,'Use activate or reject for pending requests.')
 return product.review(row.id,product.ReviewInput(decision='approved' if payload.action=='activate' else 'rejected',note='Reviewed from the mobile admin console.'),admin,db)
