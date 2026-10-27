"""Bundle the matching inference source without copying application secrets or data."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
SERVICES = PROJECT/'Backend/app/services'
CONFIG = '''import os
from pathlib import Path
ROOT=Path(os.environ['DEEPSHIELD_ROOT'])
CHECKPOINT_PATH=ROOT/'best_model.pth'
FACE_MODEL_ROOT=ROOT/'face-model'
FACE_PROVIDER='CPUExecutionProvider'
NUM_FRAMES=16
MODEL_NAME='Swin-Small + DCT + Temporal Transformer'
'''
FILES = ['model_manager.py','swin_model.py','video_processor.py','upload_validation.py','xai_engine.py','shap_explanation.py']

with zipfile.ZipFile(ROOT/'runtime.zip','w',compression=zipfile.ZIP_DEFLATED) as bundle:
    bundle.writestr('engine/__init__.py','')
    bundle.writestr('engine/services/__init__.py','')
    bundle.writestr('engine/config.py',CONFIG)
    hashes = {}
    for name in FILES:
        content=(SERVICES/name).read_bytes()
        bundle.writestr('engine/services/'+name,content)
        hashes[name]=hashlib.sha256(content).hexdigest()
(ROOT/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
print('Bundled',len(FILES),'unchanged inference modules; no database or credentials included.')
