# backend/main.py
import os
import traceback
import logging
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# import your routes and db objects
from . import routes
from .db import engine, Base

# load env
load_dotenv()

# configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sagri-api")

app = FastAPI(title="Smart Agriculture Advisor API", docs_url="/api/docs", openapi_url="/api/openapi.json")

# CORS: allow configuring via env ALLOWED_ORIGINS (comma-separated). If not set, allow all (dev).
_allowed = os.getenv("ALLOWED_ORIGINS", "*")
if _allowed.strip() == "*" or not _allowed:
    allow_origins: List[str] = ["*"]
else:
    allow_origins = [o.strip() for o in _allowed.split(",") if o.strip()]

logger.info("CORS allow_origins=%s", allow_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routes under /api prefix (frontend expects e.g. /api/predict_crop)
app.include_router(routes.router, prefix="/api")

# mount frontend static files automatically if folder exists
STATIC_CANDIDATES = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "pages")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pages")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static")),
]

mounted = False
for candidate in STATIC_CANDIDATES:
    if os.path.isdir(candidate):
        try:
            mount_path = "/"
            app.mount(mount_path, StaticFiles(directory=candidate), name="static")
            logger.info("Mounted static files from %s at %s", candidate, mount_path)
            mounted = True
            break
        except Exception as e:
            logger.warning("Failed to mount static from %s: %s", candidate, e)

if not mounted:
    logger.info("No frontend static directory found in candidates: %s", STATIC_CANDIDATES)

# Ensure uploads directory is mounted so saved images (from /ml_models/uploads) can be served
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_models", "uploads"))
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # mount at /uploads so saved paths like /path/to/uploads/xxx.jpg can be resolved by frontend to /uploads/xxx.jpg
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
    logger.info("Mounted uploads directory at /uploads -> %s", UPLOAD_DIR)
except Exception as e:
    logger.warning("Failed to mount uploads directory %s: %s", UPLOAD_DIR, e)

# Use a flag so load_models_at_startup is not invoked multiple times accidentally
_models_loaded = False

@app.on_event("startup")
async def on_startup():
    global _models_loaded
    # create DB tables (safe no-op if already exists)
    try:
        logger.info("Ensuring database tables exist...")
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.exception("Error creating tables: %s", e)

    # load ML models (safe-call)
    if not _models_loaded:
        try:
            logger.info("Loading ML models via routes.load_models_at_startup() ...")
            # call the loader function from routes module (it handles exceptions internally)
            routes.load_models_at_startup()
            _models_loaded = True
            logger.info("Model loader finished.")
        except Exception:
            logger.exception("Unexpected error while loading models on startup.")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down Smart Agriculture Advisor API...")

# simple health check (no prefix)
@app.get("/health")
async def health():
    return {"status": "ok"}

# central error handler for 500s to avoid leaking stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # log stack trace server-side
    logger.error("Unhandled exception for request=%s %s", request.method, request.url)
    logger.exception(exc)
    # return sanitized response
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# add a small index route to redirect to frontend landing if frontend was mounted
@app.get("/")
async def index():
    if mounted:
        return JSONResponse({"detail": "Frontend static files are being served from the server root."})
    else:
        return JSONResponse({"detail": "API is running. No frontend static files detected on server."})
