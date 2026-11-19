"""
Synaptix - Multi-Agent AI Personal Productivity Assistant
FastAPI Main Application Entrypoint
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.tasks import router as tasks_router
from app.api.notes import router as notes_router
from app.api.calendar import router as calendar_router
from app.config import get_settings

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] %(message)s"
)
logger = logging.getLogger("synaptix")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs startup checks and shutdown cleanup.
    """
    settings = get_settings()
    logger.info("==================================================")
    logger.info(" Starting Synaptix AI Assistant (Milestone 1)")
    logger.info(" Environment: %s", settings.ENVIRONMENT)
    logger.info(" Host: %s | Port: %d", settings.HOST, settings.PORT)
    logger.info(" Zero-Cost Policy: Active (₹0 Budget Enforced)")
    logger.info("==================================================")
    yield
    logger.info("Shutting down Synaptix AI Assistant. Goodbye!")


settings = get_settings()

app = FastAPI(
    title="Synaptix AI Assistant",
    description="Multi-Agent AI Personal Productivity Assistant",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# CORS Middleware (Allows frontend development & API access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(tasks_router)
app.include_router(notes_router)
app.include_router(calendar_router)

# Mount Static Files
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the single-page application dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Synaptix backend is running. Frontend static files not found.",
        "health_check": "/api/health",
        "docs": "/docs",
    }
