"""
Dataset Cleaning & Quality Validation Engine.
Conforms to Blueprint Section 8.4 - 8.6, 8.16.
"""

import re
import unicodedata
from typing import Optional, Tuple, Dict, Any

CONVERSATIONAL_FILLERS = [
    r"^hello,?\s*",
    r"^hi,?\s*",
    r"^sure,?\s*here is\s*",
    r"^can you tell me\s*",
    r"^please explain\s*",
    r"^as an ai language model,?\s*",
]

def clean_text(text: Optional[str]) -> str:
    """Normalize Unicode, whitespace, and formatting artifacts."""
    if not text:
        return ""
    # Normalize unicode to NFKC
    norm = unicodedata.normalize("NFKC", text)
    # Replace weird quotes and dashes
    norm = norm.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    norm = norm.replace("—", "-").replace("–", "-")
    # Clean multiple whitespaces and excessive newlines
    norm = re.sub(r"[ \t]+", " ", norm)
    norm = re.sub(r"\n\s*\n\s*\n+", "\n\n", norm)
    return norm.strip()

def extract_qa_from_sft(raw_text: str) -> Tuple[str, str]:
    """
    Extract user/question portion and assistant/answer portion from conversational SFT structures.
    Blueprint Section 8.4.
    """
    cleaned = clean_text(raw_text)
    
    # Pattern 1: Human: ... Assistant: ...
    if "Human:" in cleaned and "Assistant:" in cleaned:
        parts = cleaned.split("Assistant:", 1)
        question = parts[0].replace("Human:", "").strip()
        answer = parts[1].strip() if len(parts) > 1 else ""
        return question, answer
        
    # Pattern 2: User: ... Assistant: ...
    if "User:" in cleaned and "Assistant:" in cleaned:
        parts = cleaned.split("Assistant:", 1)
        question = parts[0].replace("User:", "").strip()
        answer = parts[1].strip() if len(parts) > 1 else ""
        return question, answer

    # Pattern 3: Question: ... Answer: ...
    if "Question:" in cleaned and "Answer:" in cleaned:
        parts = cleaned.split("Answer:", 1)
        question = parts[0].replace("Question:", "").strip()
        answer = parts[1].strip() if len(parts) > 1 else ""
        return question, answer

    # Pattern 4: ### Question ... ### Solution
    if "### Question" in cleaned or "### Solution" in cleaned:
        parts = re.split(r"###\s*(?:Solution|Answer)", cleaned, flags=re.IGNORECASE)
        question = re.sub(r"###\s*Question", "", parts[0], flags=re.IGNORECASE).strip()
        answer = parts[1].strip() if len(parts) > 1 else ""
        return question, answer

    return cleaned, ""

def validate_question_record(question: str, answer: Optional[str]) -> Tuple[bool, str]:
    """
    Run quality validation (Blueprint Section 8.16).
    Returns (is_valid, drop_reason).
    """
    q = clean_text(question)
    if not q:
        return False, "EMPTY_QUESTION"
    if len(q) < 15:
        return False, "QUESTION_TOO_SHORT"
    if len(q) > 4000:
        return False, "QUESTION_EXCESSIVELY_LONG"
    
    # Check if question is merely conversational gibberish
    if q.lower() in ["hi", "hello", "test", "ok", "yes", "no", "thanks"]:
        return False, "NON_QUESTION_CONVERSATIONAL"
        
    # Check that answer if present is not empty or corrupted
    if answer is not None and len(clean_text(answer)) < 5:
        return False, "ANSWER_CORRUPTED_OR_EMPTY"

    return True, "VALID"
