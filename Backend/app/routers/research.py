import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from PIL import Image
from ..database import get_db
from ..models.db_models import User, ResearchChallengeItem, ResearchSubmission
from ..models.schemas import ResearchItemResponse, ResearchSubmissionRequest, ResearchSubmissionResponse
from ..services.vit_lstm import model_manager
from ..services.xai_engine import xai_engine
from ..data.sample_dataset import available_items, item_path
from ..services.inference import analyze_video

from ..security import current_user, own_user, qualify
from ..models.db_models import LearningSample

router = APIRouter(prefix="/api/research", tags=["Research Challenge & Human-AI Protocol"])

@router.get("/items", response_model=List[ResearchItemResponse])
def get_research_items(user_id: int, actor=Depends(current_user), db: Session = Depends(get_db)):
    """
    Returns research challenge items for an evaluator.
    Verifies that the user has qualified or is a designated researcher.
    """
    own_user(actor,user_id)
    user = actor
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not qualify(db,user):
        raise HTTPException(
            status_code=403, 
            detail="Research Challenge locked. Achieve at least 90% game accuracy and a score of at least 5000."
        )

    seen={r.item_id for r in db.query(ResearchSubmission).filter_by(user_id=user.id)}
    items = [i for i in available_items(db) if i.id not in seen]
    results = []
    for it in items:
        try:
            cues = json.loads(it.visual_cues)
        except:
            cues = []
        results.append(ResearchItemResponse(
            id=it.id,
            title=it.title,
            media_type=it.media_type,
            media_url=it.media_path,
            thumbnail_url=it.thumbnail_path,
            manipulation_type="Unrevealed",
            difficulty=it.difficulty,
            description=it.description,
            visual_cues=[]
        ))
    return results

@router.post("/submit", response_model=ResearchSubmissionResponse)
def submit_research_evaluation(payload: ResearchSubmissionRequest, actor=Depends(current_user), db: Session = Depends(get_db)):
    """
    Academic research protocol endpoint:
    Records Human Verdict, Confidence (1-5), Clue Tags, and Reaction Time (ms).
    Computes agreement with Swin + DCT + Transformer detector, determines 4-quadrant assignment,
    generates XAI heatmap overlay, and stores in database.
    """
    item = db.query(ResearchChallengeItem).filter(ResearchChallengeItem.id == payload.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    own_user(actor,payload.user_id)
    user = actor
    if not qualify(db,user): raise HTTPException(403,"Research qualification required")
    if payload.human_prediction not in ("Real","Fake"): raise HTTPException(422,"Choose Real or Fake")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if db.query(ResearchSubmission).filter_by(user_id=user.id,item_id=item.id).first():
        raise HTTPException(409,"You have already evaluated this video. Choose another sample.")

    # Evaluate Human Correctness
    is_human_correct = (payload.human_prediction.strip().lower() == item.ground_truth.strip().lower())

    try:
        path = item_path(item)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    result = analyze_video(path)
    ai_pred = result['verdict']
    ai_conf = result['confidence_percentage'] / 100
    is_ai_correct = ai_pred == item.ground_truth
    item.ai_prediction = ai_pred
    item.ai_confidence = ai_conf
    item.ai_temporal_anomaly = json.dumps(result['temporal_scores'])

    # Compute 4-Quadrant Category
    if is_human_correct and is_ai_correct:
        quadrant = "Q1"
        quadrant_desc = "Consensus Correct (Human & AI agree with ground truth)"
    elif is_human_correct and not is_ai_correct:
        quadrant = "Q2"
        quadrant_desc = "Model Blindspot (Human correct, Swin + DCT + Transformer fooled)"
    elif not is_human_correct and is_ai_correct:
        quadrant = "Q3"
        quadrant_desc = "Human Perception Limit (AI correct, Human fooled)"
    else:
        quadrant = "Q4"
        quadrant_desc = "Frontier Edge Case (Both Human and AI fooled)"

    heatmap_url = result['spatial_heatmap_base64']
    temporal_scores = result['temporal_scores']

    explanation = xai_engine.explain_disagreement(quadrant, item.manipulation_type, payload.clue_tags)
    if result.get('xai_error'):
        explanation += ' ' + result['xai_error']
    explanation += f" Aligned faces: {result['detected_frames']}/16; final-frame repetitions: {result['repeated_frames']}."

    # Persist submission
    submission = ResearchSubmission(
        model_id=result["model_id"], model_name=result["model_name"], checkpoint_epoch=result["checkpoint_epoch"],
        inference_metadata=json.dumps({k:result[k] for k in ("frame_indices","detected_frames","repeated_frames","fusion_gates","temporal_scores","xai_error")}),
        item_id=item.id,
        user_id=user.id,
        human_prediction=payload.human_prediction,
        human_confidence=payload.human_confidence,
        clue_tags=json.dumps(payload.clue_tags),
        reaction_time_ms=payload.reaction_time_ms,
        ai_prediction=ai_pred,
        ai_confidence=ai_conf,
        ground_truth=item.ground_truth,
        is_human_correct=is_human_correct,
        is_ai_correct=is_ai_correct,
        disagreement_quadrant=quadrant
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    if user.role == "researcher":
        db.add(LearningSample(submission_id=submission.id,item_id=item.id))
        db.commit()

    return ResearchSubmissionResponse(
        model_id=result["model_id"], model_name=result["model_name"], checkpoint_epoch=result["checkpoint_epoch"], xai_error=result["xai_error"],
        submission_id=submission.id,
        item_id=item.id,
        ground_truth=item.ground_truth,
        human_prediction=payload.human_prediction,
        human_confidence=payload.human_confidence,
        is_human_correct=is_human_correct,
        ai_prediction=ai_pred,
        ai_confidence=ai_conf,
        is_ai_correct=is_ai_correct,
        disagreement_quadrant=quadrant,
        quadrant_description=quadrant_desc,
        explanation=explanation,
        xai_heatmap_url=heatmap_url,
        temporal_anomaly_scores=temporal_scores
    )
