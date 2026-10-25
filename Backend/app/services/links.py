import re,subprocess,sys
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from fastapi import HTTPException

def canonical(raw):
 try:
  u=urlsplit(raw.strip());h=(u.hostname or '').lower()
  if u.scheme!='https' or u.username or u.password or u.port not in (None,443):raise ValueError()
 except ValueError:raise HTTPException(422,'Use an HTTPS video link from YouTube, Facebook or Instagram.')
 parts=[s for s in u.path.split('/') if s]
 if h in ('youtube.com','www.youtube.com','m.youtube.com','youtu.be'):
  vid=parts[0] if h=='youtu.be' and parts else parse_qs(u.query).get('v',[''])[0] if u.path=='/watch' else parts[1] if len(parts)==2 and parts[0]=='shorts' else ''
  if re.fullmatch(r'[A-Za-z0-9_-]{11}',vid):return 'https://www.youtube.com/watch?v='+vid
 if h in ('facebook.com','www.facebook.com','m.facebook.com','web.facebook.com'):
  vid=parse_qs(u.query).get('v',[''])[0]
  if u.path in ('/watch','/watch/') and vid.isdigit():return 'https://www.facebook.com/watch/?v='+vid
  if re.fullmatch(r'/(?:reel/\d+|[^/]+/videos/\d+)/?',u.path):return 'https://www.facebook.com'+u.path
 if h in ('instagram.com','www.instagram.com') and re.fullmatch(r'/(?:reel|reels|p|tv)/[A-Za-z0-9_-]+/?',u.path):return 'https://www.instagram.com'+u.path
 raise HTTPException(422,'Paste one direct public video or reel permalink. Channels, playlists and Facebook share redirects are not supported; upload an authorized copy if necessary.')

def retrieve(url,folder):
 result=subprocess.run([sys.executable,str(Path(__file__).with_name('social_worker.py')),url,str(folder)],capture_output=True,text=True,timeout=180)
 if result.returncode:raise RuntimeError('The public video could not be retrieved. Platform restrictions, login requirements or unsupported formats can cause this. Upload a copy you are allowed to analyze instead.')
 files=[p for p in Path(folder).iterdir() if p.suffix in ('.mp4','.webm','.mkv','.mov')]
 if len(files)!=1 or files[0].stat().st_size>50_000_000:raise RuntimeError('No supported video within the 50 MB limit was retrieved.')
 return files[0]
