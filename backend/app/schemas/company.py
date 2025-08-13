from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    name: str
    url_site: Optional[HttpUrl] = None
    url_linkedin: Optional[HttpUrl] = None
    url_instagram: Optional[HttpUrl] = None
    url_x: Optional[HttpUrl] = None
    sector: Optional[str] = None
    employees_count: Optional[int] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    url_site: Optional[HttpUrl] = None
    url_linkedin: Optional[HttpUrl] = None
    url_instagram: Optional[HttpUrl] = None
    url_x: Optional[HttpUrl] = None
    sector: Optional[str] = None
    employees_count: Optional[int] = None

class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
