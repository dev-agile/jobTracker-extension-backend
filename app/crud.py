from sqlalchemy.orm import Session
from . import models, schemas


def get_jobs_by_user(db: Session, user_id: int):
    return db.query(models.Jobs).filter(models.Jobs.user_id == user_id).all()

def get_all_jobs(db: Session):
    return db.query(models.Jobs).all()

def create_job(db: Session, job: schemas.ItemCreate):
    db_job = models.Jobs(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def findIfJobExisting(db: Session, job: schemas.ItemCreate):
    existing_job = (
        db.query(models.Jobs)
        .filter(
            models.Jobs.user_id == job.user_id,
            models.Jobs.description == job.description
        )
        .first()
    )

    return existing_job is not None


def deleteTheJob(id: str, db: Session):

    existing_job = (
        db.query(models.Jobs)
        .filter(
            models.Jobs.id == id
        )
        .first()
    )

    if not existing_job:
        return False
    
    db.delete(existing_job)
    db.commit()

    return True


def get_job_by_id(db: Session, job_id: str):
    return db.query(models.Jobs).filter(models.Jobs.id == job_id).first()


def update_job(db: Session, job: models.Jobs, updates: dict):
    for field, value in updates.items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job
        
    