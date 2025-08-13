from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    url_site = Column(String(500), nullable=True)
    url_linkedin = Column(String(500), nullable=True)
    url_instagram = Column(String(500), nullable=True)
    url_x = Column(String(500), nullable=True)
    sector = Column(String(100), nullable=True)
    employees_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamentos
    scrape_logs = relationship("ScrapeLog", back_populates="company")
    aum_snapshots = relationship("AumSnapshot", back_populates="company")
    
    def __repr__(self):
        return f"<Company(name='{self.name}', sector='{self.sector}')>"
