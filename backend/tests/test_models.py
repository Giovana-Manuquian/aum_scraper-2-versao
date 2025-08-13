import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.database import Base
from app.models import Company, ScrapeLog, AumSnapshot, Usage

# Configuração do banco de teste
@pytest.fixture
def test_db():
    """Cria banco de dados de teste em memória"""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

class TestCompany:
    """Testes para o modelo Company"""
    
    def test_create_company(self, test_db):
        """Testa criação de empresa"""
        company = Company(
            name="Teste Empresa",
            url_site="https://teste.com",
            sector="Tecnologia",
            employees_count=100
        )
        
        test_db.add(company)
        test_db.commit()
        
        assert company.id is not None
        assert company.name == "Teste Empresa"
        assert company.sector == "Tecnologia"
        assert company.employees_count == 100
        assert company.created_at is not None
    
    def test_company_repr(self, test_db):
        """Testa representação string da empresa"""
        company = Company(name="Teste", sector="Tecnologia")
        assert "Teste" in str(company)
        assert "Tecnologia" in str(company)

class TestScrapeLog:
    """Testes para o modelo ScrapeLog"""
    
    def test_create_scrape_log(self, test_db):
        """Testa criação de log de scraping"""
        # Cria empresa primeiro
        company = Company(name="Teste Empresa")
        test_db.add(company)
        test_db.commit()
        
        scrape_log = ScrapeLog(
            company_id=company.id,
            source_url="https://teste.com",
            source_type="website",
            status="success",
            content_length=1000
        )
        
        test_db.add(scrape_log)
        test_db.commit()
        
        assert scrape_log.id is not None
        assert scrape_log.company_id == company.id
        assert scrape_log.status == "success"
        assert scrape_log.is_blocked is False
    
    def test_scrape_log_repr(self, test_db):
        """Testa representação string do log"""
        company = Company(name="Teste")
        test_db.add(company)
        test_db.commit()
        
        scrape_log = ScrapeLog(
            company_id=company.id,
            source_url="https://teste.com",
            source_type="website",
            status="success"
        )
        
        assert "website" in str(scrape_log)
        assert "success" in str(scrape_log)

class TestAumSnapshot:
    """Testes para o modelo AumSnapshot"""
    
    def test_create_aum_snapshot(self, test_db):
        """Testa criação de snapshot de AUM"""
        # Cria empresa primeiro
        company = Company(name="Teste Empresa")
        test_db.add(company)
        test_db.commit()
        
        aum_snapshot = AumSnapshot(
            company_id=company.id,
            aum_value=2.5,
            aum_currency="BRL",
            aum_unit="bi",
            source_url="https://teste.com",
            source_type="website",
            confidence_score=0.8
        )
        
        test_db.add(aum_snapshot)
        test_db.commit()
        
        assert aum_snapshot.id is not None
        assert aum_snapshot.aum_value == 2.5
        assert aum_snapshot.aum_currency == "BRL"
        assert aum_snapshot.aum_unit == "bi"
        assert aum_snapshot.confidence_score == 0.8
    
    def test_aum_snapshot_repr(self, test_db):
        """Testa representação string do snapshot"""
        company = Company(name="Teste")
        test_db.add(company)
        test_db.commit()
        
        aum_snapshot = AumSnapshot(
            company_id=company.id,
            aum_value=1.0,
            aum_unit="bi",
            source_url="https://teste.com",
            source_type="website"
        )
        
        assert "1.0" in str(aum_snapshot)
        assert "bi" in str(aum_snapshot)

class TestUsage:
    """Testes para o modelo Usage"""
    
    def test_create_usage(self, test_db):
        """Testa criação de registro de uso"""
        usage = Usage(
            tokens_used=1000,
            tokens_limit=10000,
            cost_usd=0.01,
            api_calls=5,
            operation_type="ai_processing"
        )
        
        test_db.add(usage)
        test_db.commit()
        
        assert usage.id is not None
        assert usage.tokens_used == 1000
        assert usage.tokens_limit == 10000
        assert usage.cost_usd == 0.01
        assert usage.api_calls == 5
        assert usage.operation_type == "ai_processing"
    
    def test_usage_percentage(self, test_db):
        """Testa cálculo de porcentagem de uso"""
        usage = Usage(
            tokens_used=8000,
            tokens_limit=10000,
            operation_type="ai_processing"
        )
        
        assert usage.usage_percentage == 80.0
    
    def test_usage_repr(self, test_db):
        """Testa representação string do uso"""
        usage = Usage(
            tokens_used=1000,
            tokens_limit=10000,
            operation_type="ai_processing"
        )
        
        assert "1000" in str(usage)
        assert "10000" in str(usage)
