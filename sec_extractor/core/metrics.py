import logging
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class ProcessingMetrics:
    """Métricas de procesamiento diario"""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    standard_processed: int = 0
    limited_processed: int = 0
    minimal_processed: int = 0
    dead_lettered: int = 0
    total_processed: int = 0
    total_duration: float = 0.0
    large_files_count: int = 0

    def record_success(self, tier: str, duration: float, file_size_mb: float):
        """Registra un procesamiento exitoso"""
        self.total_processed += 1
        self.total_duration += duration

        if file_size_mb > 50:
            self.large_files_count += 1

        if tier == "standard":
            self.standard_processed += 1
        elif tier == "limited":
            self.limited_processed += 1
        elif tier == "minimal":
            self.minimal_processed += 1

    def record_failure(self):
        """Registra un fallo que va a dead letter queue"""
        self.dead_lettered += 1

    def get_success_rate(self) -> float:
        """Calcula tasa de éxito (%)"""
        total_attempts = self.total_processed + self.dead_lettered
        if total_attempts == 0:
            return 0.0
        return (self.total_processed / total_attempts) * 100

    def get_average_duration(self) -> float:
        """Calcula duración promedio"""
        if self.total_processed == 0:
            return 0.0
        return self.total_duration / self.total_processed

    def daily_report(self) -> Dict[str, Any]:
        """Genera reporte diario"""
        return {
            "date": self.date,
            "success_rate": self.get_success_rate(),
            "total_processed": self.total_processed,
            "standard_rate": self.standard_processed / max(1, self.total_processed) * 100,
            "limited_rate": self.limited_processed / max(1, self.total_processed) * 100,
            "minimal_rate": self.minimal_processed / max(1, self.total_processed) * 100,
            "average_duration": self.get_average_duration(),
            "large_files_today": self.large_files_count,
            "dead_letters": self.dead_lettered,
        }


class MetricsLogger:
    """Logger para métricas y eventos"""

    def __init__(self):
        self.setup_logging()
        self.daily_metrics = ProcessingMetrics()

    def setup_logging(self):
        """Configura logging"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("sec_extractor.log"),
                logging.StreamHandler()
            ],
        )
        self.logger = logging.getLogger("sec_extractor")

    def log_processing_start(self, cik: str, file_size_mb: float, tier: str):
        """Log inicio de procesamiento"""
        self.logger.info(f"Starting {tier} processing for CIK {cik}, size: {file_size_mb:.1f}MB")

    def log_processing_success(self, cik: str, tier: str, duration: float, tables_extracted: int):
        """Log procesamiento exitoso"""
        self.logger.info(
            f"Success {tier} processing CIK {cik} in {duration:.1f}s, {tables_extracted} tables"
        )

    def log_processing_failure(self, cik: str, error: str, file_size_mb: float):
        """Log fallo de procesamiento"""
        self.logger.error(f"Failed processing CIK {cik} ({file_size_mb:.1f}MB): {error}")

    def log_daily_summary(self):
        """Log resumen diario"""
        report = self.daily_metrics.daily_report()
        self.logger.info(f"Daily Summary: {report}")


# Alias para compatibilidad con TieredProcessor
MetricsCollector = MetricsLogger
