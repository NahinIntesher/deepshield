"""Create browser-compatible playback copies; keep originals for model inference."""
import hashlib
import shutil
import subprocess
import threading
from pathlib import Path
from ..config import DATA_ROOT

_lock = threading.Lock()

def browser_video(source: Path) -> Path:
    from .media_store import local_path
    source=local_path(source)
    stat = source.stat()
    key = hashlib.sha256(f'{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:h264-v2'.encode()).hexdigest()
    folder = DATA_ROOT / 'browser_media'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{key}.mp4'
    if target.is_file() and target.stat().st_size > 0:
        return target
    with _lock:
        if target.is_file() and target.stat().st_size > 0:
            return target
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        temp = folder / f'{key}.tmp.mp4'
        try:
            process = subprocess.run([
                ffmpeg, '-nostdin', '-y', '-v', 'error', '-i', str(source),
                '-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'libx264',
                '-threads', '2', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
                '-vf', 'scale=w=min(1280\\,iw):h=min(720\\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                str(temp)
            ], capture_output=True, text=True, timeout=180)
            if process.returncode != 0:
                raise RuntimeError('Could not prepare browser playback. Check the video and FFmpeg installation.')
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
    return target
