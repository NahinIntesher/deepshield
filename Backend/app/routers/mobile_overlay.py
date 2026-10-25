"""Opt-in Android screen scan. Never stores submitted screenshots on disk permanently.

Uses exactly the existing trained video detector, subscription quotas, and scan history.
No retraining, alternative model, or fabricated confidence is introduced.
"""
import tempfile
from pathlib import Path
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from typing import List

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..security import current_user
from ..services.inference import analyze_video
try:
    from ..services.integration import MODEL_QUEUE, require_scan_quota
    PRODUCT_BACKEND = False
except ImportError:
    import threading, secrets
    from ..services.scan_queue import membership, lock, notify
    from ..product_models import Charge
    MODEL_QUEUE = threading.BoundedSemaphore(1)
    PRODUCT_BACKEND = True
    def require_scan_quota(db,user):
        info=membership(db,user.id)
        if info['used']>=info['limit']:raise HTTPException(429,'Daily scan allowance used.')
from .detector import save_detection

router = APIRouter(prefix='/api/integrations/mobile-overlay', tags=['Android live screen protection'])
SOURCES = {'YouTube', 'Facebook', 'Instagram'}
FRAME_COUNT = 16
MAX_FRAME_BYTES = 500_000
MAX_TOTAL_BYTES = 8_000_000


def _decode_frames(images: List[bytes]):
    """Reject malformed/oversized images; ensure all samples use one video dimension."""
    if len(images) != FRAME_COUNT:
        raise HTTPException(422, f'Provide exactly {FRAME_COUNT} chronologically ordered JPEG frames')
    decoded = []
    for idx, item in enumerate(images):
        if not 512 <= len(item) <= MAX_FRAME_BYTES:
            raise HTTPException(413, f'Frame {idx} has an invalid size')
        # Read JPEG dimensions before allocating the decompressed image.
        try:
            with Image.open(BytesIO(item)) as metadata:
                if metadata.format != 'JPEG' or min(metadata.size) < 112 or max(metadata.size) > 1920:
                    raise HTTPException(422, f'Frame {idx} has invalid JPEG dimensions')
        except (UnidentifiedImageError, OSError, ValueError):
            raise HTTPException(422, f'Frame {idx} has invalid JPEG metadata')
        frame = cv2.imdecode(np.frombuffer(item, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None or frame.ndim != 3:
            raise HTTPException(422, f'Frame {idx} is not a valid image')
        height, width = frame.shape[:2]
        if min(height, width) < 112 or max(height, width) > 1920:
            raise HTTPException(422, f'Frame {idx} has unsupported dimensions')
        decoded.append(frame)
    return decoded


def _temporary_video(frames, path: Path):
    """Compose an MJPEG AVI that cv2.VideoCapture can read using the existing pipeline."""
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'MJPG'), 1.0, (width, height))
    if not writer.isOpened():
        raise HTTPException(503, 'Video encoder is unavailable on this backend')
    try:
        for frame in frames:
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            writer.write(frame)
    finally:
        writer.release()
    if not path.exists() or path.stat().st_size < 1024:
        raise HTTPException(503, 'Cannot assemble captured frames')


@router.post('/analyze')
def scan_mobile_overlay(
    source: str,
    frames: List[UploadFile] = File(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if source not in SOURCES:
        raise HTTPException(422, 'Choose YouTube, Facebook, or Instagram')
    # Limits apply before model inference. No permission to read another user's scans.
    require_scan_quota(db, user)
    if len(frames) != FRAME_COUNT:
        raise HTTPException(422, 'Exactly 16 captured frames are required')
    if not MODEL_QUEUE.acquire(blocking=False):
        raise HTTPException(503, 'Model busy; try again shortly')
    charge_id = None
    try:
        if PRODUCT_BACKEND:
            with lock:
                require_scan_quota(db,user)
                charge_id=secrets.token_hex(16)
                db.add(Charge(id=charge_id,user_id=user.id));db.commit()
        data = []
        total = 0
        for item in frames:
            if item.content_type not in ('image/jpeg', 'application/octet-stream'):
                raise HTTPException(415, 'Only JPEG screenshots are accepted')
            buf = item.file.read(MAX_FRAME_BYTES + 1)
            total += len(buf)
            if total > MAX_TOTAL_BYTES:
                raise HTTPException(413, 'Screen capture batch exceeds upload limit')
            data.append(buf)
        decoded = _decode_frames(data)
        with tempfile.TemporaryDirectory(prefix='ds-mobile-overlay-') as temp:
            path = Path(temp) / 'screen_capture.avi'
            _temporary_video(decoded, path)
            result = analyze_video(path)
            # Only the model result is added to scan history, never the raw screen video.
            saved=save_detection(db, user, f'Android Live Guard: {source}', result)
            if PRODUCT_BACKEND:
                notify(db,user.id,'Live Guard analysis ready',f'{source}: '+result['verdict']+' (model prediction)');db.commit()
            return saved
    except Exception:
        if charge_id:
            db.rollback()
            charge=db.get(Charge,charge_id)
            if charge:charge.charged=False;db.commit()
        raise
    finally:
        MODEL_QUEUE.release()
