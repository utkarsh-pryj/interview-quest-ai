"""
Resume Upload & Parsing API Routes.
Conforms to Blueprint Section 10 & 16.
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_async_db
from app.models.user import User
from app.models.resume import Resume
from app.models.candidate_profile import CandidateProfile
from app.api.auth import get_current_user
from app.core.config import settings
from app.services.document_parser import DocumentParser
from app.services.role_service import RoleService
from app.schemas.resume import ResumeResponse

router = APIRouter(prefix="/resumes", tags=["Resumes"])

@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Upload and deterministically parse a resume (PDF, DOCX, or plain text)."""
    resume_id = str(uuid.uuid4())
    filename = "resume.txt"
    file_type = "txt"
    storage_path = None
    extracted_text = ""
    sections = {}

    if file:
        filename = file.filename
        suffix = Path(filename).suffix.lower()
        if suffix not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension: {suffix}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        file_type = suffix.replace(".", "")
        safe_filename = f"{resume_id}_{filename}"
        save_path = settings.UPLOAD_DIR / safe_filename
        
        # Save file to disk
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )
        save_path.write_bytes(content)
        storage_path = str(save_path)

        # Deterministic parsing
        parsed = DocumentParser.parse_document(save_path)
        extracted_text = parsed["extracted_text"]
        sections = parsed["sections"]
    elif raw_text:
        extracted_text = DocumentParser.normalize_document_text(raw_text)
        sections = DocumentParser.extract_sections(extracted_text)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a resume file or raw_text is required."
        )

    if not extracted_text or len(extracted_text) < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract readable text from the provided resume."
        )

    # Infer initial role and seniority
    role_family = RoleService.infer_role_family("", extracted_text)
    seniority = RoleService.infer_seniority("", extracted_text)

    # Save Resume Record
    resume = Resume(
        id=resume_id,
        user_id=current_user.id,
        filename=filename,
        storage_path=storage_path,
        file_type=file_type,
        extracted_text=extracted_text
    )
    db.add(resume)
    await db.flush()

    # Save Candidate Profile
    profile = CandidateProfile(
        id=str(uuid.uuid4()),
        resume_id=resume.id,
        role_family=role_family,
        seniority=seniority,
        summary=sections.get("summary", ""),
        structured_extraction={"sections": sections}
    )
    db.add(profile)
    await db.commit()

    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        filename=resume.filename,
        file_type=resume.file_type,
        extracted_text=resume.extracted_text,
        created_at=resume.created_at,
        sections=sections,
        role_family=role_family,
        seniority=seniority
    )

@router.get("/{id}", response_model=ResumeResponse)
async def get_resume(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Fetch user's resume by ID."""
    stmt = (
        select(Resume)
        .filter_by(id=id, user_id=current_user.id)
        .options(selectinload(Resume.profile))
    )
    resume = (await db.execute(stmt)).scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    sections = resume.profile.structured_extraction.get("sections", {}) if resume.profile else {}
    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        filename=resume.filename,
        file_type=resume.file_type,
        extracted_text=resume.extracted_text,
        created_at=resume.created_at,
        sections=sections,
        role_family=resume.profile.role_family if resume.profile else None,
        seniority=resume.profile.seniority if resume.profile else None
    )

@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all resumes for authenticated user."""
    stmt = (
        select(Resume)
        .filter_by(user_id=current_user.id)
        .options(selectinload(Resume.profile))
        .order_by(Resume.created_at.desc())
    )
    resumes = (await db.execute(stmt)).scalars().all()
    results = []
    for r in resumes:
        sections = r.profile.structured_extraction.get("sections", {}) if r.profile else {}
        results.append(ResumeResponse(
            id=r.id,
            user_id=r.user_id,
            filename=r.filename,
            file_type=r.file_type,
            extracted_text=r.extracted_text,
            created_at=r.created_at,
            sections=sections,
            role_family=r.profile.role_family if r.profile else None,
            seniority=r.profile.seniority if r.profile else None
        ))
    return results
