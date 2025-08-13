#!/usr/bin/env python3
"""
AUM Scraper - Aplicação Principal
Sistema para coleta automática de Patrimônio Sob Gestão (AUM) de empresas financeiras
"""

import uvicorn
import os
from app.main import app

if __name__ == "__main__":
    # Configurações do servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"🚀 Iniciando AUM Scraper na porta {port}")
    print(f"📊 API disponível em: http://{host}:{port}")
    print(f"📚 Documentação: http://{host}:{port}/docs")
    
    # Inicia o servidor
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
  