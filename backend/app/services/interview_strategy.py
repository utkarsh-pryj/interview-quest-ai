"""
Role-Adaptive Interview Strategy Generator.
Calculates dynamic question quotas, skill gap allocations, and assessment categories based on JD & Resume analysis.
Conforms to Blueprint Section 11.
"""

from typing import Dict, Any, List
import math

class InterviewStrategyGenerator:
    """Generates an adaptive question quota budget tailored to the candidate's target role and skill gaps."""

    @classmethod
    def generate_strategy(
        cls,
        role_family: str,
        seniority: str,
        total_questions: int,
        matched_skills: List[Dict[str, Any]],
        missing_jd_skills: List[Dict[str, Any]],
        resume_only_skills: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Dynamically distributes question budget across categories and priority topics.
        Blueprint Section 11.
        """
        total = max(3, total_questions)

        # Baseline category weights based on role family
        if role_family in ["Backend Engineer", "Software Engineer", "Full Stack Engineer"]:
            base_weights = {
                "TECHNICAL": 0.35,
                "SYSTEM_DESIGN": 0.20 if seniority in ["Senior", "Lead / Staff", "Executive / Director"] else 0.10,
                "CODING": 0.20 if seniority in ["Fresher", "Junior", "Mid-Level"] else 0.15,
                "BEHAVIORAL": 0.15,
                "SITUATIONAL": 0.10,
                "DOMAIN": 0.05
            }
        elif role_family == "Frontend Engineer":
            base_weights = {
                "TECHNICAL": 0.45,
                "CODING": 0.20,
                "SYSTEM_DESIGN": 0.10,
                "BEHAVIORAL": 0.15,
                "SITUATIONAL": 0.10,
                "DOMAIN": 0.0
            }
        elif role_family in ["Data Analyst", "Data Scientist & ML"]:
            base_weights = {
                "TECHNICAL": 0.30,
                "DOMAIN": 0.30,
                "CODING": 0.15,
                "SYSTEM_DESIGN": 0.05,
                "BEHAVIORAL": 0.10,
                "SITUATIONAL": 0.10
            }
        elif role_family == "HR / Recruiter":
            base_weights = {
                "HR": 0.40,
                "SITUATIONAL": 0.30,
                "BEHAVIORAL": 0.25,
                "DOMAIN": 0.05,
                "TECHNICAL": 0.0,
                "CODING": 0.0,
                "SYSTEM_DESIGN": 0.0
            }
        elif role_family == "Sales & Business Development":
            base_weights = {
                "DOMAIN": 0.40,
                "SITUATIONAL": 0.30,
                "BEHAVIORAL": 0.25,
                "HR": 0.05,
                "TECHNICAL": 0.0,
                "CODING": 0.0,
                "SYSTEM_DESIGN": 0.0
            }
        else: # General / Cross-Functional
            base_weights = {
                "TECHNICAL": 0.25,
                "DOMAIN": 0.25,
                "BEHAVIORAL": 0.25,
                "SITUATIONAL": 0.25
            }

        # Filter out 0.0 categories and normalize weights to sum to 1.0
        active_weights = {k: v for k, v in base_weights.items() if v > 0}
        weight_sum = sum(active_weights.values())
        normalized_weights = {k: v / weight_sum for k, v in active_weights.items()}

        # Allocate integer question counts ensuring total matches exactly
        quotas: Dict[str, int] = {}
        allocated = 0
        sorted_cats = sorted(normalized_weights.items(), key=lambda x: x[1], reverse=True)

        for cat, weight in sorted_cats:
            count = max(1, round(weight * total))
            quotas[cat] = count
            allocated += count

        # Adjust difference to match exact total
        diff = allocated - total
        idx = 0
        while diff > 0 and idx < len(sorted_cats):
            cat = sorted_cats[idx][0]
            if quotas[cat] > 1:
                quotas[cat] -= 1
                diff -= 1
            idx += 1
            if idx >= len(sorted_cats):
                idx = 0

        while diff < 0:
            quotas[sorted_cats[0][0]] += 1
            diff += 1

        # Skill Gap assessment quota: allocate up to 30% of questions to probe missing JD skills
        num_missing_skills = len(missing_jd_skills)
        missing_skill_target_count = min(num_missing_skills, math.ceil(total * 0.30))

        # Target skill priority list
        target_skills = []
        for s in missing_jd_skills[:missing_skill_target_count]:
            target_skills.append({
                "skill_id": s.get("skill_id"),
                "canonical_name": s.get("canonical_name"),
                "type": "MISSING_JD_SKILL"
            })
        for s in matched_skills[:(total - len(target_skills))]:
            target_skills.append({
                "skill_id": s.get("skill_id"),
                "canonical_name": s.get("canonical_name"),
                "type": "MATCHED_SKILL"
            })

        return {
            "role_family": role_family,
            "seniority": seniority,
            "total_questions": total,
            "category_quotas": quotas,
            "missing_skill_target_count": missing_skill_target_count,
            "target_skills": target_skills,
            "difficulty_progression": ["BEGINNER", "INTERMEDIATE", "ADVANCED"] if seniority != "Fresher" else ["BEGINNER", "INTERMEDIATE"]
        }
