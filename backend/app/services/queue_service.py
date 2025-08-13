import pika
import json
import logging
import asyncio
from typing import Dict, Any, Callable
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class QueueService:
    def __init__(self, rabbitmq_url: str = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self.queues = {
            'scraping': 'scraping_queue',
            'ai_processing': 'ai_processing_queue',
            'export': 'export_queue'
        }
        
    async def connect(self):
        """Conecta ao RabbitMQ"""
        try:
            # Converte para síncrono para compatibilidade com pika
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._connect_sync)
            logger.info("Conectado ao RabbitMQ com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
            raise
    
    def _connect_sync(self):
        """Conecta ao RabbitMQ de forma síncrona"""
        try:
            # Parse da URL do RabbitMQ
            parameters = pika.URLParameters(self.rabbitmq_url)
            
            # Estabelece conexão
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declara as filas
            for queue_name in self.queues.values():
                self.channel.queue_declare(
                    queue=queue_name,
                    durable=True,
                    arguments={
                        'x-message-ttl': 86400000,  # 24 horas em ms
                        'x-max-priority': 10
                    }
                )
            
            # Declara exchange para dead letter
            self.channel.exchange_declare(
                exchange='dead_letter_exchange',
                exchange_type='direct'
            )
            
            # Fila para mensagens mortas
            self.channel.queue_declare(
                queue='dead_letter_queue',
                durable=True
            )
            
            self.channel.queue_bind(
                exchange='dead_letter_exchange',
                queue='dead_letter_queue',
                routing_key='dead_letter'
            )
            
            logger.info("Filas e exchanges declarados com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na conexão síncrona: {e}")
            raise
    
    async def disconnect(self):
        """Desconecta do RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.connection.close
                )
                logger.info("Desconectado do RabbitMQ")
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")
    
    async def publish_message(self, queue_type: str, message: Dict[str, Any], priority: int = 5):
        """Publica uma mensagem na fila especificada"""
        if not self.channel or self.channel.is_closed:
            await self.connect()
        
        try:
            queue_name = self.queues.get(queue_type)
            if not queue_name:
                raise ValueError(f"Tipo de fila inválido: {queue_type}")
            
            # Adiciona timestamp e metadados
            message_with_metadata = {
                'data': message,
                'timestamp': datetime.utcnow().isoformat(),
                'retry_count': 0,
                'max_retries': 3
            }
            
            # Publica mensagem com prioridade
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._publish_sync,
                queue_name,
                message_with_metadata,
                priority
            )
            
            logger.info(f"Mensagem publicada na fila {queue_name}")
            
        except Exception as e:
            logger.error(f"Erro ao publicar mensagem: {e}")
            raise
    
    def _publish_sync(self, queue_name: str, message: Dict, priority: int):
        """Publica mensagem de forma síncrona"""
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistente
                    priority=priority,
                    content_type='application/json'
                )
            )
        except Exception as e:
            logger.error(f"Erro na publicação síncrona: {e}")
            raise
    
    async def consume_messages(self, queue_type: str, callback: Callable, auto_ack: bool = False):
        """Consome mensagens da fila especificada"""
        if not self.channel or self.channel.is_closed:
            await self.connect()
        
        queue_name = self.queues.get(queue_type)
        if not queue_name:
            raise ValueError(f"Tipo de fila inválido: {queue_type}")
        
        try:
            # Configura QoS
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.channel.basic_qos,
                prefetch_count=1
            )
            
            # Configura callback de consumo
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.channel.basic_consume,
                queue_name,
                lambda ch, method, properties, body: self._message_handler(
                    ch, method, properties, body, callback, auto_ack
                ),
                auto_ack=auto_ack
            )
            
            logger.info(f"Iniciando consumo da fila {queue_name}")
            
            # Inicia consumo em loop separado
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.channel.start_consuming
            )
            
        except Exception as e:
            logger.error(f"Erro ao consumir mensagens: {e}")
            raise
    
    def _message_handler(self, ch, method, properties, body, callback, auto_ack):
        """Handler para processar mensagens recebidas"""
        try:
            # Decodifica mensagem
            message = json.loads(body.decode('utf-8'))
            
            # Executa callback em executor separado
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(callback(message))
                if result and not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                elif not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            
            # Rejeita mensagem e envia para dead letter
            if not auto_ack:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    async def publish_scraping_task(self, company_data: Dict[str, Any]):
        """Publica tarefa de scraping para uma empresa"""
        message = {
            'type': 'scraping',
            'company_data': company_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.publish_message('scraping', message, priority=8)
    
    async def publish_ai_processing_task(self, scraping_result: Dict[str, Any]):
        """Publica tarefa de processamento de IA"""
        message = {
            'type': 'ai_processing',
            'scraping_result': scraping_result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.publish_message('ai_processing', message, priority=6)
    
    async def publish_export_task(self, export_data: Dict[str, Any]):
        """Publica tarefa de exportação"""
        message = {
            'type': 'export',
            'export_data': export_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.publish_message('export', message, priority=4)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das filas"""
        if not self.channel or self.channel.is_closed:
            await self.connect()
        
        try:
            stats = {}
            
            for queue_type, queue_name in self.queues.items():
                queue_info = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.channel.queue_declare,
                    queue_name,
                    passive=True
                )
                
                stats[queue_type] = {
                    'queue_name': queue_name,
                    'message_count': queue_info.method.message_count,
                    'consumer_count': queue_info.method.consumer_count
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas das filas: {e}")
            return {}
    
    async def purge_queue(self, queue_type: str):
        """Limpa uma fila específica"""
        if not self.channel or self.channel.is_closed:
            await self.connect()
        
        queue_name = self.queues.get(queue_type)
        if not queue_name:
            raise ValueError(f"Tipo de fila inválido: {queue_type}")
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.channel.queue_purge,
                queue_name
            )
            
            logger.info(f"Fila {queue_name} limpa com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao limpar fila: {e}")
            raise
