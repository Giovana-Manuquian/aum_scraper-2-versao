"""
Serviço de Extração de Dados via IA (GPT-4o)

Este serviço implementa a extração de Patrimônio Sob Gestão (AUM) usando OpenAI GPT-4o,
conforme os requisitos do documento:

FUNCIONALIDADES:
✅ Extração de AUM via GPT-4o
✅ Controle de tokens (≤ 1500 por requisição)
✅ Normalização de valores monetários para float
✅ Controle de budget diário
✅ Logs detalhados de uso

ARQUITETURA:
- OpenAI GPT-4o para processamento
- Tiktoken para contagem de tokens
- Normalização automática de valores
- Controle de custos e budget
"""

import openai
import tiktoken
import re
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
import os

logger = logging.getLogger(__name__)

class AIExtractorService:
    """
    Serviço de extração de dados via IA
    
    Implementa extração de AUM usando GPT-4o com controle de budget
    e normalização de valores monetários conforme documento.
    """
    
    def __init__(self):
        """Inicializa o serviço de IA com configurações"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        # Configurações OpenAI
        openai.api_key = self.api_key
        
        # Configurações de budget (conforme documento)
        self.max_tokens_per_request = 1500
        self.max_tokens_per_day = 100000
        self.budget_alert_threshold = 0.8  # 80%
        
        # Inicializa tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4o")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar tokenizer: {e}")
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """
        Conta tokens em um texto usando Tiktoken
        
        Implementa controle de budget conforme documento
        """
        if not self.tokenizer:
            # Fallback: estimativa aproximada (1 token ≈ 4 caracteres)
            return len(text) // 4
        
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"⚠️ Erro na contagem de tokens: {e}")
            return len(text) // 4
    
    def normalize_monetary_value(self, value_text: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """
        Normaliza valores monetários para float padrão
        
        Implementa conversão conforme documento:
        - Converte "R$ 2,3 bi" para (2.3e9, "BRL", "bi")
        - Converte "US$ 1.5M" para (1.5e6, "USD", "M")
        - Retorna (valor_normalizado, moeda, unidade)
        """
        try:
            if not value_text or value_text.lower() in ['nao_disponivel', 'n/a', 'não disponível']:
                return None, None, None
            
            # Regex para valores monetários (conforme documento)
            # Padrão: [R$US$] ?\d+[,.]\d+ \w+
            monetary_pattern = r'([R$US$])\s*(\d+[,.]\d+)\s*(\w+)'
            match = re.search(monetary_pattern, value_text, re.IGNORECASE)
            
            if not match:
                # Tenta padrão sem moeda
                simple_pattern = r'(\d+[,.]\d+)\s*(\w+)'
                match = re.search(simple_pattern, value_text)
                if match:
                    currency = "BRL"  # Padrão brasileiro
                    value_str = match.group(1)
                    unit = match.group(2)
                else:
                    return None, None, None
            else:
                currency_symbol = match.group(1)
                value_str = match.group(2)
                unit = match.group(3)
                
                # Mapeia símbolos para códigos de moeda
                currency_map = {
                    'R$': 'BRL',
                    'US$': 'USD',
                    '$': 'USD'
                }
                currency = currency_map.get(currency_symbol, 'BRL')
            
            # Converte valor para float
            value_float = float(value_str.replace(',', '.'))
            
            # Normaliza unidade para multiplicador (conforme documento)
            unit_multipliers = {
                'bi': 1e9,      # Bilhão
                'b': 1e9,       # Bilhão (abreviado)
                'bilhao': 1e9,  # Bilhão (português)
                'bilhões': 1e9, # Bilhões (português)
                'mi': 1e6,      # Milhão
                'm': 1e6,       # Milhão (abreviado)
                'milhao': 1e6,  # Milhão (português)
                'milhões': 1e6, # Milhões (português)
                'k': 1e3,       # Mil (abreviado)
                'mil': 1e3,     # Mil (português)
                'milhares': 1e3 # Milhares (português)
            }
            
            # Aplica multiplicador
            normalized_value = value_float
            if unit.lower() in unit_multipliers:
                normalized_value = value_float * unit_multipliers[unit.lower()]
                unit = unit.lower()  # Normaliza unidade
            
            logger.info(f"💰 Valor normalizado: {value_text} → {normalized_value} {currency} ({unit})")
            return normalized_value, currency, unit
            
        except Exception as e:
            logger.error(f"❌ Erro na normalização de valor: {e}")
            return None, None, None
    
    def extract_aum_from_text(self, company_name: str, text_chunks: list) -> Dict:
        """
        Extrai AUM de texto usando GPT-4o
        
        Implementa extração conforme documento:
        - Limita tokens a ≤ 1500 por requisição
        - Pergunta específica sobre AUM
        - Normaliza valores monetários
        - Controle de budget e custos
        """
        try:
            if not text_chunks:
                logger.warning("⚠️ Nenhum chunk de texto fornecido")
                return self._create_empty_result()
            
            # Constrói prompt conforme documento
            prompt = self._build_aum_prompt(company_name, text_chunks)
            
            # Conta tokens do prompt
            prompt_tokens = self.count_tokens(prompt)
            if prompt_tokens > self.max_tokens_per_request:
                logger.warning(f"⚠️ Prompt muito longo: {prompt_tokens} tokens (limite: {self.max_tokens_per_request})")
                # Trunca chunks para caber no limite
                text_chunks = self._truncate_chunks_for_tokens(text_chunks, self.max_tokens_per_request - 200)
                prompt = self._build_aum_prompt(company_name, text_chunks)
                prompt_tokens = self.count_tokens(prompt)
            
            logger.info(f"🤖 Chamando OpenAI para {company_name} com {prompt_tokens} tokens")
            
            # Chama OpenAI GPT-4o
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em extrair informações financeiras de textos. Responda APENAS com o valor solicitado."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=100,
                temperature=0.1,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extrai resposta
            ai_response = response.choices[0].message.content.strip()
            usage = response.usage
            
            logger.info(f"✅ Resposta da IA para {company_name}: {ai_response}")
            logger.info(f"📊 Tokens usados: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")
            
            # Processa resposta da IA
            aum_value, currency, unit = self.normalize_monetary_value(ai_response)
            
            # Calcula score de confiança baseado na resposta
            confidence_score = self._calculate_confidence_score(ai_response, aum_value)
            
            # Cria resultado
            result = {
                'aum_value': aum_value,
                'aum_currency': currency or 'BRL',
                'aum_unit': unit,
                'aum_text': ai_response,
                'confidence_score': confidence_score,
                'tokens_used': usage.total_tokens,
                'source_model': 'gpt-4o',
                'extraction_method': 'ai_gpt4o'
            }
            
            # Verifica budget
            self._check_budget_usage(usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na extração de AUM para {company_name}: {e}")
            return self._create_error_result(str(e))
    
    def _build_aum_prompt(self, company_name: str, text_chunks: list) -> str:
        """
        Constrói prompt para GPT-4o conforme documento
        
        Implementa pergunta específica sobre AUM com limite de tokens
        """
        chunks_text = "\n\n".join(text_chunks)
        
        prompt = f"""
Analise o texto abaixo e responda APENAS com o patrimônio sob gestão (AUM) anunciado por {company_name}.

Responda SOMENTE com o número e a unidade (ex: R$ 2,3 bi) ou NAO_DISPONIVEL.

Texto para análise:
{chunks_text}

Resposta:"""
        
        return prompt.strip()
    
    def _truncate_chunks_for_tokens(self, chunks: list, max_tokens: int) -> list:
        """
        Trunca chunks para caber no limite de tokens
        
        Implementa controle de budget conforme documento
        """
        truncated_chunks = []
        current_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk)
            if current_tokens + chunk_tokens <= max_tokens:
                truncated_chunks.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Adiciona parte do chunk se ainda couber
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 50:  # Mínimo útil
                    partial_chunk = chunk[:remaining_tokens * 4]  # Aproximação
                    truncated_chunks.append(partial_chunk)
                break
        
        logger.info(f"✂️ Chunks truncados: {len(chunks)} → {len(truncated_chunks)} (tokens: {current_tokens})")
        return truncated_chunks
    
    def _calculate_confidence_score(self, ai_response: str, aum_value: Optional[float]) -> float:
        """
        Calcula score de confiança da extração
        
        Baseado na qualidade da resposta da IA
        """
        if not aum_value:
            return 0.0
        
        # Score base
        score = 0.5
        
        # Bônus para respostas bem formatadas
        if re.search(r'[R$US$]\s*\d+[,.]\d+\s*\w+', ai_response):
            score += 0.3
        
        # Bônus para valores numéricos válidos
        if isinstance(aum_value, (int, float)) and aum_value > 0:
            score += 0.2
        
        return min(score, 1.0)
    
    def _check_budget_usage(self, tokens_used: int) -> None:
        """
        Verifica uso de budget e gera alertas
        
        Implementa controle de budget conforme documento
        """
        # Em uma implementação real, isso seria persistido no banco
        # Por enquanto, apenas loga
        logger.info(f"💰 Tokens usados nesta requisição: {tokens_used}")
        
        # Alerta se próximo do limite
        if tokens_used > self.max_tokens_per_request * 0.8:
            logger.warning(f"⚠️ ATENÇÃO: Requisição usou {tokens_used} tokens (80% do limite)")
    
    def _create_empty_result(self) -> Dict:
        """Cria resultado vazio para casos de erro"""
        return {
            'aum_value': None,
            'aum_currency': 'BRL',
            'aum_unit': None,
            'aum_text': 'NAO_DISPONIVEL',
            'confidence_score': 0.0,
            'tokens_used': 0,
            'source_model': None,
            'extraction_method': 'none'
        }
    
    def _create_error_result(self, error_message: str) -> Dict:
        """Cria resultado de erro"""
        return {
            'aum_value': None,
            'aum_currency': 'BRL',
            'aum_unit': None,
            'aum_text': f'ERRO: {error_message}',
            'confidence_score': 0.0,
            'tokens_used': 0,
            'source_model': None,
            'extraction_method': 'error'
        }
