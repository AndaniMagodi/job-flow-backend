from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.activities.service import log_activity
from app.applications.schemas import ApplicationResponse
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.jobs.schemas import (
    JobFacets,
    JobListResponse,
    JobResponse,
    SalaryBenchmarkResponse,
    SavedJobResponse,
)
from app.jobs.sync import sync_jobs
from app.models.applications import Application
from app.models.jobs import Job, SavedJob
from app.models.users import User
from app.salary.service import benchmark_for_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

MAX_PAGE_SIZE = 50


def _apply_filters(
    query,
    q: str | None = None,
    province: str | None = None,
    is_remote: bool | None = None,
    category: str | None = None,
    experience_level: str | None = None,
    contract_type: str | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    opportunity_type: str | None = None,
    no_experience_required: bool | None = None,
):
    if q:
        # Match each word separately rather than the whole phrase: a query of
        # "software engineering" must still find a "Software Engineer" whose
        # description mentions engineering. Every term has to appear somewhere
        # in the listing, so extra words narrow the search rather than break it.
        for term in q.split():
            needle = f"%{term}%"
            query = query.filter(
                or_(
                    Job.title.ilike(needle),
                    Job.company.ilike(needle),
                    Job.description.ilike(needle),
                )
            )
    if province:
        query = query.filter(Job.province == province)
    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(is_remote))
    if category:
        query = query.filter(Job.category == category)
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    if contract_type:
        query = query.filter(Job.contract_type == contract_type)
    if opportunity_type:
        query = query.filter(Job.opportunity_type == opportunity_type)
    if no_experience_required:
        query = query.filter(Job.no_experience_required.is_(True))
    if salary_min is not None:
        # Keep listings whose top of range clears the floor the seeker set.
        query = query.filter(Job.salary_max >= salary_min)
    if salary_max is not None:
        query = query.filter(Job.salary_min <= salary_max)

    return query


@router.get("", response_model=JobListResponse)
def browse_jobs(
    q: str | None = None,
    province: str | None = None,
    is_remote: bool | None = None,
    category: str | None = None,
    experience_level: str | None = None,
    contract_type: str | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    opportunity_type: str | None = None,
    no_experience_required: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
):
    query = _apply_filters(
        db.query(Job), q, province, is_remote, category,
        experience_level, contract_type, salary_min, salary_max,
        opportunity_type, no_experience_required,
    )

    total = query.count()
    items = (
        query.order_by(Job.posted_at.desc().nullslast(), Job.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return JobListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/facets", response_model=JobFacets)
def job_facets(db: Session = Depends(get_db)):
    def distinct(column) -> list[str]:
        rows = db.query(column).filter(column.isnot(None)).distinct().all()
        return sorted(r[0] for r in rows)

    return JobFacets(
        provinces=distinct(Job.province),
        categories=distinct(Job.category),
        experience_levels=distinct(Job.experience_level),
        contract_types=distinct(Job.contract_type),
        opportunity_types=distinct(Job.opportunity_type),
    )


@router.get("/saved", response_model=list[SavedJobResponse])
def list_saved_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
        .all()
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/salary-estimate", response_model=SalaryBenchmarkResponse)
def job_salary_estimate(job_id: int, db: Session = Depends(get_db)):
    """What comparable advertised roles pay, for a listing that states nothing.

    Most South African adverts omit salary entirely, which leaves seekers
    negotiating blind. Returns 404 when the listing already states a salary, or
    when there aren't enough comparable adverts to say anything useful.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    benchmark = benchmark_for_job(db, job)
    if benchmark is None:
        raise HTTPException(
            status_code=404,
            detail="No reliable benchmark for comparable roles",
        )

    return SalaryBenchmarkResponse(**benchmark.as_dict())


@router.post("/{job_id}/save", response_model=SavedJobResponse)
def save_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
        .one_or_none()
    )
    if existing:
        return existing

    saved = SavedJob(user_id=current_user.id, job_id=job_id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/{job_id}/save", status_code=204)
def unsave_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id, SavedJob.job_id == job_id
    ).delete()
    db.commit()


@router.post("/{job_id}/apply", response_model=ApplicationResponse)
def apply_to_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record that the seeker is applying, and hand back the tracked application.

    We never host the apply flow — the client sends the user to `job.apply_url`
    on the original board. This just keeps their tracker in step.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = (
        db.query(Application)
        .filter(
            Application.user_id == current_user.id,
            Application.company == job.company,
            Application.role == job.title,
        )
        .one_or_none()
    )
    if existing:
        return existing

    application = Application(
        user_id=current_user.id,
        company=job.company,
        role=job.title,
        status="Applied",
        date_applied=date.today(),
        link=job.apply_url or None,
    )
    db.add(application)
    db.flush()

    log_activity(
        db=db,
        user_id=current_user.id,
        application_id=application.id,
        event="created",
        detail=f"Applied to {job.title} at {job.company} via the job board",
    )

    db.commit()
    db.refresh(application)
    return application


@router.post("/sync")
def trigger_sync(
    q: str | None = None,
    limit_per_source: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pull fresh listings from the configured sources into our database."""
    return sync_jobs(db, query=q, limit_per_source=limit_per_source)
