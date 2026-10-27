"""Authenticated calls to the owner's private ZeroGPU inference Space."""
import math
import os
from pathlib import Path
import threading

EXPECTED_CHECKPOINT='be33edbb69a80072439b8ea361ee9b00f635a2604ea2a4b9c1bfabe731067b7e'
_client=None
_lock=threading.RLock()
_verified=False
_last_error=None

def enabled():return bool(os.getenv('MODEL_SPACE_ID','').strip())
def expected_id():return os.getenv('MODEL_CHECKPOINT_SHA256',EXPECTED_CHECKPOINT).strip()
def status():
    return {'configured':enabled(),'backend':'private Hugging Face ZeroGPU' if enabled() else 'local',
            'last_prediction_verified':_verified,'last_error':_last_error,'model_id':expected_id() if _verified else None}

def analyze(path,explain=True):
    global _client,_verified,_last_error
    path=Path(path)
    if not path.is_file():raise ValueError('Uploaded media is no longer available. Submit it again.')
    token=os.getenv('MODEL_SPACE_TOKEN','').strip()
    if not enabled() or not token:raise RuntimeError('Online model connection has not been configured.')
    with _lock:
        job=None
        try:
            from gradio_client import Client,handle_file
            if _client is None:
                _client=Client(os.environ['MODEL_SPACE_ID'].strip(),token=token,verbose=False,
                               max_workers=1,httpx_kwargs={'timeout':180},analytics_enabled=False)
            job=_client.submit(handle_file(str(path)),bool(explain),api_name='/predict')
            result=job.result(timeout=360 if explain else 180)
            if not isinstance(result,dict) or result.get('model_id')!=expected_id():
                raise RuntimeError('Online detector checkpoint verification failed.')
            for field in ('confidence_percentage','fake_probability'):
                value=result.get(field)
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise RuntimeError('Online detector returned an invalid result.')
            if not 0<=result['confidence_percentage']<=100 or not 0<=result['fake_probability']<=1:
                raise RuntimeError('Online detector returned an invalid result.')
            from ..models.schemas import DetectionResult
            DetectionResult.model_validate(result)
            if result.get('verdict') not in ('Real','Fake') or result.get('model_checkpoint_loaded') is not True:
                raise RuntimeError('Online detector returned an invalid result.')
            _verified=True;_last_error=None
            return result
        except Exception as exc:
            if isinstance(exc,TimeoutError) and job is not None:
                try:job.cancel()
                except Exception:pass
            _client=None
            text=str(exc).lower()
            if 'quota' in text or 'gpu time' in text:
                message='Online GPU allowance is currently exhausted. Try again after the hosting quota resets.'
            elif 'alignable face' in text or 'no face' in text:
                _last_error='No alignable face found in this media.'
                raise ValueError(_last_error) from None
            elif isinstance(exc,TimeoutError):message='Online detector took too long. Try again later.'
            elif 'checkpoint verification failed' in text:message='Online detector checkpoint verification failed.'
            else:message='Online detector is temporarily unavailable. Try again later.'
            _last_error=message
            raise RuntimeError(message) from None
