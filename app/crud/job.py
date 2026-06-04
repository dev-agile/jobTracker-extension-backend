from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas
from ..models import Jobs


def get_jobs_by_user(db: Session, user_id: str):
    return db.query(Jobs).filter(Jobs.user_id == user_id).all()


def get_all_jobs(db: Session):
    return db.query(Jobs).all()


def create_job(db: Session, job: schemas.ItemCreate):
    data = job.model_dump() if hasattr(job, "model_dump") else job.dict()
    db_job = Jobs(**data)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def find_if_job_existing(db: Session, job: schemas.ItemCreate):
    if job.url:
        by_url = (
            db.query(Jobs)
            .filter(Jobs.user_id == job.user_id, Jobs.url == job.url)
            .first()
        )
        if by_url:
            return True

    if job.title:
        by_title = (
            db.query(Jobs)
            .filter(
                Jobs.user_id == job.user_id,
                Jobs.title == job.title,
            )
            .first()
        )
        if by_title:
            return True

    if job.description:
        by_description = (
            db.query(Jobs)
            .filter(
                Jobs.user_id == job.user_id,
                Jobs.description == job.description,
            )
            .first()
        )
        if by_description:
            return True

    return False


def delete_job(db: Session, job_id: str):
    existing_job = db.query(Jobs).filter(Jobs.id == job_id).first()
    if not existing_job:
        return False
    db.delete(existing_job)
    db.commit()
    return True


def get_job_by_id(db: Session, job_id: str):
    return db.query(Jobs).filter(Jobs.id == job_id).first()


def update_job(db: Session, job: Jobs, updates: dict):
    for field, value in updates.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


def count_jobs_by_user(db: Session) -> dict[str, int]:
    rows = db.query(Jobs.user_id, func.count(Jobs.id)).group_by(Jobs.user_id).all()
    return {user_id: count for user_id, count in rows if user_id}


def count_jobs_by_status(db: Session) -> dict[str, int]:
    rows = db.query(Jobs.status, func.count(Jobs.id)).group_by(Jobs.status).all()
    result: dict[str, int] = {}
    for status, count in rows:
        key = (status or "unknown").lower()
        result[key] = count
    return result


def count_jobs_by_user_and_status(db: Session, user_id: str) -> dict[str, int]:
    rows = (
        db.query(Jobs.status, func.count(Jobs.id))
        .filter(Jobs.user_id == user_id)
        .group_by(Jobs.status)
        .all()
    )
    return {(status or "unknown").lower(): count for status, count in rows}
