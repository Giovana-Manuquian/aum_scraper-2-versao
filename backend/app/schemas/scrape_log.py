from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class ScrapeLogBase(BaseModel):
    company_id: int
    source_url: HttpUrl
    source_type: str
    status: str
    content_length: Optional[int] = None
    error_message: Optional[str] = None
    is_blocked: bool = False

class ScrapeLogCreate(ScrapeLogBase):
    pass

class ScrapeLogResponse(ScrapeLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
