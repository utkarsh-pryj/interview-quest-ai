from fastapi import APIRouter
from app.core.config import settings
from app.rag.embeddings import EmbeddingService
from app.llm.gemini import gemini_client

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check():
    """Health check reporting system status, embedding engine, and LLM readiness."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "embedding_model": EmbeddingService.get_model_name(),
        "gemini_configured": gemini_client.is_available(),
        "web_search_enabled": settings.WEB_SEARCH_ENABLED
    }
