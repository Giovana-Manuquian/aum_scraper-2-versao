import asyncio
import re
from typing import List, Dict, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
import logging
from datetime import datetime
import time
import random

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self, max_concurrent: int = 3, delay_range: Tuple[int, int] = (2, 5)):
        self.max_concurrent = max_concurrent
        self.delay_range = delay_range
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.browser: Optional[Browser] = None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
    
    async def scrape_company_sources(self, company_data: Dict) -> List[Dict]:
        """Scrapa todas as fontes de uma empresa com controle de paralelismo"""
        sources = []
        
        # URLs para scraping
        urls_to_scrape = [
            (company_data.get('url_site'), 'website'),
            (company_data.get('url_linkedin'), 'linkedin'),
            (company_data.get('url_instagram'), 'instagram'),
            (company_data.get('url_x'), 'x')
        ]
        
        # Filtra URLs válidas
        valid_urls = [(url, source_type) for url, source_type in urls_to_scrape if url]
        
        # Executa scraping com semáforo para controlar paralelismo
        tasks = []
        for url, source_type in valid_urls:
            task = self._scrape_with_semaphore(url, source_type, company_data['name'])
            tasks.append(task)
        
        # Aguarda todas as tarefas com timeout
        try:
            results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=300)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Erro no scraping: {result}")
                elif result:
                    sources.append(result)
        except asyncio.TimeoutError:
            logger.error("Timeout no scraping de todas as fontes")
        
        return sources
    
    async def _scrape_with_semaphore(self, url: str, source_type: str, company_name: str) -> Optional[Dict]:
        """Executa scraping com controle de concorrência"""
        async with self.semaphore:
            try:
                # Delay aleatório para evitar bloqueios
                delay = random.uniform(*self.delay_range)
                await asyncio.sleep(delay)
                
                return await self._scrape_single_source(url, source_type, company_name)
            except Exception as e:
                logger.error(f"Erro ao fazer scraping de {url}: {e}")
                return None
    
    async def _scrape_single_source(self, url: str, source_type: str, company_name: str) -> Optional[Dict]:
        """Scrapa uma única fonte"""
        page = None
        try:
            page = await self.browser.new_page()
            
            # Configurações da página
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            # Timeout para carregamento
            page.set_default_timeout(30000)
            
            # Navega para a URL
            response = await page.goto(url, wait_until='networkidle')
            
            if not response or response.status >= 400:
                return {
                    'url': url,
                    'source_type': source_type,
                    'status': 'failed',
                    'error_message': f'HTTP {response.status if response else "Unknown"}',
                    'content': None,
                    'is_blocked': False
                }
            
            # Aguarda carregamento dinâmico
            await page.wait_for_timeout(3000)
            
            # Extrai conteúdo
            content = await self._extract_content(page, source_type)
            
            # Verifica se foi bloqueado
            is_blocked = await self._check_if_blocked(page)
            
            return {
                'url': url,
                'source_type': source_type,
                'status': 'success',
                'error_message': None,
                'content': content,
                'is_blocked': is_blocked,
                'content_length': len(content) if content else 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao fazer scraping de {url}: {e}")
            return {
                'url': url,
                'source_type': source_type,
                'status': 'failed',
                'error_message': str(e),
                'content': None,
                'is_blocked': False
            }
        finally:
            if page:
                await page.close()
    
    async def _extract_content(self, page, source_type: str) -> str:
        """Extrai conteúdo baseado no tipo de fonte"""
        try:
            if source_type == 'website':
                # Para sites institucionais, foca em conteúdo principal
                content = await page.evaluate("""
                    () => {
                        const main = document.querySelector('main') || document.querySelector('#main') || document.querySelector('.main');
                        if (main) {
                            return main.innerText;
                        }
                        
                        // Fallback para body
                        return document.body.innerText;
                    }
                """)
            elif source_type == 'linkedin':
                # Para LinkedIn, extrai posts e informações da empresa
                content = await page.evaluate("""
                    () => {
                        const posts = Array.from(document.querySelectorAll('[data-test-id="post-content"]'));
                        const companyInfo = Array.from(document.querySelectorAll('.org-top-card-summary-info-list__info-item'));
                        
                        const postTexts = posts.map(p => p.innerText).join(' ');
                        const infoTexts = companyInfo.map(i => i.innerText).join(' ');
                        
                        return postTexts + ' ' + infoTexts;
                    }
                """)
            elif source_type in ['instagram', 'x']:
                # Para redes sociais, extrai posts e bio
                content = await page.evaluate("""
                    () => {
                        const posts = Array.from(document.querySelectorAll('article'));
                        const bio = document.querySelector('header')?.innerText || '';
                        
                        const postTexts = posts.map(p => p.innerText).join(' ');
                        return bio + ' ' + postTexts;
                    }
                """)
            else:
                # Fallback genérico
                content = await page.evaluate("() => document.body.innerText")
            
            return content.strip() if content else ""
            
        except Exception as e:
            logger.error(f"Erro ao extrair conteúdo: {e}")
            return ""
    
    async def _check_if_blocked(self, page) -> bool:
        """Verifica se a página foi bloqueada"""
        try:
            # Verifica indicadores comuns de bloqueio
            blocked_indicators = [
                'blocked', 'captcha', 'robot', 'access denied',
                'rate limit', 'too many requests', 'blocked by'
            ]
            
            page_text = await page.evaluate("() => document.body.innerText.toLowerCase()")
            
            for indicator in blocked_indicators:
                if indicator in page_text:
                    return True
            
            # Verifica se há captcha
            captcha_elements = await page.query_selector_all('iframe[src*="captcha"], .captcha, #captcha')
            if captcha_elements:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar bloqueio: {e}")
            return False
    
    def extract_relevant_chunks(self, html_content: str, max_chunks: int = 5) -> List[str]:
        """Extrai chunks relevantes do HTML focando em parágrafos que podem conter AUM"""
        if not html_content:
            return []
        
        # Keywords relacionados a AUM
        aum_keywords = [
            'patrimônio sob gestão', 'aum', 'assets under management',
            'patrimônio', 'gestão', 'fundo', 'investimento',
            'bilhões', 'milhões', 'milhares', 'bi', 'mi', 'mil',
            'reais', 'dólares', 'euros', 'r$', 'us$', '€'
        ]
        
        # Divide o conteúdo em parágrafos
        paragraphs = re.split(r'\n\s*\n', html_content)
        
        # Filtra parágrafos relevantes
        relevant_paragraphs = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) < 50:  # Ignora parágrafos muito curtos
                continue
                
            # Verifica se contém keywords relevantes
            paragraph_lower = paragraph.lower()
            relevance_score = sum(1 for keyword in aum_keywords if keyword in paragraph_lower)
            
            if relevance_score > 0:
                relevant_paragraphs.append((paragraph, relevance_score))
        
        # Ordena por relevância e retorna os top chunks
        relevant_paragraphs.sort(key=lambda x: x[1], reverse=True)
        
        # Limita o tamanho de cada chunk para não exceder 1500 tokens
        chunks = []
        for paragraph, score in relevant_paragraphs[:max_chunks]:
            # Estimativa: 1 token ≈ 4 caracteres
            if len(paragraph) <= 6000:  # 1500 tokens * 4
                chunks.append(paragraph)
            else:
                # Divide parágrafos muito longos
                words = paragraph.split()
                chunk = ""
                for word in words:
                    if len(chunk + " " + word) <= 6000:
                        chunk += " " + word if chunk else word
                    else:
                        if chunk:
                            chunks.append(chunk)
                        chunk = word
                if chunk:
                    chunks.append(chunk)
        
        return chunks[:max_chunks]
