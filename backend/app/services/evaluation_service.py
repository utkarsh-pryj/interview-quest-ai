"""
Two-Stage Cost-Controlled Answer Evaluator.
Stage 1: Local semantic similarity + required concept coverage (zero LLM cost).
Stage 2: Selective Gemini LLM escalation for borderline/nuanced behavioral answers.
Conforms to RAG Evaluation specifications.
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
        Two-Stage evaluation pipeline:
        Stage 1: Low-cost local semantic & keyword coverage evaluation (Free).
        Stage 2: If score is borderline (40-78%) or behavioral where nuance matters, escalate to Gemini.
        """
        # Step 1: Stage 1 Low-Cost Local Evaluator
        stage1_result = cls._stage1_local_evaluate(
            question_text=question_text,
            candidate_answer=candidate_answer,
            ideal_answer=ideal_answer,
            category=category,
            expected_keywords=expected_keywords
        )

        # Step 2: Determine if Gemini escalation is warranted
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

        if not ans_clean:
            return EvaluationResult(
                score=0.0,
                concept_coverage=0.0,
                semantic_score=0.0,
                feedback="No answer was provided.",
                strengths="N/A",
                areas_for_improvement="Provide a structured response addressing the core question.",
                evaluator_type="LOCAL_DETERMINISTIC",
                rubric_scores={"relevance": 0, "technical_accuracy": 0, "concept_coverage": 0, "clarity": 0, "depth": 0}
            )

        # 1. Semantic Similarity
        ans_vec = EmbeddingService.embed_text(ans_clean)
        ideal_text = ideal_answer if ideal_answer else question_text
        ideal_vec = EmbeddingService.embed_text(ideal_text)
        semantic_sim = EmbeddingService.cosine_similarity(ans_vec, ideal_vec)

        # 2. Concept Coverage
        covered_count = 0
        all_keywords = list(expected_keywords)
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
            star_signals = ["situation", "task", "action", "result", "when i", "my role", "we achieved", "outcome", "impact"]
            found_signals = sum(1 for s in star_signals if s in ans_lower)
            behavioral_bonus = min(0.20, found_signals * 0.05)

        # Calculate final 0-100 score
        raw_score = (semantic_sim * 0.55 + coverage_ratio * 0.35 + behavioral_bonus * 0.10) * 100.0
        final_score = max(15.0, min(96.0, raw_score))

        # Feedback generation
        if final_score >= 80:
            feedback = "Strong and articulate answer demonstrating thorough conceptual grasp."
            strengths = "Clear explanation of core principles with accurate domain terminology."
            improvement = "Could mention real-world trade-offs or performance optimization metrics."
        elif final_score >= 55:
            feedback = "Solid foundation, but lacks key technical depth or specific implementation details."
            strengths = "Demonstrates general awareness of the primary topic."
            improvement = "Elaborate more on practical mechanisms, architecture, and step-by-step workflow."
        else:
            feedback = "Answer is brief or misses critical concepts related to the question."
            strengths = "Initial context noted."
            improvement = "Review core fundamentals, architecture decisions, and edge-case handling."

        rubric = {
            "relevance": round(semantic_sim * 10, 1),
            "technical_accuracy": round(coverage_ratio * 10, 1),
            "concept_coverage": round(coverage_ratio * 10, 1),
            "clarity": 8.0 if len(ans_clean.split()) > 20 else 5.0,
            "depth": round(semantic_sim * 10, 1)
        }

        return EvaluationResult(
            score=final_score,
            concept_coverage=coverage_ratio,
            semantic_score=semantic_sim,
            feedback=feedback,
            strengths=strengths,
            areas_for_improvement=improvement,
            evaluator_type="LOCAL_SEMANTIC",
            rubric_scores=rubric
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
        """Stage 2: Structured Gemini evaluation with explicit 5-dimensional rubric."""
        system_instruction = """You are an expert technical and behavioral interview evaluator.
Evaluate the candidate's answer objectively according to 5 dimensions:
1. relevance (0-10)
2. technical_accuracy (0-10)
3. concept_coverage (0-10)
4. clarity (0-10)
5. depth (0-10)

Respond ONLY with a JSON object matching this schema:
{
  "score": <number 0-100>,
  "rubric_scores": {
    "relevance": <0-10>,
    "technical_accuracy": <0-10>,
    "concept_coverage": <0-10>,
    "clarity": <0-10>,
    "depth": <0-10>
  },
  "feedback": "<concise actionable feedback>",
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
        if json_data and "score" in json_data:
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
