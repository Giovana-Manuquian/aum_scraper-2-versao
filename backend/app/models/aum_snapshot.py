from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class AumSnapshot(Base):
    __tablename__ = "aum_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    scrape_log_id = Column(Integer, ForeignKey("scrape_logs.id"), nullable=True)
    aum_value = Column(Float, nullable=True)
    aum_currency = Column(String(10), default="BRL")
    aum_unit = Column(String(20), nullable=True)  # 'bi', 'mi', 'mil', etc.
    aum_text = Column(Text, nullable=True)  # Texto original extraído
    source_url = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)
    confidence_score = Column(Float, default=0.0)  # Score de confiança da IA
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    company = relationship("Company", back_populates="aum_snapshots")
    scrape_log = relationship("ScrapeLog")
    
    def __repr__(self):
        return f"<AumSnapshot(company_id={self.company_id}, aum={self.aum_value} {self.aum_unit}, source='{self.source_type}')>"
