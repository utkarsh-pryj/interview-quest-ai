# InterviewQuest AI — Technical Architecture Summary

This document provides an exact, engineering-level summary of the RAG implementation and architectural decisions in InterviewQuest AI. It reflects the true implemented functionality.

## 1. Exact Architecture
- **Frontend**: React + Vite
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL (Supabase) with `pgvector` for semantic similarity search
- **RAG Orchestration**: Custom Python modular pipeline (no LangChain overhead)
- **LLM**: Gemini API (used exclusively as a fallback and for advanced evaluation)
- **Authentication**: JWT-based session management

## 2. Exact Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Why**: Selected as a fast, locally executable, open-source model that generates high-quality semantic embeddings without incurring per-token API costs. It ensures offline question indexing and runtime query embedding are deterministic and identical.

## 3. Exact Vector Dimension
- **Dimension**: `384` (unit-normalized)

## 4. Exact Retrieval Method
- **Stage 1**: Candidate generation via PostgreSQL `pgvector`. Uses the `<=>` cosine distance operator to retrieve the top 40 initial candidates directly at the database level.
- **Stage 2**: Application-level reranking, diversity filtering (MMR), and confidence routing in memory on the backend.

## 5. Exact Database/Vector Index
- **Index/Column**: `embedding vector(384)`
- **Query Operator**: Cosine distance (`<=>`) matching between the stored `embedding` column and the runtime context vector.

## 6. Exact Ranking Formula
The `QuestionRanker` uses a multi-signal weighted formula combining various features to ensure business relevance:
- `FinalScore = (0.40 * Skill Match) + (0.25 * JD Relevance) + (0.15 * Resume Relevance) + (0.10 * Role Alignment) + (0.10 * Strategy Fit) - (Diversity/Duplicate Penalty)`
- The diversity penalty is computed using a Maximum Marginal Relevance (MMR) filter with a similarity ceiling of `0.80` to prevent redundant questions.

## 7. Exact Confidence Logic
The `RetrievalConfidenceRouter` measures retrieval quality using a normalized score (C in [0, 1]):
- `C = 0.35 * Top Similarity + 0.35 * Skill Coverage + 0.15 * Role Match + 0.15 * Keyword Density`
- **HIGH** (`C >= 0.78`): Candidate questions are directly returned without invoking Gemini (Cost: $0).
- **MEDIUM** (`C >= 0.65`): Returned directly, with some gap-filling if specifically requested by the strategy.
- **LOW** (`C < 0.65`): Discards poor retrievals and escalates to the Gemini fallback generator.

## 8. Exact Gemini Fallback Conditions
Gemini is **not** used to generate every question. It is invoked *only* when:
1. `RetrievalConfidenceRouter` scores the retrieved candidates as **LOW**.
2. A critical JD requirement (skill) has absolute zero coverage in the retrieved candidate pool.
3. The interview strategy demands a niche category entirely missing from the vector database.
When invoked, the prompt is highly constrained, providing only the missing context to avoid over-generation and control costs.

## 9. Exact Answer Evaluation Flow
A two-stage pipeline:
- **Stage 1 (Local/Deterministic)**: Evaluates semantic similarity, concept coverage (n-gram overlap against expected points), and structural completeness locally. Fast and free.
- **Stage 2 (Gemini Escalation)**: Only triggered for borderline scores (e.g., 40%–78%), deeply nuanced behavioral questions, or situational context. Gemini applies a structured 5-dimension rubric (Relevance, Accuracy, Concept Coverage, Clarity, Depth) returning JSON.

## 10. Exact Skill Matching Flow
Skill extraction operates outside the RAG vector loop:
1. **Document Parsing**: Resume and JD are chunked by section (Summary, Skills, Experience vs. Requirements).
2. **Canonical Mapping**: Raw text is mapped to a canonical taxonomy using a 3-tier hybrid approach: Exact Alias Match -> Normalized Text -> Conservative Semantic Similarity (threshold >= 0.78).
3. **Gap Analysis**: Identifies `matched_skills` and labels missing JD requirements explicitly as *"Not evidenced in resume"* rather than assuming the candidate lacks the skill.
4. **Context Construction**: These structured mappings form the plaintext payload embedded for semantic retrieval.

## 11. Why Each Technology Was Selected
- **FastAPI**: Asynchronous performance and native JSON schema validation via Pydantic.
- **PostgreSQL + pgvector**: Unified relational metadata storage and vector similarity without managing a separate vector DB infrastructure (like Pinecone or Milvus).
- **Custom RAG pipeline (No LangChain)**: Ensures explicitly readable ranking logic, measurable confidence metrics, precise token usage, and minimal abstraction layers—critical for a maintainable, latency-sensitive production service.
- **Sentence-Transformers**: Free, robust local embeddings for high-quality semantic similarity.

## 12. Current Limitations
- The semantic embedding model (`all-MiniLM-L6-v2`) handles English text efficiently, but lacks strong cross-lingual support.
- Heavy PDF resumes with dense, non-standard layouts can degrade the document chunker's ability to cleanly isolate the "Skills" vs. "Experience" sections.
- The PostgreSQL `pgvector` implementation currently uses Exact Nearest Neighbor (KNN) via a sequential scan. This is perfectly fine for <1 million questions, but an HNSW index would be required at greater scales.

## 13. Future Improvements
- **HNSW Indexing**: Implement `CREATE INDEX ON interview_questions USING hnsw (embedding vector_cosine_ops);` for logarithmic scaling.
- **Dynamic Chunking**: Integrate a small local NER (Named Entity Recognition) model during ingestion to better isolate semantic skills across badly formatted PDFs.
- **Self-Reflective Logging**: Pipe confidence fallback metrics back into a dashboard to automatically flag which skills are missing from the question bank.
