"""Validation-time preprocessing from the supplied extraction/alignment/normalization code."""
import threading
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image
from ..config import NUM_FRAMES, FACE_MODEL_ROOT, FACE_PROVIDER

MEAN = np.array([.485, .456, .406])
STD = np.array([.229, .224, .225])
ALIGN_TARGET = np.float32([[70,90], [154,90], [112,130], [80,170], [144,170]])

class FaceModelUnavailable(RuntimeError):
    pass

@dataclass
class PreparedVideo:
    tensors: np.ndarray
    frames: list
    source_indices: list
    detected_frames: int
    sampled_frames: int
    repeated_frames: int
    fps: float | None = None
    media_type: str = 'video'


def jpeg_roundtrip(bgr):
    ok, encoded = cv2.imencode('.jpg', bgr)
    if not ok:
        raise ValueError('Could not encode sampled frame')
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError('Could not decode sampled frame')
    return decoded


def align_detected_face(bgr, face):
    x1, y1, x2, y2 = face.bbox.astype(int)
    w, h = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - w * .25))
    y1 = max(0, int(y1 - h * .25))
    x2 = min(bgr.shape[1], int(x2 + w * .25))
    y2 = min(bgr.shape[0], int(y2 + h * .25))
    crop = bgr[y1:y2, x1:x2]
    if not crop.size or face.kps is None:
        return None
    kps = face.kps.astype(np.float32).copy()
    kps[:, 0] -= x1
    kps[:, 1] -= y1
    matrix, _ = cv2.estimateAffinePartial2D(kps, ALIGN_TARGET)
    if matrix is None:
        return None
    return cv2.warpAffine(crop, matrix, (224, 224))


def pack_aligned(aligned, indices, sampled_frames):
    if not aligned:
        raise ValueError('No alignable face found in the sampled frames. This face-based model cannot analyze this video.')
    detected = len(aligned)
    if detected >= NUM_FRAMES:
        selection = np.linspace(0, detected - 1, NUM_FRAMES).astype(int).tolist()
    else:
        selection = list(range(detected)) + [detected - 1] * (NUM_FRAMES - detected)
    frames, tensors = [], []
    for i in selection:
        bgr = cv2.resize(aligned[i], (224,224))
        rgb = np.ascontiguousarray(bgr[:,:,::-1])
        # Match normalize_celebdf.py: float64 arithmetic then float32 CHW.
        tensors.append(((rgb / 255. - MEAN) / STD).astype(np.float32).transpose(2,0,1))
        frames.append(Image.fromarray(rgb))
    return PreparedVideo(np.stack(tensors), frames, [indices[i] for i in selection],
                         detected, sampled_frames, max(0, NUM_FRAMES - detected))


class VideoProcessor:
    def __init__(self):
        self.detector = None
        self.lock = threading.RLock()

    def ensure_detector(self):
        if self.detector is not None:
            return
        try:
            from insightface.app import FaceAnalysis
            import onnxruntime as ort
            model_dir = FACE_MODEL_ROOT / 'models' / 'buffalo_l'
            if not model_dir.is_dir() or not any(model_dir.glob('*.onnx')):
                raise FaceModelUnavailable(
                    f'InsightFace buffalo_l files missing at {model_dir}. '
                    'Reuse the buffalo_l directory from your training PC, or run python setup_face_model.py in backend.'
                )
            providers = [FACE_PROVIDER]
            if FACE_PROVIDER != 'CPUExecutionProvider':
                if FACE_PROVIDER not in ort.get_available_providers():
                    raise FaceModelUnavailable(f'{FACE_PROVIDER} is not available in this ONNX Runtime installation.')
                providers.append('CPUExecutionProvider')
            detector = FaceAnalysis(name='buffalo_l', root=str(FACE_MODEL_ROOT),
                                    allowed_modules=['detection'], providers=providers)
            detector.prepare(ctx_id=-1 if FACE_PROVIDER == 'CPUExecutionProvider' else 0,
                             det_size=(640,640))
            self.detector = detector
        except FaceModelUnavailable:
            raise
        except Exception as exc:
            raise FaceModelUnavailable(f'Face detector unavailable: {exc}. Install backend/requirements.txt.') from exc

    def prepare_image(self, path):
        from .upload_validation import load_image
        with self.lock:
            self.ensure_detector()
            with load_image(path) as image:
                bgr = np.ascontiguousarray(np.asarray(image)[:, :, ::-1])
            # Apply the same extraction/alignment JPEG path as a sampled video frame.
            bgr = jpeg_roundtrip(bgr)
            faces = self.detector.get(bgr)
            if not faces:
                raise ValueError('No alignable face found in this image. Choose a clear image containing a face.')
            crop = align_detected_face(bgr, max(faces, key=lambda f: f.det_score))
            if crop is None:
                raise ValueError('The face in this image could not be aligned. Choose a clearer, front-facing image.')
            prepared = pack_aligned([jpeg_roundtrip(crop)], [0], 1)
            prepared.media_type = 'image'
            return prepared

    def prepare(self, path):
        from pathlib import Path
        from .upload_validation import IMAGE_EXTENSIONS
        if Path(path).suffix.lower() in IMAGE_EXTENSIONS:
            return self.prepare_image(path)
        with self.lock:
            self.ensure_detector()
            cap = cv2.VideoCapture(str(path))
            aligned, source_indices = [], []
            try:
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = float(cap.get(cv2.CAP_PROP_FPS))
                if not cap.isOpened() or total <= 0:
                    raise ValueError('Video cannot be decoded or has no frames')
                sampled = np.linspace(0, total - 1, NUM_FRAMES, dtype=int)
                for index in sampled:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
                    ok, frame = cap.read()
                    if not ok:
                        continue
                    # Extraction saved JPG; alignment read that JPG and saved another JPG.
                    frame = jpeg_roundtrip(frame)
                    faces = self.detector.get(frame)
                    if not faces:
                        continue
                    face = max(faces, key=lambda f: f.det_score)
                    crop = align_detected_face(frame, face)
                    if crop is None:
                        continue
                    aligned.append(jpeg_roundtrip(crop))
                    source_indices.append(int(index))
            finally:
                cap.release()
            prepared = pack_aligned(aligned, source_indices, NUM_FRAMES)
            prepared.fps = fps if np.isfinite(fps) and fps > 0 else None
            return prepared

video_processor = VideoProcessor()
