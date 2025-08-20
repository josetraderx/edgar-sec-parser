"""
TieredProcessor actualizado para usar SQLAlchemy ORM y el nuevo sistema de parsers
Mantiene la lógica tiered pero usa el nuevo DatabaseManager y parsers integrados
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..storage.database import DatabaseManager
from ..storage.dead_letter_queue import DeadLetterQueueManager
from ..config.settings import settings
from .timeout_manager import TimeoutManager, TimeoutError
from .metrics import MetricsLogger
from .http_client import http_client
from .parser_integration import ParserManager, DatabaseResultManager
from ..extractors import parsers
from ..storage import models

# Si más adelante agregas extractores reales, importa y reemplaza _mock_extractor:
# from ..extractors.standard_extractor import StandardExtractor
# from ..extractors.limited_extractor import LimitedExtractor
# from ..extractors.minimal_extractor import MinimalExtractor

logger = logging.getLogger(__name__)


class TieredProcessor:
    """
    Procesador principal con sistema tiered usando SQLAlchemy ORM y parsers integrados.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Inicializa el procesador con backend ORM y sistema de parsers.

        Args:
            database_url: URL de base de datos (opcional; usa settings si no se proporciona).
        """
        self.database_url = database_url or settings.database_url

        # ORM managers
        self.db = DatabaseManager(self.database_url)
        self.dlq = DeadLetterQueueManager(self.database_url)

        # Infra
        self.timeout_manager = TimeoutManager(settings)
        self.metrics = MetricsLogger()

        # Nuevo sistema de parsers
        self.parser_manager = ParserManager()
        self.db_result_manager = DatabaseResultManager(self.db)

        # Extractores legacy (mock por ahora)
        self.extractors = {
            "standard": self._mock_extractor,
            "limited": self._mock_extractor,
            "minimal": self._mock_extractor,
        }

        logger.info(
            f"TieredProcessor initialized with ORM backend. "
            f"Parser integration available: {self.parser_manager.is_available()}"
        )

    # === API PRINCIPAL ===

    def process_filing(self, filing_meta: Dict[str, Any], html_content: str) -> Dict[str, Any]:
        """
        Procesa un filing usando el sistema tiered con persistencia ORM.

        Args:
            filing_meta: Metadatos del filing
            html_content: Contenido HTML del filing

        Returns:
            Dict: Resultado del procesamiento
        """
        start_time = time.time()
        filing_id: Optional[int] = None
        tier: Optional[str] = None  # evitar UnboundLocalError en except

        try:
            # Crear/actualizar filing (upsert)
            filing_id = self.db.create_or_update_filing(filing_meta)
            logger.info(f"Processing filing {filing_id}: {filing_meta.get('accession_number')}")

            # Determinar tier según tamaño
            file_size_mb = float(filing_meta.get("file_size_mb", 0.0))
            tier = self._determine_processing_tier(file_size_mb)

            # Marcar "processing"
            self.db.update_filing_processing_status(filing_id, tier, "processing")

            # Dead letter inmediato por tamaño
            if tier == "dead_letter":
                return self._handle_dead_letter_filing(filing_id, filing_meta, file_size_mb)

            # Ejecutar extractor con timeout por tier
            processing_result = self._process_with_tier(tier, html_content, filing_meta)

            # Métricas/resultado final
            total_duration = time.time() - start_time
            processing_result["processing_duration"] = total_duration
            processing_result["filing_id"] = filing_id
            processing_result["processing_tier"] = tier

            # Persistir resultado
            saved = self.db.save_processing_result(filing_id, processing_result, tier)
            
            # Si tenemos parser results disponibles, guardar también con el nuevo sistema
            if (self.parser_manager.is_available() and 
                processing_result.get("parser_timing") and 
                hasattr(processing_result, 'parser_raw_data')):
                
                # Intentar guardar resultados del parser también
                try:
                    # Convertir resultado a formato de parser si es necesario
                    self._save_enhanced_parser_results(filing_id, processing_result, tier)
                except Exception as e:
                    logger.warning(f"Failed to save enhanced parser results: {e}")
            
            if saved:
                self.metrics.daily_metrics.record_success(tier, total_duration, file_size_mb)
                logger.info(
                    f"Successfully processed filing {filing_id} with tier {tier} in {total_duration:.2f}s"
                )
            else:
                logger.error(f"Failed to save processing result for filing {filing_id}")

            return processing_result

        except TimeoutError as e:
            return self._handle_timeout_error(
                filing_id, filing_meta, tier or "unknown", str(e), time.time() - start_time
            )
        except MemoryError as e:
            return self._handle_memory_error(
                filing_id, filing_meta, tier or "unknown", str(e), time.time() - start_time
            )
        except Exception as e:
            return self._handle_general_error(
                filing_id, filing_meta, tier or "unknown", str(e), time.time() - start_time
            )

    def process_batch(self, batch_filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa un lote de filings.

        Args:
            batch_filings: Lista de metadatos de filings

        Returns:
            List[Dict]: Resultados del procesamiento
        """
        results: List[Dict[str, Any]] = []
        batch_start_time = time.time()
        logger.info(f"Starting batch processing of {len(batch_filings)} filings")

        for i, filing_meta in enumerate(batch_filings, 1):
            try:
                html_content = self._download_filing_content(filing_meta)

                if html_content:
                    result = self.process_filing(filing_meta, html_content)
                    results.append(result)
                else:
                    # Manejar fallo de descarga
                    filing_id = self.db.create_or_update_filing(filing_meta)
                    self.dlq.add_filing(
                        filing_id,
                        "Failed to download content",
                        float(filing_meta.get("file_size_mb", 0.0)),
                        "network",
                    )
                    results.append({"success": False, "error": "Download failed", "filing_id": filing_id})

                # Progreso cada 10
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(batch_filings)} filings in batch")

            except Exception as e:
                logger.error(f"Error processing filing in batch: {e}")
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "accession_number": filing_meta.get("accession_number", "unknown"),
                    }
                )

        batch_duration = time.time() - batch_start_time
        successful = sum(1 for r in results if r.get("success", False))
        logger.info(
            f"Batch processing completed: {successful}/{len(batch_filings)} successful in {batch_duration:.2f}s"
        )
        return results

    def process_night_batch(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Reprocesa lote nocturno desde DLQ.

        Args:
            batch_size: Tamaño del lote a procesar

        Returns:
            Dict: Resumen del procesamiento nocturno
        """
        logger.info(f"Starting night batch processing (max {batch_size} filings)")

        night_batch = self.dlq.get_night_batch(batch_size)
        if not night_batch:
            logger.info("No filings available for night batch processing")
            return {"processed": 0, "successful": 0, "failed": 0, "duration": 0.0}

        start_time = time.time()
        successful = 0
        failed = 0

        for filing_data in night_batch:
            try:
                html_content = self._download_filing_content(filing_data)
                if html_content:
                    suggested_tier = filing_data.get("suggested_tier", "limited")
                    result = self._process_with_tier(suggested_tier, html_content, filing_data)

                    if result.get("success", False):
                        self.db.save_processing_result(filing_data["filing_id"], result, suggested_tier)
                        self.dlq.mark_as_processed(filing_data["filing_id"], True)
                        successful += 1
                        logger.info(
                            f"Night batch: Successfully reprocessed filing {filing_data['filing_id']}"
                        )
                    else:
                        self.dlq.mark_as_processed(filing_data["filing_id"], False)
                        failed += 1
                        logger.warning(
                            f"Night batch: Failed to reprocess filing {filing_data['filing_id']}"
                        )
                else:
                    self.dlq.mark_as_processed(filing_data["filing_id"], False)
                    failed += 1

            except Exception as e:
                logger.error(
                    f"Error in night batch processing filing {filing_data.get('filing_id')}: {e}"
                )
                self.dlq.mark_as_processed(filing_data.get("filing_id"), False)
                failed += 1

        duration = time.time() - start_time
        summary = {
            "processed": len(night_batch),
            "successful": successful,
            "failed": failed,
            "duration": duration,
            "success_rate": (successful / len(night_batch)) * 100 if night_batch else 0.0,
        }
        logger.info(f"Night batch completed: {summary}")
        return summary

    # === PRIVADOS ===

    def _mock_extractor(self, html_content: str, filing_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Mock extractor temporal para testing."""
        return {
            "success": True,
            "tables": [
                {
                    "section": "mock_section",
                    "data": [["Header1", "Header2"], ["Data1", "Data2"]],
                    "row_count": 2,
                    "column_count": 2,
                    "type": "mock_table",
                    "extraction_method": "mock",
                }
            ],
            "sections": ["mock_section"],
            "extraction_method": "mock",
            "table_count": 1,
            "processing_duration": 0.1,
        }

    def _determine_processing_tier(self, file_size_mb: float) -> str:
        """Determina tier basado en tamaño de archivo."""
        if file_size_mb > settings.LARGE_FILE_THRESHOLD:
            return "dead_letter"
        if file_size_mb > settings.MEDIUM_FILE_THRESHOLD:
            return "minimal"
        if file_size_mb > settings.SMALL_FILE_THRESHOLD:
            return "limited"
        return "standard"

    def _process_with_tier(self, tier: str, html_content: str, filing_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa con el tier especificado bajo timeout."""
        if tier not in self.extractors:
            raise ValueError(f"Unknown processing tier: {tier}")

        extractor = self.extractors[tier]
        timeout = settings.get_timeout_for_tier(tier)

        with self.timeout_manager.timeout_context(timeout):
            # Aquí se integra el parser híbrido
            return self._hybrid_extraction_logic(html_content, filing_meta, tier)

    def _handle_dead_letter_filing(self, filing_id: int, filing_meta: Dict[str, Any], file_size_mb: float) -> Dict[str, Any]:
        """Maneja filing que va directo a dead letter queue."""
        error_msg = f"File too large for processing: {file_size_mb}MB > {settings.LARGE_FILE_THRESHOLD}MB"
        self.dlq.add_filing(filing_id, error_msg, file_size_mb, "file_too_large")
        return {"success": False, "error": error_msg, "processing_tier": "dead_letter", "filing_id": filing_id}

    def _handle_timeout_error(self, filing_id: Optional[int], filing_meta: Dict[str, Any], tier: str, error: str, duration: float) -> Dict[str, Any]:
        """Maneja errores de timeout."""
        file_size_mb = float(filing_meta.get("file_size_mb", 0.0))
        self.dlq.add_filing(filing_id, f"Timeout in {tier} tier: {error}", file_size_mb, "timeout", tier)
        if hasattr(self.metrics, "record_timeout"):
            # opcional si implementas este método
            self.metrics.record_timeout(tier, duration)  # type: ignore
        return {
            "success": False,
            "error": error,
            "error_type": "timeout",
            "processing_tier": tier,
            "processing_duration": duration,
            "filing_id": filing_id,
        }

    def _handle_memory_error(self, filing_id: Optional[int], filing_meta: Dict[str, Any], tier: str, error: str, duration: float) -> Dict[str, Any]:
        """Maneja errores de memoria."""
        file_size_mb = float(filing_meta.get("file_size_mb", 0.0))
        self.dlq.add_filing(filing_id, f"Memory error in {tier} tier: {error}", file_size_mb, "memory", tier)
        return {
            "success": False,
            "error": error,
            "error_type": "memory",
            "processing_tier": tier,
            "processing_duration": duration,
            "filing_id": filing_id,
        }

    def _handle_general_error(self, filing_id: Optional[int], filing_meta: Dict[str, Any], tier: str, error: str, duration: float) -> Dict[str, Any]:
        """Maneja errores generales."""
        file_size_mb = float(filing_meta.get("file_size_mb", 0.0))
        self.dlq.add_filing(filing_id, f"Processing error in {tier} tier: {error}", file_size_mb, "processing", tier)
        return {
            "success": False,
            "error": error,
            "error_type": "processing",
            "processing_tier": tier,
            "processing_duration": duration,
            "filing_id": filing_id,
        }

    def _download_filing_content(self, filing_meta: Dict[str, Any]) -> Optional[str]:
        """Descarga contenido del filing usando el cliente HTTP robusto."""
        filing_url = filing_meta.get("filing_html_url")
        if not filing_url:
            logger.warning("No filing_html_url provided in filing_meta.")
            return None
        
        return http_client.get_text(filing_url)

    def _hybrid_extraction_logic(self, html_content: str, filing_meta: Dict[str, Any], tier: str) -> Dict[str, Any]:
        """
        Lógica de extracción híbrida que utiliza el nuevo sistema de parsers integrados.
        """
        start_time = time.time()
        
        # Usar el nuevo sistema de parsers si está disponible
        if self.parser_manager.is_available():
            logger.info(f"Using integrated parser system for tier: {tier}")
            
            # Procesar con el sistema de parsers integrados
            parsing_result = self.parser_manager.parse_filing_content(
                html_content, filing_meta, tier
            )
            
            # El ParserManager ya devuelve el formato legacy compatible
            return parsing_result
        
        else:
            # Fallback al sistema legacy si los parsers no están disponibles
            logger.warning("Parser system not available, using legacy extraction")
            return self._legacy_extraction_logic(html_content, filing_meta, tier)
    
    def _legacy_extraction_logic(self, html_content: str, filing_meta: Dict[str, Any], tier: str) -> Dict[str, Any]:
        """
        Lógica de extracción legacy (sistema original).
        """
        from bs4 import BeautifulSoup

        start_time = time.time()
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Extraer metadatos y secciones
        fund_meta = parsers.extract_fund_metadata(soup)
        sections = parsers.extract_sections(html_content)
        
        # 2. Extraer tablas (la operación más costosa)
        # La profundidad de la extracción de tablas puede depender del tier
        if tier == "standard":
            tables = parsers.extract_tables(html_content)
        elif tier == "limited":
            # Versión limitada: solo las primeras N tablas
            tables = parsers.extract_tables(html_content)[:10]
        else: # minimal
            tables = []

        # 3. (Opcional) Extraer datos XBRL si existen
        # Esto requeriría descargar y pasar el contenido del XML
        xbrl_metrics = {}
        # xbrl_url = ... (lógica para encontrar la URL del XBRL)
        # if xbrl_url:
        #     xml_content = http_client.get_text(xbrl_url)
        #     if xml_content:
        #         xbrl_metrics = parsers.extract_xbrl_metrics(xml_content)

        duration = time.time() - start_time
        
        # Construir el resultado para guardar en la base de datos
        # Nota: Esto no guarda directamente, solo prepara los datos.
        # El guardado se hará en el `DatabaseManager`.
        return {
            "success": True,
            "fund_metadata": fund_meta,
            "sections": sections,
            "tables": tables,
            "xbrl_metrics": xbrl_metrics,
            "table_count": len(tables),
            "section_count": len(sections),
            "processing_duration": duration,
            "extraction_method": f"legacy_{tier}"
        }

    def _save_enhanced_parser_results(self, filing_id: int, processing_result: Dict[str, Any], tier: str):
        """
        Guarda resultados mejorados del sistema de parsers.
        
        Args:
            filing_id: ID del filing
            processing_result: Resultado del procesamiento
            tier: Tier de procesamiento
        """
        try:
            # Crear un pseudo ParsingResult desde el processing_result para compatibilidad
            # Esto es útil si el sistema de parsers generó información adicional
            
            if processing_result.get("parser_timing"):
                logger.debug(f"Enhanced parser data available for filing {filing_id}")
                
                # Aquí podríamos extraer y guardar información adicional
                # que el nuevo sistema de parsers proporciona pero que el sistema legacy no maneja
                
                parser_name = processing_result["parser_timing"].get("parser_name", "unknown")
                parsing_time = processing_result["parser_timing"].get("parsing_time", 0.0)
                
                logger.info(
                    f"Filing {filing_id} processed with parser {parser_name} "
                    f"in {parsing_time:.2f}s (tier: {tier})"
                )
                
        except Exception as e:
            logger.warning(f"Error saving enhanced parser results for filing {filing_id}: {e}")

    # === MÉTRICAS/REPORTES ===

    def get_processing_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de procesamiento usando ORM y métricas locales."""
        try:
            today_metrics = self.db.get_daily_metrics()
            dlq_stats = self.dlq.get_retry_statistics()
            parser_status = self.parser_manager.get_parser_status()
            
            return {
                "daily_metrics": today_metrics,
                "dlq_statistics": dlq_stats,
                "system_metrics": self.metrics.daily_metrics.daily_report(),
                "parser_system": parser_status
            }
        except Exception as e:
            logger.error(f"Error getting processing summary: {e}")
            return {}

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Limpia datos antiguos en BD y DLQ."""
        try:
            cleanup_results = self.db.cleanup_old_data(days_to_keep)
            dlq_cleanup = self.dlq.cleanup_old_entries(days_to_keep)
            cleanup_results["dlq_entries"] = dlq_cleanup
            logger.info(f"Data cleanup completed: {cleanup_results}")
            return cleanup_results
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            return {}
