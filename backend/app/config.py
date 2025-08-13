"""
Configurações do AUM Scraper

Este arquivo centraliza todas as configurações do projeto conforme o documento:
- Configurações de banco de dados
- Configurações da API OpenAI
- Configurações de scraping
- Configurações de budget e tokens
- Configurações de exportação

ARQUITETURA:
- Configurações via variáveis de ambiente
- Valores padrão para desenvolvimento
- Validação com Pydantic Settings
- Configurações específicas por ambiente
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Configurações principais do AUM Scraper
    
    Implementa todas as configurações necessárias conforme documento
    """
    
    # ============================================================================
    # CONFIGURAÇÕES DE BANCO DE DADOS
    # ============================================================================
    
    # URL do banco PostgreSQL
    database_url: str = Field(
        default="postgresql://scraper:scraperpw@localhost:5432/scraperdb",
        description="URL de conexão com PostgreSQL"
    )
    
    # Configurações de pool de conexões
    database_pool_size: int = Field(
        default=10,
        description="Tamanho do pool de conexões"
    )
    
    database_max_overflow: int = Field(
        default=20,
        description="Máximo de conexões extras no pool"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DA API OPENAI
    # ============================================================================
    
    # Chave da API OpenAI (obrigatória)
    openai_api_key: str = Field(
        description="Chave da API OpenAI para GPT-4o"
    )
    
    # Modelo da OpenAI
    openai_model: str = Field(
        default="gpt-4o",
        description="Modelo da OpenAI para extração de dados"
    )
    
    # Configurações de tokens (conforme documento)
    max_tokens_per_request: int = Field(
        default=1500,
        description="Máximo de tokens por requisição (conforme documento)"
    )
    
    max_tokens_per_day: int = Field(
        default=100000,
        description="Máximo de tokens por dia (conforme documento)"
    )
    
    budget_alert_threshold: float = Field(
        default=0.8,
        description="Alerta quando atingir 80% do budget diário"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE SCRAPING
    # ============================================================================
    
    # Timeout para scraping
    scrape_timeout: int = Field(
        default=30,
        description="Timeout em segundos para operações de scraping"
    )
    
    # Número máximo de requisições simultâneas
    max_concurrent_scrapes: int = Field(
        default=5,
        description="Máximo de scrapes simultâneos para evitar bloqueios"
    )
    
    # Delay entre requisições
    scrape_delay: float = Field(
        default=1.0,
        description="Delay em segundos entre requisições de scraping"
    )
    
    # User agent para scraping
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User agent para requisições de scraping"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE RABBITMQ
    # ============================================================================
    
    # URL do RabbitMQ
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="URL de conexão com RabbitMQ"
    )
    
    # Configurações de filas
    queue_name: str = Field(
        default="aum_scraping_queue",
        description="Nome da fila principal de scraping"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE EXPORTAÇÃO
    # ============================================================================
    
    # Diretório para arquivos de exportação
    export_directory: str = Field(
        default="./exports",
        description="Diretório para salvar relatórios Excel"
    )
    
    # Formato de data para nomes de arquivo
    date_format: str = Field(
        default="%Y%m%d_%H%M%S",
        description="Formato de data para nomes de arquivo"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE LOGGING
    # ============================================================================
    
    # Nível de logging
    log_level: str = Field(
        default="INFO",
        description="Nível de logging da aplicação"
    )
    
    # Formato de log
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Formato das mensagens de log"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE SEGURANÇA
    # ============================================================================
    
    # CORS origins permitidos
    cors_origins: list = Field(
        default=["*"],
        description="Origens permitidas para CORS"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Número máximo de requisições por minuto"
    )
    
    rate_limit_window: int = Field(
        default=60,
        description="Janela de tempo para rate limiting em segundos"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE TESTES
    # ============================================================================
    
    # Cobertura mínima de testes
    min_test_coverage: float = Field(
        default=80.0,
        description="Cobertura mínima de testes (conforme documento)"
    )
    
    # Diretório de testes
    test_directory: str = Field(
        default="./tests",
        description="Diretório contendo os testes"
    )
    
    # ============================================================================
    # CONFIGURAÇÕES DE DESENVOLVIMENTO
    # ============================================================================
    
    # Modo de debug
    debug: bool = Field(
        default=False,
        description="Modo de debug da aplicação"
    )
    
    # Ambiente
    environment: str = Field(
        default="development",
        description="Ambiente da aplicação (development, staging, production)"
    )
    
    # ============================================================================
    # MÉTODOS DE VALIDAÇÃO
    # ============================================================================
    
    def validate_config(self) -> bool:
        """
        Valida as configurações da aplicação
        
        Retorna True se todas as configurações estiverem válidas
        """
        errors = []
        
        # Validações obrigatórias
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY é obrigatória")
        
        if not self.database_url:
            errors.append("DATABASE_URL é obrigatória")
        
        # Validações de valores
        if self.max_tokens_per_request > 1500:
            errors.append("MAX_TOKENS_PER_REQUEST não pode exceder 1500")
        
        if self.max_tokens_per_day > 1000000:
            errors.append("MAX_TOKENS_PER_DAY não pode exceder 1.000.000")
        
        if self.budget_alert_threshold <= 0 or self.budget_alert_threshold >= 1:
            errors.append("BUDGET_ALERT_THRESHOLD deve estar entre 0 e 1")
        
        if self.scrape_timeout < 10:
            errors.append("SCRAPE_TIMEOUT deve ser pelo menos 10 segundos")
        
        if self.max_concurrent_scrapes < 1:
            errors.append("MAX_CONCURRENT_SCRAPES deve ser pelo menos 1")
        
        # Retorna resultado da validação
        if errors:
            for error in errors:
                print(f"❌ Erro de configuração: {error}")
            return False
        
        print("✅ Todas as configurações estão válidas")
        return True
    
    def get_database_config(self) -> dict:
        """Retorna configurações do banco de dados"""
        return {
            'url': self.database_url,
            'pool_size': self.database_pool_size,
            'max_overflow': self.database_max_overflow
        }
    
    def get_openai_config(self) -> dict:
        """Retorna configurações da OpenAI"""
        return {
            'api_key': self.openai_api_key,
            'model': self.openai_model,
            'max_tokens_per_request': self.max_tokens_per_request,
            'max_tokens_per_day': self.max_tokens_per_day,
            'budget_alert_threshold': self.budget_alert_threshold
        }
    
    def get_scraping_config(self) -> dict:
        """Retorna configurações de scraping"""
        return {
            'timeout': self.scrape_timeout,
            'max_concurrent': self.max_concurrent_scrapes,
            'delay': self.scrape_delay,
            'user_agent': self.user_agent
        }
    
    def get_rabbitmq_config(self) -> dict:
        """Retorna configurações do RabbitMQ"""
        return {
            'url': self.rabbitmq_url,
            'queue_name': self.queue_name
        }
    
    def get_export_config(self) -> dict:
        """Retorna configurações de exportação"""
        return {
            'directory': self.export_directory,
            'date_format': self.date_format
        }
    
    class Config:
        """Configurações do Pydantic"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Instância global das configurações
settings = Settings()

# Valida configurações na inicialização
if not settings.validate_config():
    raise ValueError("Configurações inválidas. Verifique as variáveis de ambiente.")

# Configurações específicas por ambiente
if settings.environment == "production":
    # Configurações de produção
    settings.debug = False
    settings.log_level = "WARNING"
    settings.cors_origins = ["https://seu-dominio.com"]
elif settings.environment == "staging":
    # Configurações de staging
    settings.debug = True
    settings.log_level = "INFO"
    settings.cors_origins = ["https://staging.seu-dominio.com"]
else:
    # Configurações de desenvolvimento
    settings.debug = True
    settings.log_level = "DEBUG"
    settings.cors_origins = ["*"]

# Configurações de logging
import logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)

# Cria diretório de exportação se não existir
os.makedirs(settings.export_directory, exist_ok=True)

# Log das configurações carregadas
logger = logging.getLogger(__name__)
logger.info(f"🚀 Configurações carregadas para ambiente: {settings.environment}")
logger.info(f"📊 OpenAI: {settings.openai_model}, Tokens: {settings.max_tokens_per_request}/{settings.max_tokens_per_day}")
logger.info(f"🕷️ Scraping: {settings.max_concurrent_scrapes} simultâneos, Timeout: {settings.scrape_timeout}s")
logger.info(f"💾 Banco: {settings.database_url}")
logger.info(f"🐰 RabbitMQ: {settings.rabbitmq_url}")
logger.info(f"📁 Export: {settings.export_directory}")
