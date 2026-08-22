"""
Role Family and Seniority Inference Service.
Supports technical, data, sales, HR, and cross-functional roles.
Conforms to Blueprint Section 10 & 11.
"""

import re
from typing import Dict, Any, Tuple, List

ROLE_PATTERNS = {
    "Backend Engineer": [
        r"backend", r"back-end", r"server-side", r"python developer", r"fastapi",
        r"django", r"java engineer", r"golang", r"node\.js engineer", r"microservices"
    ],
    "Frontend Engineer": [
        r"frontend", r"front-end", r"react", r"ui developer", r"web developer",
        r"vue\.js", r"angular", r"css", r"javascript developer"
    ],
    "Full Stack Engineer": [
        r"fullstack", r"full-stack", r"full stack", r"mern", r"mean stack"
    ],
    "DevOps & Cloud Engineer": [
        r"devops", r"site reliability", r"sre", r"cloud engineer", r"aws engineer",
        r"kubernetes", r"infrastructure", r"platform engineer"
    ],
    "Data Analyst": [
        r"data analyst", r"bi developer", r"business intelligence", r"tableau developer",
        r"power bi", r"analytics specialist", r"reporting analyst"
    ],
    "Data Scientist & ML": [
        r"data scientist", r"machine learning", r"ml engineer", r"ai engineer",
        r"nlp engineer", r"deep learning", r"computer vision"
    ],
    "Product Manager": [
        r"product manager", r"technical product manager", r"product owner",
        r"associate product manager", r"group product manager"
    ],
    "HR / Recruiter": [
        r"human resources", r"recruiter", r"talent acquisition", r"hr business partner",
        r"hr generalist", r"technical recruiter", r"people operations"
    ],
    "Sales & Business Development": [
        r"sales", r"account executive", r"business development", r"bdr", r"sdr",
        r"sales manager", r"enterprise sales", r"client relationship"
    ]
}

SENIORITY_PATTERNS = {
    "Executive / Director": [r"director", r"vp", r"vice president", r"head of", r"chief", r"cto", r"cio", r"cpo"],
    "Lead / Staff": [r"lead", r"staff", r"principal", r"architect", r"team lead", r"manager"],
    "Senior": [r"senior", r"sr\.", r"sr ", r"5\+ years", r"6\+ years", r"7\+ years", r"8\+ years", r"expert"],
    "Mid-Level": [r"mid", r"mid-level", r"intermediate", r"2\+ years", r"3\+ years", r"4\+ years"],
    "Junior": [r"junior", r"jr\.", r"jr ", r"associate", r"1\+ years", r"1-2 years"],
    "Fresher": [r"fresher", r"entry level", r"graduate", r"trainee", r"intern", r"internship", r"0-1 years"]
}

class RoleService:
    """Infers role family, seniority, and key assessment dimensions from resume and JD."""

    @classmethod
    def infer_role_family(cls, title: str = "", text: str = "") -> str:
        combined = f"{title} {text}".lower()
        for role_name, patterns in ROLE_PATTERNS.items():
            for pat in patterns:
                if re.search(r"\b" + pat + r"\b", combined):
                    return role_name
        return "Software Engineer"

    @classmethod
    def infer_seniority(cls, title: str = "", text: str = "") -> str:
        combined = f"{title} {text}".lower()
        for seniority_level, patterns in SENIORITY_PATTERNS.items():
            for pat in patterns:
                if re.search(r"\b" + pat + r"\b", combined):
                    return seniority_level
        return "Mid-Level"

    @classmethod
    def get_role_dimensions(cls, role_family: str) -> List[str]:
        """Blueprint Section 11: Dominant interview dimensions per role family."""
        if role_family in ["Backend Engineer", "Software Engineer", "Full Stack Engineer"]:
            return ["Technical Fundamentals", "Missing Skills Probing", "System Architecture", "Hands-on Coding", "Behavioral & Collaboration"]
        elif role_family == "Frontend Engineer":
            return ["Core JavaScript/DOM", "UI Component Architecture", "State & Performance", "Web Standards & A11y", "Behavioral"]
        elif role_family == "Data Analyst":
            return ["SQL & Data Manipulation", "Statistical Analysis", "Business Scenarios", "Data Storytelling", "Behavioral"]
        elif role_family == "HR / Recruiter":
            return ["Sourcing & Talent Funnel", "Candidate Assessment", "HR Operations", "Situational Conflict", "Stakeholder Communication"]
        elif role_family == "Sales & Business Development":
            return ["Lead Qualification & MEDDPICC", "Objection Handling", "Negotiation & Closing", "Customer Scenarios", "Behavioral"]
        else:
            return ["Core Domain Knowledge", "Practical Problem Solving", "Missing JD Requirements", "Situational Judgment", "Communication"]
