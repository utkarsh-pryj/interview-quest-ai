from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ResumeSection(BaseModel):
    title: str
    content: str

class ResumeParsedData(BaseModel):
    filename: str
    extracted_text: str
    sections: Dict[str, str] = Field(default_factory=dict)
    contact_info: Dict[str, Any] = Field(default_factory=dict)

class ResumeResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: str
    extracted_text: str
    created_at: datetime
    sections: Optional[Dict[str, str]] = None
    role_family: Optional[str] = None
    seniority: Optional[str] = None

    class Config:
        from_attributes = True

class ResumeSkillItem(BaseModel):
    skill_id: str
    canonical_name: str
    category: str
    confidence: float
    evidence_text: Optional[str] = None

class JobDescriptionCreate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    text: str = Field(..., min_length=20, description="Job description text")

class JobDescriptionResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    company: Optional[str] = None
    filename: Optional[str] = None
    extracted_text: str
    role_family: Optional[str] = None
    seniority: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
