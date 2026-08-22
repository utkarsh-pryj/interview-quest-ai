"""
Job Description Management API Routes.
Conforms to Blueprint Section 10 & 16.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_db
from app.models.user import User
from app.models.job_description import JobDescription
from app.api.auth import get_current_user
from app.services.document_parser import DocumentParser
from app.services.role_service import RoleService
from app.schemas.resume import JobDescriptionCreate, JobDescriptionResponse

router = APIRouter(prefix="/job-descriptions", tags=["Job Descriptions"])

@router.post("", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    payload: JobDescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create and analyze a target Job Description."""
    cleaned_text = DocumentParser.normalize_document_text(payload.text)
    if len(cleaned_text) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description text is too short."
        )

    # Infer Role Family & Seniority
    role_family = RoleService.infer_role_family(payload.title or "", cleaned_text)
    seniority = RoleService.infer_seniority(payload.title or "", cleaned_text)

    jd_id = str(uuid.uuid4())
    jd = JobDescription(
        id=jd_id,
        user_id=current_user.id,
        title=payload.title or role_family,
        company=payload.company or "Target Company",
        filename="job_description.txt",
        extracted_text=cleaned_text,
        role_family=role_family,
        seniority=seniority
    )
    db.add(jd)
    await db.commit()

    return JobDescriptionResponse(
        id=jd.id,
        user_id=jd.user_id,
        title=jd.title,
        company=jd.company,
        filename=jd.filename,
        extracted_text=jd.extracted_text,
        role_family=jd.role_family,
        seniority=jd.seniority,
        created_at=jd.created_at
    )

@router.get("/{id}", response_model=JobDescriptionResponse)
async def get_job_description(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Fetch user's job description by ID."""
    stmt = select(JobDescription).filter_by(id=id, user_id=current_user.id)
    jd = (await db.execute(stmt)).scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

    return JobDescriptionResponse(
        id=jd.id,
        user_id=jd.user_id,
        title=jd.title,
        company=jd.company,
        filename=jd.filename,
        extracted_text=jd.extracted_text,
        role_family=jd.role_family,
        seniority=jd.seniority,
        created_at=jd.created_at
    )

@router.get("", response_model=List[JobDescriptionResponse])
async def list_job_descriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all job descriptions for authenticated user."""
    stmt = (
        select(JobDescription)
        .filter_by(user_id=current_user.id)
        .order_by(JobDescription.created_at.desc())
    )
    jds = (await db.execute(stmt)).scalars().all()
    return [
        JobDescriptionResponse(
            id=jd.id,
            user_id=jd.user_id,
            title=jd.title,
            company=jd.company,
            filename=jd.filename,
            extracted_text=jd.extracted_text,
            role_family=jd.role_family,
            seniority=jd.seniority,
            created_at=jd.created_at
        )
        for jd in jds
    ]
