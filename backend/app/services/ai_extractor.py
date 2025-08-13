import openai
import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import os
from decimal import Decimal

logger = logging.getLogger(__name__)

class AIExtractorService:
    def __init__(self, api_key: str = None, daily_token_limit: int = 100000):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key não configurada")
        
        openai.api_key = self.api_key
        self.daily_token_limit = daily_token_limit
        self.daily_usage = 0
        self.daily_calls = 0
        self.last_reset_date = date.today()
        
    def _reset_daily_usage(self):
        """Reseta o uso diário se for um novo dia"""
        current_date = date.today()
        if current_date > self.last_reset_date:
            self.daily_usage = 0
            self.daily_calls = 0
            self.last_reset_date = current_date
    
    def _check_budget_limit(self, estimated_tokens: int) -> bool:
        """Verifica se o uso estimado não excede o limite diário"""
        self._reset_daily_usage()
        
        if (self.daily_usage + estimated_tokens) > self.daily_token_limit:
            logger.warning(f"Limite diário de tokens excedido: {self.daily_usage + estimated_tokens}/{self.daily_token_limit}")
            return False
        return True
    
    def _estimate_tokens(self, text: str) -> int:
        """Estima o número de tokens em um texto (aproximação)"""
        # Estimativa: 1 token ≈ 4 caracteres
        return len(text) // 4
    
    async def extract_aum_from_chunks(self, company_name: str, chunks: List[str], source_url: str, source_type: str) -> Dict:
        """Extrai AUM de chunks de texto usando GPT-4o"""
        if not chunks:
            return {
                'aum_value': None,
                'aum_currency': 'BRL',
                'aum_unit': None,
                'aum_text': None,
                'confidence_score': 0.0,
                'tokens_used': 0,
                'error': 'Nenhum chunk disponível para análise'
            }
        
        # Filtra chunks que não excedem o limite de tokens
        valid_chunks = []
        total_estimated_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = self._estimate_tokens(chunk)
            if chunk_tokens <= 1500:  # Limite por chunk
                valid_chunks.append(chunk)
                total_estimated_tokens += chunk_tokens
        
        if not valid_chunks:
            return {
                'aum_value': None,
                'aum_currency': 'BRL',
                'aum_unit': None,
                'aum_text': None,
                'confidence_score': 0.0,
                'tokens_used': 0,
                'error': 'Todos os chunks excedem o limite de tokens'
            }
        
        # Verifica limite de budget
        if not self._check_budget_limit(total_estimated_tokens):
            return {
                'aum_value': None,
                'aum_currency': 'BRL',
                'aum_unit': None,
                'aum_text': None,
                'confidence_score': 0.0,
                'tokens_used': 0,
                'error': 'Limite diário de tokens excedido'
            }
        
        # Processa cada chunk
        best_result = None
        total_tokens_used = 0
        
        for chunk in valid_chunks:
            try:
                result = await self._extract_aum_single_chunk(company_name, chunk)
                total_tokens_used += result.get('tokens_used', 0)
                
                # Atualiza o melhor resultado baseado no score de confiança
                if result.get('confidence_score', 0) > (best_result.get('confidence_score', 0) if best_result else 0):
                    best_result = result
                
                # Se encontrou um resultado com alta confiança, para aqui
                if result.get('confidence_score', 0) >= 0.8:
                    break
                    
            except Exception as e:
                logger.error(f"Erro ao processar chunk: {e}")
                continue
        
        # Atualiza uso diário
        self.daily_usage += total_tokens_used
        self.daily_calls += 1
        
        if best_result:
            best_result['tokens_used'] = total_tokens_used
            return best_result
        else:
            return {
                'aum_value': None,
                'aum_currency': 'BRL',
                'aum_unit': None,
                'aum_text': None,
                'confidence_score': 0.0,
                'tokens_used': total_tokens_used,
                'error': 'Não foi possível extrair AUM de nenhum chunk'
            }
    
    async def _extract_aum_single_chunk(self, company_name: str, chunk: str) -> Dict:
        """Extrai AUM de um único chunk usando GPT-4o"""
        try:
            # Prompt otimizado para extração de AUM
            prompt = f"""
            Analise o seguinte texto sobre a empresa {company_name} e extraia o patrimônio sob gestão (AUM):

            TEXTO:
            {chunk}

            INSTRUÇÕES:
            1. Procure por informações sobre patrimônio sob gestão, AUM, ou valores de fundos
            2. Responda APENAS com o número e unidade (ex: R$ 2,3 bi, US$ 500 mi, € 1,2 bi)
            3. Se não encontrar AUM, responda "NAO_DISPONIVEL"
            4. Se encontrar múltiplos valores, use o mais recente ou relevante
            5. Mantenha a moeda original (R$, US$, €)
            6. Use abreviações padrão: bi (bilhões), mi (milhões), mil (milhares)

            RESPOSTA (apenas o valor ou NAO_DISPONIVEL):
            """
            
            # Chama a API OpenAI (nova sintaxe)
            response = await openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em extrair informações financeiras de textos corporativos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            # Extrai a resposta (nova sintaxe)
            ai_response = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens
            
            # Processa a resposta da IA
            aum_data = self._parse_ai_response(ai_response)
            
            return {
                'aum_value': aum_data['value'],
                'aum_currency': aum_data['currency'],
                'aum_unit': aum_data['unit'],
                'aum_text': ai_response,
                'confidence_score': aum_data['confidence'],
                'tokens_used': tokens_used,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Erro na API OpenAI: {e}")
            return {
                'aum_value': None,
                'aum_currency': 'BRL',
                'aum_unit': None,
                'aum_text': None,
                'confidence_score': 0.0,
                'tokens_used': 0,
                'error': str(e)
            }
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Processa a resposta da IA para extrair valor, moeda e unidade"""
        if not ai_response or ai_response.lower() == "nao_disponivel":
            return {
                'value': None,
                'currency': 'BRL',
                'unit': None,
                'confidence': 0.0
            }
        
        try:
            # Regex para capturar valores monetários
            # Padrões: R$ 2,3 bi, US$ 500 mi, € 1,2 bi, 2.5 bilhões, etc.
            patterns = [
                r'([R$]|[U][S][$]|[€])\s*([\d,\.]+)\s*(bi|mi|mil|bilh[õo]es?|milh[õo]es?|milhares?)',
                r'([\d,\.]+)\s*(bi|mi|mil|bilh[õo]es?|milh[õo]es?|milhares?)\s*([R$]|[U][S][$]|[€])',
                r'([R$]|[U][S][$]|[€])\s*([\d,\.]+)',
                r'([\d,\.]+)\s*([R$]|[U][S][$]|[€])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, ai_response, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    # Determina moeda, valor e unidade
                    if len(groups) == 3:
                        currency = groups[0] if groups[0] in ['R$', 'US$', '€'] else groups[2]
                        value_str = groups[1] if groups[0] in ['R$', 'US$', '€'] else groups[0]
                        unit = groups[2] if groups[0] in ['R$', 'US$', '€'] else groups[1]
                    elif len(groups) == 2:
                        if groups[0] in ['R$', 'US$', '€']:
                            currency = groups[0]
                            value_str = groups[1]
                            unit = None
                        else:
                            currency = groups[1]
                            value_str = groups[0]
                            unit = None
                    else:
                        continue
                    
                    # Converte valor para float
                    value = float(value_str.replace(',', '.'))
                    
                    # Normaliza unidade
                    unit = self._normalize_unit(unit)
                    
                    # Calcula score de confiança
                    confidence = self._calculate_confidence(ai_response, value, unit)
                    
                    return {
                        'value': value,
                        'currency': currency,
                        'unit': unit,
                        'confidence': confidence
                    }
            
            # Se não encontrou padrão específico, tenta extrair apenas números
            numbers = re.findall(r'[\d,\.]+', ai_response)
            if numbers:
                value = float(numbers[0].replace(',', '.'))
                return {
                    'value': value,
                    'currency': 'BRL',  # Default
                    'unit': None,
                    'confidence': 0.3  # Baixa confiança
                }
            
            return {
                'value': None,
                'currency': 'BRL',
                'unit': None,
                'confidence': 0.0
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar resposta da IA: {e}")
            return {
                'value': None,
                'currency': 'BRL',
                'unit': None,
                'confidence': 0.0
            }
    
    def _normalize_unit(self, unit: str) -> str:
        """Normaliza unidades para formato padrão"""
        if not unit:
            return None
        
        unit_lower = unit.lower()
        
        # Mapeia variações para unidades padrão
        unit_mapping = {
            'bi': 'bi',
            'bilhão': 'bi',
            'bilhões': 'bi',
            'bilh': 'bi',
            'mi': 'mi',
            'milhão': 'mi',
            'milhões': 'mi',
            'milh': 'mi',
            'mil': 'mil',
            'milhares': 'mil'
        }
        
        for pattern, normalized in unit_mapping.items():
            if pattern in unit_lower:
                return normalized
        
        return unit
    
    def _calculate_confidence(self, text: str, value: float, unit: str) -> float:
        """Calcula score de confiança baseado em indicadores no texto"""
        confidence = 0.5  # Base
        
        # Indicadores de alta confiança
        high_confidence_indicators = [
            'patrimônio sob gestão', 'aum', 'assets under management',
            'patrimônio', 'gestão', 'fundo', 'investimento'
        ]
        
        # Indicadores de baixa confiança
        low_confidence_indicators = [
            'estimativa', 'projeção', 'meta', 'objetivo', 'esperado'
        ]
        
        text_lower = text.lower()
        
        # Ajusta confiança baseado nos indicadores
        for indicator in high_confidence_indicators:
            if indicator in text_lower:
                confidence += 0.2
        
        for indicator in low_confidence_indicators:
            if indicator in text_lower:
                confidence -= 0.1
        
        # Ajusta baseado na presença de moeda e unidade
        if unit:
            confidence += 0.1
        
        # Limita entre 0 e 1
        return max(0.0, min(1.0, confidence))
    
    def get_daily_usage_stats(self) -> Dict:
        """Retorna estatísticas de uso diário"""
        self._reset_daily_usage()
        
        return {
            'tokens_used': self.daily_usage,
            'tokens_limit': self.daily_token_limit,
            'usage_percentage': (self.daily_usage / self.daily_token_limit) * 100,
            'api_calls': self.daily_calls,
            'date': self.last_reset_date.isoformat()
        }
    
    def is_budget_exceeded(self) -> bool:
        """Verifica se o budget diário foi excedido"""
        self._reset_daily_usage()
        return self.daily_usage >= self.daily_token_limit
