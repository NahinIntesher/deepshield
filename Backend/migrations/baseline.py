"""Frozen v1 schema for legacy adoption. Do not modify when application models change."""
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    display_name = Column(String(64), nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(32), default="participant")  # "participant", "researcher", "admin"
    score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_rounds_played = Column(Integer, default=0)
    qualified_for_research = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submissions = relationship("ResearchSubmission", back_populates="user")
    game_sessions = relationship("GameSession", back_populates="user")

    @property
    def accuracy(self) -> float:
        if self.total_rounds_played == 0:
            return 0.0
        return round((self.total_correct / self.total_rounds_played) * 100, 1)


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(10), unique=True, index=True, nullable=False)
    host_user_id = Column(Integer, nullable=False)
    status = Column(String(32), default="waiting")  # "waiting", "playing", "finished"
    deadline = Column(Float, nullable=True)
    current_round = Column(Integer, default=0)
    total_rounds = Column(Integer, default=5)
    selected_items_json = Column(Text, default="[]")  # List of ChallengeItem IDs
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    participants = relationship("RoomParticipant", back_populates="room", cascade="all, delete-orphan")


class RoomParticipant(Base):
    __tablename__ = "room_participants"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    display_name = Column(String(64), nullable=False)
    score = Column(Integer, default=0)
    is_ready = Column(Boolean, default=False)
    last_answer = Column(String(32), nullable=True)
    last_answer_time_ms = Column(Integer, nullable=True)

    room = relationship("Room", back_populates="participants")


class ResearchChallengeItem(Base):
    __tablename__ = "research_challenge_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    media_type = Column(String(32), default="video")  # "video", "frames", "image"
    media_path = Column(String(256), nullable=False)
    thumbnail_path = Column(String(256), nullable=True)
    ground_truth = Column(String(16), nullable=False)  # "Real", "Fake"
    manipulation_type = Column(String(64), default="Original")  # "FaceSwap", "LipSync", "NeuralTextures", "FullSynthesis", "Original"
    difficulty = Column(String(32), default="Medium")  # "Easy", "Medium", "Hard"
    description = Column(Text, nullable=True)
    visual_cues = Column(Text, default="[]")  # JSON array of expected cues: ["Mouth/Teeth", "Eyes/Blink"]
    
    # Pre-calculated or baseline model outputs
    ai_prediction = Column(String(16), nullable=True)  # "Real", "Fake"
    ai_confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    ai_temporal_anomaly = Column(Text, default="[]")  # JSON array of 16 frame anomaly values
    xai_heatmap_path = Column(String(256), nullable=True)

    submissions = relationship("ResearchSubmission", back_populates="item")


class ResearchSubmission(Base):
    __tablename__ = "research_submissions"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("research_challenge_items.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Human input
    human_prediction = Column(String(16), nullable=False)  # "Real", "Fake"
    human_confidence = Column(Integer, nullable=False)  # 1 (Guess) to 5 (Certain)
    clue_tags = Column(Text, default="[]")  # JSON array of tagged clues
    reaction_time_ms = Column(Integer, default=0)

    # AI result snapshot
    ai_prediction = Column(String(16), nullable=False)
    ai_confidence = Column(Float, nullable=False)
    
    model_id = Column(String(64), nullable=True)
    model_name = Column(String(128), nullable=True)
    checkpoint_epoch = Column(Integer, nullable=True)
    inference_metadata = Column(Text, default="{}")

    # Ground truth snapshot
    ground_truth = Column(String(16), nullable=False)
    is_human_correct = Column(Boolean, nullable=False)
    is_ai_correct = Column(Boolean, nullable=False)
    
    # Academic 4-Quadrant Disagreement Category:
    # Q1: Human+ AI+ (Consensus Correct)
    # Q2: Human+ AI- (Model Blindspot)
    # Q3: Human- AI+ (Human Perception Limit)
    # Q4: Human- AI- (Edge Case Failure)
    disagreement_quadrant = Column(String(8), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="submissions")
    item = relationship("ResearchChallengeItem", back_populates="submissions")


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mode = Column(String(32), default="solo")  # "solo", "multiplayer"
    total_score = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_items = Column(Integer, default=5)
    accuracy = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="game_sessions")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires = Column(Float, nullable=False)

class VideoAttempt(Base):
    __tablename__ = "video_attempts"
    key = Column(String(128), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("research_challenge_items.id"), nullable=False)
    correct = Column(Boolean, nullable=False)

class SoloTicket(Base):
    __tablename__ = "solo_tickets"
    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False)
    item_id = Column(Integer, nullable=False)
    batch = Column(String(64), nullable=False)
    used = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    points = Column(Integer, default=0)
    correct = Column(Boolean, default=False)
    expires = Column(Float, nullable=False)

class LearningSample(Base):
    __tablename__ = "learning_samples"
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("research_submissions.id"), unique=True)
    item_id = Column(Integer, ForeignKey("research_challenge_items.id"), nullable=False)
    status = Column(String(32), default="pending")
    verified_label = Column(String(16), nullable=True)
    reviewer_id = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    note = Column(Text, default="")
