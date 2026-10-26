import asyncio
import io
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.services import media_playback as playback

@pytest.mark.parametrize('header,expected',[
    (None,None),('bytes=0-9',(0,9)),('bytes=20-',(20,99)),
    ('bytes=-10',(90,99)),('bytes=90-999',(90,99)),('bytes=-999',(0,99)),
])
def test_single_ranges_match_browser_seek_requests(header,expected):
    assert playback.byte_range(header,100)==expected

@pytest.mark.parametrize('header',['bytes=100-','bytes=5-1','bytes=-0','bytes=','items=1-2','bytes=0-1,4-5'])
def test_invalid_ranges_are_416(header):
    with pytest.raises(HTTPException) as error:playback.byte_range(header,100)
    assert error.value.status_code==416
    assert error.value.headers['Content-Range']=='bytes */100'

def request(method='GET',**headers):
    return Request({'type':'http','method':method,'path':'/','headers':[(k.replace('_','-').encode(),v.encode()) for k,v in headers.items()]})

def test_prepared_remote_video_streams_only_requested_bytes(monkeypatch):
    content=b'0123456789'*1000
    bodies=[];calls=[]
    class Body(io.BytesIO):
        was_closed=False
        def close(self):self.was_closed=True;super().close()
    def get_object(**kwargs):
        calls.append(kwargs)
        start,end=map(int,kwargs['Range'][6:].split('-'))
        body=Body(content[start:end+1]);bodies.append(body);return {'Body':body}
    monkeypatch.setattr(playback.media_store,'enabled',lambda:True)
    monkeypatch.setattr(playback.media_store,'bucket',lambda:'private-fixture')
    monkeypatch.setattr(playback.media_store,'key_for',lambda path:'videos/real/test.mp4')
    monkeypatch.setattr(playback.media_store,'client',lambda:SimpleNamespace(get_object=get_object))
    monkeypatch.setattr(playback,'_info',lambda key:{'ContentLength':len(content),'ETag':'"fixture"'})
    monkeypatch.setattr(playback,'browser_video',lambda source:pytest.fail('Must not download/transcode during prepared playback'))
    response=playback.playback_response(Path('test.mp4'),request(range='bytes=100-199'))
    assert response.status_code==206 and response.headers['content-range']=='bytes 100-199/10000'
    async def read():return b''.join([chunk async for chunk in response.body_iterator])
    assert asyncio.run(read())==content[100:200]
    assert calls[0]['Range']=='bytes=100-199' and bodies[0].was_closed
    assert response.headers['cache-control'].startswith('private')
    calls.clear()
    assert playback.playback_response(Path('test.mp4'),request('HEAD')).headers['content-length']=='10000'
    assert not calls
    assert playback.playback_response(Path('test.mp4'),request(if_none_match='"fixture"')).status_code==304
    assert not calls
