from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class SkillDetail(BaseModel):
    skill_id: str
    canonical_name: str
    category: str
    confidence: float
    evidence_text: Optional[str] = None
    required_or_desired: Optional[str] = "REQUIRED"

class SkillGapAnalysis(BaseModel):
    matched_skills: List[SkillDetail] = Field(default_factory=list)
    missing_jd_skills: List[SkillDetail] = Field(default_factory=list)
    resume_only_skills: List[SkillDetail] = Field(default_factory=list)
    match_percentage: float = 0.0

class RoleAnalysis(BaseModel):
    inferred_role_family: str
    inferred_seniority: str
    dominant_dimensions: List[str] = Field(default_factory=list)
    role_description: Optional[str] = None

class FullAnalysisResponse(BaseModel):
    resume_id: str
    jd_id: str
    role_analysis: RoleAnalysis
    skill_gap: SkillGapAnalysis
    suggested_interview_dimensions: Dict[str, int] = Field(default_factory=dict)
    summary: str
