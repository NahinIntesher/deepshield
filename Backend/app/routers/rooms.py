"""Authoritative multiplayer clock. Run one API worker; room deadlines survive restart."""
from ..activity import round_event
import asyncio, json, secrets, time
from collections import defaultdict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from ..database import get_db, SessionLocal
from ..models.db_models import Room, RoomParticipant, User, ResearchChallengeItem
from ..models.schemas import CreateRoomRequest, JoinRoomRequest
from ..data.sample_dataset import available_items
from ..security import current_user, own_user, session_user, bearer_mobile_user, COOKIE, record_attempt
from ..config import CORS_ORIGINS

router=APIRouter(prefix="/api/rooms",tags=["Multiplayer"])
sockets=defaultdict(set)
locks=defaultdict(asyncio.Lock)
tasks={}
ROUND_SECONDS=10
PREP_SECONDS=3

def players(room):
    return [{"user_id":p.user_id,"display_name":p.display_name,"score":p.score,"answered":p.last_answer is not None} for p in sorted(room.participants,key=lambda p:-p.score)]

def snapshot(db,room):
    result={"type":"STATE","room_code":room.room_code,"host_id":room.host_user_id,"status":room.status,"round":room.current_round,"total_rounds":room.total_rounds,"deadline":room.deadline,"server_time":time.time(),"players":players(room),"can_advance":room.status=="playing" and all(p.last_answer is not None for p in room.participants)}
    if room.current_round and room.status in ("playing","preparing"):
        item=db.get(ResearchChallengeItem,json.loads(room.selected_items_json)[room.current_round-1])
        result["item"]={"id":item.id,"title":item.title,"media_type":"video","media_url":item.media_path}
    return result

async def broadcast(code,data):
    for ws in list(sockets[code]):
        try: await ws.send_json(data)
        except Exception: sockets[code].discard(ws)

async def publish(code):
    with SessionLocal() as db:
        room=db.query(Room).filter_by(room_code=code).first()
        if room: await broadcast(code,snapshot(db,room))

def schedule(code):
    old=tasks.get(code)
    if old and old is not asyncio.current_task(): old.cancel()
    tasks[code]=asyncio.create_task(clock(code))

def prepare(db,room):
    if room.status!="playing": return
    item=db.get(ResearchChallengeItem,json.loads(room.selected_items_json)[room.current_round-1])
    for p in room.participants:
        if p.last_answer is None:
            p.last_answer="Timeout"
            user=db.get(User,p.user_id)
            user.total_rounds_played+=1
            record_attempt(db,user,item,False)
            round_event(db,user,item,f"room:{room.id}:{room.current_round}:{user.id}","multiplayer","Timeout",False,0,10000)
    room.status="preparing"
    room.deadline=time.time()+PREP_SECONDS
    db.commit()

async def clock(code):
    try:
        while True:
            with SessionLocal() as db:
                room=db.query(Room).filter_by(room_code=code).first()
                if not room or room.status not in ("playing","preparing"): return
                deadline=room.deadline or time.time()
            await asyncio.sleep(max(0,deadline-time.time()))
            async with locks[code]:
                with SessionLocal() as db:
                    room=db.query(Room).filter_by(room_code=code).first()
                    if room.deadline and room.deadline>time.time(): continue
                    if room.status=="playing": prepare(db,room)
                    elif room.status=="preparing":
                        if room.current_round>=room.total_rounds:
                            room.status="finished";room.deadline=None
                            for p in room.participants: db.get(User,p.user_id).games_played+=1
                        else:
                            room.current_round+=1;room.status="playing";room.deadline=time.time()+ROUND_SECONDS
                            for p in room.participants: p.last_answer=None;p.last_answer_time_ms=None
                        db.commit()
                    else: return
                    await broadcast(code,snapshot(db,room))
    except asyncio.CancelledError: return

async def recover():
    with SessionLocal() as db:
        for room in db.query(Room).filter(Room.status.in_(["playing","preparing"])):
            schedule(room.room_code)

@router.post("/create")
def create(payload:CreateRoomRequest,user=Depends(current_user),db=Depends(get_db)):
    own_user(user,payload.user_id)
    items=available_items(db)
    if not items: raise HTTPException(404,"Add videos to videos/real and videos/fake first")
    import random
    chosen=random.sample(items,min(max(1,payload.total_rounds or 5),len(items),50))
    code=secrets.token_hex(3).upper()
    while db.query(Room).filter_by(room_code=code).first(): code=secrets.token_hex(3).upper()
    room=Room(room_code=code,host_user_id=user.id,total_rounds=len(chosen),selected_items_json=json.dumps([i.id for i in chosen]))
    db.add(room);db.flush()
    db.add(RoomParticipant(room_id=room.id,user_id=user.id,display_name=user.display_name,is_ready=True))
    db.commit()
    return {"room_code":code,"room_id":room.id,"host_id":user.id}

@router.post("/join")
def join(payload:JoinRoomRequest,user=Depends(current_user),db=Depends(get_db)):
    own_user(user,payload.user_id)
    room=db.query(Room).filter_by(room_code=payload.room_code.upper()).first()
    if not room: raise HTTPException(404,"Room not found")
    if not any(p.user_id==user.id for p in room.participants):
        if room.status!="waiting": raise HTTPException(409,"This game has already started")
        if len(room.participants)>=12: raise HTTPException(409,"Room is full")
        db.add(RoomParticipant(room_id=room.id,user_id=user.id,display_name=user.display_name,is_ready=True));db.commit()
    return {"room_code":room.room_code,"host_id":room.host_user_id}

@router.websocket("/ws/{room_code}/{user_id}")
async def websocket(ws:WebSocket,room_code:str,user_id:int):
    code=room_code.upper()
    mobile_header=ws.headers.get('authorization', '')
    is_mobile=mobile_header.startswith('Bearer dsm_')
    if not is_mobile and ws.headers.get("origin") not in CORS_ORIGINS:
        await ws.close(code=4403);return
    with SessionLocal() as db:
        user=bearer_mobile_user(db,mobile_header) if is_mobile else session_user(db,ws.cookies.get(COOKIE))
        room=db.query(Room).filter_by(room_code=code).first()
        if not user or user.id!=user_id or not room or not any(p.user_id==user_id for p in room.participants):
            await ws.close(code=4403);return
    await ws.accept();sockets[code].add(ws)
    await publish(code)
    try:
        while True:
            event=await ws.receive_json()
            if not isinstance(event,dict): continue
            async with locks[code]:
                with SessionLocal() as db:
                    user=bearer_mobile_user(db,mobile_header) if is_mobile else session_user(db,ws.cookies.get(COOKIE))
                    if not user: await ws.close(code=4401);return
                    room=db.query(Room).filter_by(room_code=code).first()
                    part=next(p for p in room.participants if p.user_id==user_id)
                    action=event.get("action")
                    error=None
                    if action=="START_GAME":
                        if room.host_user_id!=user_id or room.status!="waiting": error="Only the host can start a waiting game"
                        else:
                            room.status="playing";room.current_round=1;room.deadline=time.time()+ROUND_SECONDS;db.commit();schedule(code)
                    elif action=="NEXT_ROUND":
                        if room.host_user_id!=user_id or room.status!="playing" or not all(p.last_answer is not None for p in room.participants): error="Wait until every player has answered"
                        else: prepare(db,room);schedule(code)
                    elif action=="SUBMIT_ANSWER":
                        item_id=json.loads(room.selected_items_json)[room.current_round-1] if room.current_round else None
                        if room.status!="playing" or time.time()>=(room.deadline or 0): error="This round has ended"
                        elif part.last_answer is not None: error="Your answer is already recorded"
                        elif event.get("item_id")!=item_id or event.get("prediction") not in ("Real","Fake"): error="Invalid answer for this round"
                        else:
                            item=db.get(ResearchChallengeItem,item_id)
                            correct=event["prediction"]==item.ground_truth
                            pts=100+int(max(0,room.deadline-time.time())/ROUND_SECONDS*50) if correct else 0
                            part.last_answer=event["prediction"];part.score+=pts
                            part.last_answer_time_ms=int((ROUND_SECONDS-room.deadline+time.time())*1000)
                            user.score+=pts;user.total_correct+=int(correct);user.total_rounds_played+=1
                            record_attempt(db,user,item,correct)
                            round_event(db,user,item,f"room:{room.id}:{room.current_round}:{user.id}","multiplayer",part.last_answer,correct,pts,part.last_answer_time_ms)
                            db.commit()
                            await ws.send_json({"type":"ANSWER_FEEDBACK","round":room.current_round,"is_correct":correct,"ground_truth":item.ground_truth,"points":pts,"explanation":"Compared with the dataset label. AI analysis is available in the Detector."})
                    if error: await ws.send_json({"type":"ERROR","message":error})
                    await broadcast(code,snapshot(db,room))
    except (WebSocketDisconnect,ValueError,RuntimeError): pass
    finally: sockets[code].discard(ws)
