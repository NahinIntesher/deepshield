import json
from .models.db_models import AuditLog, GameRoundRecord

def audit(db,actor,action,target,detail=None):
    db.add(AuditLog(actor_id=actor,action=action,target=target,detail=json.dumps(detail or {})))

def round_event(db,user,item,key,mode,prediction,correct,points,response_ms):
    db.add(GameRoundRecord(event_key=key,user_id=user.id,item_id=item.id,mode=mode,prediction=prediction,ground_truth=item.ground_truth,correct=correct,points=points,response_ms=max(0,response_ms)))
