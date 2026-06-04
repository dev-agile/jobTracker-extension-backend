from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import get_db

router = APIRouter()


def _to_extension_job(job: models.Jobs):
    return {
        "id": job.id,
        "userId": job.user_id,
        "profile": job.profile or "",
        "jobTitle": job.title or "",
        "company": job.role or job.description or "",
        "jobDetails": job.description or "",
        "skills": job.skills or [],
        "experienceLevel": job.experience_level or "",
        "hourlyRange": job.hourly_range or "",
        "hourly": job.hourly or "",
        "projectLength": job.project_length or "",
        "url": job.url,
        "posted": job.posted or "",
        "appliedAt": job.applied_date,
        "status": (job.status or "applied").lower(),
    }


@router.get("/api/jobs/{user_id}")
def read_jobs(user_id: str, db: Session = Depends(get_db)):
    jobs = crud.get_jobs_by_user(db, user_id)
    return [_to_extension_job(job) for job in jobs]


@router.get("/api/allJobs")
def read_jobs_legacy(db: Session = Depends(get_db)):
    jobs = crud.get_all_jobs(db)
    return [_to_extension_job(job) for job in jobs]


@router.post("/api/jobs")
def create_job_legacy(job: schemas.ExtensionJobIn, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    user_key = job.userId or "local-extension-user"

    db_job = schemas.ItemCreate(
        id=job.id or f"ext-{uuid4().hex}",
        user_id=user_key,
        title=job.jobTitle,
        role=job.company,
        description=job.jobDetails,
        skills=job.skills,
        experience_level=job.experienceLevel,
        hourly_range=job.hourlyRange,
        hourly=job.hourly,
        project_length=job.projectLength,
        url=job.url,
        posted=job.posted,
        applied_date=job.appliedAt or now,
        status=(job.status or "applied").lower(),
        created_at=now,
        updated_at=now,
        source="extension",
    )

    exists = crud.findIfJobExisting(db, db_job)

    if exists:
        raise HTTPException(status_code=409, detail="Job already exists for this user")

    created = crud.create_job(db, db_job)
    return _to_extension_job(created)


@router.patch("/api/jobs/{job_id}")
def update_job_legacy(
    job_id: str,
    updates: dict,
    userId: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    existing_job = crud.get_job_by_id(db, job_id)
    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if userId and existing_job.user_id != userId:
        raise HTTPException(status_code=403, detail="Forbidden for this user")

    next_status = (updates.get("status") or existing_job.status or "applied").lower()
    updated = crud.update_job(
        db,
        existing_job,
        {"status": next_status, "updated_at": datetime.now(timezone.utc).isoformat()},
    )
    return _to_extension_job(updated)


@router.delete("/api/jobs/{job_id}")
def delete_job_legacy(
    job_id: str,
    userId: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    existing_job = crud.get_job_by_id(db, job_id)
    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")
    if userId and existing_job.user_id != userId:
        raise HTTPException(status_code=403, detail="Forbidden for this user")

    crud.deleteTheJob(job_id, db)
    return {"ok": True, "id": job_id}
