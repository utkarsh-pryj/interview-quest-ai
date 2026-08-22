"""
Diversity, Deduplication & Near-Duplicate Suppression Filters for RAG Candidates.
Implements MMR (Maximum Marginal Relevance) and semantic diversity selection.
Conforms to RAG Diversity specifications.
"""

from typing import List, Set, Dict, Any, Optional
from app.rag.ranker import QuestionCandidate
from app.rag.embeddings import EmbeddingService
from app.core.config import settings

class RAGFilters:
    """Filters and diversifies retrieved questions to eliminate near-duplicate prompts."""

    @classmethod
    def filter_and_diversify(
        cls,
        candidates: List[QuestionCandidate],
        target_count: int,
        similarity_ceiling: Optional[float] = None
    ) -> List[QuestionCandidate]:
        """
        Greedy Maximum Marginal Relevance (MMR) style diversity filter.
        Eliminates questions that are semantically identical (similarity > ceiling).
        """
        if not candidates:
            return []

        ceiling = similarity_ceiling or settings.DIVERSITY_SIMILARITY_CEILING

        # Sort candidate pool descending by multi-signal final_score
        sorted_candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)

        selected: List[QuestionCandidate] = []
        selected_vectors: List[List[float]] = []

        for cand in sorted_candidates:
            if len(selected) >= target_count:
                break

            # Calculate candidate vector if missing
            cand_vec = cand.vector_embedding
            if not cand_vec:
                cand_vec = EmbeddingService.embed_text(cand.question_text)
                cand.vector_embedding = cand_vec

            # Check semantic vector overlap against already selected questions
            is_redundant = False
            for prev_cand, prev_vec in zip(selected, selected_vectors):
                if cand_vec and prev_vec:
                    sim = EmbeddingService.cosine_similarity(cand_vec, prev_vec)
                    if sim > ceiling:
                        is_redundant = True
                        cand.duplicate_penalty = 0.25 # Track duplicate penalty
                        break

            if not is_redundant:
                selected.append(cand)
                selected_vectors.append(cand_vec)

        return selected
