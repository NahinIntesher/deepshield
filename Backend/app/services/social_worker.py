"""Restricted subprocess: no browser cookies, non-public IPs or external downloaders."""
import socket,ipaddress,time,sys,shutil
from pathlib import Path
_connect=socket.socket.connect
_connect_ex=socket.socket.connect_ex
def guard(address):
 host,port=address[:2]
 if port not in (80,443):raise OSError('Blocked port')
 for row in socket.getaddrinfo(host,port,type=socket.SOCK_STREAM):
  ip=ipaddress.ip_address(row[4][0].split('%')[0])
  if not ip.is_global or (ip.version==6 and ip.ipv4_mapped and not ip.ipv4_mapped.is_global):raise OSError('Blocked non-public destination')
def connect(self,address):
 if self.family in (socket.AF_INET,socket.AF_INET6):guard(address)
 return _connect(self,address)
def connect_ex(self,address):
 if self.family in (socket.AF_INET,socket.AF_INET6):guard(address)
 return _connect_ex(self,address)
socket.socket.connect=connect;socket.socket.connect_ex=connect_ex
if __name__=='__main__':
 from yt_dlp import YoutubeDL
 from yt_dlp.utils import DownloadError,MaxDownloadsReached
 start=time.monotonic()
 def progress(info):
  if info.get('downloaded_bytes',0)>50_000_000 or time.monotonic()-start>160:raise DownloadError('Processing limit reached')
 def match(info,*,incomplete):
  if info.get('is_live') or info.get('duration',0)>600:return 'Choose a non-live video under ten minutes'
 opts={'outtmpl':str(Path(sys.argv[2])/'video.%(ext)s'),'quiet':True,'no_warnings':True,'proxy':'','cachedir':False,'noplaylist':True,'playlistend':1,'max_downloads':1,'max_filesize':50_000_000,'socket_timeout':15,'retries':1,'extractor_retries':1,'fragment_retries':1,'enable_file_urls':False,'allowed_extractors':['youtube','facebook.*','instagram.*'],'format':'best[height<=720][protocol=https]/bestvideo[height<=720][protocol=https]/best[height<=720][protocol=http]','fixup':'never','progress_hooks':[progress],'match_filter':match,'windowsfilenames':True}
 # Official yt-dlp EJS support, using the host's maintained runtime. EJS ships
 # with yt-dlp[default]; no cookies, proxy rotation or downloaded remote scripts.
 opts['js_runtimes']={name:{'path':runtime} for name in ('deno','node') if (runtime:=shutil.which(name))}
 opts['remote_components']=set()
 try:
  with YoutubeDL(opts) as y:y.download([sys.argv[1]])
 except MaxDownloadsReached:
  # yt-dlp raises this after successfully finishing the one permitted download.
  # Accept only that specific signal with exactly one completed, bounded file;
  # ordinary network/extractor errors must still fail the subprocess.
  files=[p for p in Path(sys.argv[2]).iterdir() if p.is_file() and p.suffix.lower() in ('.mp4','.webm','.mkv','.mov')]
  if len(files)!=1 or not 0<files[0].stat().st_size<=50_000_000:raise
