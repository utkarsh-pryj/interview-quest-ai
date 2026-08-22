"""
Dataset Normalization Engine.
Implements controlled categories, difficulties, experience levels, question types, and role families.
Conforms to Blueprint Section 8.7 - 8.11.
"""

from typing import Optional, Set

# Blueprint Section 8.7: Controlled Categories
ALLOWED_CATEGORIES: Set[str] = {
    "TECHNICAL",
    "CODING",
    "SYSTEM_DESIGN",
    "BEHAVIORAL",
    "SITUATIONAL",
    "DOMAIN",
    "HR",
    "CULTURAL"
}

# Blueprint Section 8.8: Controlled Difficulty
ALLOWED_DIFFICULTIES: Set[str] = {
    "BEGINNER",
    "INTERMEDIATE",
    "ADVANCED",
    "UNKNOWN"
}

# Blueprint Section 8.9: Controlled Experience
ALLOWED_EXPERIENCES: Set[str] = {
    "FRESHER",
    "JUNIOR",
    "MID",
    "SENIOR",
    "LEAD",
    "EXECUTIVE",
    "UNKNOWN"
}

# Blueprint Section 8.11: Controlled Question Types
ALLOWED_QUESTION_TYPES: Set[str] = {
    "CONCEPTUAL",
    "CODING",
    "SCENARIO",
    "BEHAVIORAL",
    "SYSTEM_DESIGN",
    "TROUBLESHOOTING"
}

# Controlled Role Families
ROLE_FAMILY_MAPPINGS = {
    "backend": "Backend Engineer",
    "software engineer": "Software Engineer",
    "software developer": "Software Engineer",
    "frontend": "Frontend Engineer",
    "full stack": "Full Stack Engineer",
    "devops": "DevOps Engineer",
    "cloud": "Cloud Engineer",
    "data analyst": "Data Analyst",
    "data engineer": "Data Engineer",
    "data scientist": "Data Scientist",
    "product manager": "Product Manager",
    "recruiter": "HR / Recruiter",
    "human resources": "HR / Recruiter",
    "talent acquisition": "HR / Recruiter",
    "sales": "Sales & Business Development",
    "customer success": "Customer Success"
}

def normalize_category(cat: Optional[str]) -> str:
    if not cat:
        return "TECHNICAL"
    c = cat.strip().upper().replace(" ", "_").replace("-", "_")
    if c in ALLOWED_CATEGORIES:
        return c
    if "CODE" in c or "PROGRAMMING" in c or "ALGORITHM" in c:
        return "CODING"
    if "SYSTEM" in c or "ARCHITECTURE" in c or "DESIGN" in c:
        return "SYSTEM_DESIGN"
    if "BEHAVIOR" in c or "SOFT" in c or "STAR" in c:
        return "BEHAVIORAL"
    if "SITUATION" in c or "SCENARIO" in c:
        return "SITUATIONAL"
    if "HR" in c or "RECRUIT" in c or "PEOPLE" in c:
        return "HR"
    if "CULTUR" in c or "VALUES" in c:
        return "CULTURAL"
    if "DATA" in c or "FINANCE" in c or "MARKET" in c or "DOMAIN" in c:
        return "DOMAIN"
    return "TECHNICAL"

def normalize_difficulty(diff: Optional[str]) -> str:
    if not diff:
        return "INTERMEDIATE"
    d = diff.strip().upper()
    if d in ALLOWED_DIFFICULTIES:
        return d
    if "EASY" in d or "BASIC" in d or "LOW" in d or "ENTRY" in d or "BEGINNER" in d:
        return "BEGINNER"
    if "HARD" in d or "ADVANCE" in d or "HIGH" in d or "EXPERT" in d:
        return "ADVANCED"
    if "MED" in d or "MODERATE" in d or "INTERMEDIATE" in d:
        return "INTERMEDIATE"
    return "UNKNOWN"

def normalize_experience(exp: Optional[str]) -> str:
    if not exp:
        return "UNKNOWN"
    e = exp.strip().upper()
    if e in ALLOWED_EXPERIENCES:
        return e
    if "FRESH" in e or "INTERN" in e or "0" in e or "ENTRY" in e:
        return "FRESHER"
    if "JUNIOR" in e or "1-2" in e or "ASSOCIATE" in e:
        return "JUNIOR"
    if "MID" in e or "3-5" in e:
        return "MID"
    if "SENIOR" in e or "SR" in e or "5-8" in e:
        return "SENIOR"
    if "LEAD" in e or "STAFF" in e or "PRINCIPAL" in e or "ARCHITECT" in e:
        return "LEAD"
    if "DIRECTOR" in e or "VP" in e or "EXECUTIVE" in e or "CTO" in e:
        return "EXECUTIVE"
    return "UNKNOWN"

def normalize_question_type(qtype: Optional[str], question_text: str = "") -> str:
    if qtype:
        qt = qtype.strip().upper().replace(" ", "_")
        if qt in ALLOWED_QUESTION_TYPES:
            return qt
    
    # Infer from question text
    q_lower = question_text.lower()
    if any(k in q_lower for k in ["write a function", "implement", "write code", "time complexity", "leetcode", "algorithm"]):
        return "CODING"
    if any(k in q_lower for k in ["design a", "architect", "scale to", "high level design", "microservice", "throughput"]):
        return "SYSTEM_DESIGN"
    if any(k in q_lower for k in ["tell me about a time", "describe a situation", "how do you handle conflict", "give an example when"]):
        return "BEHAVIORAL"
    if any(k in q_lower for k in ["what would you do if", "how would you respond", "scenario"]):
        return "SITUATIONAL"
    if any(k in q_lower for k in ["debug", "troubleshoot", "fix", "memory leak", "out of memory", "latency spike"]):
        return "TROUBLESHOOTING"
    return "CONCEPTUAL"

def normalize_role(role: Optional[str]) -> str:
    if not role:
        return "Software Engineer"
    r_lower = role.strip().lower()
    for pattern, normalized in ROLE_FAMILY_MAPPINGS.items():
        if pattern in r_lower:
            return normalized
    return role.strip().title()
