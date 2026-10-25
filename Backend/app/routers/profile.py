import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..database import get_db
from ..security import current_user, qualify
from ..models.db_models import GameRoundRecord, DetectionRecord, CourseProgress, ResearchSubmission
from ..config import QUALIFICATION_MIN_SCORE, QUALIFICATION_ACCURACY_THRESHOLD
router=APIRouter(prefix='/api/profile',tags=['Member history'])
# Stable course IDs 0..11. Content is frontend-owned; answers are verified here.
ANSWERS=[1,1,2,0,1,0,2,1,0,2,1,0]

@router.get('')
def profile(user=Depends(current_user),db=Depends(get_db)):
    qualify(db,user);db.commit()
    from ..product_models import Lesson
    active_lessons={r.id for r in db.query(Lesson).filter_by(archived=False)}
    progress=db.query(CourseProgress).filter_by(user_id=user.id).all()
    rounds=db.query(GameRoundRecord).filter_by(user_id=user.id).order_by(GameRoundRecord.id.desc()).limit(100).all()
    detections=db.query(DetectionRecord).filter_by(user_id=user.id).order_by(DetectionRecord.id.desc()).limit(50).all()
    research=db.query(ResearchSubmission).filter_by(user_id=user.id).order_by(ResearchSubmission.id.desc()).limit(50).all()
    return {'user':{'id':user.id,'display_name':user.display_name,'username':user.username,'role':user.role,'created_at':user.created_at,'score':user.score,'accuracy':user.accuracy,'rounds':user.total_rounds_played,'games':user.games_played,'qualified':user.qualified_for_research},'requirements':{'accuracy':QUALIFICATION_ACCURACY_THRESHOLD*100,'score':QUALIFICATION_MIN_SCORE},'totals':{'detections':db.query(DetectionRecord).filter_by(user_id=user.id).count(),'research':db.query(ResearchSubmission).filter_by(user_id=user.id).count(),'lessons':sum(bool(p.completed) and p.lesson_id in active_lessons for p in progress),'lesson_count':len(active_lessons)},'course':[{'lesson_id':p.lesson_id,'completed':p.completed,'attempts':p.attempts,'updated_at':p.updated_at} for p in progress],'rounds':[{'id':r.id,'mode':r.mode,'prediction':r.prediction,'ground_truth':r.ground_truth,'correct':r.correct,'points':r.points,'response_ms':r.response_ms,'created_at':r.created_at} for r in rounds],'detections':[{'id':r.id,'source_name':r.source_name,'verdict':r.verdict,'confidence':r.confidence,'model_id':r.model_id,'created_at':r.created_at} for r in detections],'research':[{'id':r.id,'prediction':r.human_prediction,'ai_prediction':r.ai_prediction,'correct':r.is_human_correct,'quadrant':r.disagreement_quadrant,'created_at':r.created_at} for r in research]}

@router.get('/course')
def course(user=Depends(current_user),db=Depends(get_db)):
    return [{'lesson_id':p.lesson_id,'completed':p.completed,'attempts':p.attempts} for p in db.query(CourseProgress).filter_by(user_id=user.id)]
class LessonAnswer(BaseModel):
    choice:int=Field(ge=0,le=2)
@router.post('/course/{lesson_id}')
def answer(lesson_id:int,payload:LessonAnswer,user=Depends(current_user),db=Depends(get_db)):
    from ..product_models import Lesson
    lesson=db.get(Lesson,lesson_id)
    if not lesson or lesson.archived:raise HTTPException(404,'Lesson not found')
    key=f'{user.id}:{lesson_id}'
    row=db.get(CourseProgress,key)
    if row is None:
        row=CourseProgress(key=key,user_id=user.id,lesson_id=lesson_id,attempts=0,completed=False,last_choice=payload.choice);db.add(row)
    correct=payload.choice==lesson.correct_choice
    row.attempts+=1;row.last_choice=payload.choice;row.completed=row.completed or correct
    db.commit()
    return {'completed':row.completed,'correct':correct,'attempts':row.attempts}

@router.get('/detections/{record_id}')
def detection(record_id:int,user=Depends(current_user),db=Depends(get_db)):
    row=db.get(DetectionRecord,record_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,'Detection not found')
    return json.loads(row.result_json)
@router.delete('/detections/{record_id}')
def delete_detection(record_id:int,user=Depends(current_user),db=Depends(get_db)):
    row=db.get(DetectionRecord,record_id)
    if not row or row.user_id!=user.id:raise HTTPException(404,'Detection not found')
    from ..product_models import Scan
    from ..services.scan_queue import delete_source
    for scan in db.query(Scan).filter_by(result_id=row.id,user_id=user.id):
        delete_source(scan);db.delete(scan)
    db.flush()
    db.delete(row);db.commit();return {'ok':True}
