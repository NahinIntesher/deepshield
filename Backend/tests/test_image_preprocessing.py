"""Deterministic image input/security contracts; synthetic fixtures are not predictions."""
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException
from PIL import Image

from app.services.upload_validation import validate_image,load_image
from app.services.video_processor import VideoProcessor, ALIGN_TARGET


def test_image_uses_one_aligned_face_repeated_sixteen_times(tmp_path):
    path=tmp_path/'face.png'
    Image.fromarray(np.arange(224*224*3,dtype=np.uint32).reshape(224,224,3).astype('uint8')).save(path)
    processor=VideoProcessor()
    face=SimpleNamespace(bbox=np.array([0,0,224,224]),kps=ALIGN_TARGET.copy(),det_score=.99)
    processor.detector=SimpleNamespace(get=lambda pixels:[face])
    prepared=processor.prepare(path)
    assert prepared.media_type=='image'
    assert prepared.tensors.shape==(16,3,224,224)
    assert prepared.tensors.dtype==np.float32
    assert prepared.detected_frames==1 and prepared.repeated_frames==15
    assert prepared.sampled_frames==1 and prepared.fps is None
    for frame in prepared.tensors:np.testing.assert_array_equal(frame,prepared.tensors[0])


def test_image_without_face_is_not_given_a_prediction(tmp_path):
    path=tmp_path/'blank.jpg';Image.new('RGB',(224,224)).save(path)
    processor=VideoProcessor();processor.detector=SimpleNamespace(get=lambda pixels:[])
    with pytest.raises(ValueError,match='No alignable face'):processor.prepare(path)


def test_image_validation_blocks_disguised_animated_and_oversized_files(tmp_path):
    fake=tmp_path/'fake.png';fake.write_text('not a picture')
    with pytest.raises(HTTPException):validate_image(fake)
    mismatch=tmp_path/'mismatch.jpg';Image.new('RGB',(20,20)).save(mismatch,format='PNG')
    with pytest.raises(HTTPException):validate_image(mismatch)
    animated=tmp_path/'animated.webp'
    Image.new('RGB',(20,20),'red').save(animated,save_all=True,append_images=[Image.new('RGB',(20,20),'blue')],duration=50,loop=0)
    with pytest.raises(HTTPException) as error:validate_image(animated)
    assert 'Animated' in error.value.detail
    huge=tmp_path/'huge.png';Image.new('1',(8193,2)).save(huge)
    with pytest.raises(HTTPException):validate_image(huge)


def test_image_orientation_and_transparency_are_normalized(tmp_path):
    rotated=tmp_path/'oriented.jpg';image=Image.new('RGB',(40,20),'white');exif=image.getexif();exif[274]=6;image.save(rotated,exif=exif)
    with load_image(rotated) as result:assert result.size==(20,40)
    transparent=tmp_path/'alpha.png';Image.new('RGBA',(20,20),(0,0,0,0)).save(transparent)
    with load_image(transparent) as result:
        assert result.mode=='RGB'
        assert result.getpixel((0,0))==(255,255,255)
