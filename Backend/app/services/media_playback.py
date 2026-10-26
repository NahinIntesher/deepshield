"""Prepared private playback copies and bounded range streaming; originals stay untouched."""
import hashlib
import logging
import re
import threading
import time
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from . import media_store
from .browser_media import browser_video

_metadata = {}
_metadata_lock = threading.Lock()

def playback_key(source):
    original_key = media_store.key_for(source)
    digest = hashlib.sha256(('playback-v2:' + original_key).encode()).hexdigest()
    return 'library/playback/' + digest + '.mp4'

def prepare_playback(source):
    path = browser_video(source)
    if media_store.enabled():
        key = playback_key(source)
        media_store.client().upload_file(str(path), media_store.bucket(), key,
            ExtraArgs={'ContentType': 'video/mp4', 'CacheControl': 'private, max-age=900'})
        with _metadata_lock:
            _metadata.pop(key, None)
    return path

def prepare_in_background(source):
    try:
        prepare_playback(source)
    except Exception:
        logging.getLogger(__name__).warning('Playback preparation failed; the original is retained.')

def _info(key):
    with _metadata_lock:
        cached = _metadata.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    info = media_store.client().head_object(Bucket=media_store.bucket(), Key=key)
    with _metadata_lock:
        if len(_metadata) >= 128:
            _metadata.clear()
        _metadata[key] = (time.monotonic() + 120, info)
    return info

def byte_range(header, length):
    if not header:
        return None
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
    if not match or not any(match.groups()):
        raise HTTPException(416, 'Invalid byte range', headers={'Content-Range': f'bytes */{length}'})
    start, end = match.groups()
    if not start:
        count = int(end)
        start, end = max(0, length-count), length-1
        if count == 0:
            start = length
    else:
        start, end = int(start), min(int(end), length-1) if end else length-1
    if start >= length or start > end:
        raise HTTPException(416, 'Invalid byte range', headers={'Content-Range': f'bytes */{length}'})
    return start, end

def playback_response(source, request):
    if not media_store.enabled():
        return FileResponse(browser_video(source), media_type='video/mp4', headers={'Cache-Control': 'private, max-age=900'})
    key = playback_key(source)
    try:
        info = _info(key)
    except Exception as error:
        code = getattr(error, 'response', {}).get('Error', {}).get('Code')
        if code not in ('404', 'NoSuchKey', 'NotFound'):
            raise HTTPException(503, 'Could not load video. Try again.') from None
        prepare_playback(source)
        info = _info(key)
    length = int(info['ContentLength'])
    etag = info.get('ETag')
    headers = {'Accept-Ranges': 'bytes', 'Cache-Control': 'private, max-age=900', 'Vary': 'Cookie, Authorization'}
    if etag:
        headers['ETag'] = etag
    if request.headers.get('if-none-match') == etag and etag and not request.headers.get('range'):
        return Response(status_code=304, headers=headers)
    requested = request.headers.get('range')
    if request.headers.get('if-range') and request.headers['if-range'] != etag:
        requested = None
    selected = byte_range(requested, length)
    start, end = selected or (0, length-1)
    headers['Content-Length'] = str(end-start+1)
    if selected:
        headers['Content-Range'] = f'bytes {start}-{end}/{length}'
    status = 206 if selected else 200
    if request.method == 'HEAD':
        return Response(status_code=status, media_type='video/mp4', headers=headers)
    try:
        body = media_store.client().get_object(Bucket=media_store.bucket(), Key=key,
            **({'Range': f'bytes={start}-{end}'} if selected else {}))['Body']
    except Exception:
        raise HTTPException(503, 'Could not load video. Try again.') from None
    def chunks():
        try:
            while chunk := body.read(64*1024):
                yield chunk
        finally:
            body.close()
    return StreamingResponse(chunks(), status_code=status, media_type='video/mp4', headers=headers)
