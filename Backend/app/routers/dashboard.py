from ..security import current_user
from fastapi import Depends
import csv
import io
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.db_models import ResearchSubmission, ResearchChallengeItem
from ..models.schemas import PerformanceMetrics
from ..services.metrics_calc import metrics_calculator

router = APIRouter(dependencies=[Depends(current_user)], prefix="/api/dashboard", tags=["Research Dashboard & Academic Analytics"])

@router.get("/metrics", response_model=PerformanceMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Computes academic KPIs, side-by-side confusion matrices, calibration plots,
    and 4-quadrant disagreement distribution across all evaluations.
    """
    submissions = db.query(ResearchSubmission).all()
    metrics = metrics_calculator.calculate_kpis(submissions)
    return metrics

@router.get("/quadrants/{quadrant}")
def get_quadrant_items(quadrant: str, user=Depends(current_user), db: Session = Depends(get_db)):
    """
    Returns submissions belonging to a specific quadrant (Q1, Q2, Q3, Q4)
    with item details and XAI explanation for granular error analysis.
    """
    quadrant = quadrant.upper()
    if quadrant not in ["Q1", "Q2", "Q3", "Q4", "ALL"]:
        raise HTTPException(status_code=400, detail="Invalid quadrant code. Use Q1, Q2, Q3, Q4 or ALL")

    query = db.query(ResearchSubmission)
    if user.role == "participant": query=query.filter_by(user_id=user.id)
    if quadrant != "ALL":
        query = query.filter(ResearchSubmission.disagreement_quadrant == quadrant)
    
    submissions = query.order_by(ResearchSubmission.created_at.desc()).all()
    results = []
    for s in submissions:
        item = db.query(ResearchChallengeItem).filter(ResearchChallengeItem.id == s.item_id).first()
        try:
            clues = json.loads(s.clue_tags)
        except:
            clues = []
        try:
            temporal = json.loads(s.inference_metadata or "{}").get("temporal_scores", [])
        except:
            temporal = []

        results.append({
            "submission_id": s.id,
            "model_id": s.model_id,
            "model_name": s.model_name,
            "checkpoint_epoch": s.checkpoint_epoch,
            "inference_metadata": json.loads(s.inference_metadata or "{}"),
            "item_id": s.item_id,
            "title": item.title if item else f"Item #{s.item_id}",
            "media_url": item.media_path if item else "",
            "ground_truth": s.ground_truth,
            "human_prediction": s.human_prediction,
            "human_confidence": s.human_confidence,
            "is_human_correct": s.is_human_correct,
            "ai_prediction": s.ai_prediction,
            "ai_confidence": round(s.ai_confidence * 100, 1),
            "is_ai_correct": s.is_ai_correct,
            "disagreement_quadrant": s.disagreement_quadrant,
            "reaction_time_ms": s.reaction_time_ms,
            "clue_tags": clues,
            "temporal_anomaly_scores": temporal,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return results

@router.get("/export/csv")
def export_research_data_csv(user=Depends(current_user), db: Session = Depends(get_db)):
    """
    Exports all human-AI evaluation trials as a CSV formatted for research papers / pandas / SPSS.
    """
    if user.role not in ("admin","researcher"): raise HTTPException(403,"Researcher access required for exports")
    submissions = db.query(ResearchSubmission).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Submission_ID",
        "Timestamp",
        "User_ID",
        "Item_ID",
        "Ground_Truth",
        "Human_Prediction",
        "Human_Confidence_1to5",
        "Human_Correct",
        "Reaction_Time_MS",
        "AI_Prediction",
        "AI_Confidence",
        "AI_Correct",
        "Disagreement_Quadrant",
        "Clue_Tags", "Model_SHA256", "Model_Name", "Checkpoint_Epoch", "Inference_Metadata"
    ])

    for s in submissions:
        writer.writerow([
            s.id,
            s.created_at.isoformat(),
            s.user_id,
            s.item_id,
            s.ground_truth,
            s.human_prediction,
            s.human_confidence,
            s.is_human_correct,
            s.reaction_time_ms,
            s.ai_prediction,
            s.ai_confidence,
            s.is_ai_correct,
            s.disagreement_quadrant,
            s.clue_tags, s.model_id, s.model_name, s.checkpoint_epoch, s.inference_metadata
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=human_ai_evaluation_dataset.csv"}
    )

@router.get("/export/json")
def export_research_data_json(user=Depends(current_user), db: Session = Depends(get_db)):
    """
    Exports all human-AI evaluation trials as clean structured JSON.
    """
    if user.role not in ("admin","researcher"): raise HTTPException(403,"Researcher access required for exports")
    submissions = db.query(ResearchSubmission).all()
    data = [
        {
            "submission_id": s.id,
            "model_id": s.model_id,
            "model_name": s.model_name,
            "checkpoint_epoch": s.checkpoint_epoch,
            "inference_metadata": json.loads(s.inference_metadata or "{}"),
            "timestamp": s.created_at.isoformat(),
            "user_id": s.user_id,
            "item_id": s.item_id,
            "ground_truth": s.ground_truth,
            "human_prediction": s.human_prediction,
            "human_confidence": s.human_confidence,
            "human_correct": s.is_human_correct,
            "reaction_time_ms": s.reaction_time_ms,
            "ai_prediction": s.ai_prediction,
            "ai_confidence": s.ai_confidence,
            "ai_correct": s.is_ai_correct,
            "disagreement_quadrant": s.disagreement_quadrant,
            "clue_tags": json.loads(s.clue_tags) if s.clue_tags else []
        }
        for s in submissions
    ]
    return data
