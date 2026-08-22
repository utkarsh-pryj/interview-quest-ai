"""
Diversity, Deduplication & Budget Constraint Filters for RAG Candidate Sets.
Conforms to Blueprint Section 12 (points 22-24).
"""

from typing import List, Set, Dict, Any
from app.rag.ranker import QuestionCandidate
from app.rag.embeddings import EmbeddingService
from app.ingestion.deduplicate import jaccard_similarity, get_word_shingles

class RAGFilters:
    """Filters and diversifies retrieved questions."""

    @classmethod
    def filter_and_diversify(
        cls,
        candidates: List[QuestionCandidate],
        target_count: int,
        similarity_ceiling: float = 0.78
    ) -> List[QuestionCandidate]:
        """
        Greedy maximum-marginal-relevance (MMR) style diversity filter.
        Ensures questions in the final set are diverse in topic and text.
        """
        if not candidates:
            return []

        # Sort candidate pool descending by final_score
        sorted_candidates = sorted(candidates, key=lambda c: c.final_score, reverse=True)

        selected: List[QuestionCandidate] = []
        selected_shingles: List[Set[str]] = []

        for cand in sorted_candidates:
            if len(selected) >= target_count:
                break

            cand_shingles = get_word_shingles(cand.question_text)
            
            # Check overlap against already selected questions
            is_redundant = False
            for prev_cand, prev_shingles in zip(selected, selected_shingles):
                # Text shingle overlap check
                j_sim = jaccard_similarity(cand_shingles, prev_shingles)
                if j_sim > similarity_ceiling:
                    is_redundant = True
                    break
                
                # Semantic vector overlap check if embeddings available
                if cand.vector_embedding and prev_cand.vector_embedding:
                    v_sim = EmbeddingService.cosine_similarity(cand.vector_embedding, prev_cand.vector_embedding)
                    if v_sim > 0.90:
                        is_redundant = True
                        break

            if not is_redundant:
                selected.append(cand)
                selected_shingles.append(cand_shingles)

        return selected
