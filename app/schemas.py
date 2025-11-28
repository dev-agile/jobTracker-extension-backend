from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    id: str
    user_id: str
    profile: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    posted: Optional[str] = None
    description: Optional[str] = None  
    skills: Optional[List[str]] = None 
    experience_level: Optional[str] = None
    hourly_range: Optional[str] = None
    hourly: Optional[str] = None
    project_length: Optional[str] = None
    hourly_rate: Optional[str] = None
    fixed_price: Optional[str] = None
    cover_letter: Optional[str] = None
    location: Optional[str] = None
    connects: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    applied_date: Optional[str] = None
    status: Optional[str] = None
    salary: Optional[str] = None
    created_at: Optional[str] = None 
    updated_at: Optional[str] = None  

class ItemCreate(ItemBase):
    pass

class ItemOut(ItemBase):
    id: str

    class Config:
        orm_mode = True
