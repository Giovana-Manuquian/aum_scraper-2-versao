# Usa Python 3.11 como especificado
FROM python:3.11-slim

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências do sistema, incluindo fontes necessárias para Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxss1 \
    libgtk-3-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libxshmfence1 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia requirements primeiro para aproveitar cache do Docker
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright browsers (chromium) sem --with-deps para evitar erros
RUN playwright install chromium

# Copia código da aplicação
COPY . .

# Cria diretório para exports
RUN mkdir -p exports

# Cria usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expõe porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a aplicação
CMD ["python", "main.py"]
