"""
InterviewQuest AI - Main FastAPI Application.
Conforms to Blueprint Section 16 & 22.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.api.auth import router as auth_router
from app.api.resumes import router as resumes_router
from app.api.job_descriptions import router as jd_router
from app.api.analysis import router as analysis_router
from app.api.interviews import router as interviews_router
from app.api.health import router as health_router
from app.db.base import Base
from app.db.session import async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    logger.info("Initializing InterviewQuest AI database tables...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")
    yield
    logger.info("Shutting down InterviewQuest AI application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Production-Oriented RAG Interview Platform",
    lifespan=lifespan
)

# Configure CORS (Permissive for local development and deployed Vercel frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(jd_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(interviews_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to InterviewQuest AI API",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )
