import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.session import AsyncSessionLocal, async_engine
from app.models.question import InterviewQuestion
from app.rag.embeddings import EmbeddingService
from app.core.logging import logger

async def create_vector_extension():
    try:
        async with async_engine.begin() as conn:
            logger.info("Ensuring pgvector extension is installed...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        logger.error(f"Failed to create pgvector extension. Ensure pgvector is installed in your PostgreSQL instance: {e}")
        # We don't raise here, so the script can still try to proceed or fail gracefully later.

async def index_questions(reindex: bool = False):
    async with AsyncSessionLocal() as db:
        if reindex:
            logger.info("Reindexing all questions. Ignoring existing embeddings.")
            stmt = select(InterviewQuestion)
        else:
            logger.info("Indexing only questions missing embeddings.")
            stmt = select(InterviewQuestion).filter(InterviewQuestion.embedding.is_(None))
        
        res = await db.execute(stmt)
        questions = res.scalars().all()

        if not questions:
            logger.info("No questions to index.")
            return

        logger.info(f"Generating embeddings for {len(questions)} questions using {EmbeddingService.get_model_name()}...")

        # Batch process
        batch_size = 32
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]
            for q in batch:
                # Construct meaningful text representation
                skill = q.primary_skill.canonical_name if getattr(q, 'primary_skill', None) else (q.topic or "General")
                content = f"[{q.category}] [{skill}] {q.question}"
                q.embedding = EmbeddingService.embed_text(content)
            
            await db.commit()
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(questions)-1)//batch_size + 1}")

        logger.info("Indexing complete.")

async def main():
    parser = argparse.ArgumentParser(description="Index questions for semantic retrieval.")
    parser.add_argument("--reindex", action="store_true", help="Re-embed all questions")
    args = parser.parse_args()

    await create_vector_extension()
    await index_questions(args.reindex)

if __name__ == "__main__":
    asyncio.run(main())
