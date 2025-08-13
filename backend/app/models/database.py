from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://scraper:scraperpw@localhost:5432/scraperdb")

# Engine do banco
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Sessão do banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Função para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
