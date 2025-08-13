from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from app.models.database import Base

class Usage(Base):
    __tablename__ = "usage"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    tokens_used = Column(Integer, nullable=False)
    tokens_limit = Column(Integer, nullable=False)
    cost_usd = Column(Float, nullable=True)
    api_calls = Column(Integer, default=0)
    company_id = Column(Integer, nullable=True)  # Para rastrear uso por empresa
    operation_type = Column(String(50), nullable=False)  # 'scraping', 'extraction', 'other'
    
    def __repr__(self):
        return f"<Usage(date='{self.date}', tokens={self.tokens_used}/{self.tokens_limit}, cost=${self.cost_usd})>"
    
    @property
    def usage_percentage(self):
        return (self.tokens_used / self.tokens_limit) * 100 if self.tokens_limit > 0 else 0
