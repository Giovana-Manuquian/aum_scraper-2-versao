from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UsageBase(BaseModel):
    tokens_used: int
    tokens_limit: int
    cost_usd: Optional[float] = None
    api_calls: int = 0
    company_id: Optional[int] = None
    operation_type: str

class UsageCreate(UsageBase):
    pass

class UsageResponse(UsageBase):
    id: int
    date: datetime
    usage_percentage: float
    
    class Config:
        from_attributes = True
