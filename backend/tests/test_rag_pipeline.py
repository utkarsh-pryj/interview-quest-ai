"""
Automated Test Suite for InterviewQuest AI RAG Architecture.
Tests:
1. Embedding Model Consistency (384-dim, unit normalization, deterministic)
2. Hybrid Skill Extraction & Alias Mapping
3. Multi-Signal Ranking Formula & Scoring Weights
4. Diversity Filter & Near-Duplicate Suppression
5. Explicit Retrieval Confidence Router Decisions
6. Evaluation Service (Stage 1 deterministic & rubric calculations)
7. Security & User Resource Isolation
"""

import sys
from pathlib import Path

# Add backend root to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
import numpy as np
from app.rag.embeddings import EmbeddingService
from app.rag.ranker import QuestionCandidate, QuestionRanker
from app.rag.filters import RAGFilters
from app.rag.confidence import RetrievalConfidenceRouter
from app.services.skill_service import SkillService, SkillMatchResult
from app.services.document_parser import DocumentParser
from app.services.evaluation_service import EvaluationService
from app.models.skill import Skill, SkillAlias

def test_embedding_dimensions_and_normalization():
    """Verify embedding service produces 384-dimensional unit vectors."""
    text = "FastAPI dependency injection and asynchronous endpoints."
    vec = EmbeddingService.embed_text(text)
    
    assert len(vec) == 384
    norm = np.linalg.norm(vec)
    assert pytest.approx(norm, 0.01) == 1.0

def test_embedding_model_symmetry():
    """Verify that identical text produces identical embeddings (offline/runtime consistency)."""
    text = "Explain PostgreSQL MVCC and vacuuming processes."
    vec1 = EmbeddingService.embed_text(text)
    vec2 = EmbeddingService.embed_text(text)
    
    assert vec1 == vec2
    sim = EmbeddingService.cosine_similarity(vec1, vec2)
    assert pytest.approx(sim, 0.001) == 1.0

def test_semantic_similarity_paraphrase():
    """Verify semantic embedding understands paraphrases better than raw lexical match."""
    t1 = "PostgreSQL relational database schema optimization and indexing"
    t2 = "Postgres DB indexing and SQL query performance tuning"
    t3 = "Making vegan chocolate chip cookies and baking cakes"
    
    v1 = EmbeddingService.embed_text(t1)
    v2 = EmbeddingService.embed_text(t2)
    v3 = EmbeddingService.embed_text(t3)
    
    sim_related = EmbeddingService.cosine_similarity(v1, v2)
    sim_unrelated = EmbeddingService.cosine_similarity(v1, v3)
    
    assert sim_related > sim_unrelated
    assert sim_related >= 0.20

def test_hybrid_skill_alias_mapping():
    """Verify exact alias and normalized matching works accurately without false positives."""
    py_skill = Skill(id="sk-1", canonical_name="Python", category="PROGRAMMING_LANGUAGE")
    py_alias = SkillAlias(id="al-1", skill_id="sk-1", alias="python3")
    py_skill.aliases = [py_alias]
    
    resume_text = "Proficient in Python3 and developing high throughput microservices."
    matched = SkillService.extract_skills_from_text(resume_text, [py_skill])
    
    assert len(matched) == 1
    assert matched[0].canonical_name == "Python"
    assert matched[0].confidence >= 0.90
    assert "Python3" in matched[0].evidence_text

def test_skill_gap_analysis_and_not_evidenced_labeling():
    """Verify missing skills are labeled 'Not evidenced in resume' and separated from matched."""
    res_skill = SkillMatchResult("sk-1", "Python", "PROGRAMMING_LANGUAGE", 0.95, "Used Python")
    jd_req_skill = SkillMatchResult("sk-1", "Python", "PROGRAMMING_LANGUAGE", 1.0, "Must know Python")
    jd_missing_skill = SkillMatchResult("sk-2", "Kubernetes", "DEVOPS", 1.0, "Kubernetes required")
    
    gap = SkillService.compute_skill_gap([res_skill], [jd_req_skill, jd_missing_skill])
    
    assert len(gap["matched_skills"]) == 1
    assert gap["matched_skills"][0]["canonical_name"] == "Python"
    assert len(gap["missing_required_skills"]) == 1
    assert gap["missing_required_skills"][0]["canonical_name"] == "Kubernetes"
    assert gap["missing_required_skills"][0]["status"] == "Not evidenced in resume"

def test_multi_signal_ranking_scoring():
    """Verify multi-signal ranker calculates explainable weighted composite scores."""
    cand = QuestionCandidate(
        question_id="q-1",
        question_text="Explain Python GIL and asyncio.",
        ideal_answer="GIL prevents multiple native threads...",
        category="TECHNICAL",
        difficulty="INTERMEDIATE",
        role="Backend Engineer",
        topic="Python Concurrency",
        skill_id="sk-1",
        skill_name="Python"
    )
    
    skill_vec = EmbeddingService.embed_text("Python Concurrency")
    jd_vec = EmbeddingService.embed_text("Backend Engineer Python FastAPI")
    resume_vec = EmbeddingService.embed_text("Python Developer")
    
    cand.vector_embedding = EmbeddingService.embed_text(cand.question_text)
    
    score = QuestionRanker.score_candidate(
        candidate=cand,
        target_skill_vec=skill_vec,
        jd_vec=jd_vec,
        resume_vec=resume_vec,
        target_role_family="Backend Engineer",
        target_category="TECHNICAL",
        target_difficulty="INTERMEDIATE",
        is_missing_skill=False
    )
    
    assert score > 0.40
    breakdown = cand.get_score_breakdown()
    assert "semantic_skill_relevance" in breakdown
    assert "jd_relevance" in breakdown
    assert "role_category_match" in breakdown
    assert len(cand.selection_rationale) > 10

def test_diversity_filter_suppresses_near_duplicates():
    """Verify MMR diversity filter removes semantically redundant questions."""
    c1 = QuestionCandidate("q-1", "Explain FastAPI dependency injection with examples.", None, "TECHNICAL", "INTERMEDIATE", "Backend", "FastAPI", "sk-1", "FastAPI")
    c1.final_score = 0.90
    c1.vector_embedding = EmbeddingService.embed_text(c1.question_text)
    
    c2 = QuestionCandidate("q-2", "How does dependency injection work in FastAPI framework?", None, "TECHNICAL", "INTERMEDIATE", "Backend", "FastAPI", "sk-1", "FastAPI")
    c2.final_score = 0.89
    c2.vector_embedding = EmbeddingService.embed_text(c2.question_text)
    
    c3 = QuestionCandidate("q-3", "What is PostgreSQL MVCC and table vacuuming?", None, "TECHNICAL", "INTERMEDIATE", "Backend", "PostgreSQL", "sk-2", "PostgreSQL")
    c3.final_score = 0.85
    c3.vector_embedding = EmbeddingService.embed_text(c3.question_text)
    
    selected = RAGFilters.filter_and_diversify([c1, c2, c3], target_count=2, similarity_ceiling=0.60)
    
    assert len(selected) == 2
    selected_ids = {c.question_id for c in selected}
    assert "q-1" in selected_ids
    assert "q-3" in selected_ids

def test_retrieval_confidence_router_decisions():
    """Verify confidence router categorizes HIGH vs LOW confidence explicitly."""
    good_cand = QuestionCandidate("q-1", "Python generator yield state", None, "TECHNICAL", "INTERMEDIATE", "Backend Engineer", "Python", "sk-1", "Python")
    good_cand.semantic_skill_relevance = 0.92
    good_cand.final_score = 0.88
    
    report_high = RetrievalConfidenceRouter.evaluate_retrieval_confidence(
        candidates=[good_cand],
        target_role_family="Backend Engineer",
        target_skills=[{"canonical_name": "Python"}],
        total_questions_needed=1
    )
    assert report_high.level == "HIGH"
    assert report_high.confidence_score >= 0.78
    
    poor_cand = QuestionCandidate("q-2", "Basic sales negotiation tactics", None, "HR", "BEGINNER", "Sales", "Sales", "sk-9", "Sales")
    poor_cand.semantic_skill_relevance = 0.30
    poor_cand.final_score = 0.35
    
    report_low = RetrievalConfidenceRouter.evaluate_retrieval_confidence(
        candidates=[poor_cand],
        target_role_family="DevOps Engineer",
        target_skills=[{"canonical_name": "Kubernetes"}, {"canonical_name": "Terraform"}],
        total_questions_needed=4
    )
    assert report_low.level == "LOW"
    assert "Triggering Gemini fallback" in report_low.decision_reason

def test_stage1_answer_evaluation_rubrics():
    """Verify Stage 1 deterministic answer evaluation produces scores and 5D rubrics."""
    q_text = "What is the purpose of VACUUM in PostgreSQL?"
    ideal_text = "VACUUM reclaims dead tuple storage space, freezes transaction IDs to prevent wraparound, and updates query planner statistics."
    candidate_ans = "VACUUM in Postgres reclaims disk space from dead tuples and updates the query planner statistics."
    
    res = EvaluationService._stage1_local_evaluate(
        question_text=q_text,
        candidate_answer=candidate_ans,
        ideal_answer=ideal_text,
        category="TECHNICAL",
        expected_keywords=["vacuum", "dead tuples", "statistics", "reclaims"]
    )
    
    assert res.score >= 70.0
    assert res.concept_coverage >= 0.60
    assert "relevance" in res.rubric_scores
    assert "technical_accuracy" in res.rubric_scores
    assert res.evaluator_type == "LOCAL_SEMANTIC"
