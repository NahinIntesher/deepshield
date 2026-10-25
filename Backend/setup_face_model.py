"""Optional one-time buffalo_l setup. Reuse your training copy when available."""
from app.config import FACE_MODEL_ROOT
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l', root=str(FACE_MODEL_ROOT),
                   allowed_modules=['detection'], providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1, det_size=(640,640))
print(f'Face detector ready: {FACE_MODEL_ROOT / "models" / "buffalo_l"}')
