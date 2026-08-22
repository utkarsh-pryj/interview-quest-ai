"""
Deterministic Document Parser.
Extracts normalized text and preserves section boundaries from PDF and DOCX files without AI dependency.
Conforms to Blueprint Section 10.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from app.core.logging import logger

SECTION_HEADERS = {
    "summary": [
        r"summary", r"professional summary", r"executive summary",
        r"about me", r"profile", r"career objective", r"objective"
    ],
    "experience": [
        r"experience", r"work experience", r"employment history",
        r"professional experience", r"work history", r"career history"
    ],
    "projects": [
        r"projects", r"personal projects", r"key projects",
        r"technical projects", r"portfolio", r"open source"
    ],
    "skills": [
        r"skills", r"technical skills", r"core competencies",
        r"skills & tools", r"technologies", r"tools & technologies",
        r"proficiencies", r"programming skills"
    ],
    "education": [
        r"education", r"academic background", r"qualifications",
        r"degrees", r"certifications", r"courses"
    ],
    "responsibilities": [
        r"responsibilities", r"key responsibilities", r"duties",
        r"requirements", r"job requirements", r"what you'll do"
    ]
}

class DocumentParser:
    """Deterministic parser for PDF, DOCX, and TXT documents."""

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
    def parse_document(cls, file_path: Path) -> Dict[str, Any]:
        """Main entry point to parse a document and extract sections and metadata."""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            raw_text = cls.extract_text_from_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            raw_text = cls.extract_text_from_docx(file_path)
        elif suffix in [".txt", ".md"]:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        normalized_text = cls.normalize_document_text(raw_text)
        sections = cls.extract_sections(normalized_text)
        contact_info = cls.extract_contact_info(normalized_text)

        return {
            "filename": file_path.name,
            "raw_text": raw_text,
            "extracted_text": normalized_text,
            "sections": sections,
            "contact_info": contact_info
        }

    @classmethod
    def normalize_document_text(cls, text: str) -> str:
        """Clean text, remove weird characters, and preserve paragraph structure."""
        if not text:
            return ""
        # Normalize non-breaking spaces and tabs
        cleaned = text.replace("\u00a0", " ").replace("\t", " ")
        # Clean carriage returns
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple spaces
        cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
        # Collapse 3+ newlines to 2
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def extract_sections(cls, text: str) -> Dict[str, str]:
        """Detect and segment standard resume/JD sections."""
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {
            "summary": [],
            "experience": [],
            "projects": [],
            "skills": [],
            "education": [],
            "responsibilities": [],
            "other": []
        }

        current_section = "other"

        # Regex to detect heading lines
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            # Check if line looks like a header (short line, upper case, or ending with colon)
            detected_header = None
            if len(trimmed) < 40:
                clean_header = re.sub(r"[:\-_|#]", "", trimmed).strip().lower()
                for section_name, patterns in SECTION_HEADERS.items():
                    for pat in patterns:
                        if re.fullmatch(pat, clean_header, re.IGNORECASE):
                            detected_header = section_name
                            break
                    if detected_header:
                        break

            if detected_header:
                current_section = detected_header
            else:
                sections[current_section].append(trimmed)

        # Merge section lines into text blocks
        result = {}
        for sec, lines_list in sections.items():
            content = "\n".join(lines_list).strip()
            if content:
                result[sec] = content

        return result

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
