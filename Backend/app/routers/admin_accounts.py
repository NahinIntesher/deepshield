"""Admin-only account CRUD. Owner identity and computed history are protected."""
import secrets
from pathlib import Path
from typing import Literal
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from ..activity import audit
from ..database import get_db
from ..models.db_models import (User,AuthSession,ResearchSubmission,GameSession,VideoAttempt,
    SoloTicket,LearningSample,GameRoundRecord,DetectionRecord,CourseProgress,AuditLog,TrainingJob,Room,RoomParticipant)
from ..models.schemas import UserResponse
from ..product_models import Scan,Charge,Membership,Subscription,ExtensionToken,Ticket,Notice,Assessment,GoogleIdentity
from ..security import admin_user
from ..services.scan_queue import lock,ROOT,delete_source
from .auth import _hash_password

router=APIRouter(prefix='/api/admin/users',tags=['Account management'],dependencies=[Depends(admin_user)])

class AccountFields(BaseModel):
    username:str=Field(min_length=2,max_length=50)
    display_name:str=Field(min_length=1,max_length=64)
    role:Literal['participant','researcher']='participant'
    @field_validator('username',mode='before')
    @classmethod
    def username_valid(cls,value):
        if not isinstance(value,str):return value
        value=value.strip().lower()
        if any(c.isspace() or ord(c)<32 for c in value):raise ValueError('Username cannot contain spaces or control characters.')
        return value
    @field_validator('display_name',mode='before')
    @classmethod
    def name_valid(cls,value):return value.strip() if isinstance(value,str) else value

class CreateAccount(AccountFields):
    password:str=Field(min_length=12,max_length=128)

class UpdateAccount(AccountFields):
    new_password:str|None=Field(default=None,min_length=12,max_length=128)

class DeleteAccount(BaseModel):
    confirm_username:str=Field(min_length=2,max_length=50)

def target(db,user_id):
    row=db.get(User,user_id)
    if not row:raise HTTPException(404,'Account not found')
    if row.role=='admin':raise HTTPException(403,'The owner administrator account cannot be edited or deleted.')
    return row

def revoke(db,user_id):
    db.query(AuthSession).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(ExtensionToken).filter_by(user_id=user_id).delete(synchronize_session=False)

@router.post('',response_model=UserResponse,status_code=201)
def create(payload:CreateAccount,actor=Depends(admin_user),db=Depends(get_db)):
    row=User(username=payload.username,display_name=payload.display_name,role=payload.role,password_hash=_hash_password(payload.password))
    db.add(row)
    try:
        db.flush();audit(db,actor.id,'account_created',str(row.id),{'role':row.role});db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'That username is already registered')
    return row

@router.get('/{user_id}',response_model=UserResponse)
def read(user_id:int,db=Depends(get_db)):
    row=db.get(User,user_id)
    if not row:raise HTTPException(404,'Account not found')
    return row

@router.patch('/{user_id}',response_model=UserResponse)
def update(user_id:int,payload:UpdateAccount,actor=Depends(admin_user),db=Depends(get_db)):
    row=target(db,user_id)
    before={'username':row.username,'display_name':row.display_name,'role':row.role}
    row.username=payload.username;row.display_name=payload.display_name;row.role=payload.role
    if payload.new_password is not None:row.password_hash=_hash_password(payload.new_password)
    # Renames and permission/password changes invalidate copied session credentials.
    revoke(db,row.id)
    try:
        db.flush();audit(db,actor.id,'account_updated',str(row.id),{'before':before,'after':{'username':row.username,'display_name':row.display_name,'role':row.role},'password_reset':payload.new_password is not None});db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'That username is already registered')
    return row

@router.delete('/{user_id}')
async def delete(user_id:int,payload:DeleteAccount,actor=Depends(admin_user),db=Depends(get_db)):
    with lock:
        row=target(db,user_id)
        if payload.confirm_username!=row.username:raise HTTPException(422,'Type the exact username to confirm deletion.')
        if db.query(Scan).filter(Scan.user_id==user_id,Scan.state.in_(['downloading','processing'])).first():raise HTTPException(409,'Wait for this account’s active scans to finish before deleting it.')
        active=db.query(RoomParticipant).join(Room,RoomParticipant.room_id==Room.id).filter(RoomParticipant.user_id==user_id,Room.status.in_(['playing','preparing'])).first()
        if active:raise HTTPException(409,'Wait for this account’s active multiplayer game to finish.')
        files=[SimpleNamespace(path=r.path) for r in db.query(Scan).filter_by(user_id=user_id)]
        hosted=list(db.query(Room).filter_by(host_user_id=user_id))
        room_ids=[r.id for r in hosted];room_codes=[r.room_code for r in hosted]
        submissions=db.query(ResearchSubmission.id).filter_by(user_id=user_id)
        db.query(LearningSample).filter(LearningSample.submission_id.in_(submissions)).delete(synchronize_session=False)
        db.query(LearningSample).filter_by(reviewer_id=user_id).update({'reviewer_id':None},synchronize_session=False)
        db.query(AuditLog).filter_by(actor_id=user_id).update({'actor_id':None},synchronize_session=False)
        db.query(TrainingJob).filter_by(actor_id=user_id).update({'actor_id':None},synchronize_session=False)
        if room_ids:db.query(RoomParticipant).filter(RoomParticipant.room_id.in_(room_ids)).delete(synchronize_session=False)
        db.query(RoomParticipant).filter_by(user_id=user_id).delete(synchronize_session=False)
        if room_ids:db.query(Room).filter(Room.id.in_(room_ids)).delete(synchronize_session=False)
        for model in (Scan,Charge,Membership,Subscription,ExtensionToken,Ticket,Notice,Assessment,GoogleIdentity,
                      AuthSession,VideoAttempt,SoloTicket,GameRoundRecord,DetectionRecord,CourseProgress,GameSession,ResearchSubmission):
            db.query(model).filter(model.user_id==user_id).delete(synchronize_session=False)
        audit(db,actor.id,'account_deleted',str(user_id),{'username':row.username,'role':row.role})
        db.query(User).filter_by(id=user_id).delete(synchronize_session=False)
        db.commit()
    # Files are removed only after the database transaction succeeds and only
    # inside the configured uploads directory. Audit/payment fingerprints remain.
    cleanup_pending=0
    for scan in files:
        if not scan.path:continue
        try:
            from ..services.media_store import local_path
            if not local_path(scan.path,fetch=False).resolve().is_relative_to(ROOT.resolve()):cleanup_pending+=1;continue
            delete_source(scan)
        except (OSError,RuntimeError,ValueError):cleanup_pending+=1
    from . import rooms
    for code in room_codes:
        task=rooms.tasks.pop(code,None)
        if task:task.cancel()
        for socket in list(rooms.sockets.pop(code,set())):
            try:await socket.close(code=4401)
            except RuntimeError:pass
    return {'ok':True,'cleanup_pending':cleanup_pending}
