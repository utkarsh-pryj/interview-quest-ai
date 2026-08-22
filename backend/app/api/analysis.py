from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_db
from app.models.user import User
from app.models.resume import Resume
from app.models.job_description import JobDescription
from app.api.auth import get_current_user
from app.services.skill_service import SkillService
from app.services.role_service import RoleService
from app.schemas.analysis import FullAnalysisResponse, SkillGapAnalysis, RoleAnalysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.post("/{resume_id}/{jd_id}", response_model=FullAnalysisResponse)
async def analyze_resume_and_jd(
    resume_id: str,
    jd_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Perform deep skill gap analysis between resume and target JD."""
    res_stmt = select(Resume).filter_by(id=resume_id, user_id=current_user.id)
    resume = (await db.execute(res_stmt)).scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    jd_stmt = select(JobDescription).filter_by(id=jd_id, user_id=current_user.id)
    jd = (await db.execute(jd_stmt)).scalar_one_or_none()
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job Description not found")

    canonical_skills = await SkillService.get_all_canonical_skills(db)
    resume_skills = SkillService.extract_skills_from_text(resume.extracted_text, canonical_skills)
    jd_skills = SkillService.extract_skills_from_text(jd.extracted_text, canonical_skills)
    gap_data = SkillService.compute_skill_gap(resume_skills, jd_skills)

    role_family = jd.role_family or RoleService.infer_role_family(jd.title or "", jd.extracted_text)
    seniority = jd.seniority or RoleService.infer_seniority(jd.title or "", jd.extracted_text)
    dominant_dims = RoleService.get_role_dimensions(role_family)
    dim_budget = {dim: 2 for dim in dominant_dims}

    summary = (
        f"Candidate matched {len(gap_data['matched_skills'])} out of {len(gap_data['matched_skills']) + len(gap_data['missing_jd_skills'])} "
        f"core requirements ({gap_data['match_percentage']}% alignment) for '{role_family}' ({seniority})."
    )

    return FullAnalysisResponse(
        resume_id=resume_id,
        jd_id=jd_id,
        role_analysis=RoleAnalysis(
            inferred_role_family=role_family,
            inferred_seniority=seniority,
            dominant_dimensions=dominant_dims,
            role_description=f"Blueprint for {role_family} candidates."
        ),
        skill_gap=SkillGapAnalysis(
            matched_skills=gap_data["matched_skills"],
            missing_jd_skills=gap_data["missing_jd_skills"],
            resume_only_skills=gap_data["resume_only_skills"],
            match_percentage=gap_data["match_percentage"]
        ),
        suggested_interview_dimensions=dim_budget,
        summary=summary
    )
