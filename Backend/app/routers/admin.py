import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from ..activity import audit
from ..security import admin_user
from ..database import get_db
from ..models.db_models import User, LearningSample, ResearchSubmission, ResearchChallengeItem
from ..models.schemas import UserResponse
router=APIRouter(prefix="/api/admin",tags=["Administration"],dependencies=[Depends(admin_user)])

class Role(BaseModel):
    role:Literal["participant","researcher"]
class Review(BaseModel):
    decision:Literal["approved","rejected"]
    label:Literal["Real","Fake"]
    note:str=Field(min_length=5,max_length=1000)

@router.get("/users",response_model=list[UserResponse])
def users(db=Depends(get_db)):
    from ..security import qualify
    rows=db.query(User).order_by(User.created_at.desc()).all()
    for user in rows: qualify(db,user)
    db.commit()
    return rows

@router.patch("/users/{user_id}/role",response_model=UserResponse)
def role(user_id:int,payload:Role,actor=Depends(admin_user),db=Depends(get_db)):
    user=db.get(User,user_id)
    if not user: raise HTTPException(404,"User not found")
    if user.role=="admin":
        raise HTTPException(403,"The owner administrator role cannot be changed")
    previous=user.role
    user.role=payload.role
    audit(db,actor.id,"role_changed",str(user_id),{"before":previous,"after":payload.role})
    db.commit();return user

@router.get("/learning")
def learning(db=Depends(get_db)):
    from ..services.continual import status
    rows=db.query(LearningSample).order_by(LearningSample.id.desc()).all()
    return {"training":status(),"samples":[{"id":r.id,"submission_id":r.submission_id,"item_id":r.item_id,"media_url":db.get(ResearchChallengeItem,r.item_id).media_path,"status":r.status,"label":r.verified_label,"note":r.note,"human_prediction":db.get(ResearchSubmission,r.submission_id).human_prediction} for r in rows]}

@router.post("/learning/{sample_id}/review")
def review(sample_id:int,payload:Review,actor=Depends(admin_user),db=Depends(get_db)):
    row=db.get(LearningSample,sample_id)
    if not row: raise HTTPException(404,"Sample not found")
    if row.status!="pending": raise HTTPException(409,"Sample already reviewed")
    row.status=payload.decision;row.verified_label=payload.label;row.note=payload.note;row.reviewer_id=actor.id;row.reviewed_at=datetime.datetime.utcnow()
    audit(db,actor.id,"sample_reviewed",str(row.id),{"decision":payload.decision,"label":payload.label})
    db.commit()
    from ..services.continual import MANIFEST, start
    import os
    if payload.decision=="approved" and MANIFEST.is_file() and os.getenv("AUTO_CONTINUAL_LEARNING","true").lower()=="true":
        try: start(actor.id)
        except ValueError: pass
    return {"ok":True}

@router.post("/learning/train")
def train(actor=Depends(admin_user)):
    from ..services.continual import start
    try: return start(actor.id)
    except ValueError as exc: raise HTTPException(409,str(exc))
