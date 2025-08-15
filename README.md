# 🚀 AUM Scraper - Coletor Automático de Patrimônio Sob Gestão

Sistema Full-Stack em Python 3.11 para coleta automática de Patrimônio Sob Gestão (AUM) de empresas financeiras, utilizando web scraping inteligente e IA GPT-4o para extração de dados.

## ✨ Características Principais

- **Web Scraping Inteligente**: Usa Playwright para capturar conteúdo estático e dinâmico
- **IA GPT-4o**: Extração automática de AUM com controle de budget de tokens
- **Fallback com Regex**: Sistema inteligente que extrai valores quando IA falha
- **Paralelismo Controlado**: Sistema de filas RabbitMQ para evitar bloqueios
- **Persistência Robusta**: PostgreSQL com SQLAlchemy 2 e Alembic
- **API REST Completa**: FastAPI com documentação automática
- **Monitoramento**: Controle de uso de tokens e estatísticas de scraping
- **Exportação Excel**: Relatórios sem duplicatas com valores corretos
- **Tratamento de Erros**: Sistema robusto com fallbacks automáticos

## 🆕 **ÚLTIMAS ATUALIZAÇÕES (v2.0)**

### ✅ **Correções Implementadas:**
- **Excel sem duplicatas**: Cada empresa aparece apenas uma vez
- **Coluna "AUM Valor" corrigida**: Mostra "NAO_DISPONIVEL" ou valor real
- **Fallback com Regex**: Extrai valores quando OpenAI falha
- **Tratamento de erros**: Sem mais crashes por problemas de sintaxe
- **Sistema robusto**: Funciona mesmo com falhas de API externa

### 🔧 **Fallback com Regex:**
- **Padrões inteligentes**: "290 milhões sob custódia", "patrimônio sob gestão"
- **Normalização automática**: Converte para valores numéricos
- **Score de confiança**: 0.7 para extrações via regex
- **Ativação automática**: Quando OpenAI falha, regex assume

## 🏗️ Arquitetura

```
AUM_Scraper/
├── backend/                 # Backend Python
│   ├── app/                # Aplicação principal
│   │   ├── models/         # Modelos SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── services/       # Serviços de negócio
│   │   └── main.py         # Aplicação FastAPI
│   ├── tests/              # Testes Pytest
│   ├── alembic/            # Migrações do banco
│   ├── Dockerfile          # Container Docker
│   └── requirements.txt    # Dependências Python
├── data/                   # Dados e arquivos CSV
└── docker-compose.yml      # Orquestração Docker
```

## 🚀 Instalação e Configuração

### Pré-requisitos

- Docker e Docker Compose
- Python 3.11+ (para desenvolvimento local)
- OpenAI API Key (opcional - sistema funciona com fallback)

### 1. Clone o repositório

```bash
git clone <repository-url>
cd AUM_Scraper
```

### 2. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# OpenAI API (opcional - sistema funciona sem ela)
OPENAI_API_KEY=sua_chave_api_aqui

# Banco de dados
DATABASE_URL=postgresql://scraper:scraperpw@localhost:5432/scraperdb

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Configurações da aplicação
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

### 3. Execute com Docker Compose

```bash
# Inicia todos os serviços
docker-compose up -d

# Verifica status
docker-compose ps

# Logs em tempo real
docker-compose logs -f backend
```

### 4. Acesse a aplicação

- **API**: http://localhost:8000
- **Documentação**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

## 📊 Uso da API

### Endpoints Principais

#### Empresas
- `POST /companies/` - Criar empresa
- `GET /companies/` - Listar empresas
- `GET /companies/{id}` - Obter empresa específica
- `PUT /companies/{id}` - Atualizar empresa
- `DELETE /companies/{id}` - Remover empresa (com limpeza automática)

#### Scraping
- `POST /companies/{id}/scrape` - Disparar scraping para empresa
- `POST /companies/bulk-scrape` - Scraping em lote
- `GET /scraping/status` - Status geral do scraping

#### AUM
- `GET /aum/` - Listar snapshots de AUM
- `GET /aum/latest` - AUM mais recente de cada empresa

#### Monitoramento
- `GET /usage/today` - Uso de tokens do dia
- `GET /usage/stats` - Estatísticas de uso
- `GET /queues/stats` - Status das filas

#### Exportação
- `POST /export/excel` - Gerar relatório Excel (sem duplicatas)
- `GET /export/download/{filename}` - Download do arquivo

#### Upload
- `POST /upload/csv` - Importar empresas via CSV

### Exemplo de Uso

#### 1. Criar empresa

```bash
curl -X POST "http://localhost:8000/companies/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Banco Teste",
    "url_site": "https://bancoteste.com.br",
    "sector": "Bancos"
  }'
```

#### 2. Disparar scraping

```bash
curl -X POST "http://localhost:8000/companies/1/scrape"
```

#### 3. Verificar status

```bash
curl "http://localhost:8000/scraping/status"
```

#### 4. Exportar dados

```bash
curl -X POST "http://localhost:8000/export/excel"
```

## 📁 Estrutura de Dados

### CSV de Entrada

O arquivo `data/companies.csv` deve conter:

```csv
name,url_site,url_linkedin,url_instagram,url_x,sector,employees_count
Empresa A,https://site.com,https://linkedin.com/empresa,https://instagram.com/empresa,https://x.com/empresa,Bancos,1000
```

### Tabelas do Banco

- **companies**: Informações das empresas
- **scrape_logs**: Logs de scraping
- **aum_snapshots**: Snapshots de AUM coletados
- **usage**: Monitoramento de uso de tokens

## 🔧 Desenvolvimento

### Configuração do Ambiente Local

```bash
# Cria ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instala dependências
pip install -r backend/requirements.txt

# Instala Playwright
playwright install

# Configura variáveis de ambiente
export OPENAI_API_KEY=sua_chave_aqui
export DATABASE_URL=postgresql://scraper:scraperpw@localhost:5432/scraperdb
```

### Executar Testes

```bash
# Todos os testes
pytest backend/tests/ -v

# Com cobertura
pytest backend/tests/ --cov=app --cov-report=html

# Teste específico
pytest backend/tests/test_models.py::TestCompany::test_create_company -v
```

### Migrações do Banco

```bash
# Gerar migração
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrações
alembic upgrade head

# Reverter migração
alembic downgrade -1
```

### Executar Localmente

```bash
# Inicia apenas o banco e RabbitMQ
docker-compose up db rabbitmq -d

# Executa a aplicação
cd backend
python main.py
```

## 🐳 Docker

### Serviços

- **PostgreSQL 15**: Banco de dados principal
- **RabbitMQ**: Sistema de filas assíncronas
- **Backend**: Aplicação Python com FastAPI

### Comandos Úteis

```bash
# Rebuild da imagem
docker-compose build --no-cache

# Logs específicos
docker-compose logs backend

# Executar comando no container
docker-compose exec backend python -c "print('Hello World')"

# Parar todos os serviços
docker-compose down

# Parar e remover volumes
docker-compose down -v
```

## 📈 Monitoramento e Logs

### Logs da Aplicação

```bash
# Logs em tempo real
docker-compose logs -f backend

# Logs específicos
docker-compose logs backend | grep "ERROR"
```

### Métricas de Uso

- **Tokens OpenAI**: Monitoramento automático de budget
- **Status de Scraping**: Taxa de sucesso, bloqueios, erros
- **Filas RabbitMQ**: Número de mensagens, consumidores
- **Fallback Regex**: Estatísticas de extração alternativa

### Alertas

- Budget de tokens > 80% do limite diário
- Taxa de sucesso de scraping < 50%
- Filas com muitas mensagens pendentes

## 🔒 Segurança

- Usuário não-root no container Docker
- Validação de entrada com Pydantic
- Sanitização de URLs e conteúdo
- Rate limiting nas filas
- Logs de auditoria para todas as operações
- Proteção contra exposição de chaves API

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Erro de conexão com banco

```bash
# Verifica se o PostgreSQL está rodando
docker-compose ps db

# Testa conexão
docker-compose exec backend python -c "
from app.models.database import engine
print(engine.execute('SELECT 1').scalar())
"
```

#### 2. Erro de Playwright

```bash
# Reinstala browsers
docker-compose exec backend playwright install --with-deps chromium

# Verifica dependências do sistema
docker-compose exec backend ldd /usr/bin/chromium
```

#### 3. Erro de RabbitMQ

```bash
# Verifica status
docker-compose exec rabbitmq rabbitmqctl status

# Reinicia serviço
docker-compose restart rabbitmq
```

#### 4. Erro de OpenAI

```bash
# Verifica API key
echo $OPENAI_API_KEY

# Testa conexão
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models

# Sistema funciona com fallback regex mesmo sem OpenAI
```

#### 5. Excel com duplicatas (RESOLVIDO ✅)

```bash
# Sistema agora gera Excel sem duplicatas
# Cada empresa aparece apenas uma vez
# Coluna "AUM Valor" mostra valores corretos
```

## 📝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🤝 Suporte

- **Issues**: Use o GitHub Issues para reportar bugs
- **Documentação**: Consulte `/docs` na API para documentação interativa
- **Logs**: Verifique logs do container para debugging

## 🔮 Roadmap

- [x] **Sistema robusto com fallbacks** ✅
- [x] **Excel sem duplicatas** ✅
- [x] **Fallback com regex** ✅
- [x] **Tratamento de erros** ✅
- [ ] Interface web para administração
- [ ] Sistema de notificações por email
- [ ] Integração com mais fontes de dados
- [ ] Machine Learning para melhorar extração
- [ ] Dashboard de métricas em tempo real
- [ ] API para terceiros
- [ ] Sistema de backup automático

## 🎯 **STATUS ATUAL DO PROJETO**

### ✅ **FUNCIONALIDADES IMPLEMENTADAS:**
- **Sistema 100% funcional** com 5 empresas bancárias
- **Scraping automático** funcionando perfeitamente
- **Fallback com regex** ativo quando OpenAI falha
- **Excel sem duplicatas** com valores corretos
- **API robusta** com tratamento de erros
- **Docker funcionando** perfeitamente

### 🔧 **TECNOLOGIAS UTILIZADAS:**
- **Python 3.11** + FastAPI
- **PostgreSQL** + SQLAlchemy 2
- **RabbitMQ** para filas assíncronas
- **Playwright** para web scraping
- **OpenAI GPT-4o** + **Regex fallback**
- **Docker Compose** para orquestração

### 📊 **DADOS DE TESTE:**
- **5 empresas bancárias** cadastradas
- **Scraping funcionando** em todas as fontes
- **Fallback ativo** quando necessário
- **Excel sendo gerado** corretamente

---

**Desenvolvido por Giovana Manuquian 2025** 🚀
**Projeto AUM Scraper - Versão 2.0 - COMPLETO E FUNCIONAL** ✅
