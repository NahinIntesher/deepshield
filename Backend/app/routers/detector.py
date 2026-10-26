from ..security import current_user
from fastapi import Depends
import tempfile, json
from ..models.db_models import DetectionRecord
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..data.sample_dataset import available_items, video_index, item_path, EXTENSIONS
from ..models.schemas import DetectionResult
from ..services.inference import analyze_video
from ..services.browser_media import browser_video

router = APIRouter(dependencies=[Depends(current_user)], prefix='/api', tags=['Video detection'])

@router.get('/detector/service')
def detector_service():
    from ..services.remote_inference import enabled
    return {'remote_processing':enabled(),'processor':'Hugging Face private Space' if enabled() else 'DeepShield server',
            'temporary_remote_media':enabled(),'max_video_bytes':50_000_000,'max_image_bytes':20*1024*1024}

@router.get('/media/{token}')
@router.head('/media/{token}')
def serve_video(token: str, request: Request):
    entry = video_index().get(token)
    if entry is None:
        raise HTTPException(404, 'Video not found')
    try:
        from ..services.media_playback import playback_response
        return playback_response(entry[0], request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, 'Could not prepare video playback. Check FFmpeg and the source file.') from exc

@router.get('/detector/presets')
def get_presets(db: Session = Depends(get_db)):
    return [{'id':str(i.id), 'title':i.title, 'category':'Local video', 'thumbnail':i.media_path} for i in available_items(db)]

@router.post('/detector/analyze-preset/{sample_id}', response_model=DetectionResult)
def analyze_preset(sample_id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    item = next((i for i in available_items(db) if i.id == sample_id), None)
    if item is None:
        raise HTTPException(404, 'Video not found')
    return save_detection(db,user,item.title,analyze_video(item_path(item)))

@router.post('/detector/upload', response_model=DetectionResult)
def upload_and_detect(file: UploadFile = File(...), user=Depends(current_user),db=Depends(get_db)):
    from .product import upload
    from ..product_models import Scan
    import time
    job=upload(file,user,db)
    for _ in range(2400):
        db.expire_all();row=db.get(Scan,job['id'])
        if row.state=='completed':return json.loads(db.get(DetectionRecord,row.result_id).result_json)
        if row.state=='failed':raise HTTPException(503,row.message)
        time.sleep(.1)
    raise HTTPException(504,'Check your scan history: the analysis is still pending.')



def save_detection(db,user,name,result):
    row=DetectionRecord(user_id=user.id,source_name=name,verdict=result['verdict'],confidence=result['confidence_percentage'],model_id=result.get('model_id'),result_json=json.dumps(result))
    db.add(row);db.flush();result={**result,'detection_id':row.id};row.result_json=json.dumps(result);db.commit()
    return result
