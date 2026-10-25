"""Private media survives local-cache loss without allowing arbitrary file access."""
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.services import media_store as store

@pytest.fixture
def cloud(monkeypatch,tmp_path):
    monkeypatch.setenv('MEDIA_STORAGE_ENABLED','true');monkeypatch.setenv('MEDIA_BUCKET','fixture-private')
    monkeypatch.setattr(store,'DATA_ROOT',tmp_path/'data');monkeypatch.setattr(store,'VIDEOS_DIR',tmp_path/'videos')
    monkeypatch.setattr(store,'_index',(0,[]))
    objects={}
    class S3:
        def upload_file(self,path,bucket,key):objects[key]=Path(path).read_bytes()
        def download_file(self,bucket,key,path):Path(path).write_bytes(objects[key])
        def head_object(self,**kw):return {'ContentLength':len(objects[kw['Key']])}
        def delete_object(self,**kw):objects.pop(kw['Key'],None)
        def get_paginator(self,name):return SimpleNamespace(paginate=lambda **kw:[{'Contents':[{'Key':k} for k in objects if k.startswith(kw['Prefix'])]}])
    monkeypatch.setattr(store,'_cached_client',S3())
    return objects

def test_private_original_survives_restart_and_delete_removes_cloud_copy(cloud):
    path=store.DATA_ROOT/'uploads/private.mp4';path.parent.mkdir(parents=True);path.write_bytes(b'fixture-video')
    ref=store.reference(path);assert ref=='s3://fixture-private/uploads/private.mp4'
    store.persist(path);path.unlink()
    assert store.local_path(ref).read_bytes()==b'fixture-video'
    store.remove(ref)
    assert not path.exists() and not cloud

@pytest.mark.parametrize('ref',['s3://another-bucket/uploads/x.mp4','s3://fixture-private/uploads/../../secret','s3://fixture-private/credentials/token','s3://fixture-private/uploads/x.mp4?secret=yes'])
def test_invalid_storage_references_never_access_files(cloud,ref):
    with pytest.raises(ValueError):store.local_path(ref)

def test_remote_library_does_not_need_a_local_file(cloud):
    cloud['videos/real/fixture.mp4']=b'video'
    cloud['library/fake/fixture.mp4']=b'video'
    cloud['uploads/private.mp4']=b'private'
    paths=store.library_paths()
    assert len(paths)==2 and {label for _,label in paths}=={'Real','Fake'}
    assert all(not path.exists() for path,_ in paths)

def test_files_outside_configured_roots_cannot_be_uploaded(cloud,tmp_path):
    path=tmp_path/'secret.env';path.write_text('fixture')
    with pytest.raises(ValueError):store.key_for(path)
    assert not cloud
