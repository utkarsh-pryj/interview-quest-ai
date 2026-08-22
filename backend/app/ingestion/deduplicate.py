"""
Deduplication Engine for Canonical Interview Question Corpus.
Conforms to Blueprint Section 8.13 & 8.14.
"""

import hashlib
import re
from typing import List, Dict, Any, Tuple, Set

def normalize_for_dedup(text: str) -> str:
    """Normalize text strictly for exact duplicate hash comparison."""
    # Lowercase, remove all non-alphanumeric, collapse whitespace
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
    return " ".join(cleaned.split())

def compute_question_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

def get_word_shingles(text: str, k: int = 3) -> Set[str]:
    """Generate k-word shingles for Jaccard similarity estimation."""
    words = normalize_for_dedup(text).split()
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i:i+k]) for i in range(len(words) - k + 1)}

def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0

class Deduplicator:
    """Detects exact duplicates and near-duplicate candidates."""
    
    def __init__(self, near_duplicate_threshold: float = 0.82):
        self.exact_hashes: Dict[str, str] = {} # hash -> question_id
        self.shingles_index: List[Tuple[str, Set[str]]] = [] # (question_id, shingles)
        self.near_duplicate_threshold = near_duplicate_threshold
        self.exact_duplicate_count = 0
        self.near_duplicate_count = 0

    def check_duplicate(self, question_id: str, question_text: str) -> Tuple[bool, str, float]:
        """
        Check if question is exact or near duplicate.
        Returns (is_duplicate, duplicate_type, similarity_score).
        """
        norm = normalize_for_dedup(question_text)
        q_hash = compute_question_hash(norm)
        
        # 1. Exact Duplicate Check
        if q_hash in self.exact_hashes:
            self.exact_duplicate_count += 1
            return True, "EXACT_DUPLICATE", 1.0
            
        # 2. Near Duplicate Check
        current_shingles = get_word_shingles(question_text)
        max_sim = 0.0
        matching_id = None
        for existing_id, existing_shingles in self.shingles_index:
            sim = jaccard_similarity(current_shingles, existing_shingles)
            if sim > max_sim:
                max_sim = sim
                matching_id = existing_id
            if sim >= self.near_duplicate_threshold:
                self.near_duplicate_count += 1
                return True, "NEAR_DUPLICATE", sim

        # Not a duplicate -> register in index
        self.exact_hashes[q_hash] = question_id
        self.shingles_index.append((question_id, current_shingles))
        return False, "UNIQUE", max_sim
