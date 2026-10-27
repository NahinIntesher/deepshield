from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr

# --- User & Auth Schemas ---
class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

class UserSignupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=r'^[A-Za-z0-9_.-]+$')
    display_name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr = Field(max_length=254)
    language: str = Field(default='en', pattern=r'^(en|bn)$')

class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    score: int
    games_played: int
    total_correct: int
    total_rounds_played: int
    accuracy: float
    qualified_for_research: bool
    has_password: bool = True
    needs_profile: bool = False

    class Config:
        from_attributes = True

class RoleUpdateRequest(BaseModel):
    role: str  # "participant" or "researcher"

# --- Game & Room Schemas ---
class CreateRoomRequest(BaseModel):
    user_id: int
    total_rounds: Optional[int] = 5

class JoinRoomRequest(BaseModel):
    room_code: str
    user_id: int
    display_name: str

class SubmitAnswerRequest(BaseModel):
    ticket: Optional[str] = None
    room_code: Optional[str] = None
    user_id: int
    item_id: int
    prediction: str  # "Real" or "Fake"
    time_taken_ms: int

class AnswerResultResponse(BaseModel):
    ai_prediction: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_error: Optional[str] = None
    item_id: int
    is_correct: bool
    ground_truth: str
    points_awarded: int
    explanation: str
    visual_cues: List[str]
    manipulation_type: str

class SoloGameSubmitRequest(BaseModel):
    user_id: int
    rounds: List[Dict[str, Any]]  # List of {item_id, prediction, time_taken_ms}

# --- Research Challenge Schemas ---
class ResearchItemResponse(BaseModel):
    id: int
    title: str
    media_type: str
    media_url: str
    thumbnail_url: Optional[str] = None
    manipulation_type: str
    difficulty: str
    description: Optional[str] = None
    visual_cues: List[str]

class ResearchSubmissionRequest(BaseModel):
    user_id: int
    item_id: int
    human_prediction: str  # "Real" or "Fake"
    human_confidence: int = Field(..., ge=1, le=5)
    clue_tags: List[str]
    reaction_time_ms: int

class ResearchSubmissionResponse(BaseModel):
    analysis: Optional[Dict[str, Any]] = None
    model_id: Optional[str] = None
    model_name: Optional[str] = None
    checkpoint_epoch: Optional[int] = None
    xai_error: Optional[str] = None
    submission_id: int
    item_id: int
    ground_truth: str
    human_prediction: str
    human_confidence: int
    is_human_correct: bool
    ai_prediction: str
    ai_confidence: float
    is_ai_correct: bool
    disagreement_quadrant: str  # Q1, Q2, Q3, Q4
    quadrant_description: str
    explanation: str
    xai_heatmap_url: Optional[str] = None
    temporal_anomaly_scores: List[float]

# --- AI Detector Schemas ---
class DetectionResult(BaseModel):
    shap_explanation: Optional[Dict[str, Any]] = None
    shap_error: Optional[str] = None
    explanation_method: Optional[str] = None
    media_type: str = 'video'
    analysis_mode: str = 'video_sequence'
    experimental: bool = False
    analysis_warning: Optional[str] = None
    temporal_analysis_available: bool = True
    detection_id: Optional[int] = None
    frame_details: List[Dict[str, Any]] = Field(default_factory=list)
    focus_frame: Optional[int] = None
    model_id: Optional[str] = None
    checkpoint_epoch: Optional[int] = None
    fusion_gates: Dict[str, float] = Field(default_factory=dict)
    frame_indices: List[int] = Field(default_factory=list)
    detected_frames: Optional[int] = None
    repeated_frames: Optional[int] = None
    xai_error: Optional[str] = None
    verdict: str  # "Real" or "Fake"
    fake_probability: float
    confidence_percentage: float
    model_name: str
    model_checkpoint_loaded: bool
    spatial_heatmap_base64: Optional[str] = None
    temporal_scores: List[float]
    detected_artifacts: List[str]
    verification_tips: List[str]

# --- Dashboard & Analytics Schemas ---
class PerformanceMetrics(BaseModel):
    total_evaluations: int
    human_accuracy: float
    human_precision: float
    human_recall: float
    human_f1: float
    ai_accuracy: float
    ai_precision: float
    ai_recall: float
    ai_f1: float
    hybrid_accuracy: float  # Human + AI complementary ensemble
    human_confusion_matrix: Dict[str, int]  # TP, FP, TN, FN
    ai_confusion_matrix: Dict[str, int]     # TP, FP, TN, FN
    quadrant_breakdown: Dict[str, int]      # Q1, Q2, Q3, Q4 counts
    calibration_data: List[Dict[str, Any]]
