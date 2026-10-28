"""Run the restricted worker in a subprocess, without network or social cookies."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

WORKER=Path(__file__).resolve().parents[1]/'app/services/social_worker.py'

@pytest.mark.parametrize('mode,ok', [('completed_limit',True),('empty_limit',False),('network_error',False)])
def test_one_download_limit_is_not_a_retrieval_failure(tmp_path,mode,ok):
    package=tmp_path/'yt_dlp';package.mkdir()
    (package/'utils.py').write_text('class DownloadError(Exception): pass\nclass MaxDownloadsReached(Exception): pass\n')
    (package/'__init__.py').write_text('''
import os
from pathlib import Path
from .utils import DownloadError, MaxDownloadsReached
class YoutubeDL:
 def __init__(self,opts):
  self.opts=opts
  assert opts['max_downloads']==1 and opts['noplaylist'] is True
  assert opts['max_filesize']==50_000_000 and opts['proxy']==''
  assert 'cookiefile' not in opts and 'cookiesfrombrowser' not in opts
  assert isinstance(opts['js_runtimes'],dict) and opts['remote_components']==set()
 def __enter__(self): return self
 def __exit__(self,*args): return False
 def download(self,urls):
  assert len(urls)==1
  mode=os.environ['WORKER_TEST_MODE']
  if mode=='network_error': raise DownloadError('Retrieval unavailable')
  if mode=='completed_limit': Path(self.opts['outtmpl'].replace('%(ext)s','mp4')).write_bytes(b'finished fixture')
  raise MaxDownloadsReached('Maximum number of downloads reached')
''')
    output=tmp_path/'output';output.mkdir()
    env={**os.environ,'PYTHONPATH':str(tmp_path),'WORKER_TEST_MODE':mode}
    result=subprocess.run([sys.executable,str(WORKER),'https://www.youtube.com/watch?v=9pEx7ZaD_6I',str(output)],env=env,capture_output=True,text=True,timeout=20)
    assert (result.returncode==0) is ok,result.stderr
