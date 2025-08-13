from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class AumSnapshotBase(BaseModel):
    company_id: int
    aum_value: Optional[float] = None
    aum_currency: str = "BRL"
    aum_unit: Optional[str] = None
    aum_text: Optional[str] = None
    source_url: HttpUrl
    source_type: str
    confidence_score: float = 0.0
    is_verified: bool = False

class AumSnapshotCreate(AumSnapshotBase):
    pass

class AumSnapshotResponse(AumSnapshotBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
