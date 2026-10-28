from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from fastapi import HTTPException
from app.services import links

def test_retrieval_timeout_has_no_server_paths(monkeypatch,tmp_path):
 def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(['private/server/path'],180)
 monkeypatch.setattr(links.subprocess,'run',timeout)
 with pytest.raises(RuntimeError,match='platform took too long') as error:
  links.retrieve('https://www.youtube.com/watch?v=9pEx7ZaD_6I',tmp_path)
 assert 'private/server' not in str(error.value)

def test_failed_extraction_never_returns_a_media_result(monkeypatch,tmp_path):
 monkeypatch.setattr(links.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=1,stderr='Sign in to confirm you are not a bot'))
 with pytest.raises(RuntimeError,match='did not provide'):
  links.retrieve('https://www.youtube.com/watch?v=9pEx7ZaD_6I',tmp_path)

@pytest.mark.parametrize('url',['https://127.0.0.1/private','https://www.youtube.com/channel/example','https://www.youtube.com.evil.invalid/watch?v=9pEx7ZaD_6I'])
def test_public_link_scope_is_not_broadened(url):
 with pytest.raises(HTTPException):links.canonical(url)
