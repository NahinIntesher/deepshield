"""Isolated public-link handling and conservative media processing safeguards.

Only three explicit public social platforms are supported. A public URL is not a
promise of downloadable media; login-only, DRM and unsupported links are rejected.
"""
import datetime
import hashlib
import hmac
import os
import secrets
import threading
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import or_
from ..models.db_models import DetectionRecord, Subscription

ALLOWED_HOSTS = {
    'youtube.com':'YouTube','www.youtube.com':'YouTube',
    'm.youtube.com':'YouTube','youtu.be':'YouTube',
    'facebook.com':'Facebook','www.facebook.com':'Facebook',
    'm.facebook.com':'Facebook','web.facebook.com':'Facebook',
    'fb.watch':'Facebook','instagram.com':'Instagram','www.instagram.com':'Instagram',
}
MAX_UPLOAD_BYTES=250*1024*1024
MODEL_QUEUE=threading.BoundedSemaphore(1)

def platform_for_url(value: str) -> str:
    if len(value)>2048: raise HTTPException(422,'URL is too long')
    try: parts=urlsplit(value.strip())
    except ValueError: raise HTTPException(422,'Invalid video URL')
    try: has_forbidden_port=bool(parts.port)
    except ValueError: raise HTTPException(422,'Invalid URL port')
    if parts.scheme!='https' or not parts.netloc or parts.username or parts.password or has_forbidden_port:
        raise HTTPException(422,'Use an HTTPS public video link')
    host=(parts.hostname or '').lower().rstrip('.')
    platform=ALLOWED_HOSTS.get(host)
    if not platform: raise HTTPException(422,'Only public YouTube, Facebook and Instagram links are supported')
    if not parts.path or parts.path=='/': raise HTTPException(422,'Provide a direct public video link')
    return platform

def plan_info(db,user):
    today=datetime.datetime.utcnow()
    row=db.get(Subscription,user.id)
    premium=bool(row and row.plan=='premium' and row.status=='active' and (not row.expires_at or row.expires_at>today))
    plan='premium' if premium else 'free'
    limit=50 if premium else 5
    start=today.replace(hour=0,minute=0,second=0,microsecond=0)
    used=db.query(DetectionRecord).filter(DetectionRecord.user_id==user.id,DetectionRecord.created_at>=start,or_(DetectionRecord.source_name.like('Link: %'),DetectionRecord.source_name.like('Extension: %'))).count()
    return {'plan':plan,'limit':limit,'used_today':used,'remaining':max(0,limit-used),
            'status':row.status if row else 'active',
            'requested_at':row.requested_at.isoformat() if row and row.requested_at else None,
            'expires_at':row.expires_at.isoformat() if premium and row.expires_at else None}

def require_scan_quota(db,user):
    info=plan_info(db,user)
    if info['remaining']<1: raise HTTPException(429,'Daily link/extension scan quota reached. Try tomorrow or request Premium.')

def download_public_video(url: str, directory: Path) -> Path:
    """Use yt-dlp if installed; never pass URL to a shell command."""
    platform_for_url(url)
    try:
        import yt_dlp
    except ImportError:
        raise HTTPException(503,'Link extraction dependency is missing: install yt-dlp from requirements.txt')
    def progress(p):
        count=p.get('downloaded_bytes') or p.get('total_bytes') or p.get('total_bytes_estimate') or 0
        if count>MAX_UPLOAD_BYTES: raise HTTPException(413,'Video exceeds the 250 MiB limit')
    opts={
        'quiet':True,'no_warnings':True,'noplaylist':True,'skip_download':False,
        'outtmpl':str(directory/'public-video.%(ext)s'),
        'format':'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best',
        'merge_output_format':'mp4','max_filesize':MAX_UPLOAD_BYTES,
        'socket_timeout':15,'retries':1,'fragment_retries':1,
        'extractor_retries':1,'nocheckcertificate':False,
        'progress_hooks':[progress],
        'ignoreerrors':False,'no_color':True,
        'cachedir':False,
        'match_filter':yt_dlp.utils.match_filter_func('duration <= 600'),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as dl:
            meta=dl.extract_info(url,download=True)
            if not meta or meta.get('_type')=='playlist': raise ValueError('Playlists are not supported')
    except HTTPException: raise
    except Exception as exc:
        raise HTTPException(422,'Could not access this public video. It may require login, be restricted or have an unsupported format.') from exc
    files=[p for p in directory.glob('public-video.*') if p.is_file() and p.suffix.lower() in ('.mp4','.webm','.mkv','.mov')]
    if len(files)!=1: raise HTTPException(422,'The public link did not produce a playable video')
    target=files[0]
    if target.stat().st_size>MAX_UPLOAD_BYTES: raise HTTPException(413,'Video exceeds 250 MiB')
    return target
