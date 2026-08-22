"""
Explicit Retrieval Confidence Router.
Calculates transparent multi-factor confidence scores to govern when questions are returned directly vs when Gemini fallback is triggered.
Conforms to RAG Confidence Decision specifications.
"""

from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import logger

class ConfidenceReport:
    def __init__(
        self,
        confidence_score: float,
        level: str, # "HIGH", "MEDIUM", "LOW"
        top_similarity: float,
        skill_coverage_ratio: float,
        role_match_ratio: float,
        candidate_density: float,
        covered_skills: List[str],
        uncovered_skills: List[str],
        decision_reason: str
    ):
        self.confidence_score = round(confidence_score, 3)
        self.level = level
        self.top_similarity = round(top_similarity, 3)
        self.skill_coverage_ratio = round(skill_coverage_ratio, 3)
        self.role_match_ratio = round(role_match_ratio, 3)
        self.candidate_density = round(candidate_density, 3)
        self.covered_skills = covered_skills
        self.uncovered_skills = uncovered_skills
        self.decision_reason = decision_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score": self.confidence_score,
            "level": self.level,
            "top_similarity": self.top_similarity,
            "skill_coverage_ratio": self.skill_coverage_ratio,
            "role_match_ratio": self.role_match_ratio,
            "candidate_density": self.candidate_density,
            "covered_skills": self.covered_skills,
            "uncovered_skills": self.uncovered_skills,
            "decision_reason": self.decision_reason
        }

class RetrievalConfidenceRouter:
    """
    Evaluates measurable confidence of retrieved question candidates against target interview requirements.
    """

    @classmethod
    def evaluate_retrieval_confidence(
        cls,
        candidates: List[Any],
        target_role_family: str,
        target_skills: List[Dict[str, Any]],
        total_questions_needed: int
    ) -> ConfidenceReport:
        """
        Computes composite confidence:
        C = 0.35 * top_similarity + 0.35 * skill_coverage + 0.15 * role_match + 0.15 * candidate_density
        """
        if not candidates:
            return ConfidenceReport(
                confidence_score=0.0,
                level="LOW",
                top_similarity=0.0,
                skill_coverage_ratio=0.0,
                role_match_ratio=0.0,
                candidate_density=0.0,
                covered_skills=[],
                uncovered_skills=[s.get("canonical_name", "Skill") for s in target_skills],
                decision_reason="No question candidates were retrieved from knowledge base."
            )

        # 1. Top Similarity Score (0.35)
        top_similarity = max((c.semantic_skill_relevance for c in candidates), default=0.0)

        # 2. Skill Gap Coverage Ratio (0.35)
        all_target_names = {s.get("canonical_name", "").lower() for s in target_skills if s.get("canonical_name")}
        candidate_skill_names = {c.skill_name.lower() for c in candidates if getattr(c, "skill_name", None)}
        
        covered_names = all_target_names.intersection(candidate_skill_names)
        uncovered_names = all_target_names.difference(candidate_skill_names)

        skill_coverage_ratio = (len(covered_names) / len(all_target_names)) if all_target_names else 1.0

        # 3. Role Match Ratio (0.15)
        role_matches = sum(
            1 for c in candidates 
            if c.role and target_role_family.lower() in c.role.lower()
        )
        role_match_ratio = (role_matches / len(candidates)) if candidates else 0.0

        # 4. Candidate Density (0.15) - ratio of candidates meeting solid threshold (>= 0.60)
        solid_count = sum(1 for c in candidates if getattr(c, "final_score", 0.0) >= 0.60)
        candidate_density = min(1.0, (solid_count / max(1, total_questions_needed)))

        # Composite Confidence Formula
        confidence_score = (
            0.35 * top_similarity +
            0.35 * skill_coverage_ratio +
            0.15 * role_match_ratio +
            0.15 * candidate_density
        )

        # Classify Level
        high_thresh = settings.CONFIDENCE_HIGH_THRESHOLD
        med_thresh = settings.CONFIDENCE_MEDIUM_THRESHOLD

        if confidence_score >= high_thresh and len(candidates) >= total_questions_needed:
            level = "HIGH"
            reason = f"High retrieval confidence ({round(confidence_score, 2)} >= {high_thresh}). Knowledge base covers target skills and role. Returning direct grounded questions."
        elif confidence_score >= med_thresh:
            level = "MEDIUM"
            reason = f"Medium retrieval confidence ({round(confidence_score, 2)}). Sufficient candidate pool with minor skill gap. Augmenting only uncovered skills if needed."
        else:
            level = "LOW"
            reason = f"Low retrieval confidence ({round(confidence_score, 2)} < {med_thresh}). Knowledge base lacks strong match for {len(uncovered_names)} skills or target role. Triggering Gemini fallback."

        return ConfidenceReport(
            confidence_score=confidence_score,
            level=level,
            top_similarity=top_similarity,
            skill_coverage_ratio=skill_coverage_ratio,
            role_match_ratio=role_match_ratio,
            candidate_density=candidate_density,
            covered_skills=list(covered_names),
            uncovered_skills=list(uncovered_names),
            decision_reason=reason
        )
