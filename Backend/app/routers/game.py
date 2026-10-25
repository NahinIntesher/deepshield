from ..activity import round_event
import json
import random
import secrets, time
from ..security import current_user, own_user, record_attempt, qualify
from ..models.db_models import SoloTicket
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.db_models import User, ResearchChallengeItem, GameSession
from ..models.schemas import SubmitAnswerRequest, AnswerResultResponse, SoloGameSubmitRequest
from ..config import QUALIFICATION_ACCURACY_THRESHOLD

from ..data.sample_dataset import available_items
from ..services.inference import game_prediction

router = APIRouter(prefix="/api/game", tags=["Gamified Real vs Fake"])

@router.get("/items")
def get_game_items(count: int = 5, user=Depends(current_user), db: Session = Depends(get_db)):
    """
    Returns randomized items for a game session, stripping out ground truth for honest gameplay.
    """
    all_items = available_items(db)
    if not all_items:
        raise HTTPException(status_code=404, detail="No game items available")
    
    selected = random.sample(all_items, min(max(1, count), len(all_items)))
    batch = secrets.token_hex(16)
    tickets = {}
    for it in selected:
        token = secrets.token_hex(24)
        tickets[it.id] = token
        db.add(SoloTicket(token=token, user_id=user.id, item_id=it.id, batch=batch, expires=time.time()+3600))
    db.commit()
    return [
        {
            "ticket": tickets[it.id],
            "id": it.id,
            "title": it.title,
            "media_type": it.media_type,
            "media_url": it.media_path,
            "difficulty": it.difficulty,
            "description": it.description
        }
        for it in selected
    ]

@router.post("/submit-round", response_model=AnswerResultResponse)
def submit_round_answer(payload: SubmitAnswerRequest, actor=Depends(current_user), db: Session = Depends(get_db)):
    """
    Validates a player's Real vs Fake answer, awards points based on correctness and speed,
    and returns immediate educational explanation of the manipulation artifacts.
    """
    own_user(actor, payload.user_id)
    ticket = db.get(SoloTicket, payload.ticket or "")
    if not ticket or ticket.user_id != actor.id or ticket.item_id != payload.item_id or ticket.expires < time.time():
        raise HTTPException(400, "Start a new solo game before answering")
    if payload.prediction not in ("Real", "Fake", "Timeout"):
        raise HTTPException(422, "Choose Real or Fake")
    if ticket.used: raise HTTPException(409, "This round has already been answered")
    changed = db.query(SoloTicket).filter_by(token=ticket.token,used=False).update({"used":True})
    if not changed: raise HTTPException(409,"Answer already recorded")
    item = db.query(ResearchChallengeItem).filter(ResearchChallengeItem.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_correct = (payload.prediction.strip().lower() == item.ground_truth.strip().lower())
    
    # Scoring algorithm: Base 100 points for correct answer + speed bonus (up to 50 pts if < 5000ms)
    points = 0
    if is_correct:
        base_points = 100
        time_factor = max(0, 15000 - max(0, payload.time_taken_ms)) / 15000.0  # 15s round
        speed_bonus = int(time_factor * 50)
        points = base_points + speed_bonus
        user.score += points
        user.total_correct += 1

    user.total_rounds_played += 1

    record_attempt(db,user,item,is_correct)
    round_event(db,user,item,"solo:"+ticket.token,"solo",payload.prediction,is_correct,points,payload.time_taken_ms)
    ticket.points = points
    ticket.correct = is_correct
    db.commit()

    # Generate educational explanation
    try:
        cues = json.loads(item.visual_cues)
    except:
        cues = []

    explanation = f"The dataset owner labeled this video {item.ground_truth}. Specific visual artifacts have not been annotated."

    prediction_result = game_prediction(item)
    return AnswerResultResponse(
        **prediction_result,
        item_id=item.id,
        is_correct=is_correct,
        ground_truth=item.ground_truth,
        points_awarded=points,
        explanation=explanation,
        visual_cues=cues,
        manipulation_type=item.manipulation_type
    )

@router.post("/complete-session")
def complete_game_session(payload: SoloGameSubmitRequest, actor=Depends(current_user), db: Session = Depends(get_db)):
    """
    Records game session completion and increments user games_played.
    """
    own_user(actor,payload.user_id)
    tokens = [r.get("ticket") for r in payload.rounds]
    tickets = db.query(SoloTicket).filter(SoloTicket.token.in_(tokens),SoloTicket.user_id==actor.id).all()
    if not tickets or len(tickets)!=len(tokens) or len({t.batch for t in tickets})!=1 or not all(t.used for t in tickets):
        raise HTTPException(400,"Finish the issued rounds first")
    batch_rows = db.query(SoloTicket).filter_by(batch=tickets[0].batch,user_id=actor.id).all()
    if len(batch_rows)!=len(tickets): raise HTTPException(400,"Incomplete game")
    user = actor
    if not any(t.completed for t in tickets):
        user.games_played += 1
        for t in tickets: t.completed=True
        db.add(GameSession(user_id=user.id,mode="solo",total_items=len(tickets),total_correct=sum(t.correct for t in tickets),total_score=sum(t.points for t in tickets),accuracy=100*sum(t.correct for t in tickets)/len(tickets)))
    qualify(db,user)
    db.commit()

    return {
        "status": "success",
        "user_score": user.score,
        "user_accuracy": user.accuracy,
        "qualified_for_research": user.qualified_for_research
    }

@router.get("/leaderboard")
def get_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """
    Returns top participants ranked by score and accuracy.
    """
    top_users = db.query(User).order_by(User.score.desc()).limit(limit).all()
    return [
        {
            "rank": idx + 1,
            "display_name": u.display_name,
            "score": u.score,
            "games_played": u.games_played,
            "accuracy": u.accuracy,
            "qualified": u.qualified_for_research
        }
        for idx, u in enumerate(top_users)
    ]
