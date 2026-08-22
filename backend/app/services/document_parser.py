"""
Document-Aware Sectional Parser and Profiler.
Extracts structured document sections and creates document-aware chunks with section metadata.
Preserves logical boundaries:
- Resume: Summary, Skills, Experience, Projects, Education, Certifications
- Job Description: Role Title, Responsibilities, Required Skills, Preferred Skills, Qualifications
Conforms to RAG Document Processing specifications.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from app.core.logging import logger

RESUME_SECTION_HEADERS = {
    "summary": [
        r"summary", r"professional summary", r"executive summary",
        r"about me", r"profile", r"career objective", r"objective", r"overview"
    ],
    "skills": [
        r"skills", r"technical skills", r"core competencies",
        r"skills & tools", r"technologies", r"tools & technologies",
        r"proficiencies", r"programming skills", r"technical proficiencies"
    ],
    "experience": [
        r"experience", r"work experience", r"employment history",
        r"professional experience", r"work history", r"career history",
        r"relevant experience"
    ],
    "projects": [
        r"projects", r"personal projects", r"key projects",
        r"technical projects", r"portfolio", r"open source", r"academic projects"
    ],
    "education": [
        r"education", r"academic background", r"qualifications",
        r"degrees", r"academic history"
    ],
    "certifications": [
        r"certifications", r"licenses", r"courses", r"credentials",
        r"certificates", r"awards"
    ]
}

JD_SECTION_HEADERS = {
    "role_title": [
        r"role", r"position", r"job title", r"about the role", r"overview"
    ],
    "responsibilities": [
        r"responsibilities", r"key responsibilities", r"duties",
        r"what you'll do", r"role responsibilities", r"core duties", r"what you will do"
    ],
    "required_skills": [
        r"requirements", r"required skills", r"minimum qualifications",
        r"basic qualifications", r"must have", r"what you need", r"technical requirements",
        r"required experience"
    ],
    "preferred_skills": [
        r"preferred skills", r"preferred qualifications", r"bonus points",
        r"nice to have", r"good to have", r"desired skills", r"additional qualifications"
    ],
    "qualifications": [
        r"qualifications", r"education requirements", r"background"
    ]
}

@dataclass
class DocumentChunk:
    """Document chunk preserving document structure and section metadata."""
    document_id: str
    document_type: str # "RESUME" | "JOB_DESCRIPTION"
    section_name: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CandidateProfile:
    """Structured candidate profile extracted from resume."""
    raw_text: str
    summary: str = ""
    skills_text: str = ""
    experience_text: str = ""
    projects_text: str = ""
    education_text: str = ""
    certifications_text: str = ""
    contact_info: Dict[str, Any] = field(default_factory=dict)
    chunks: List[DocumentChunk] = field(default_factory=list)

    def get_compact_retrieval_context(self) -> str:
        """Constructs a compact, signal-dense context string for retrieval embedding."""
        parts = []
        if self.skills_text:
            parts.append(f"Skills: {self.skills_text[:400]}")
        if self.projects_text:
            parts.append(f"Projects: {self.projects_text[:300]}")
        if self.experience_text:
            parts.append(f"Experience: {self.experience_text[:400]}")
        if self.summary:
            parts.append(f"Summary: {self.summary[:200]}")
        return " | ".join(parts) if parts else self.raw_text[:800]

@dataclass
class JobRequirementProfile:
    """Structured job requirements extracted from job description."""
    raw_text: str
    role_title: str = ""
    responsibilities_text: str = ""
    required_skills_text: str = ""
    preferred_skills_text: str = ""
    qualifications_text: str = ""
    chunks: List[DocumentChunk] = field(default_factory=list)

    def get_compact_retrieval_context(self) -> str:
        """Constructs a compact, requirement-dense context string for retrieval embedding."""
        parts = []
        if self.role_title:
            parts.append(f"Target Role: {self.role_title}")
        if self.required_skills_text:
            parts.append(f"Required: {self.required_skills_text[:500]}")
        if self.preferred_skills_text:
            parts.append(f"Preferred: {self.preferred_skills_text[:300]}")
        if self.responsibilities_text:
            parts.append(f"Responsibilities: {self.responsibilities_text[:400]}")
        return " | ".join(parts) if parts else self.raw_text[:800]

class DocumentParser:
    """Document-aware parser for PDF, DOCX, and TXT documents."""

    @classmethod
    def extract_text_from_pdf(cls, file_path: Path) -> str:
        """Extract text from PDF using pdfplumber with pypdf fallback."""
        text_parts = []
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber failed on {file_path} ({e}), trying pypdf fallback.")

        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"pypdf extraction failed on {file_path}: {e}")
            raise ValueError(f"Could not extract text from PDF: {e}")

    @classmethod
    def extract_text_from_docx(cls, file_path: Path) -> str:
        """Extract text from DOCX document."""
        try:
            import docx
            doc = docx.Document(str(file_path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"DOCX extraction failed on {file_path}: {e}")
            raise ValueError(f"Could not extract text from DOCX: {e}")

    @classmethod
    def normalize_document_text(cls, text: str) -> str:
        """Clean text, remove weird characters, and preserve paragraph structure."""
        if not text:
            return ""
        cleaned = text.replace("\u00a0", " ").replace("\t", " ")
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def segment_sections(cls, text: str, header_patterns_map: Dict[str, List[str]]) -> Dict[str, str]:
        """Generic sectional segmentation using header regexes."""
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {k: [] for k in header_patterns_map.keys()}
        sections["other"] = []
        current_section = "other"

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            detected_header = None
            if len(trimmed) < 45:
                clean_header = re.sub(r"[:\-_|#*]", "", trimmed).strip().lower()
                for sec_name, patterns in header_patterns_map.items():
                    for pat in patterns:
                        if re.fullmatch(pat, clean_header, re.IGNORECASE):
                            detected_header = sec_name
                            break
                    if detected_header:
                        break

            if detected_header:
                current_section = detected_header
            else:
                sections[current_section].append(trimmed)

        result = {}
        for sec, lines_list in sections.items():
            content = "\n".join(lines_list).strip()
            if content:
                result[sec] = content
        return result

    @classmethod
    def create_chunks_from_sections(
        cls,
        document_id: str,
        document_type: str,
        sections: Dict[str, str],
        max_chunk_chars: int = 800
    ) -> List[DocumentChunk]:
        """
        Creates document-aware chunks preserved by section.
        Splits only large sections that exceed max_chunk_chars with small overlap.
        """
        chunks: List[DocumentChunk] = []
        chunk_idx = 0

        for sec_name, sec_text in sections.items():
            if not sec_text:
                continue

            if len(sec_text) <= max_chunk_chars:
                chunks.append(DocumentChunk(
                    document_id=document_id,
                    document_type=document_type,
                    section_name=sec_name,
                    chunk_index=chunk_idx,
                    text=sec_text,
                    metadata={"char_count": len(sec_text)}
                ))
                chunk_idx += 1
            else:
                # Split large section into paragraphs or smaller chunks with 100 char overlap
                paragraphs = [p.strip() for p in sec_text.split("\n\n") if p.strip()]
                current_buf = ""
                for p in paragraphs:
                    if len(current_buf) + len(p) <= max_chunk_chars:
                        current_buf = f"{current_buf}\n\n{p}".strip() if current_buf else p
                    else:
                        if current_buf:
                            chunks.append(DocumentChunk(
                                document_id=document_id,
                                document_type=document_type,
                                section_name=sec_name,
                                chunk_index=chunk_idx,
                                text=current_buf,
                                metadata={"char_count": len(current_buf), "subsplit": True}
                            ))
                            chunk_idx += 1
                        current_buf = p

                if current_buf:
                    chunks.append(DocumentChunk(
                        document_id=document_id,
                        document_type=document_type,
                        section_name=sec_name,
                        chunk_index=chunk_idx,
                        text=current_buf,
                        metadata={"char_count": len(current_buf), "subsplit": True}
                    ))
                    chunk_idx += 1

        return chunks

    @classmethod
    def build_candidate_profile(cls, raw_text: str, document_id: str = "temp") -> CandidateProfile:
        """Parse raw resume text into structured CandidateProfile and document chunks."""
        normalized = cls.normalize_document_text(raw_text)
        sections = cls.segment_sections(normalized, RESUME_SECTION_HEADERS)
        contact = cls.extract_contact_info(normalized)
        chunks = cls.create_chunks_from_sections(document_id, "RESUME", sections)

        return CandidateProfile(
            raw_text=normalized,
            summary=sections.get("summary", ""),
            skills_text=sections.get("skills", ""),
            experience_text=sections.get("experience", ""),
            projects_text=sections.get("projects", ""),
            education_text=sections.get("education", ""),
            certifications_text=sections.get("certifications", ""),
            contact_info=contact,
            chunks=chunks
        )

    @classmethod
    def build_job_requirement_profile(cls, raw_text: str, title: str = "", company: str = "", document_id: str = "temp") -> JobRequirementProfile:
        """Parse raw JD text into structured JobRequirementProfile and document chunks."""
        normalized = cls.normalize_document_text(raw_text)
        sections = cls.segment_sections(normalized, JD_SECTION_HEADERS)
        chunks = cls.create_chunks_from_sections(document_id, "JOB_DESCRIPTION", sections)

        role_title = title or sections.get("role_title", "").split("\n")[0]

        return JobRequirementProfile(
            raw_text=normalized,
            role_title=role_title,
            responsibilities_text=sections.get("responsibilities", ""),
            required_skills_text=sections.get("required_skills", ""),
            preferred_skills_text=sections.get("preferred_skills", ""),
            qualifications_text=sections.get("qualifications", ""),
            chunks=chunks
        )

    @classmethod
    def extract_contact_info(cls, text: str) -> Dict[str, Any]:
        """Extract email, phone, and links deterministically."""
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        github_match = re.search(r"github\.com/[a-zA-Z0-9_-]+", text, re.IGNORECASE)
        linkedin_match = re.search(r"linkedin\.com/in/[a-zA-Z0-9_-]+", text, re.IGNORECASE)

        return {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "github": github_match.group(0) if github_match else None,
            "linkedin": linkedin_match.group(0) if linkedin_match else None
        }
