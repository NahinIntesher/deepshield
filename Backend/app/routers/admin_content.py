"""Validated bilingual lessons and video-library management."""
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from pydantic import BaseModel,ConfigDict,Field,field_validator

from ..activity import audit
from ..config import DATA_ROOT
from ..database import get_db
from ..models.db_models import ResearchChallengeItem,CourseProgress,SoloTicket,Room
from ..product_models import Lesson
from ..security import admin_user,current_user
from ..services.scan_queue import lock
from ..services.upload_validation import validate_video
from ..data.sample_dataset import EXTENSIONS,seed_database

router=APIRouter(prefix='/api/admin/content',tags=['Content management'],dependencies=[Depends(admin_user)])
public=APIRouter(prefix='/api/profile',tags=['Lessons'],dependencies=[Depends(current_user)])

class LessonCopy(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    title:str=Field(min_length=2,max_length=160)
    time:str=Field(min_length=1,max_length=30)
    intro:str=Field(min_length=5,max_length=4000)
    sections:list[tuple[str,str]]=Field(min_length=1,max_length=8)
    flow:list[tuple[str,str]]=Field(min_length=3,max_length=3)
    question:str=Field(min_length=5,max_length=1000)
    choices:list[str]=Field(min_length=3,max_length=3)
    feedback:str=Field(min_length=5,max_length=2000)
    @field_validator('sections','flow')
    @classmethod
    def bounded_sections(cls,rows):
        for title,text in rows:
            if not title.strip() or not text.strip() or len(title)>200 or len(text)>4000:raise ValueError('Every section needs a heading (up to 200 characters) and text (up to 4000).')
        return [(title.strip(),text.strip()) for title,text in rows]
    @field_validator('choices')
    @classmethod
    def bounded_choices(cls,choices):
        if any(not c.strip() or len(c)>500 for c in choices):raise ValueError('Each quiz choice must have 1–500 characters.')
        return [c.strip() for c in choices]

class LessonPayload(BaseModel):
    en:LessonCopy
    bn:LessonCopy
    answer:int=Field(ge=0,le=2)
    archived:bool=False

def lesson_view(row,admin=False):
    result={'id':row.id,'en':json.loads(row.content_en),'bn':json.loads(row.content_bn),'archived':row.archived}
    if admin:result['answer']=row.correct_choice
    return result

def lesson_row(db,ident):
    row=db.get(Lesson,ident)
    if not row:raise HTTPException(404,'Lesson not found')
    return row

@public.get('/lessons')
def available_lessons(db=Depends(get_db)):
    return [lesson_view(r) for r in db.query(Lesson).filter_by(archived=False).order_by(Lesson.id)]

@router.get('/lessons')
def lessons(db=Depends(get_db)):return [lesson_view(r,True) for r in db.query(Lesson).order_by(Lesson.id)]

@router.post('/lessons',status_code=201)
def create_lesson(payload:LessonPayload,actor=Depends(admin_user),db=Depends(get_db)):
    row=Lesson(content_en=payload.en.model_dump_json(),content_bn=payload.bn.model_dump_json(),correct_choice=payload.answer,archived=payload.archived)
    db.add(row);db.flush();audit(db,actor.id,'lesson_created',str(row.id));db.commit();return lesson_view(row,True)

@router.put('/lessons/{ident}')
def update_lesson(ident:int,payload:LessonPayload,actor=Depends(admin_user),db=Depends(get_db)):
    row=lesson_row(db,ident);old=json.loads(row.content_en)
    quiz_changed=row.correct_choice!=payload.answer or old['question']!=payload.en.question or old['choices']!=payload.en.choices
    row.content_en=payload.en.model_dump_json();row.content_bn=payload.bn.model_dump_json();row.correct_choice=payload.answer;row.archived=payload.archived
    if quiz_changed:db.query(CourseProgress).filter_by(lesson_id=ident).update({'completed':False},synchronize_session=False)
    audit(db,actor.id,'lesson_updated',str(ident),{'quiz_changed':quiz_changed,'archived':row.archived});db.commit();return lesson_view(row,True)

@router.delete('/lessons/{ident}')
def archive_lesson(ident:int,actor=Depends(admin_user),db=Depends(get_db)):
    row=lesson_row(db,ident);row.archived=True;audit(db,actor.id,'lesson_archived',str(ident));db.commit();return {'ok':True}

class MediaMetadata(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True)
    title:str=Field(min_length=2,max_length=128)
    description:str=Field(default='',max_length=4000)
    ground_truth:Literal['Real','Fake']
    difficulty:Literal['Easy','Medium','Hard','Not rated']='Not rated'
    archived:bool=False

def media_view(r):return {'id':r.id,'title':r.title,'description':r.description or '', 'ground_truth':r.ground_truth,'difficulty':r.difficulty,'media_url':r.media_path,'archived':r.archived}

@router.get('/library')
def library(db=Depends(get_db)):
    seed_database(db)
    return [media_view(r) for r in db.query(ResearchChallengeItem).order_by(ResearchChallengeItem.id.desc())]

@router.post('/library',status_code=201)
def create_media(file:UploadFile=File(...),title:str=Form(...),ground_truth:Literal['Real','Fake']=Form(...),description:str=Form(''),difficulty:str=Form('Not rated'),actor=Depends(admin_user),db=Depends(get_db)):
    from pydantic import ValidationError
    try:metadata=MediaMetadata(title=title,ground_truth=ground_truth,description=description,difficulty=difficulty)
    except ValidationError:raise HTTPException(422,'Check the video title, label and difficulty.')
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in EXTENSIONS:raise HTTPException(415,'The game library accepts MP4, MOV, AVI, MKV or WebM videos.')
    folder=DATA_ROOT/'library'/ground_truth.lower();folder.mkdir(parents=True,exist_ok=True)
    path=folder/(secrets.token_hex(16)+suffix)
    try:
        size=0
        with path.open('wb') as out:
            while chunk:=file.file.read(1024*1024):
                size+=len(chunk)
                if size>250*1024*1024:raise HTTPException(413,'Maximum video size is 250 MiB.')
                out.write(chunk)
        validate_video(path)
        from ..services.media_store import persist
        persist(path)
        token=hashlib.sha256(('library/'+path.relative_to(DATA_ROOT/'library').as_posix()).encode()).hexdigest()[:24]
        row=ResearchChallengeItem(title=metadata.title,description=metadata.description,ground_truth=ground_truth,difficulty=metadata.difficulty,media_type='video',media_path='/api/media/'+token,manipulation_type='Not annotated',visual_cues='[]',archived=False)
        db.add(row);db.flush();audit(db,actor.id,'library_video_created',str(row.id));db.commit();return media_view(row)
    except Exception:db.rollback();path.unlink(missing_ok=True);raise
    finally:file.file.close()

@router.put('/library/{ident}')
def update_media(ident:int,payload:MediaMetadata,actor=Depends(admin_user),db=Depends(get_db)):
    with lock:
        row=db.get(ResearchChallengeItem,ident)
        if not row:raise HTTPException(404,'Video not found')
        if row.ground_truth!=payload.ground_truth:
            tickets=db.query(SoloTicket).filter(SoloTicket.item_id==ident,SoloTicket.used==False,SoloTicket.expires>time.time()).first()
            rooms=any(ident in json.loads(r.selected_items_json) for r in db.query(Room).filter(Room.status.in_(['waiting','playing','preparing'])))
            if tickets or rooms:raise HTTPException(409,'Finish active games before changing this video’s label.')
        before=row.ground_truth
        for key,value in payload.model_dump().items():setattr(row,key,value)
        audit(db,actor.id,'library_video_updated',str(ident),{'label_before':before,'label_after':row.ground_truth,'archived':row.archived});db.commit();return media_view(row)

@router.delete('/library/{ident}')
def archive_media(ident:int,actor=Depends(admin_user),db=Depends(get_db)):
    row=db.get(ResearchChallengeItem,ident)
    if not row:raise HTTPException(404,'Video not found')
    row.archived=True;audit(db,actor.id,'library_video_archived',str(ident));db.commit();return {'ok':True}
