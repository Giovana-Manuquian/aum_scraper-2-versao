from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import logging
import asyncio
from datetime import datetime, date, timedelta
import os

from .models.database import get_db, engine, Base
from .models import Company, ScrapeLog, AumSnapshot, Usage
from .schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    AumSnapshotResponse, ScrapeLogResponse, UsageResponse
)
from .services.scraper import ScraperService
from .services.ai_extractor import AIExtractorService
from .services.queue_service import QueueService

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria tabelas do banco
Base.metadata.create_all(bind=engine)

# Inicializa FastAPI
app = FastAPI(
    title="AUM Scraper API",
    description="API para coleta automática de Patrimônio Sob Gestão (AUM) de empresas financeiras",
    version="1.0.0"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa serviços
queue_service = QueueService()
ai_extractor = AIExtractorService()

@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da aplicação"""
    try:
        await queue_service.connect()
        logger.info("Aplicação iniciada com sucesso")
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de encerramento da aplicação"""
    try:
        await queue_service.disconnect()
        logger.info("Aplicação encerrada com sucesso")
    except Exception as e:
        logger.error(f"Erro no encerramento: {e}")

# ============================================================================
# ENDPOINTS DE EMPRESAS
# ============================================================================

@app.post("/companies/", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Cria uma nova empresa"""
    try:
        db_company = Company(**company.dict())
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        return db_company
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao criar empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/companies/", response_model=List[CompanyResponse])
async def get_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista todas as empresas"""
    companies = db.query(Company).offset(skip).limit(limit).all()
    return companies

@app.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int, db: Session = Depends(get_db)):
    """Obtém uma empresa específica"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company

@app.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza uma empresa"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    try:
        for field, value in company_update.dict(exclude_unset=True).items():
            setattr(db_company, field, value)
        
        db.commit()
        db.refresh(db_company)
        return db_company
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.delete("/companies/{company_id}")
async def delete_company(company_id: int, db: Session = Depends(get_db)):
    """Remove uma empresa"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    try:
        db.delete(db_company)
        db.commit()
        return {"message": "Empresa removida com sucesso"}
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao remover empresa: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# ============================================================================
# ENDPOINTS DE SCRAPING
# ============================================================================

@app.post("/companies/{company_id}/scrape")
async def trigger_scraping(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Dispara scraping para uma empresa específica"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    # Adiciona tarefa de scraping ao background
    background_tasks.add_task(
        process_company_scraping,
        company_id,
        {
            'id': company.id,
            'name': company.name,
            'url_site': company.url_site,
            'url_linkedin': company.url_linkedin,
            'url_instagram': company.url_instagram,
            'url_x': company.url_x,
            'sector': company.sector,
            'employees_count': company.employees_count
        }
    )
    
    return {"message": "Scraping iniciado em background", "company_id": company_id}

@app.post("/companies/bulk-scrape")
async def trigger_bulk_scraping(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Dispara scraping para todas as empresas"""
    companies = db.query(Company).all()
    
    if not companies:
        raise HTTPException(status_code=404, detail="Nenhuma empresa encontrada")
    
    # Adiciona tarefas de scraping ao background
    for company in companies:
        background_tasks.add_task(
            process_company_scraping,
            company.id,
            {
                'id': company.id,
                'name': company.name,
                'url_site': company.url_site,
                'url_linkedin': company.url_linkedin,
                'url_instagram': company.url_instagram,
                'url_x': company.url_x,
                'sector': company.sector,
                'employees_count': company.employees_count
            }
        )
    
    return {
        "message": f"Scraping em lote iniciado para {len(companies)} empresas",
        "companies_count": len(companies)
    }

@app.get("/scraping/status")
async def get_scraping_status(db: Session = Depends(get_db)):
    """Retorna status geral do scraping"""
    total_companies = db.query(Company).count()
    total_scrape_logs = db.query(ScrapeLog).count()
    successful_scrapes = db.query(ScrapeLog).filter(ScrapeLog.status == "success").count()
    failed_scrapes = db.query(ScrapeLog).filter(ScrapeLog.status == "failed").count()
    blocked_scrapes = db.query(ScrapeLog).filter(ScrapeLog.is_blocked == True).count()
    
    return {
        "total_companies": total_companies,
        "total_scrape_logs": total_scrape_logs,
        "successful_scrapes": successful_scrapes,
        "failed_scrapes": failed_scrapes,
        "blocked_scrapes": blocked_scrapes,
        "success_rate": (successful_scrapes / total_scrape_logs * 100) if total_scrape_logs > 0 else 0
    }


# ============================================================================
# ENDPOINTS DE AUM
# ============================================================================

@app.get("/aum/", response_model=List[AumSnapshotResponse])
async def get_aum_snapshots(
    company_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista snapshots de AUM"""
    query = db.query(AumSnapshot)
    
    if company_id:
        query = query.filter(AumSnapshot.company_id == company_id)
    
    snapshots = query.offset(skip).limit(limit).all()
    return snapshots

@app.get("/aum/latest")
async def get_latest_aum(db: Session = Depends(get_db)):
    """Retorna o AUM mais recente de cada empresa"""
    # Subquery para obter o ID do snapshot mais recente por empresa
    latest_snapshots = db.query(
        AumSnapshot.company_id,
        AumSnapshot.id.label('latest_id')
    ).distinct(AumSnapshot.company_id).order_by(
        AumSnapshot.company_id,
        AumSnapshot.created_at.desc()
    ).subquery()
    
    # Query principal para obter os snapshots mais recentes
    latest_aum = db.query(AumSnapshot).join(
        latest_snapshots,
        AumSnapshot.id == latest_snapshots.c.latest_id
    ).all()
    
    return latest_aum

# ============================================================================
# ENDPOINTS DE USO DE TOKENS
# ============================================================================

@app.get("/usage/today", response_model=UsageResponse)
async def get_today_usage(db: Session = Depends(get_db)):
    """Retorna uso de tokens do dia atual"""
    today = date.today()
    
    # Busca uso do dia no banco
    daily_usage = db.query(Usage).filter(
        Usage.date >= today
    ).first()
    
    if daily_usage:
        return daily_usage
    
    # Se não existe no banco, retorna estatísticas do serviço
    stats = ai_extractor.get_daily_usage_stats()
    
    # Cria registro no banco
    new_usage = Usage(
        date=today,
        tokens_used=stats['tokens_used'],
        tokens_limit=stats['tokens_limit'],
        cost_usd=None,  # OpenAI não fornece custo por chamada
        api_calls=stats['api_calls'],
        operation_type='ai_processing'
    )
    
    db.add(new_usage)
    db.commit()
    db.refresh(new_usage)
    
    return new_usage

@app.get("/usage/stats")
async def get_usage_stats(db: Session = Depends(get_db)):
    """Retorna estatísticas de uso de tokens"""
    # Estatísticas do dia
    today_stats = ai_extractor.get_daily_usage_stats()
    
    # Estatísticas históricas do banco
    total_tokens = db.query(Usage).with_entities(
        db.func.sum(Usage.tokens_used)
    ).scalar() or 0
    
    total_calls = db.query(Usage).with_entities(
        db.func.sum(Usage.api_calls)
    ).scalar() or 0
    
    # Uso dos últimos 7 dias
    week_ago = date.today() - timedelta(days=7)
    weekly_usage = db.query(Usage).filter(
        Usage.date >= week_ago
    ).all()
    
    weekly_tokens = sum(u.tokens_used for u in weekly_usage)
    weekly_calls = sum(u.api_calls for u in weekly_usage)
    
    return {
        "today": today_stats,
        "total": {
            "tokens_used": total_tokens,
            "api_calls": total_calls
        },
        "weekly": {
            "tokens_used": weekly_tokens,
            "api_calls": weekly_calls
        },
        "budget_warning": today_stats['usage_percentage'] >= 80
    }

# ============================================================================
# ENDPOINTS DE FILAS
# ============================================================================

@app.get("/queues/stats")
async def get_queue_stats():
    """Retorna estatísticas das filas RabbitMQ"""
    try:
        stats = await queue_service.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas das filas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter estatísticas das filas")

@app.get("/queues/status")
async def get_queues_status():
    """Retorna o status das filas RabbitMQ"""
    try:
        # Conectar ao RabbitMQ para verificar status
        import pika
        
        # Usar as credenciais do docker-compose
        credentials = pika.PlainCredentials('guest', 'guest')
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='rabbitmq',
                port=5672,
                credentials=credentials
            )
        )
        
        channel = connection.channel()
        
        # Verificar status das filas
        queues_info = {}
        for queue_name in ['scraping_queue', 'ai_processing_queue', 'export_queue']:
            try:
                method = channel.queue_declare(queue=queue_name, passive=True)
                queue_info = channel.queue_declare(queue=queue_name, passive=True)
                queues_info[queue_name] = {
                    'messages': queue_info.method.message_count,
                    'consumers': queue_info.method.consumer_count,
                    'status': 'active'
                }
            except Exception as e:
                queues_info[queue_name] = {
                    'messages': 0,
                    'consumers': 0,
                    'status': 'error',
                    'error': str(e)
                }
        
        connection.close()
        
        return {
            "status": "success",
            "queues": queues_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status das filas: {e}")
        return {
            "status": "error",
            "message": "Erro ao conectar com RabbitMQ",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/queues/{queue_type}/purge")
async def purge_queue(queue_type: str):
    """Limpa uma fila específica"""
    try:
        await queue_service.purge_queue(queue_type)
        return {"message": f"Fila {queue_type} limpa com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao limpar fila: {e}")
        raise HTTPException(status_code=500, detail="Erro ao limpar fila")

# ============================================================================
# ENDPOINTS DE EXPORTAÇÃO
# ============================================================================

@app.post("/export/excel")
async def export_to_excel(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Exporta dados para Excel"""
    background_tasks.add_task(generate_excel_report, db)
    return {"message": "Exportação iniciada em background"}

@app.get("/export/files")
async def list_export_files():
    """Lista todos os arquivos Excel disponíveis para download"""
    try:
        exports_dir = "exports"
        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir, exist_ok=True)
            return {"files": [], "message": "Nenhum arquivo gerado ainda"}
        
        files = []
        for filename in os.listdir(exports_dir):
            if filename.endswith('.xlsx'):
                file_path = os.path.join(exports_dir, filename)
                file_stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                    "download_url": f"/export/download/{filename}"
                })
        
        return {
            "files": sorted(files, key=lambda x: x['created'], reverse=True),
            "total_files": len(files)
        }
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao listar arquivos")

@app.get("/export/download/{filename}")
async def download_excel(filename: str):
    """Download do arquivo Excel gerado"""
    file_path = f"exports/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ============================================================================
# ENDPOINTS DE UPLOAD
# ============================================================================

@app.post("/upload/csv")
async def upload_companies_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload de CSV com lista de empresas"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser CSV")
    
    try:
        # Lê o CSV
        df = pd.read_csv(file.file)
        
        # Valida colunas obrigatórias
        required_columns = ['name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Colunas obrigatórias ausentes: {missing_columns}"
            )
        
        # Processa cada linha
        companies_created = 0
        for _, row in df.iterrows():
            company_data = {
                'name': row['name'],
                'url_site': row.get('url_site'),
                'url_linkedin': row.get('url_linkedin'),
                'url_instagram': row.get('url_instagram'),
                'url_x': row.get('url_x'),
                'sector': row.get('sector'),
                'employees_count': row.get('employees_count')
            }
            
            # Remove valores NaN
            company_data = {k: v for k, v in company_data.items() if pd.notna(v)}
            
            # Cria empresa
            db_company = Company(**company_data)
            db.add(db_company)
            companies_created += 1
        
        db.commit()
        
        return {
            "message": f"{companies_created} empresas importadas com sucesso",
            "companies_created": companies_created
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao importar CSV: {e}")
        raise HTTPException(status_code=500, detail="Erro ao importar CSV")

# ============================================================================
# FUNÇÕES DE BACKGROUND
# ============================================================================

async def process_company_scraping(company_id: int, company_data: dict):
    """Processa scraping de uma empresa em background"""
    try:
        logger.info(f"Iniciando scraping para empresa: {company_data['name']}")
        
        # Executa scraping
        async with ScraperService() as scraper:
            scraping_results = await scraper.scrape_company_sources(company_data)
        
        logger.info(f"Scraping concluído para {company_data['name']}. Resultados: {len(scraping_results)}")
        
        # Processa resultados com IA
        for i, result in enumerate(scraping_results):
            logger.info(f"Processando resultado {i+1}/{len(scraping_results)} para {company_data['name']}")
            
            if result['status'] == 'success' and result['content']:
                # Extrai chunks relevantes
                chunks = scraper.extract_relevant_chunks(result['content'])
                logger.info(f"Chunks extraídos para {company_data['name']}: {len(chunks)}")
                
                if chunks:
                    # Processa com IA
                    logger.info(f"Chamando IA para {company_data['name']} com {len(chunks)} chunks")
                    try:
                        # Cria nova instância do AIExtractorService
                        from .services.ai_extractor import AIExtractorService
                        ai_service = AIExtractorService()
                        
                        aum_result = await ai_service.extract_aum_from_chunks(
                            company_data['name'],
                            chunks,
                            result['url'],
                            result['source_type']
                        )
                        
                        # Salva no banco (simplificado para exemplo)
                        logger.info(f"AUM extraído para {company_data['name']}: {aum_result}")
                    except Exception as ai_error:
                        logger.error(f"Erro na IA para {company_data['name']}: {ai_error}")
                        import traceback
                        logger.error(f"Traceback IA: {traceback.format_exc()}")
                else:
                    logger.warning(f"Nenhum chunk relevante encontrado para {company_data['name']}")
            else:
                logger.warning(f"Resultado {i+1} para {company_data['name']} falhou: {result.get('status', 'unknown')}")
        
        logger.info(f"Processamento concluído para empresa: {company_data['name']}")
        
    except Exception as e:
        logger.error(f"Erro no scraping da empresa {company_data['name']}: {e}")
        # Log mais detalhado para debug
        import traceback
        logger.error(f"Traceback completo: {traceback.format_exc()}")

async def generate_excel_report(db: Session):
    """Gera relatório Excel em background"""
    try:
        # Busca dados
        companies = db.query(Company).all()
        aum_snapshots = db.query(AumSnapshot).all()
        
        # Cria DataFrame
        data = []
        for company in companies:
            company_aum = next(
                (aum for aum in aum_snapshots if aum.company_id == company.id),
                None
            )
            
            data.append({
                'Empresa': company.name,
                'Setor': company.sector or 'N/A',
                'Funcionários': company.employees_count or 'N/A',
                'AUM Valor': company_aum.aum_value if company_aum else 'N/A',
                'AUM Moeda': company_aum.aum_currency if company_aum else 'N/A',
                'AUM Unidade': company_aum.aum_unit if company_aum else 'N/A',
                'Fonte': company_aum.source_url if company_aum else 'N/A',
                'Confiança': company_aum.confidence_score if company_aum else 'N/A',
                'Data Coleta': company_aum.created_at.strftime('%Y-%m-%d %H:%M') if company_aum else 'N/A'
            })
        
        # Cria Excel
        df = pd.DataFrame(data)
        
        # Cria diretório de exports se não existir
        os.makedirs('exports', exist_ok=True)
        
        filename = f"aum_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = f"exports/{filename}"
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='AUM Report', index=False)
        
        logger.info(f"Relatório Excel gerado: {filepath}")
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório Excel: {e}")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check da aplicação"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
