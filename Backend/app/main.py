import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from .config import CORS_ORIGINS, STATIC_DIR, MODEL_NAME, CHECKPOINT_PATH
from .database import engine, Base, SessionLocal
from .data.sample_dataset import seed_database
from .services.vit_lstm import model_manager
from .routers import auth, game, rooms, research, detector, dashboard, admin, profile, analytics, product
from .security import current_user

# Versioned, non-destructive schema migration (also supports alembic upgrade head).
from .migrate import upgrade
upgrade()

# Index videos on startup
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title="Deepfake Literacy & Human-AI Evaluation API",
    description="Backend API powering Deepfake Literacy, Real vs Fake Multiplayer, Swin + DCT + Transformer Detection, and Explainable AI (XAI) Evaluation.",
    version="1.0.0"
)

from .services.media_store import StorageUnavailable
@app.exception_handler(StorageUnavailable)
async def media_storage_error(request,exc):
    return JSONResponse({'detail':str(exc)},status_code=503)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_security(request: Request, call_next):
    length = request.headers.get('content-length')
    if length:
        try:
            if int(length) > 50_000_000 + 1024 * 1024:
                return JSONResponse({'detail': 'Maximum video size is 50 MB.'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': 'Invalid request size.'}, status_code=400)
    if request.method in ("POST","PATCH","PUT","DELETE"):
        origin=request.headers.get("origin")
        if not origin and request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-site request is not allowed'}, status_code=403)
        if origin and origin not in CORS_ORIGINS:
            return JSONResponse({"detail":"Request origin is not allowed"},status_code=403)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/media/"):
        response.headers["Cache-Control"]="no-store"
    return response

# Mount static files for media & presets
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register routers
app.include_router(auth.router)
from .routers import mobile_bridge
app.include_router(mobile_bridge.router)
from .routers import google_auth
app.include_router(google_auth.router)
app.include_router(game.router)
app.include_router(rooms.router)
app.include_router(research.router)
app.include_router(detector.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
from .routers import admin_accounts
app.include_router(admin_accounts.router)
from .routers import admin_content
app.include_router(admin_content.router)
app.include_router(admin_content.public)
from .routers import admin_records
app.include_router(admin_records.router)
app.include_router(profile.router)
app.include_router(analytics.router)
app.include_router(product.router)
from .routers import mobile_overlay
app.include_router(mobile_overlay.router)
from .routers import mobile_workspace
app.include_router(mobile_workspace.router)
from .routers import mobile_compat
app.include_router(mobile_compat.router)
mobile_workspace.initialize()

@app.on_event("startup")
async def recover_rooms():
    from .models.db_models import TrainingJob
    with SessionLocal() as session:
        session.query(TrainingJob).filter_by(status="running").update({"status":"interrupted","message":"Server restarted; start a new candidate job."})
        session.commit()
    await rooms.recover()
    from .services.scan_queue import recover
    recover()

@app.get("/")
def health_check():
    from .services.remote_inference import status as inference_status
    return {
        "status": "online",
        "service": "Deepfake Literacy & Human-AI Evaluation Platform",
        "inference_service": inference_status(),
        "model_status": {
            "name": MODEL_NAME,
            "checkpoint_present": CHECKPOINT_PATH.is_file(),
            "checkpoint_sha256": model_manager.checkpoint_sha256,
            "checkpoint_epoch": model_manager.checkpoint_epoch,
            "last_error": model_manager.last_error,
            "custom_checkpoint_loaded": model_manager.is_custom_checkpoint_loaded,
            "device": str(model_manager.device)
        },
        "modules": [
            "Learn (Tutorials & Scam Simulations)",
            "Play (Solo & Multiplayer Rooms)",
            "Detect (Swin + DCT + Transformer Detector & Presets)",
            "Research Challenge (Human-AI Judgments)",
            "Explainable AI (Spatial & Temporal Saliency)",
            "Research Dashboard (KPIs, Confusion Matrix, CSV Export)"
        ]
    }
