"""Reviewed-sample replay adaptation. Never overwrites or auto-promotes the locked baseline.
The manifest must contain independently curated training/holdout videos, not Celeb-DF or WildDeepfake.
"""
import json, os, threading, time, hashlib, traceback
from pathlib import Path
from ..config import DATA_ROOT
ROOT=DATA_ROOT/'continual'
MANIFEST=Path(os.getenv('REPLAY_MANIFEST',str(ROOT/'replay_manifest.json')))
_guard=threading.Lock()
_state={"state":"idle","message":"Configure replay memory and review research samples before training."}

def status():
    with _guard:
        result=dict(_state)
    result['manifest_ready']=MANIFEST.is_file()
    result['readiness']=readiness()
    report=ROOT/'latest_report.json'
    if report.exists():
        try: result['last_report']=json.loads(report.read_text())
        except (ValueError,OSError): pass
    return result


def readiness():
    from ..database import SessionLocal
    from ..models.db_models import LearningSample
    from ..config import CHECKPOINT_PATH
    with SessionLocal() as db:
        approved=db.query(LearningSample).filter_by(status='approved').count()
    problems=[]
    counts={split:0 for split in ('replay','retention','new_validation')}
    if not CHECKPOINT_PATH.is_file():problems.append('The trained baseline checkpoint is missing.')
    if not approved:problems.append('No reviewed research samples have been approved.')
    if not MANIFEST.is_file():problems.append('Replay memory is not configured. Add a curated replay_manifest.json with old training and separate holdout videos.')
    else:
        try:
            manifest=json.loads(MANIFEST.read_text(encoding='utf8'))
            rows=manifest.get('samples',[])
            if not isinstance(rows,list):raise ValueError()
            for split in counts:
                chosen=[r for r in rows if r.get('split')==split]
                counts[split]=len(chosen)
                if {r.get('label') for r in chosen}!={'Real','Fake'}:problems.append(split+' needs both Real and Fake videos.')
            for row in rows:
                if row.get('split') not in counts or row.get('dataset') not in ('FaceForensics++','consented_collection') or row.get('label') not in ('Real','Fake'):
                    problems.append('Replay entries must use allowed training data, valid splits and verified labels.');break
                path=Path(row['path']).expanduser()
                if not path.is_absolute():path=MANIFEST.parent/path
                if not path.is_file():problems.append('One or more replay/holdout video files are missing.');break
        except (ValueError,TypeError,KeyError,OSError,AttributeError):problems.append('The replay manifest is not valid. Check the example and setup guide.')
    return {'ready':not problems,'approved_samples':approved,'manifest_configured':MANIFEST.is_file(),'checkpoint_present':CHECKPOINT_PATH.is_file(),'split_counts':counts,'problems':problems}

def start(actor_id=None):
    with _guard:
        if _state['state']=='running': raise ValueError('A training job is already running')
        checks=readiness()
        if not checks['ready']:raise ValueError(' '.join(checks['problems']))
        _state.update(state='running',message='Validating reviewed samples and replay memory')
        from ..database import SessionLocal
        from ..models.db_models import TrainingJob
        from ..activity import audit
        with SessionLocal() as db:
            job=TrainingJob(actor_id=actor_id,status='running',message='Preparing replay memory')
            db.add(job);db.flush();job_id=job.id
            audit(db,actor_id,'training_started',str(job_id));db.commit()
        threading.Thread(target=_run,args=(job_id,),daemon=True).start()
    return status()

def update(message):
    with _guard: _state['message']=message

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _run(job_id):
    try:
        result=train_candidate()
        ROOT.mkdir(parents=True,exist_ok=True)
        tmp=ROOT/'latest_report.tmp'
        tmp.write_text(json.dumps(result,indent=2));tmp.replace(ROOT/'latest_report.json')
        finish(job_id,'completed','Candidate evaluated; baseline unchanged.',result)
        with _guard: _state.update(state='completed',message='Candidate evaluated. Baseline remains unchanged.')
    except Exception as exc:
        finish(job_id,'failed',str(exc))
        with _guard: _state.update(state='failed',message=str(exc))
        ROOT.mkdir(parents=True,exist_ok=True)
        (ROOT/'last_error.log').write_text(traceback.format_exc())

def train_candidate():
    import random, copy
    import torch
    import torch.nn.functional as F
    from ..database import SessionLocal
    from ..models.db_models import LearningSample, ResearchChallengeItem
    from ..data.sample_dataset import item_path
    from .model_manager import classify_features
    from .runtime import model_manager
    from .video_processor import video_processor
    manifest=json.loads(MANIFEST.read_text())
    rows=manifest.get('samples',[])
    required={'replay','retention','new_validation'}
    for r in rows:
        if r.get('split') not in required: raise ValueError('Unknown manifest split')
        if r.get('dataset') not in ('FaceForensics++','consented_collection'):
            raise ValueError('Only FF++ training partitions or a consented collection are allowed. Celeb-DF and WildDeepfake stay held out.')
        if r.get('label') not in ('Real','Fake'): raise ValueError('Every replay sample needs a verified Real/Fake label')
    for split in required:
        if {r['label'] for r in rows if r['split']==split}!={'Real','Fake'}:
            raise ValueError(f'{split} requires both Real and Fake videos')
    with SessionLocal() as db:
        approved=db.query(LearningSample).filter_by(status='approved').all()
        for r in approved:
            rows.append({'path':str(item_path(db.get(ResearchChallengeItem,r.item_id))),'label':r.verified_label,'split':'new','submission_id':r.submission_id})
    if not approved: raise ValueError('No reviewed research samples have been approved')
    seen={};clean=[]
    for r in rows:
        path=Path(r['path']).expanduser()
        if not path.is_absolute(): path=MANIFEST.parent/path
        if not path.is_file(): raise ValueError(f'Missing memory video: {path}')
        key=digest(path)
        if key in seen:
            old=seen[key]
            if old['label']!=r['label'] or old['split']!=r['split']:
                raise ValueError('Duplicate video has conflicting labels or crosses training/holdout splits')
            continue
        r={**r,'path':path,'sha256':key};seen[key]=r;clean.append(r)
    # This lock bounds GPU use on 6 GB cards. Incoming analysis waits for training.
    with model_manager.lock:
        model_manager.ensure_loaded()
        baseline=model_manager.model
        device=model_manager.device
        seed=manifest.get('seed',42);random.seed(seed);torch.manual_seed(seed)
        features=[]
        for index,r in enumerate(clean):
            update(f'Extracting aligned features {index+1}/{len(clean)}')
            prepared=video_processor.prepare(r['path'])
            x=torch.from_numpy(prepared.tensors).to(device)
            with torch.no_grad():
                rgb=torch.cat([baseline.rgb(f[None]) for f in x]).unsqueeze(0).cpu()
                freq=torch.cat([baseline.freq(f[None]) for f in x]).unsqueeze(0).cpu()
                teacher=classify_features(baseline,rgb.to(device),freq.to(device))[0].cpu()
            features.append({**r,'rgb':rgb,'freq':freq,'teacher':teacher})
        # Copy only adaptation head; the feature encoders stay frozen and unchanged.
        class Head(torch.nn.Module):
            def __init__(self):
                super().__init__()
                for name in ('rgb_proj','temporal','fusion','cls'): setattr(self,name,copy.deepcopy(getattr(baseline,name)))
                self.pos=torch.nn.Parameter(baseline.pos.detach().clone())
            def forward(self,r,f): return classify_features(self,r,f)[0]
        head=Head().to(device)
        for param in head.parameters(): param.requires_grad_(True)
        optimizer=torch.optim.AdamW(head.parameters(),lr=float(manifest.get('learning_rate',1e-5)),weight_decay=.01)
        def accuracy(module,split):
            module.eval();correct=0;count=0
            with torch.no_grad():
                for r in features:
                    if r['split']!=split: continue
                    output=classify_features(module,r['rgb'].to(device),r['freq'].to(device))[0]
                    correct+=int(output.argmax(1).item()==int(r['label']=='Fake'));count+=1
            return correct/count
        old_before=accuracy(baseline,'retention');new_before=accuracy(baseline,'new_validation')
        replay=[r for r in features if r['split']=='replay'];new=[r for r in features if r['split']=='new']
        for epoch in range(min(10,max(1,int(manifest.get('epochs',3))))):
            update(f'Training candidate epoch {epoch+1}: balanced old/new replay and distillation')
            pairs=list(new);random.shuffle(pairs);head.train()
            for new_row in pairs:
                optimizer.zero_grad()
                # Equal weighting of one old and one new video, independent of set sizes.
                for r in (new_row,random.choice(replay)):
                    logits=head(r['rgb'].to(device),r['freq'].to(device))
                    target=torch.tensor([int(r['label']=='Fake')],device=device)
                    loss=F.cross_entropy(logits,target)
                    if r['split']=='replay':
                        loss+=F.kl_div(F.log_softmax(logits/2,dim=1),F.softmax(r['teacher'].to(device)/2,dim=1),reduction='batchmean')*4
                    (loss/2).backward()
                torch.nn.utils.clip_grad_norm_(head.parameters(),1.0);optimizer.step()
        old_after=accuracy(head,'retention');new_after=accuracy(head,'new_validation')
        tolerance=float(manifest.get('max_retention_drop',.02))
        passed=old_after>=old_before-tolerance and new_after>=new_before
        report={'created_at':time.time(),'baseline_sha256':model_manager.checkpoint_sha256,'retention_before':old_before,'retention_after':old_after,'new_before':new_before,'new_after':new_after,'max_retention_drop':tolerance,'passed':passed,'promoted':False,'method':'Frozen RGB/DCT encoders; replay plus teacher distillation; train projection, temporal, fusion and classifier','samples':[{'sha256':r['sha256'],'split':r['split'],'label':r['label']} for r in features]}
        candidate={k:v.detach().cpu() for k,v in baseline.state_dict().items()}
        candidate.update({k:v.detach().cpu() for k,v in head.state_dict().items()})
        folder=ROOT/'candidates';folder.mkdir(parents=True,exist_ok=True)
        name=f'candidate_{time.time_ns()}.pth'
        temp=folder/(name+'.tmp')
        torch.save({'model':candidate,'epoch':model_manager.checkpoint_epoch,'continual_report':report},temp)
        temp.replace(folder/name)
        report['candidate']=str(folder/name)
        return report


def finish(job_id,status,message,report=None):
    import datetime
    from ..database import SessionLocal
    from ..models.db_models import TrainingJob
    with SessionLocal() as db:
        row=db.get(TrainingJob,job_id)
        if row:
            row.status=status;row.message=message;row.finished_at=datetime.datetime.utcnow()
            row.report_json=json.dumps(report) if report else None
            db.commit()
