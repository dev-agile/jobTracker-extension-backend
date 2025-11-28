from sqlalchemy import Column, Integer, String, ARRAY
from .database import Base

class Jobs(Base):
    __tablename__ = "jobbs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=True)
    profile = Column(String, nullable=True)
    title = Column(String, nullable=True)
    role = Column(String, nullable=True)
    posted = Column(String, nullable=True)
    description = Column(String, nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    experience_level = Column(String, nullable=True)
    hourly_range = Column(String, nullable=True)
    hourly = Column(String, nullable=True)
    project_length = Column(String, nullable=True)
    hourly_rate = Column(String, nullable=True)
    fixed_price = Column(String, nullable=True)
    cover_letter = Column(String, nullable=True)
    location = Column(String, nullable=True)
    connects = Column(String, nullable=True)
    source = Column(String, nullable=True)
    url = Column(String, nullable=True)
    applied_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
