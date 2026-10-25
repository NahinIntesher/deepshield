"""Private S3 originals, portable references and bounded local download caching."""
import os,threading,time,uuid
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
from ..config import DATA_ROOT,VIDEOS_DIR

class StorageUnavailable(RuntimeError):pass
_lock=threading.RLock()
_cached_client=None
_index=(0,[])
def enabled():return os.getenv('MEDIA_STORAGE_ENABLED','false').lower()=='true'
def bucket():return os.getenv('MEDIA_BUCKET','').strip()
def client():
 global _cached_client
 if _cached_client is None:
  import boto3
  from botocore.config import Config
  endpoint,access,secret=[os.getenv(k,'').strip() for k in ('AWS_ENDPOINT_URL_S3','AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY')]
  if not bucket() or not all((endpoint,access,secret)):raise StorageUnavailable('Private file storage is not configured.')
  if not endpoint.startswith('https://'):raise StorageUnavailable('Private file storage requires HTTPS.')
  _cached_client=boto3.client('s3',endpoint_url=endpoint,aws_access_key_id=access,aws_secret_access_key=secret,
   region_name=os.getenv('AWS_REGION','ap-southeast-1'),config=Config(signature_version='s3v4',s3={'addressing_style':'path'},connect_timeout=15,read_timeout=120,retries={'max_attempts':3}))
 return _cached_client
def path_for(key):
 parts=PurePosixPath(key).parts
 if len(parts)<2 or parts[0] not in ('uploads','library','videos') or any(p in ('.','..') or '\\' in p or ':' in p for p in parts):raise ValueError('Invalid private media reference.')
 root=VIDEOS_DIR if parts[0]=='videos' else DATA_ROOT/parts[0]
 target=root.joinpath(*parts[1:]).resolve()
 if not target.is_relative_to(root.resolve()):raise ValueError('Invalid private media reference.')
 return target
def key_for(path):
 path=Path(path).resolve()
 for prefix,root in [('uploads',DATA_ROOT/'uploads'),('library',DATA_ROOT/'library'),('videos',VIDEOS_DIR)]:
  if path.is_relative_to(root.resolve()):
   key=prefix+'/'+path.relative_to(root.resolve()).as_posix();path_for(key);return key
 raise ValueError('Media file is outside configured storage.')
def reference(path):return 's3://'+bucket()+'/'+key_for(path) if enabled() else str(path)
def ref_key(ref):
 parsed=urlsplit(str(ref))
 if parsed.scheme!='s3' or parsed.netloc!=bucket() or parsed.query or parsed.fragment:raise ValueError('Invalid private media reference.')
 key=parsed.path.lstrip('/');path_for(key);return key
def local_path(ref,fetch=True):
 if str(ref).startswith('s3://'):
  if not enabled():raise StorageUnavailable('Private file storage is not configured.')
  key=ref_key(ref);path=path_for(key)
 else:path=Path(ref);key=key_for(path) if enabled() else None
 if fetch and enabled() and not path.is_file():
  with _lock:
   if path.is_file():return path
   path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.part')
   try:
    info=client().head_object(Bucket=bucket(),Key=key)
    if info['ContentLength']>250*1024*1024:raise ValueError('Stored media exceeds the allowed size.')
    client().download_file(bucket(),key,str(temp));temp.replace(path)
   except Exception:raise StorageUnavailable('Could not retrieve the private media file. Try again.') from None
   finally:temp.unlink(missing_ok=True)
 return path
def persist(path):
 global _index
 if not enabled():return
 try:client().upload_file(str(path),bucket(),key_for(path))
 except Exception:raise StorageUnavailable('Could not save the private media file. Try again.') from None
 _index=(0,[])
def remove(ref):
 global _index
 if enabled():
  key=ref_key(ref) if str(ref).startswith('s3://') else key_for(ref)
  try:client().delete_object(Bucket=bucket(),Key=key)
  except Exception:raise StorageUnavailable('Could not remove the private media file. Try again.') from None
 local_path(ref,fetch=False).unlink(missing_ok=True);_index=(0,[])
def library_paths():
 global _index
 if not enabled():return []
 with _lock:
  if time.monotonic()-_index[0]<30:return list(_index[1])
  paths=[]
  try:
   for prefix in ('videos/','library/'):
    for page in client().get_paginator('list_objects_v2').paginate(Bucket=bucket(),Prefix=prefix):
     for item in page.get('Contents',[]):
      key=item['Key'];parts=PurePosixPath(key).parts
      if len(parts)>=3 and parts[1] in ('real','fake') and Path(key).suffix.lower() in ('.mp4','.mov','.avi','.mkv','.webm'):paths.append((path_for(key),parts[1].title()))
  except Exception:raise StorageUnavailable('Could not load the private video library. Try again.') from None
  _index=(time.monotonic(),paths);return list(paths)
