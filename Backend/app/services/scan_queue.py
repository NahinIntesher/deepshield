import datetime as dt,hashlib,json,secrets,threading,os,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from ..config import BASE_DIR,DATA_ROOT,CHECKPOINT_PATH
from ..database import SessionLocal
from ..product_models import Scan,Charge,Membership,Notice
from ..models.db_models import DetectionRecord
from .inference import analyze_video
from .links import retrieve
from .upload_validation import IMAGE_EXTENSIONS
from . import remote_inference
from . import media_store
ROOT=DATA_ROOT/'uploads';ROOT.mkdir(parents=True,exist_ok=True)
lock=threading.RLock()
executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='detector')
def now():return dt.datetime.utcnow()
def limits():return int(os.getenv('FREE_DAILY_SCANS','10')),int(os.getenv('PREMIUM_DAILY_SCANS','100'))
def membership(db,uid):
 row=db.get(Membership,uid);premium=bool(row and row.expires and row.expires>now());free,paid=limits()
 used=db.query(Charge).filter(Charge.user_id==uid,Charge.charged==True,Charge.created_at>=now().replace(hour=0,minute=0,second=0,microsecond=0)).count()
 return {'plan':'premium' if premium else 'free','used':used,'limit':paid if premium else free,'free_limit':free,'premium_limit':paid,'expires':row.expires if premium else None,'activation':row.activation if premium else 'none'}
def notify(db,uid,title,message):db.add(Notice(user_id=uid,title=title,message=message))
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def view(row):return {'id':row.id,'source':row.source,'source_name':row.name,'media_type':'image' if row.path and Path(row.path).suffix.lower() in IMAGE_EXTENSIONS else 'video','state':row.state,'message':row.message,'result_id':row.result_id,'created_at':row.created_at}
def enqueue(db,user,source,name,url=None,path=None):
 with lock:
  stat=CHECKPOINT_PATH.stat() if CHECKPOINT_PATH.is_file() else None
  signature=remote_inference.expected_id() if remote_inference.enabled() else (stat.st_size,stat.st_mtime_ns) if stat else 'missing'
  key=hashlib.sha256((str(user.id)+str(url or digest(path))+str(signature)).encode()).hexdigest()
  old=db.query(Scan).filter(Scan.cache_key==key,Scan.created_at>now()-dt.timedelta(hours=1),Scan.state.in_(['queued','downloading','processing','completed'])).first()
  if old:
   if path:Path(path).unlink(missing_ok=True)
   return view(old)
  info=membership(db,user.id)
  if info['used']>=info['limit']:raise HTTPException(429,'Daily allowance used. It resets at 00:00 UTC.')
  pending=db.query(Scan).filter(Scan.state.in_(['queued','downloading','processing']))
  if pending.count()>=int(os.getenv('MAX_PENDING_SCANS','12')):raise HTTPException(503,'The scan queue is full. Try again shortly.')
  if pending.filter(Scan.user_id==user.id).count()>=3:raise HTTPException(429,'Wait for one of your pending scans to finish.')
  if path:media_store.persist(path)
  row=Scan(id=secrets.token_hex(16),user_id=user.id,name=name[:256],source=source,url=url,path=media_store.reference(path) if path else None,cache_key=key,state='queued')
  db.add(row);db.add(Charge(id=row.id,user_id=user.id));db.commit();db.refresh(row);result=view(row);executor.submit(run,row.id);return result
def run(job_id):
 with SessionLocal() as db:
  with lock:
   row=db.get(Scan,job_id)
   if not row or row.state!='queued':return
   row.state='downloading' if row.url else 'processing';db.commit()
  try:
   if not remote_inference.enabled() and not CHECKPOINT_PATH.is_file():raise RuntimeError('Place your trained best_model.pth in the project model folder before running detection.')
   if row.url:
    folder=ROOT/row.id;folder.mkdir(exist_ok=True);path=retrieve(row.url,folder);media_store.persist(path);row.path=media_store.reference(path)
   else:path=media_store.local_path(row.path)
   row.state='processing';row.message='Analyzing one face as a repeated still image (experimental)' if path.suffix.lower() in IMAGE_EXTENSIONS else 'Sampling 16 face frames and running the trained model';db.commit()
   result=analyze_video(path)
   record=DetectionRecord(user_id=row.user_id,source_name=row.name,verdict=result['verdict'],confidence=result['confidence_percentage'],model_id=result.get('model_id'),result_json='{}');db.add(record);db.flush()
   result.update(detection_id=record.id,source_name=row.name);record.result_json=json.dumps(result);row.result_id=record.id;row.state='completed';row.message='Analysis ready';notify(db,row.user_id,'Analysis ready',row.name+' — '+result['verdict']+' (model prediction)');db.commit()
  except Exception as exc:
   db.rollback();row=db.get(Scan,job_id);row.state='failed';row.message=str(exc.detail if isinstance(exc,HTTPException) else exc)[:600]
   charge=db.get(Charge,job_id)
   if charge:charge.charged=False
   if row.path:
    try:media_store.remove(row.path)
    except (RuntimeError,OSError,ValueError):pass
   shutil.rmtree(ROOT/job_id,ignore_errors=True);notify(db,row.user_id,'File could not be analyzed',row.message);db.commit()
def recover():
 with SessionLocal() as db:
  for row in db.query(Scan).filter(Scan.state.in_(['processing','downloading'])):
   row.state='failed';row.message='Server restarted. Please submit again.'
   charge=db.get(Charge,row.id)
   if charge:charge.charged=False
   if row.path:
    try:media_store.remove(row.path)
    except (RuntimeError,OSError,ValueError):pass
  db.commit()
  for row in db.query(Scan).filter_by(state='queued'):executor.submit(run,row.id)
def delete_source(row):
 if not row.path:return
 path=media_store.local_path(row.path,fetch=False)
 if path.is_file():
  stat=path.stat();key=hashlib.sha256(f'{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:h264-v1'.encode()).hexdigest()
  (DATA_ROOT/'browser_media'/f'{key}.mp4').unlink(missing_ok=True)
 media_store.remove(row.path)
