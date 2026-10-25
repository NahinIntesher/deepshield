"""All aggregates below come from stored events; empty collections remain empty/zero."""
import datetime, json
from collections import Counter
from fastapi import APIRouter, Depends, Query
from ..database import get_db
from ..security import admin_user, qualify
from ..models.db_models import User, GameRoundRecord, DetectionRecord, CourseProgress, ResearchSubmission, AuditLog, TrainingJob, LearningSample
from ..services.metrics_calc import metrics_calculator
from ..product_models import Lesson
router=APIRouter(prefix='/api/admin',tags=['Live administration analytics'],dependencies=[Depends(admin_user)])

@router.get('/analytics')
def analytics(days:int=Query(14,ge=7,le=90),db=Depends(get_db)):
    now=datetime.datetime.utcnow();since=now.replace(hour=0,minute=0,second=0,microsecond=0)-datetime.timedelta(days=days-1)
    users=db.query(User).all()
    for u in users:qualify(db,u)
    db.commit()
    rounds=db.query(GameRoundRecord).filter(GameRoundRecord.created_at>=since).all()
    detections=db.query(DetectionRecord).filter(DetectionRecord.created_at>=since).all()
    research=db.query(ResearchSubmission).filter(ResearchSubmission.created_at>=since).all()
    progress=db.query(CourseProgress).all()
    active={r.user_id for rows in (rounds,detections,research) for r in rows}|{p.user_id for p in progress if p.updated_at and p.updated_at>=since}
    daykeys=[(since+datetime.timedelta(days=i)).date().isoformat() for i in range(days)]
    counts={name:Counter(r.created_at.date().isoformat() for r in rows) for name,rows in [('rounds',rounds),('detections',detections),('research',research)]}
    daily=[{'date':day,**{k:v.get(day,0) for k,v in counts.items()}} for day in daykeys]
    bands={'Not played':0,'Below 70%':0,'70–89%':0,'90% and above':0}
    for u in users:
        if u.role=='admin':continue
        band='Not played' if not u.total_rounds_played else '90% and above' if u.accuracy>=90 else '70–89%' if u.accuracy>=70 else 'Below 70%'
        bands[band]+=1
    total=sum(u.total_rounds_played for u in users if u.role!='admin');correct=sum(u.total_correct for u in users if u.role!='admin')
    return {'generated_at':now,'days':days,'timezone':'UTC','summary':{'members':sum(u.role!='admin' for u in users),'active':len(active),'qualified':sum(u.qualified_for_research and u.role!='admin' for u in users),'accuracy':round(100*correct/total,1) if total else None,'rounds':db.query(GameRoundRecord).count(),'detections':db.query(DetectionRecord).count(),'research':db.query(ResearchSubmission).count(),'pending_reviews':db.query(LearningSample).filter_by(status='pending').count()},'daily':daily,'accuracy_bands':[{'label':k,'value':v} for k,v in bands.items()],'roles':[{'label':role,'value':sum(u.role==role for u in users)} for role in ('participant','researcher','admin')],'verdicts':[{'label':label,'value':sum(r.verdict==label for r in detections)} for label in ('Real','Fake')],'course':[{'lesson':i+1,'completed':sum(p.lesson_id==i and p.completed for p in progress),'attempts':sum(p.attempts for p in progress if p.lesson_id==i)} for i in [r.id for r in db.query(Lesson).filter_by(archived=False).order_by(Lesson.id)]],'research_metrics':metrics_calculator.calculate_kpis(research),'top_members':[{'id':u.id,'name':u.display_name,'score':u.score,'accuracy':u.accuracy,'qualified':u.qualified_for_research} for u in sorted([u for u in users if u.role!='admin'],key=lambda u:-u.score)[:8]]}

@router.get('/audit')
def audit(limit:int=Query(50,ge=1,le=200),db=Depends(get_db)):
    users={u.id:u.display_name for u in db.query(User)}
    return [{'id':r.id,'actor':users.get(r.actor_id,'System'),'action':r.action,'target':r.target,'detail':json.loads(r.detail or '{}'),'created_at':r.created_at} for r in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit)]

@router.get('/training-jobs')
def jobs(db=Depends(get_db)):
    return [{'id':r.id,'status':r.status,'message':r.message,'report':json.loads(r.report_json) if r.report_json else None,'created_at':r.created_at,'finished_at':r.finished_at} for r in db.query(TrainingJob).order_by(TrainingJob.id.desc()).limit(50)]
