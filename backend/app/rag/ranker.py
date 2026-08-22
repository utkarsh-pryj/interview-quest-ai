"""
Multi-Signal Question Ranking Engine.
Computes weighted composite relevance scores using semantic vectors, JD context, resume context, and strategy fit.
Conforms to RAG Multi-Signal Ranking specifications.
"""

from typing import Dict, Any, List, Optional
from app.rag.embeddings import EmbeddingService
from app.core.config import settings

class QuestionCandidate:
    def __init__(
        self,
        question_id: str,
        question_text: str,
        ideal_answer: Optional[str],
        category: str,
        difficulty: str,
        role: Optional[str],
        topic: Optional[str],
        skill_id: Optional[str],
        skill_name: Optional[str],
        source_type: str = "RAG_RETRIEVAL",
        vector_embedding: Optional[List[float]] = None
    ):
        self.question_id = question_id
        self.question_text = question_text
        self.ideal_answer = ideal_answer
        self.category = category
        self.difficulty = difficulty
        self.role = role
        self.topic = topic
        self.skill_id = skill_id
        self.skill_name = skill_name
        self.source_type = source_type
        self.vector_embedding = vector_embedding

        # Scoring components
        self.semantic_skill_relevance: float = 0.0
        self.jd_relevance: float = 0.0
        self.resume_relevance: float = 0.0
        self.role_category_match: float = 0.0
        self.difficulty_strategy_fit: float = 0.0
        self.duplicate_penalty: float = 0.0
        self.final_score: float = 0.0
        self.selection_rationale: str = ""

    def get_score_breakdown(self) -> Dict[str, Any]:
        """Return explainable internal score breakdown."""
        return {
            "question_id": self.question_id,
            "final_score": round(self.final_score, 3),
            "semantic_skill_relevance": round(self.semantic_skill_relevance, 3),
            "jd_relevance": round(self.jd_relevance, 3),
            "resume_relevance": round(self.resume_relevance, 3),
            "role_category_match": round(self.role_category_match, 3),
            "difficulty_strategy_fit": round(self.difficulty_strategy_fit, 3),
            "duplicate_penalty": round(self.duplicate_penalty, 3),
            "selection_rationale": self.selection_rationale
        }

class QuestionRanker:
    """Ranks question candidates using configurable multi-signal formula."""

    @classmethod
    def score_candidate(
        cls,
        candidate: QuestionCandidate,
        target_skill_vec: Optional[List[float]],
        jd_vec: Optional[List[float]],
        resume_vec: Optional[List[float]],
        target_role_family: str,
        target_category: str,
        target_difficulty: str = "INTERMEDIATE",
        is_missing_skill: bool = False
    ) -> float:
        """
        Calculates configurable weighted multi-signal score:
        final_score = w_skill * skill + w_jd * jd + w_res * resume + w_role * role + w_strat * strategy - penalty
        """
        q_vec = candidate.vector_embedding

        # 1. Semantic Skill Relevance
        if q_vec and target_skill_vec:
            candidate.semantic_skill_relevance = EmbeddingService.cosine_similarity(q_vec, target_skill_vec)
        else:
            candidate.semantic_skill_relevance = 0.60

        # 2. JD Relevance
        if q_vec and jd_vec:
            candidate.jd_relevance = EmbeddingService.cosine_similarity(q_vec, jd_vec)
        else:
            candidate.jd_relevance = 0.50

        # 3. Resume Relevance
        if q_vec and resume_vec:
            candidate.resume_relevance = EmbeddingService.cosine_similarity(q_vec, resume_vec)
        else:
            candidate.resume_relevance = 0.50

        # 4. Role / Category Match
        cat_match = 1.0 if candidate.category == target_category else 0.45
        role_match = 1.0 if (candidate.role and target_role_family.lower() in candidate.role.lower()) else 0.60
        candidate.role_category_match = (cat_match * 0.6) + (role_match * 0.4)

        # 5. Difficulty / Strategy Fit (Gives targeted boost to missing required skills)
        diff_score = 1.0 if candidate.difficulty == target_difficulty else 0.70
        missing_boost = 0.30 if is_missing_skill else 0.0
        candidate.difficulty_strategy_fit = min(1.0, diff_score + missing_boost)

        # Read weights dynamically from configuration
        w_skill = settings.RANKING_WEIGHT_SKILL
        w_jd = settings.RANKING_WEIGHT_JD
        w_resume = settings.RANKING_WEIGHT_RESUME
        w_role = settings.RANKING_WEIGHT_ROLE
        w_strategy = settings.RANKING_WEIGHT_STRATEGY

        # Calculate Final Weighted Composite Score
        candidate.final_score = max(0.0, (
            w_skill * candidate.semantic_skill_relevance +
            w_jd * candidate.jd_relevance +
            w_resume * candidate.resume_relevance +
            w_role * candidate.role_category_match +
            w_strategy * candidate.difficulty_strategy_fit -
            candidate.duplicate_penalty
        ))

        # Construct Explainable Selection Rationale
        reasons = []
        if is_missing_skill:
            reasons.append(f"Probes identified JD skill gap ({candidate.skill_name or candidate.topic})")
        elif candidate.skill_name:
            reasons.append(f"Validates core competency in {candidate.skill_name}")
        
        reasons.append(f"Category {candidate.category} ({candidate.difficulty})")
        reasons.append(f"Semantic match: {round(candidate.semantic_skill_relevance * 100)}%")

        candidate.selection_rationale = "; ".join(reasons)
        return candidate.final_score
