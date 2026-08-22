"""
Multi-Signal Question Ranking Engine.
Computes weighted composite relevance scores using semantic vectors, JD context, resume context, and strategy fit.
Conforms to Blueprint Section 12 (points 21 & 26).
"""

from typing import Dict, Any, List, Optional
from app.rag.embeddings import EmbeddingService

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
        self.final_score: float = 0.0
        self.selection_rationale: str = ""

class QuestionRanker:
    """Ranks question candidates using the weighted multi-signal blueprint formula."""

    # Blueprint Section 12 formula weights:
    WEIGHT_SKILL = 0.40
    WEIGHT_JD = 0.25
    WEIGHT_RESUME = 0.15
    WEIGHT_ROLE = 0.10
    WEIGHT_STRATEGY = 0.10

    @classmethod
    def score_candidate(
        cls,
        candidate: QuestionCandidate,
        target_skill_vec: Optional[List[float]],
        jd_vec: Optional[List[float]],
        resume_vec: Optional[List[float]],
        target_role_family: str,
        target_category: str,
        target_difficulty: str,
        is_missing_skill: bool = False
    ) -> float:
        """
        Calculates the combined score for a question candidate:
        final_score = 0.40 * skill + 0.25 * jd + 0.15 * resume + 0.10 * role_category + 0.10 * difficulty_strategy
        """
        q_vec = candidate.vector_embedding

        # 1. Semantic Skill Relevance (0.40)
        if q_vec and target_skill_vec:
            candidate.semantic_skill_relevance = EmbeddingService.cosine_similarity(q_vec, target_skill_vec)
        else:
            candidate.semantic_skill_relevance = 0.60

        # 2. JD Relevance (0.25)
        if q_vec and jd_vec:
            candidate.jd_relevance = EmbeddingService.cosine_similarity(q_vec, jd_vec)
        else:
            candidate.jd_relevance = 0.50

        # 3. Resume Relevance (0.15)
        if q_vec and resume_vec:
            candidate.resume_relevance = EmbeddingService.cosine_similarity(q_vec, resume_vec)
        else:
            candidate.resume_relevance = 0.50

        # 4. Role / Category Match (0.10)
        cat_match = 1.0 if candidate.category == target_category else 0.4
        role_match = 1.0 if (candidate.role and target_role_family.lower() in candidate.role.lower()) else 0.6
        candidate.role_category_match = (cat_match * 0.6) + (role_match * 0.4)

        # 5. Difficulty / Strategy Fit (0.10)
        diff_score = 1.0 if candidate.difficulty == target_difficulty else 0.7
        missing_boost = 0.3 if is_missing_skill else 0.0
        candidate.difficulty_strategy_fit = min(1.0, diff_score + missing_boost)

        # Calculate Final Weighted Composite Score
        candidate.final_score = (
            cls.WEIGHT_SKILL * candidate.semantic_skill_relevance +
            cls.WEIGHT_JD * candidate.jd_relevance +
            cls.WEIGHT_RESUME * candidate.resume_relevance +
            cls.WEIGHT_ROLE * candidate.role_category_match +
            cls.WEIGHT_STRATEGY * candidate.difficulty_strategy_fit
        )

        # Construct Explainable Selection Rationale (Blueprint Section 12.26)
        reasons = []
        if is_missing_skill:
            reasons.append(f"Probes identified JD skill gap ({candidate.skill_name or candidate.topic})")
        elif candidate.skill_name:
            reasons.append(f"Validates core competency in {candidate.skill_name}")
        
        reasons.append(f"Category {candidate.category} ({candidate.difficulty})")
        reasons.append(f"Semantic match: {round(candidate.semantic_skill_relevance * 100)}%")

        candidate.selection_rationale = "; ".join(reasons)
        return candidate.final_score
