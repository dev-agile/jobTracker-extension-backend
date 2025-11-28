from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import Base, engine, SessionLocal

app = FastAPI()

origins = [
    "https://www.upwork.com",
    "http://localhost:3000",
    "http://localhost:5173",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/allJobs/{user_id}", response_model=list[schemas.ItemOut])
def read_jobs(user_id: str, db: Session = Depends(get_db)):
    jobs = crud.get_jobs_by_user(db, user_id)
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found for this user")
    return jobs


@app.post("/jobs", response_model=schemas.ItemOut)
def create_job_endpoint(job: schemas.ItemCreate, db: Session = Depends(get_db)):

    exists = crud.findIfJobExisting(db, job)

    if exists:
        raise HTTPException(status_code=409, detail="Job already exists for this user")

    created_job = crud.create_job(db, job)
    return created_job


@app.delete("/delete/jobs/{id}", response_model=list[schemas.ItemOut])
def delete_job(id: str, db: Session = Depends(get_db)):
    
    jobDeleted = crud.deleteTheJob(id, db)

    if not jobDeleted:
        raise HTTPException(status_code=409, detail="Job not found")
    else: raise HTTPException(status_code=200, detail="Job is deleted")




