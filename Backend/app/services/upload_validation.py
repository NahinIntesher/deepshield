"""Reject disguised files and oversized/long clips before charging or queueing."""
from pathlib import Path

import cv2
import math
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
IMAGE_MAX_BYTES = 20 * 1024 * 1024
IMAGE_MAX_PIXELS = 32_000_000
IMAGE_FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}


def load_image(path: Path):
    """Decode bounded, static raster images; honor orientation before face alignment."""
    if path.stat().st_size > IMAGE_MAX_BYTES:
        raise HTTPException(413, 'Maximum image size is 20 MiB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path, formats=['JPEG', 'PNG', 'WEBP']) as image:
                if image.format != IMAGE_FORMATS.get(path.suffix.lower()):
                    raise HTTPException(422, 'Image contents do not match its extension. Export it as JPG, PNG or WebP.')
                if image.width * image.height > IMAGE_MAX_PIXELS or max(image.size) > 8192:
                    raise HTTPException(422, 'Choose an image up to 32 megapixels and 8192 pixels on either side.')
                if getattr(image, 'is_animated', False):
                    raise HTTPException(422, 'Animated images are not supported. Choose a still image or upload a video.')
                image.load()
                oriented = ImageOps.exif_transpose(image)
                if oriented.mode in ('RGBA', 'LA') or 'transparency' in oriented.info:
                    rgba = oriented.convert('RGBA')
                    background = Image.new('RGBA', rgba.size, 'white')
                    return Image.alpha_composite(background, rgba).convert('RGB')
                return oriented.convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise HTTPException(422, 'This image could not be read safely. Export a still JPG, PNG or WebP image and try again.') from exc


def validate_image(path: Path):
    image = load_image(path)
    image.close()


def validate_video(path: Path):
    with path.open('rb') as source:
        header = source.read(64)
    recognized = (b'ftyp' in header[:32] or header[:4] == b'\x1aE\xdf\xa3'
                  or (header[:4] == b'RIFF' and header[8:12] == b'AVI ')
                  or header[4:8] in (b'moov', b'mdat', b'wide', b'free'))
    if not recognized:
        raise HTTPException(422, 'This file is not a supported video. Export a genuine MP4, MOV, AVI, MKV or WebM file.')
    capture = cv2.VideoCapture(str(path))
    try:
        width, height = capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        frames, fps = capture.get(cv2.CAP_PROP_FRAME_COUNT), capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or not all(math.isfinite(v) and v > 0 for v in (width, height, frames, fps)):
            raise HTTPException(422, 'Video metadata could not be read. Try exporting the video as MP4.')
        if width > 7680 or height > 7680 or width * height > 33_177_600:
            raise HTTPException(422, 'Choose a video at 8K resolution or below.')
        if frames / fps > 600:
            raise HTTPException(422, 'Choose a video no longer than 10 minutes.')
        readable, _ = capture.read()
        if not readable:
            raise HTTPException(422, 'The video could not be decoded. Try exporting the video as MP4.')
    finally:
        capture.release()
