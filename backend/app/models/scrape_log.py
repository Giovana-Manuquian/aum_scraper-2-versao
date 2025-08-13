from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class ScrapeLog(Base):
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source_url = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'website', 'linkedin', 'instagram', 'x', 'news'
    status = Column(String(50), nullable=False)  # 'success', 'failed', 'blocked'
    content_length = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamento
    company = relationship("Company", back_populates="scrape_logs")
    
    def __repr__(self):
        return f"<ScrapeLog(company_id={self.company_id}, source='{self.source_type}', status='{self.status}')>"
