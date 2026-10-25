"""Functional contracts on an isolated database/media directory; no fake model output."""
import atexit
import json
import os
import tempfile
from pathlib import Path

# Shared isolation is established in conftest before any app import.

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.database import SessionLocal,engine
from app.models.db_models import User,ResearchChallengeItem,DetectionRecord,GameRoundRecord,AuthSession,CourseProgress,AuditLog
from app.product_models import Scan,Charge,Ticket,Notice,Subscription,GoogleIdentity
from app.routers import game,rooms
from app.routers.auth import _hash_password

atexit.register(engine.dispose)
with SessionLocal() as db:
    db.add(User(username='deepshild',display_name='Test owner',role='admin',password_hash=_hash_password('deepshield')))
    db.commit()

@pytest.fixture
def client(monkeypatch):
    from app.routers.auth import _attempts
    from app.services import email_verification
    monkeypatch.setenv('EMAIL_VERIFICATION_REQUIRED','true')
    client_emails={}
    monkeypatch.setattr(email_verification,'configured',lambda:True)
    monkeypatch.setattr(email_verification,'send_link',lambda email,token,language:client_emails.__setitem__(email,token))
    _attempts.clear()
    monkeypatch.setattr(game,'game_prediction',lambda item:{'ai_prediction':None,'ai_confidence':None,'ai_error':'Model inference is outside this isolated API test'})
    with SessionLocal() as db:
        if not db.query(ResearchChallengeItem).count():
            for i in range(8):db.add(ResearchChallengeItem(title=f'Test {i}',media_path=f'/api/media/test{i}',ground_truth='Real' if i<4 else 'Fake'))
            db.commit()
    monkeypatch.setattr(game,'available_items',lambda db:db.query(ResearchChallengeItem).filter_by(archived=False).all())
    monkeypatch.setattr(rooms,'available_items',lambda db:db.query(ResearchChallengeItem).filter_by(archived=False).all())
    with TestClient(app) as c:
        c.verification_emails=client_emails
        yield c
    # Queued fixture media must never be picked up by a later test's startup.
    with SessionLocal() as db:
        db.query(Scan).filter(Scan.state.in_(['queued','downloading','processing'])).update({'state':'failed'},synchronize_session=False)
        db.commit()

def signup(client,name):
    r=client.post('/api/auth/signup',json={'username':name,'display_name':name,'password':'password123','email':name+'@example.com'})
    assert r.status_code==202,r.text
    token=client.verification_emails[name+'@example.com']
    assert client.post('/api/auth/verify-email',json={'token':token}).status_code==200
    r=client.post('/api/auth/login',json={'username':name,'password':'password123'})
    assert r.status_code==200,r.text
    return r.json()

def owner(client):
    response=client.post('/api/auth/admin/login',json={'username':'deepshild','password':'deepshield'})
    assert response.status_code==200,response.text
    return response.json()

def receive(socket,kind):
    for _ in range(30):
        msg=socket.receive_json()
        if msg['type']==kind:return msg
    raise AssertionError('Expected '+kind)

def test_auth_and_admin_boundaries(client):
    assert client.get('/api/admin/users').status_code==401
    user=signup(client,'alice')
    assert client.get('/api/admin/users').status_code==403
    assert client.get('/api/auth/user/999').status_code==403
    assert client.post('/api/rooms/create',json={'user_id':999}).status_code==403
    assert client.get(f'/api/research/items?user_id={user["id"]}').status_code==403
    assert client.post('/api/research/submit',json={'user_id':user['id'],'item_id':1,'human_prediction':'Real','human_confidence':4,'clue_tags':[],'reaction_time_ms':1000}).status_code==403
    admin=owner(client)
    assert client.patch(f'/api/admin/users/{user["id"]}/role',json={'role':'researcher'}).status_code==200
    assert client.patch(f'/api/admin/users/{user["id"]}/role',json={'role':'root'}).status_code==422
    assert client.patch(f'/api/admin/users/{admin["id"]}/role',json={'role':'participant'}).status_code==403
    client.post('/api/auth/logout')
    assert client.get('/api/admin/users').status_code==401

def test_score_qualification_and_solo_replay(client):
    user=signup(client,'bob');items=client.get('/api/game/items?count=4').json()
    with SessionLocal() as db:labels={i.id:i.ground_truth for i in db.query(ResearchChallengeItem)}
    for n,item in enumerate(items):
        payload={'user_id':user['id'],'item_id':item['id'],'ticket':item['ticket'],'prediction':labels[item['id']],'time_taken_ms':1000}
        result=client.post('/api/game/submit-round',json=payload)
        assert result.status_code==200,result.text
        assert client.post('/api/game/submit-round',json=payload).status_code==409
        q=client.get('/api/auth/qualification').json()
        assert q['rounds']==n+1 and q['qualified']==(q['score']>=5000)
    body={'user_id':user['id'],'rounds':items}
    assert client.post('/api/game/complete-session',json=body).status_code==200
    assert client.post('/api/game/complete-session',json=body).status_code==200
    assert client.get('/api/auth/me').json()['games_played']==1
    assert client.post('/api/game/submit-round',json={**payload,'ticket':'forged'}).status_code==400

def test_multiplayer_host_gate_and_preparation(client,monkeypatch):
    monkeypatch.setattr(rooms,'ROUND_SECONDS',5);monkeypatch.setattr(rooms,'PREP_SECONDS',.1)
    host=signup(client,'host');hc=client.cookies.get('deepshield_session')
    code=client.post('/api/rooms/create',json={'user_id':host['id'],'total_rounds':2}).json()['room_code']
    client.cookies.clear();peer=signup(client,'peer');pc=client.cookies.get('deepshield_session')
    assert client.post('/api/rooms/join',json={'user_id':peer['id'],'display_name':'Forged name','room_code':code}).status_code==200
    with client.websocket_connect(f'/api/rooms/ws/{code}/{host["id"]}',headers={'origin':'http://localhost:3000','cookie':f'deepshield_session={hc}'}) as a:
        receive(a,'STATE')
        with client.websocket_connect(f'/api/rooms/ws/{code}/{peer["id"]}',headers={'origin':'http://localhost:3000','cookie':f'deepshield_session={pc}'}) as b:
            receive(a,'STATE');receive(b,'STATE')
            b.send_json({'action':'START_GAME'});assert receive(b,'ERROR')
            receive(a,'STATE');receive(b,'STATE')
            a.send_json({'action':'START_GAME'});state=receive(a,'STATE');receive(b,'STATE')
            assert state['status']=='playing' and not state['can_advance']
            a.send_json({'action':'NEXT_ROUND'});assert receive(a,'ERROR')
            for ws in (a,b):ws.send_json({'action':'SUBMIT_ANSWER','item_id':state['item']['id'],'prediction':'Real'})
            receive(a,'ANSWER_FEEDBACK');receive(b,'ANSWER_FEEDBACK')
            a.send_json({'action':'NEXT_ROUND'})
            for _ in range(20):
                state=receive(a,'STATE')
                if state['status']=='preparing':break
            assert state['status']=='preparing'

def test_multiplayer_timeout_auto_advance(client,monkeypatch):
    monkeypatch.setattr(rooms,'ROUND_SECONDS',.1);monkeypatch.setattr(rooms,'PREP_SECONDS',.05)
    user=signup(client,'timeoutplayer')
    code=client.post('/api/rooms/create',json={'user_id':user['id'],'total_rounds':1}).json()['room_code']
    with client.websocket_connect(f'/api/rooms/ws/{code}/{user["id"]}',headers={'origin':'http://localhost:3000'}) as ws:
        receive(ws,'STATE');ws.send_json({'action':'START_GAME'})
        assert receive(ws,'STATE')['status']=='playing'
        assert receive(ws,'STATE')['status']=='preparing'
        assert receive(ws,'STATE')['status']=='finished'
    assert client.get('/api/auth/me').json()['total_rounds_played']==1

def test_exact_research_thresholds_and_legacy_totals(client):
    user=signup(client,'thresholduser')
    with SessionLocal() as db:
        u=db.get(User,user['id']);u.score=5000;u.total_correct=90;u.total_rounds_played=100;db.commit()
    assert client.get('/api/auth/qualification').json()['qualified']
    with SessionLocal() as db:u=db.get(User,user['id']);u.score=4999;db.commit()
    assert not client.get('/api/auth/qualification').json()['qualified']
    with SessionLocal() as db:u=db.get(User,user['id']);u.score=5000;u.total_correct=89;u.role='researcher';db.commit()
    assert not client.get('/api/auth/qualification').json()['qualified']

def test_course_progress_and_private_detection_history(client):
    user=signup(client,'courseuser')
    assert not client.post('/api/profile/course/0',json={'choice':0}).json()['completed']
    assert client.post('/api/profile/course/0',json={'choice':1}).json()['completed']
    assert client.post('/api/profile/course/0',json={'choice':0}).json()['completed']
    with SessionLocal() as db:
        row=DetectionRecord(user_id=user['id'],source_name='Test-only record',verdict='Real',confidence=50,result_json='{"fixture":true}');db.add(row);db.commit();ident=row.id
    assert client.get('/api/profile/detections/'+str(ident)).json()['fixture']
    signup(client,'historystranger')
    assert client.get('/api/profile/detections/'+str(ident)).status_code==404
    assert client.delete('/api/profile/detections/'+str(ident)).status_code==404

def test_admin_login_analytics_and_audit(client):
    signup(client,'analyticsmember');admin=owner(client)
    assert client.get('/api/admin/analytics?days=7').status_code==200
    assert client.get('/api/admin/analytics?days=1').status_code==422
    assert client.get('/api/admin/audit').json()
    assert client.get('/api/admin/training-jobs').status_code==200

def test_product_pairing_scope_and_revocation(client):
    signup(client,'extensionowner')
    code=client.post('/api/extension/pair').json()['code']
    token=client.post('/api/extension/redeem',json={'code':code}).json()['token']
    assert client.post('/api/extension/redeem',json={'code':code}).status_code==400
    ident=client.get('/api/extension/tokens').json()[0]['id']
    client.post('/api/auth/logout');headers={'Authorization':'Bearer '+token}
    assert client.get('/api/extension/account',headers=headers).status_code==200
    assert client.get('/api/auth/me',headers=headers).status_code==401
    assert client.get('/api/operations',headers=headers).status_code==401
    client.post('/api/auth/login',json={'username':'extensionowner','password':'password123'})
    client.delete('/api/extension/tokens/'+ident)
    assert client.get('/api/extension/account',headers=headers).status_code==401

def test_product_membership_support_and_notifications(client):
    signup(client,'membershipowner')
    rid=client.post('/api/billing/request',json={'note':'Please grant an academic demonstration'}).json()['id']
    assert client.post('/api/billing/request',json={'note':'Duplicate request'}).status_code==409
    ticket=client.post('/api/support',json={'subject':'Video retrieval','message':'A public video link could not be retrieved.'}).json()
    assert client.get('/api/operations').status_code==403
    owner(client)
    assert client.post(f'/api/operations/subscriptions/{rid}',json={'decision':'approved','activation':'manual_payment','note':'Missing payment reference'}).status_code==422
    assert client.post(f'/api/operations/subscriptions/{rid}',json={'decision':'approved','activation':'academic_demo','note':'Academic demonstration; no payment'}).status_code==200
    assert client.post(f'/api/operations/subscriptions/{rid}',json={'decision':'approved','note':'Duplicate decision'}).status_code==409
    assert client.post(f'/api/operations/support/{ticket["id"]}',json={'reply':'Upload an authorized copy instead.'}).status_code==200
    client.post('/api/auth/login',json={'username':'membershipowner','password':'password123'})
    assert client.get('/api/billing').json()['activation']=='academic_demo'
    assert client.get('/api/billing/export/scans').status_code==200
    assert client.get('/api/support').json()[0]['status']=='resolved'
    assert len(client.get('/api/notifications').json())==2
    client.post('/api/notifications/read');assert all(r['read'] for r in client.get('/api/notifications').json())
    signup(client,'privatestranger');assert client.get('/api/support').json()==[] and client.get('/api/notifications').json()==[]

def test_product_url_queue_and_quota_ledger(client,monkeypatch):
    from app.services import scan_queue
    monkeypatch.setattr(scan_queue.executor,'submit',lambda *a:None);monkeypatch.setattr(scan_queue,'limits',lambda:(2,100))
    signup(client,'queueowner')
    for url in ['http://youtube.com/watch?v=abcdefghijk','https://youtube.com.evil.example/watch?v=abcdefghijk','https://127.0.0.1/private','file:///etc/passwd','https://www.youtube.com/playlist?list=abc','https://user:pass@youtube.com/watch?v=abcdefghijk']:
        assert client.post('/api/scans/link',json={'url':url}).status_code==422
    a=client.post('/api/scans/link',json={'url':'https://youtu.be/abcdefghijk'}).json()
    assert client.post('/api/scans/link',json={'url':'https://www.youtube.com/watch?v=abcdefghijk&tracking=1'}).json()['id']==a['id']
    assert client.post('/api/scans/upload',files={'file':('empty.mp4',b'','video/mp4')}).status_code==422
    assert client.post('/api/scans/upload',files={'file':('bad.txt',b'text','text/plain')}).status_code==415
    b=client.post('/api/scans/link',json={'url':'https://www.instagram.com/reel/ABC123/'}).json()
    assert client.post('/api/scans/link',json={'url':'https://www.facebook.com/reel/1234567'}).status_code==429
    with SessionLocal() as db:db.get(Scan,a['id']).state='completed';db.commit()
    client.delete('/api/scans/'+a['id']);assert client.get('/api/billing').json()['used']==2
    client.delete('/api/scans/'+b['id']);assert client.get('/api/billing').json()['used']==1

def test_product_assessment_does_not_change_game_logic(client,monkeypatch):
    from app.routers import product
    monkeypatch.setattr(product,'available_items',lambda db:db.query(ResearchChallengeItem).all())
    signup(client,'assessmentowner');before=client.get('/api/auth/me').json()
    assert client.post('/api/assessment/start',json={'consent':False}).status_code==422
    data=client.post('/api/assessment/start',json={'consent':True}).json();pre={r['id'] for r in data['items']};assert len(pre)==4
    with SessionLocal() as db:labels={r.id:r.ground_truth for r in db.query(ResearchChallengeItem)}
    response=client.post(f'/api/assessment/{data["id"]}/submit',json={'phase':'pre','answers':[{'item_id':i,'prediction':labels[i]} for i in pre]})
    assert response.status_code==200,response.text
    post=response.json();post_ids={r['id'] for r in post['items']};assert not pre&post_ids
    payload={'phase':'post','answers':[{'item_id':i,'prediction':labels[i]} for i in post_ids]}
    assert client.post(f'/api/assessment/{data["id"]}/submit',json=payload).status_code==409
    client.post('/api/profile/course/0',json={'choice':1})
    assert client.post(f'/api/assessment/{data["id"]}/submit',json=payload).json()['state']=='completed'
    after=client.get('/api/auth/me').json()
    for key in ['score','total_correct','total_rounds_played','games_played','qualified_for_research']:assert before[key]==after[key]

def test_trimmed_forms_disguised_upload_and_mobile_session(client,monkeypatch):
    from app.services import scan_queue
    monkeypatch.setattr(scan_queue.executor,'submit',lambda *a:None)
    signup(client,'validationowner')
    assert client.post('/api/support',json={'subject':'    ','message':'             '}).status_code==422
    assert client.post('/api/billing/request',json={'note':'       '}).status_code==422
    assert client.post('/api/scans/upload',files={'file':('pretend.mp4',b'not a video','video/mp4')}).status_code==422
    assert client.get('/api/billing').json()['used']==0
    mobile=client.post('/api/auth/mobile/login',json={'username':'validationowner','password':'password123'}).json()
    client.post('/api/auth/logout');headers={'Authorization':'Bearer '+mobile['token']}
    assert client.get('/api/scans',headers=headers).status_code==200
    assert client.get('/api/scans',headers={'Authorization':'Bearer dsm_invalid'}).status_code==401
    assert client.get('/api/operations',headers=headers).status_code==403

def test_session_rotation_and_cross_site_rejection(client):
    signup(client,'rotationowner');previous=client.cookies.get('deepshield_session')
    client.post('/api/auth/login',json={'username':'rotationowner','password':'password123'})
    assert client.cookies.get('deepshield_session')!=previous
    with TestClient(app) as old:
        old.cookies.set('deepshield_session',previous);assert old.get('/api/auth/me').status_code==401
    assert client.post('/api/support',headers={'sec-fetch-site':'cross-site'},json={'subject':'Blocked request','message':'A cross-site request should be rejected.'}).status_code==403

def test_image_upload_uses_existing_queue_and_private_history(client,monkeypatch):
    import io
    from PIL import Image
    from app.services import scan_queue
    monkeypatch.setattr(scan_queue.executor,'submit',lambda *a:None)
    signup(client,'stillowner');buffer=io.BytesIO();Image.new('RGB',(224,224),'white').save(buffer,format='PNG')
    response=client.post('/api/scans/upload',files={'file':('still.png',buffer.getvalue(),'image/png')});assert response.status_code==202,response.text
    job=response.json();assert job['media_type']=='image' and client.get('/api/billing').json()['used']==1
    assert client.post('/api/scans/upload',files={'file':('still.png',buffer.getvalue(),'image/png')}).json()['id']==job['id']
    signup(client,'stillstranger');assert client.get('/api/scans/'+job['id']).status_code==404

def test_owner_is_immutable_and_only_three_roles_are_allowed(client):
    from sqlalchemy.exc import IntegrityError
    member=signup(client,'roleparticipant');admin=owner(client)
    for role in ('admin','moderator','root'):assert client.patch(f'/api/admin/users/{member["id"]}/role',json={'role':role}).status_code==422
    assert client.patch(f'/api/admin/users/{admin["id"]}/role',json={'role':'participant'}).status_code==403
    assert client.patch(f'/api/admin/users/{member["id"]}/role',json={'role':'researcher'}).status_code==200
    client.post('/api/auth/logout');assert client.post('/api/auth/admin/login',json={'username':'roleparticipant','password':'password123'}).status_code==403
    with SessionLocal() as db:
        db.add(User(username='forgedadmin',display_name='Forbidden',role='admin'))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()

def test_bkash_reference_verification_and_recipient(client):
    signup(client,'bkashmember');assert client.get('/api/billing').json()['payment']['number']=='01815808291'
    assert client.post('/api/billing/request',json={'note':'bKash payment request','request_type':'manual_payment'}).status_code==422
    result=client.post('/api/billing/request',json={'note':'bKash payment request','request_type':'manual_payment','reference':'abc123def4'});assert result.status_code==201
    rid=result.json()['id'];signup(client,'duplicatepayment')
    assert client.post('/api/billing/request',json={'note':'Duplicate request','reference':'ABC123DEF4','request_type':'manual_payment'}).status_code==409
    owner(client);payload={'decision':'approved','activation':'manual_payment','note':'Verified actual recipient, amount and transaction.'}
    assert client.post(f'/api/operations/subscriptions/{rid}',json=payload).status_code==422
    assert client.post(f'/api/operations/subscriptions/{rid}',json={**payload,'payment_verified':True}).status_code==200
    client.post('/api/auth/login',json={'username':'bkashmember','password':'password123'})
    assert client.get('/api/billing').json()['plan']=='premium'
    assert client.get('/api/notifications').json()[-1]['title']=='Subscription request approved'

def test_google_tokens_need_nonce_and_cannot_promote_or_link_by_email(client,monkeypatch):
    from app.routers import google_auth
    monkeypatch.setenv('GOOGLE_CLIENT_ID','fixture.apps.googleusercontent.com')
    headers={'origin':'http://localhost:3000'};token='x'*120
    assert client.post('/api/auth/google',json={'credential':token},headers=headers).status_code==401
    challenge=client.post('/api/auth/google/challenge',json={},headers=headers).json()
    claims={'iss':'https://accounts.google.com','aud':'fixture.apps.googleusercontent.com','sub':'fixture-google-subject','email_verified':True,'nonce':'wrong','name':'Google member','email':'admin@example.test','role':'admin'}
    monkeypatch.setattr(google_auth,'verify_credential',lambda *a:claims)
    assert client.post('/api/auth/google',json={'credential':token},headers=headers).status_code==401
    claims['nonce']=challenge['nonce'];first=client.post('/api/auth/google',json={'credential':token},headers=headers)
    assert first.status_code==200,first.text
    assert first.json()['role']=='participant' and first.json()['has_password'] is False
    assert client.get('/api/admin/users').status_code==403
    assert first.json()['needs_profile'] is True
    assert client.get('/api/scans').status_code==401
    assert client.post('/api/auth/password',json={'current_password':'password123','new_password':'new-password-123'}).status_code==403
    complete=client.post('/api/auth/onboarding',json={'username':'googlemember','display_name':'Chosen name','password':'chosen-password-123'})
    assert complete.status_code==200 and complete.json()['needs_profile'] is False
    assert client.get('/api/scans').status_code==200
    client.post('/api/auth/logout');challenge=client.post('/api/auth/google/challenge',json={},headers=headers).json();claims['nonce']=challenge['nonce']
    assert client.post('/api/auth/google',json={'credential':token},headers=headers).json()['id']==first.json()['id']

def test_admin_account_crud_and_cascaded_deletion(client,monkeypatch):
    from app.services import scan_queue
    monkeypatch.setattr(scan_queue.executor,'submit',lambda *a:None)
    actor=owner(client);payload={'username':'createdmember','display_name':'Created member','role':'researcher','password':'created-password-123'}
    response=client.post('/api/admin/users',json=payload);assert response.status_code==201,response.text
    user=response.json();assert 'password_hash' not in user
    assert client.post('/api/admin/users',json=payload).status_code==409
    assert client.post('/api/admin/users',json={**payload,'username':'invalidrole','role':'admin'}).status_code==422
    client.cookies.clear();client.post('/api/auth/login',json={'username':'createdmember','password':'created-password-123'});old_cookie=client.cookies.get('deepshield_session')
    client.post('/api/profile/course/0',json={'choice':1});client.post('/api/support',json={'subject':'Example ticket','message':'Example support ticket for deletion.'})
    client.post('/api/scans/link',json={'url':'https://youtu.be/abcdefghijk'})
    client.cookies.clear();owner(client)
    updated=client.patch('/api/admin/users/'+str(user['id']),json={'username':'renamedmember','display_name':'Updated member','role':'participant'})
    assert updated.status_code==200 and updated.json()['username']=='renamedmember'
    with TestClient(app) as old:
        old.cookies.set('deepshield_session',old_cookie);assert old.get('/api/auth/me').status_code==401
    assert client.patch('/api/admin/users/'+str(actor['id']),json={'username':'ownerchanged','display_name':'Blocked','role':'participant'}).status_code==403
    assert client.request('DELETE','/api/admin/users/'+str(actor['id']),json={'confirm_username':actor['username']}).status_code==403
    assert client.request('DELETE','/api/admin/users/'+str(user['id']),json={'confirm_username':'wrong'}).status_code==422
    removed=client.request('DELETE','/api/admin/users/'+str(user['id']),json={'confirm_username':'renamedmember'});assert removed.status_code==200,removed.text
    assert client.get('/api/admin/users/'+str(user['id'])).status_code==404
    with SessionLocal() as db:
        for model in (AuthSession,CourseProgress,Ticket,Notice,GoogleIdentity,Subscription,Scan):assert db.query(model).filter_by(user_id=user['id']).count()==0
        assert db.query(AuditLog).filter_by(action='account_deleted',target=str(user['id'])).count()==1
        assert db.execute(text('PRAGMA foreign_key_check')).all()==[]

def test_bilingual_lesson_crud_preserves_progress_and_hides_answers(client):
    signup(client,'lessonlearner');public=client.get('/api/profile/lessons').json()
    assert len(public)>=12 and all('answer' not in r for r in public)
    client.post('/api/profile/course/0',json={'choice':1});owner(client)
    row=client.get('/api/admin/content/lessons').json()[0];payload={k:row[k] for k in ('en','bn','answer','archived')}
    payload['en']['title']='New course lesson';payload['bn']['title']='নতুন পাঠ'
    made=client.post('/api/admin/content/lessons',json=payload);assert made.status_code==201,made.text
    ident=made.json()['id'];payload['en']['title']='Updated course lesson'
    assert client.put('/api/admin/content/lessons/'+str(ident),json=payload).status_code==200
    assert client.delete('/api/admin/content/lessons/'+str(ident)).status_code==200
    client.post('/api/auth/login',json={'username':'lessonlearner','password':'password123'})
    assert ident not in {r['id'] for r in client.get('/api/profile/lessons').json()}
    assert client.post('/api/profile/course/'+str(ident),json={'choice':1}).status_code==404
    assert client.get('/api/admin/content/lessons').status_code==403
    assert next(r for r in client.get('/api/profile/course').json() if r['lesson_id']==0)['completed']

def test_admin_record_edits_do_not_allow_prediction_tampering(client):
    signup(client,'recordowner');ticket=client.post('/api/support',json={'subject':'Example support','message':'This message can be updated by the administrator.'}).json()
    assert client.get('/api/admin/records/support').status_code==403
    owner(client)
    assert client.patch('/api/admin/records/support/'+str(ticket['id']),json={'title':'Updated support','note':'The administrator corrected this support record.'}).status_code==200
    assert client.patch('/api/admin/records/support/'+str(ticket['id']),json={'ai_prediction':'Real'}).status_code==422
    assert client.request('DELETE','/api/admin/records/support/'+str(ticket['id']),json={'confirm_id':'wrong'}).status_code==422
    assert client.request('DELETE','/api/admin/records/support/'+str(ticket['id']),json={'confirm_id':str(ticket['id'])}).status_code==200

def test_library_archive_keeps_original_media_and_can_be_restored(client):
    owner(client);rows=client.get('/api/admin/content/library').json();assert rows
    row=rows[0];payload={k:row[k] for k in ('title','description','ground_truth','difficulty','archived')}
    payload['title']='Library metadata updated'
    assert client.put('/api/admin/content/library/'+str(row['id']),json=payload).status_code==200
    assert client.delete('/api/admin/content/library/'+str(row['id'])).status_code==200
    assert client.get(row['media_url'],headers={'Range':'bytes=0-99'}).status_code==206
    payload['archived']=False
    assert client.put('/api/admin/content/library/'+str(row['id']),json=payload).status_code==200
    assert client.post('/api/admin/content/library',data={'title':'Invalid video','ground_truth':'Real'},files={'file':('bad.mp4',b'not a video','video/mp4')}).status_code==422


def test_email_registration_requires_verified_ownership_and_single_use(client,monkeypatch):
    import hashlib,time
    from app.product_models import PendingRegistration
    payload={'username':'verifiednew','display_name':'Verified member','password':'registration-password','email':'verifiednew@example.com'}
    client.cookies.clear()
    assert client.post('/api/auth/signup',json={**payload,'email':'invalid-email'}).status_code==422
    response=client.post('/api/auth/signup',json=payload)
    assert response.status_code==202 and response.json()['verification_required']
    assert 'deepshield_session' not in response.cookies
    assert client.post('/api/auth/login',json={'username':payload['username'],'password':payload['password']}).status_code==401
    token=client.verification_emails[payload['email']]
    with SessionLocal() as db:
        pending=db.get(PendingRegistration,hashlib.sha256(token.encode()).hexdigest())
        assert pending and pending.password_hash!=payload['password']
        assert not db.query(User).filter_by(username=payload['username']).first()
    assert client.post('/api/auth/resend-verification',json={'email':payload['email']}).status_code==429
    with SessionLocal() as db:
        pending=db.get(PendingRegistration,hashlib.sha256(token.encode()).hexdigest());pending.sent_at=time.time()-61;db.commit()
    assert client.post('/api/auth/resend-verification',json={'email':payload['email']}).status_code==200
    new_token=client.verification_emails[payload['email']]
    assert new_token!=token
    assert client.post('/api/auth/verify-email',json={'token':token}).status_code==400
    assert client.post('/api/auth/verify-email',json={'token':new_token}).status_code==200
    assert client.post('/api/auth/verify-email',json={'token':new_token}).status_code==400
    assert client.post('/api/auth/login',json={'username':payload['username'],'password':payload['password']}).status_code==200
    with SessionLocal() as db:
        user=db.query(User).filter_by(username=payload['username']).one()
        assert user.email_verified_at and user.email==payload['email']
    monkeypatch.setattr(__import__('app.services.email_verification',fromlist=['configured']),'configured',lambda:False)
    assert client.post('/api/auth/signup',json={**payload,'username':'disabledmail','email':'disabledmail@example.com'}).status_code==503


def test_video_over_50_mb_rejected_before_decoding_or_charging(client,tmp_path):
    from app.services.upload_validation import validate_video
    from fastapi import HTTPException
    path=tmp_path/'too-large.mp4'
    with path.open('wb') as stream:stream.truncate(50_000_001)
    with pytest.raises(HTTPException) as error:validate_video(path)
    assert error.value.status_code==413
    signup(client,'sizecheck')
    before=client.get('/api/billing').json()['used']
    with path.open('rb') as stream:
        response=client.post('/api/scans/upload',files={'file':('too-large.mp4',stream,'video/mp4')})
    assert response.status_code==413 and '50 MB' in response.json()['detail']
    assert client.get('/api/billing').json()['used']==before
    assert client.get('/api/scans').json()==[]


def test_signup_with_email_verification_deferred_still_works(client,monkeypatch):
    monkeypatch.setenv('EMAIL_VERIFICATION_REQUIRED','false')
    client.cookies.clear()
    payload={'username':'deferredmember','display_name':'Deferred member','password':'signup-password','email':'deferredmember@example.com'}
    response=client.post('/api/auth/signup',json=payload)
    assert response.status_code==202 and response.json()['verification_required'] is False
    assert client.post('/api/auth/login',json={'username':payload['username'],'password':payload['password']}).status_code==200
    with SessionLocal() as db:assert db.query(User).filter_by(username=payload['username']).one().email_verified_at is None
