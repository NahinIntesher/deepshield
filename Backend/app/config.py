import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/".env")

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
DATA_ROOT = Path(os.getenv('DATA_ROOT',str(PROJECT_DIR / 'Database'))).expanduser()
MODEL_ROOT = Path(os.getenv('MODEL_ROOT',str(PROJECT_DIR / 'Model'))).expanduser()
DATA_ROOT.mkdir(parents=True,exist_ok=True)

# Database configuration (SQLite for seamless zero-config portability)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_ROOT / 'swin_research.db'}")

# Paths
CHECKPOINT_PATH = Path(os.getenv("CHECKPOINT_PATH",str(MODEL_ROOT / "best_model.pth")))
DATASET_DIR = DATA_ROOT / "dataset"
STATIC_DIR = BASE_DIR / "static"

# Research Qualification Criteria
QUALIFICATION_ACCURACY_THRESHOLD = float(os.getenv("QUALIFICATION_ACCURACY_THRESHOLD", "0.90"))  # Required overall game accuracy

# Game configuration
DEFAULT_ROUND_TIME_SECONDS = 10
DEFAULT_ROUNDS_PER_GAME = 5

# CORS configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001"
]

VIDEOS_DIR = Path(os.getenv('VIDEOS_DIR',str(MODEL_ROOT / 'videos'))).expanduser()

# Swin-Small + DCT + temporal transformer inference, matching training/model.py.
MODEL_NAME = "Swin-Small + DCT + Temporal Transformer"
NUM_FRAMES = 16
FACE_MODEL_ROOT = Path(os.getenv("INSIGHTFACE_ROOT", str(Path.home() / ".insightface"))).expanduser()
# Keep face detection on CPU to leave GPU memory for the Swin model.
FACE_PROVIDER = os.getenv("FACE_PROVIDER", "CPUExecutionProvider")

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv('COOKIE_SAMESITE','lax').lower()
if COOKIE_SAMESITE not in ('lax','strict','none') or (COOKIE_SAMESITE=='none' and not COOKIE_SECURE):
    raise RuntimeError('COOKIE_SAMESITE must be lax/strict, or none with COOKIE_SECURE=true.')

if os.getenv("CORS_ORIGINS"):
    CORS_ORIGINS = [origin.strip() for origin in os.environ["CORS_ORIGINS"].split(",") if origin.strip()]

QUALIFICATION_MIN_SCORE = int(os.getenv("QUALIFICATION_MIN_SCORE", "5000"))

CORS_ORIGINS += [v.strip() for v in os.getenv("EXTENSION_ORIGINS", "").split(",") if v.strip()]
