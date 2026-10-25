"""Deterministic contract tests, not a real face-detector test."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from app.services.video_processor import align_detected_face, jpeg_roundtrip, pack_aligned, ALIGN_TARGET

# This image and these landmarks are test fixtures only. They are not game data.
bgr = np.arange(224*224*3, dtype=np.uint32).reshape(224,224,3).astype(np.uint8)
face = SimpleNamespace(bbox=np.array([0,0,224,224]), kps=ALIGN_TARGET.copy(), det_score=.9)
aligned = align_detected_face(bgr, face)
np.testing.assert_array_equal(aligned, bgr)
encoded = jpeg_roundtrip(aligned)
prepared = pack_aligned([encoded], [17], 16)
assert prepared.tensors.shape == (16,3,224,224)
assert prepared.tensors.dtype == np.float32
assert prepared.detected_frames == 1 and prepared.repeated_frames == 15
assert prepared.source_indices == [17]*16
expected = ((encoded[:,:,::-1]/255. - np.array([.485,.456,.406])) / np.array([.229,.224,.225])).astype(np.float32).transpose(2,0,1)
np.testing.assert_array_equal(prepared.tensors[0], expected)
np.testing.assert_array_equal(prepared.tensors[15], expected)
try:
    pack_aligned([], [], 16)
except ValueError:
    pass
else:
    raise AssertionError('No-face sequence must not produce an input')
print('Alignment geometry, JPEG path, exact normalization, padding and no-face rejection: PASS')
