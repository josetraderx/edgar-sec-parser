"""
Dead Letter Queue Manager usando SQLAlchemy ORM
Maneja reintentos inteligentes de filings fallidos con backoff exponencial
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
import logging
import psutil
import json

from .models import DeadLetterQueue as DLQModel, Filing, ProcessingResult
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class DeadLetterQueueManager:
    """
    Manager para Dead Letter Queue usando ORM
    Mantiene compatibilidad con interfaz existente pero usa SQLAlchemy internamente
    """
    
    def __init__(self, database_url: str):
        self.db = DatabaseManager(database_url)
        logger.info("DeadLetterQueueManager initialized with ORM")
    
    def add_filing(self, filing_id: int, error: str, file_size_mb: float, 
                   failure_type: str = 'timeout', original_tier: str = None,
                   error_details: str = None) -> bool:
        """
        Añade filing fallido a DLQ con lógica inteligente de retry
        
        Args:
            filing_id: ID del filing fallido
            error: Mensaje de error
            file_size_mb: Tamaño del archivo
            failure_type: Tipo de fallo (timeout, memory, network, parsing)
            original_tier: Tier que falló originalmente
            error_details: Detalles completos del error (stack trace)
        
        Returns:
            bool: True si se añadió exitosamente
        """
        session = self.db.get_session()
        try:
            # Verificar si ya existe en DLQ
            existing = session.query(DLQModel).filter_by(filing_id=filing_id).first()
            
            if existing:
                # Actualizar entrada existente
                existing.attempt_count += 1
                existing.last_attempt = datetime.utcnow()
                existing.failure_reason = error
                existing.failure_type = failure_type
                existing.file_size_mb = file_size_mb
                
                # Actualizar eligibilidad para retry
                existing.retry_eligible = self._calculate_retry_eligibility(
                    existing.attempt_count, file_size_mb, failure_type
                )
                
                # Calcular próximo retry con backoff exponencial
                if existing.retry_eligible:
                    backoff_hours = self._calculate_backoff_hours(existing.attempt_count)
                    existing.next_retry = datetime.utcnow() + timedelta(hours=backoff_hours)
                    existing.retry_after_hours = backoff_hours
                    existing.suggested_tier = self._suggest_tier(existing.attempt_count, file_size_mb, failure_type)
                else:
                    existing.next_retry = None
                    existing.suggested_tier = None
                
                # Actualizar detalles del error
                if error_details:
                    existing.original_error_details = error_details
                
                # Capturar métricas del sistema
                existing.system_metrics = self._capture_system_metrics()
                existing.updated_at = datetime.utcnow()
                
                logger.info(f"Updated DLQ entry for filing {filing_id} - attempt {existing.attempt_count}")
                
            else:
                # Crear nueva entrada en DLQ
                retry_eligible = self._calculate_retry_eligibility(1, file_size_mb, failure_type)
                
                dlq_entry = DLQModel(
                    filing_id=filing_id,
                    failure_reason=error,
                    failure_type=failure_type,
                    original_tier=original_tier,
                    file_size_mb=file_size_mb,
                    attempt_count=1,
                    retry_eligible=retry_eligible,
                    next_retry=datetime.utcnow() + timedelta(hours=24) if retry_eligible else None,
                    retry_after_hours=24 if retry_eligible else 0,
                    suggested_tier=self._suggest_tier(1, file_size_mb, failure_type) if retry_eligible else None,
                    priority=self._calculate_priority(file_size_mb, failure_type),
                    original_error_details=error_details,
                    system_metrics=self._capture_system_metrics()
                )
                session.add(dlq_entry)
                
                logger.info(f"Added new filing {filing_id} to DLQ: {error}")
            
            # Actualizar status del filing
            filing = session.query(Filing).filter_by(id=filing_id).first()
            if filing:
                filing.processing_status = 'dead_letter'
                filing.updated_at = datetime.utcnow()
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding filing {filing_id} to DLQ: {e}")
            return False
        finally:
            session.close()
    
    def get_night_batch(self, batch_size: int = 50, max_file_size_mb: float = 50.0) -> List[Dict[str, Any]]:
        """
        Obtiene batch para procesamiento nocturno con priorización inteligente
        
        Args:
            batch_size: Número máximo de filings a procesar
            max_file_size_mb: Tamaño máximo de archivo a incluir
        
        Returns:
            List[Dict]: Lista de filings listos para retry
        """
        try:
            with self.db.get_session() as session:
                current_time = datetime.utcnow()
                
                # Query optimizada con joins para obtener toda la info necesaria
                dlq_entries = session.query(DLQModel, Filing).join(Filing).filter(
                    and_(
                        DLQModel.retry_eligible == True,
                        DLQModel.next_retry <= current_time,
                        DLQModel.attempt_count < DLQModel.max_attempts,
                        DLQModel.file_size_mb <= max_file_size_mb
                    )
                ).order_by(
                    DLQModel.priority.desc(),  # Prioridad alta primero
                    DLQModel.file_size_mb.asc(),  # Archivos pequeños primero
                    DLQModel.attempt_count.asc(),  # Menos intentos primero
                    DLQModel.created_at.asc()  # Más antiguos primero
                ).limit(batch_size).all()
                
                result = []
                for dlq_entry, filing in dlq_entries:
                    result.append({
                        'filing_id': filing.id,
                        'accession_number': filing.accession_number,
                        'cik': filing.cik,
                        'company_name': filing.company_name,
                        'file_size_mb': dlq_entry.file_size_mb,
                        'attempt_count': dlq_entry.attempt_count,
                        'suggested_tier': dlq_entry.suggested_tier or 'limited',
                        'failure_type': dlq_entry.failure_type,
                        'original_tier': dlq_entry.original_tier,
                        'filing_html_url': filing.filing_html_url,
                        'priority': dlq_entry.priority,
                        'last_failure_reason': dlq_entry.failure_reason
                    })
                
                logger.info(f"Retrieved {len(result)} filings for night batch processing")
                return result
                
        except Exception as e:
            logger.error(f"Error getting night batch: {e}")
            return []
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del DLQ para monitoreo"""
        try:
            with self.db.get_session() as session:
                # Contadores básicos
                total_entries = session.query(func.count(DLQModel.id)).scalar()
                eligible_for_retry = session.query(func.count(DLQModel.id)).filter(
                    DLQModel.retry_eligible == True
                ).scalar()
                ready_for_retry = session.query(func.count(DLQModel.id)).filter(
                    and_(
                        DLQModel.retry_eligible == True,
                        DLQModel.next_retry <= datetime.utcnow()
                    )
                ).scalar()
                
                # Estadísticas por tipo de fallo
                failure_stats = session.query(
                    DLQModel.failure_type,
                    func.count(DLQModel.id).label('count'),
                    func.avg(DLQModel.attempt_count).label('avg_attempts')
                ).group_by(DLQModel.failure_type).all()
                
                # Estadísticas por tamaño de archivo
                size_stats = session.query(
                    func.count(DLQModel.id).label('count'),
                    func.avg(DLQModel.file_size_mb).label('avg_size'),
                    func.max(DLQModel.file_size_mb).label('max_size')
                ).filter(DLQModel.retry_eligible == True).first()
                
                return {
                    'total_entries': total_entries or 0,
                    'eligible_for_retry': eligible_for_retry or 0,
                    'ready_for_retry': ready_for_retry or 0,
                    'failure_breakdown': {
                        result.failure_type: {
                            'count': result.count,
                            'avg_attempts': float(result.avg_attempts or 0)
                        }
                        for result in failure_stats
                    },
                    'file_size_stats': {
                        'avg_size_mb': float(size_stats.avg_size or 0),
                        'max_size_mb': float(size_stats.max_size or 0),
                        'eligible_count': size_stats.count or 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting retry statistics: {e}")
            return {}
    
    def mark_as_processed(self, filing_id: int, success: bool) -> bool:
        """
        Marca un filing como procesado después de un retry
        
        Args:
            filing_id: ID del filing procesado
            success: Si el procesamiento fue exitoso
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            with self.db.get_session() as session:
                dlq_entry = session.query(DLQModel).filter_by(filing_id=filing_id).first()
                
                if dlq_entry:
                    if success:
                        # Remover de DLQ si fue exitoso
                        session.delete(dlq_entry)
                        logger.info(f"Removed filing {filing_id} from DLQ after successful retry")
                    else:
                        # Actualizar para próximo intento
                        dlq_entry.attempt_count += 1
                        dlq_entry.last_attempt = datetime.utcnow()
                        dlq_entry.retry_eligible = self._calculate_retry_eligibility(
                            dlq_entry.attempt_count, dlq_entry.file_size_mb, dlq_entry.failure_type
                        )
                        
                        if dlq_entry.retry_eligible:
                            backoff_hours = self._calculate_backoff_hours(dlq_entry.attempt_count)
                            dlq_entry.next_retry = datetime.utcnow() + timedelta(hours=backoff_hours)
                        else:
                            dlq_entry.next_retry = None
                        
                        dlq_entry.updated_at = datetime.utcnow()
                        logger.info(f"Updated DLQ entry for filing {filing_id} after failed retry")
                
                return True
                
        except Exception as e:
            logger.error(f"Error marking filing {filing_id} as processed: {e}")
            return False
    
    def cleanup_old_entries(self, days_to_keep: int = 30) -> int:
        """
        Limpia entradas antiguas no elegibles para retry
        
        Args:
            days_to_keep: Días a mantener entradas no elegibles
        
        Returns:
            int: Número de entradas eliminadas
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            with self.db.get_session() as session:
                old_entries = session.query(DLQModel).filter(
                    and_(
                        DLQModel.retry_eligible == False,
                        DLQModel.created_at < cutoff_date
                    )
                ).all()
                
                count = len(old_entries)
                
                for entry in old_entries:
                    session.delete(entry)
                
                logger.info(f"Cleaned up {count} old DLQ entries")
                return count
                
        except Exception as e:
            logger.error(f"Error cleaning up old DLQ entries: {e}")
            return 0
    
    # === MÉTODOS PRIVADOS DE LÓGICA ===
    
    def _calculate_retry_eligibility(self, attempt_count: int, file_size_mb: float, failure_type: str) -> bool:
        """Calcula si un filing es elegible para retry"""
        # Límites por número de intentos
        if attempt_count >= 5:
            return False
        
        # Límites por tamaño de archivo
        if file_size_mb > 100:  # Archivos muy grandes nunca se reintentan
            return False
        elif file_size_mb > 50 and attempt_count >= 2:  # Archivos grandes máximo 2 intentos
            return False
        
        # Límites por tipo de fallo
        if failure_type == 'memory' and file_size_mb > 25:
            return False
        elif failure_type == 'parsing' and attempt_count >= 3:
            return False
        
        return True
    
    def _calculate_backoff_hours(self, attempt_count: int) -> int:
        """Calcula horas de backoff exponencial"""
        # Backoff exponencial: 24h, 48h, 96h, 192h (8 días max)
        backoff_hours = min(24 * (2 ** (attempt_count - 1)), 192)
        return backoff_hours
    
    def _suggest_tier(self, attempt_count: int, file_size_mb: float, failure_type: str) -> str:
        """Sugiere tier más conservador para retry"""
        if failure_type == 'memory' or file_size_mb > 30:
            return 'minimal'
        elif attempt_count >= 2 or file_size_mb > 15:
            return 'limited'
        else:
            return 'standard'
    
    def _calculate_priority(self, file_size_mb: float, failure_type: str) -> int:
        """Calcula prioridad del filing (1=low, 5=high)"""
        priority = 1  # Base priority
        
        # Archivos pequeños tienen mayor prioridad
        if file_size_mb < 5:
            priority += 2
        elif file_size_mb < 15:
            priority += 1
        
        # Ciertos tipos de fallo tienen mayor prioridad
        if failure_type in ['network', 'temporary']:
            priority += 1
        elif failure_type in ['memory', 'timeout']:
            priority -= 1
        
        return max(1, min(5, priority))
    
    def _capture_system_metrics(self) -> Dict[str, Any]:
        """Captura métricas del sistema en el momento del fallo"""
        try:
            return {
                'memory_usage_mb': psutil.virtual_memory().used / 1024 / 1024,
                'memory_percent': psutil.virtual_memory().percent,
                'cpu_percent': psutil.cpu_percent(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except:
            return {}

    # === MÉTODOS DE COMPATIBILIDAD CON INTERFAZ EXISTENTE ===
    
    def should_retry_tonight(self, filing_meta: Dict[str, Any]) -> bool:
        """Método de compatibilidad - verifica si filing debe reintentarse"""
        try:
            with self.db.get_session() as session:
                dlq_entry = session.query(DLQModel).filter_by(
                    filing_id=filing_meta.get('filing_id')
                ).first()
                
                if not dlq_entry:
                    return False
                
                return (
                    dlq_entry.retry_eligible and 
                    dlq_entry.next_retry and 
                    dlq_entry.next_retry <= datetime.utcnow()
                )
        except:
            return False
    
    def get_failure_stats(self) -> Dict[str, int]:
        """Método de compatibilidad - obtiene estadísticas básicas"""
        stats = self.get_retry_statistics()
        return {
            'total_failed': stats.get('total_entries', 0),
            'eligible_retry': stats.get('eligible_for_retry', 0),
            'ready_retry': stats.get('ready_for_retry', 0)
        }
    
    def mark_retry_attempt(self, filing_id: int, success: bool) -> bool:
        """
        Marca un intento de retry como completado (método de compatibilidad)
        
        Args:
            filing_id: ID del filing
            success: Si el retry fue exitoso
        
        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            with self.db.get_session() as session:
                dlq_entry = session.query(DLQModel).filter_by(filing_id=filing_id).first()
                
                if dlq_entry:
                    if success:
                        # Remover de DLQ si fue exitoso
                        session.delete(dlq_entry)
                        logger.info(f"Removed filing {filing_id} from DLQ after successful retry")
                    else:
                        # Actualizar para próximo intento
                        dlq_entry.attempt_count += 1
                        dlq_entry.last_attempt = datetime.utcnow()
                        dlq_entry.retry_eligible = self._calculate_retry_eligibility(
                            dlq_entry.attempt_count, dlq_entry.file_size_mb, dlq_entry.failure_type
                        )
                        
                        if dlq_entry.retry_eligible:
                            backoff_hours = self._calculate_backoff_hours(dlq_entry.attempt_count)
                            dlq_entry.next_retry = datetime.utcnow() + timedelta(hours=backoff_hours)
                        else:
                            dlq_entry.next_retry = None
                        
                        dlq_entry.updated_at = datetime.utcnow()
                        logger.info(f"Updated DLQ entry for filing {filing_id} after failed retry")
                
                return True
                
        except Exception as e:
            logger.error(f"Error marking retry attempt for filing {filing_id}: {e}")
            return False