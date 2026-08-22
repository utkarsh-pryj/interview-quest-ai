"""
Two-Stage Cost-Controlled Answer Evaluator.
Stage 1: Local semantic similarity + required concept coverage (free).
Stage 2: Selective Gemini LLM escalation for borderline/complex answers.
Conforms to Blueprint Section 14.
"""

import re
from typing import Dict, Any, Optional, List
from app.rag.embeddings import EmbeddingService
from app.llm.gemini import gemini_client
from app.core.logging import logger

class EvaluationResult:
    def __init__(
        self,
        score: float,
        concept_coverage: float,
        semantic_score: float,
        feedback: str,
        strengths: str,
        areas_for_improvement: str,
        evaluator_type: str,
        rubric_scores: Optional[Dict[str, float]] = None
    ):
        self.score = round(score, 1)
        self.concept_coverage = round(concept_coverage, 2)
        self.semantic_score = round(semantic_score, 2)
        self.feedback = feedback
        self.strengths = strengths
        self.areas_for_improvement = areas_for_improvement
        self.evaluator_type = evaluator_type
        self.rubric_scores = rubric_scores or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "concept_coverage": self.concept_coverage,
            "semantic_score": self.semantic_score,
            "feedback": self.feedback,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "evaluator_type": self.evaluator_type,
            "rubric_scores": self.rubric_scores
        }

class EvaluationService:
    """Evaluates candidate answers via local semantic analysis and selective LLM escalation."""

    @classmethod
    async def evaluate_answer(
        cls,
        question_text: str,
        candidate_answer: str,
        ideal_answer: Optional[str],
        category: str,
        expected_keywords: List[str]
    ) -> EvaluationResult:
        """
        Executes Two-Stage evaluation pipeline:
        Stage 1: Low cost local semantic & keyword coverage evaluation.
        Stage 2: If score is borderline (45-75%) and Gemini is available, escalate to Gemini.
        """
        # Step 1: Stage 1 Low-Cost Local Evaluator
        stage1_result = cls._stage1_local_evaluate(
            question_text=question_text,
            candidate_answer=candidate_answer,
            ideal_answer=ideal_answer,
            category=category,
            expected_keywords=expected_keywords
        )

        # Step 2: Determine if Gemini escalation is necessary (Blueprint Section 14)
        # Escalate if:
        # 1. Answer is borderline (score between 40 and 78)
        # 2. Or behavioral answer where nuance matters
        # 3. And Gemini client is configured
        is_borderline = 40.0 <= stage1_result.score <= 78.0
        is_behavioral = category in ["BEHAVIORAL", "SITUATIONAL", "HR"]
        should_escalate = (is_borderline or is_behavioral) and gemini_client.is_available()

        if should_escalate:
            try:
                escalated = await cls._stage2_gemini_escalate(
                    question_text=question_text,
                    candidate_answer=candidate_answer,
                    ideal_answer=ideal_answer,
                    category=category,
                    stage1_semantic_score=stage1_result.semantic_score,
                    stage1_coverage=stage1_result.concept_coverage
                )
                if escalated:
                    return escalated
            except Exception as e:
                logger.warning(f"Gemini escalation failed ({e}), falling back to Stage 1 result.")

        return stage1_result

    @classmethod
    def _stage1_local_evaluate(
        cls,
        question_text: str,
        candidate_answer: str,
        ideal_answer: Optional[str],
        category: str,
        expected_keywords: List[str]
    ) -> EvaluationResult:
        """
        Stage 1 local evaluator:
        - Vector semantic cosine similarity between candidate answer and ideal answer / question.
        - Keyword concept coverage.
        - Behavioral structure check (e.g. STAR indicators for behavioral questions).
        """
        ans_clean = candidate_answer.strip()
        ans_lower = ans_clean.lower()

        # 1. Semantic Similarity
        ans_vec = EmbeddingService.embed_text(ans_clean)
        ideal_text = ideal_answer if ideal_answer else question_text
        ideal_vec = EmbeddingService.embed_text(ideal_text)
        semantic_sim = EmbeddingService.cosine_similarity(ans_vec, ideal_vec)

        # 2. Concept Coverage
        covered_count = 0
        all_keywords = list(expected_keywords)
        # If no explicit keywords, extract key nouns/terms from ideal answer
        if not all_keywords and ideal_answer:
            words = [w.strip(".,;:()[]\"'") for w in ideal_answer.split() if len(w) > 4]
            all_keywords = words[:8]

        for kw in all_keywords:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", ans_lower):
                covered_count += 1

        coverage_ratio = (covered_count / len(all_keywords)) if all_keywords else semantic_sim

        # 3. Behavioral Structure analysis (if behavioral question)
        behavioral_bonus = 0.0
        if category in ["BEHAVIORAL", "SITUATIONAL"]:
            star_signals = ["situation", "task", "action", "result", "when i", "my role", "we achieved", "outcome"]
            found_signals = sum(1 for s in star_signals if s in ans_lower)
            behavioral_bonus = min(0.20, found_signals * 0.05)

        # Calculate final 0-100 score
        raw_score = (semantic_sim * 0.55 + coverage_ratio * 0.35 + behavioral_bonus * 0.10) * 100.0
        final_score = max(15.0, min(96.0, raw_score))

        # Feedback generation
        if final_score >= 80:
            feedback = "Strong and articulate answer demonstrating thorough conceptual grasp."
            strengths = "Clear explanation of core principles with relevant terminology."
            improvement = "Could add real-world edge cases or concrete performance metrics."
        elif final_score >= 55:
            feedback = "Good foundation, but lacks key technical depth or specific examples."
            strengths = "Demonstrates general awareness of the primary topic."
            improvement = "Elaborate more on practical implementation details and key mechanisms."
        else:
            feedback = "Answer is too brief or misses critical concepts related to the question."
            strengths = "Touched upon initial context."
            improvement = "Review the fundamental concepts, trade-offs, and step-by-step workflow."

        return EvaluationResult(
            score=final_score,
            concept_coverage=coverage_ratio,
            semantic_score=semantic_sim,
            feedback=feedback,
            strengths=strengths,
            areas_for_improvement=improvement,
            evaluator_type="LOCAL_SEMANTIC"
        )

    @classmethod
    async def _stage2_gemini_escalate(
        cls,
        question_text: str,
        candidate_answer: str,
        ideal_answer: Optional[str],
        category: str,
        stage1_semantic_score: float,
        stage1_coverage: float
    ) -> Optional[EvaluationResult]:
        """Stage 2: Structured Gemini evaluation with explicit rubric."""
        system_instruction = """You are an expert technical and behavioral interview evaluator.
Evaluate the candidate's answer objectively according to:
1. Relevance (Does it answer the prompt?)
2. Technical correctness & depth
3. Specificity & Evidence (STAR structure if behavioral)
4. Communication clarity

Return JSON with:
{
  "score": <number 0-100>,
  "rubric_scores": {"relevance": <0-10>, "correctness": <0-10>, "depth": <0-10>, "communication": <0-10>},
  "feedback": "<concise actionable evaluation>",
  "strengths": "<key strengths demonstrated>",
  "areas_for_improvement": "<specific areas to improve>"
}"""

        prompt = f"""
Question: {question_text}
Category: {category}
Reference Ideal Answer: {ideal_answer or 'N/A'}
Candidate Answer: {candidate_answer}
Stage 1 Semantic Similarity: {stage1_semantic_score}
Stage 1 Concept Coverage: {stage1_coverage}
"""
        json_data = await gemini_client.generate_json(prompt, system_instruction, max_tokens=512)
        if "score" in json_data:
            return EvaluationResult(
                score=float(json_data["score"]),
                concept_coverage=stage1_coverage,
                semantic_score=stage1_semantic_score,
                feedback=json_data.get("feedback", "Evaluation completed by AI evaluator."),
                strengths=json_data.get("strengths", "Accurate points highlighted."),
                areas_for_improvement=json_data.get("areas_for_improvement", "Deepen technical rigor."),
                evaluator_type="GEMINI_ESCALATED",
                rubric_scores=json_data.get("rubric_scores", {})
            )
        return None
