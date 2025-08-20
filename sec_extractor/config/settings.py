"""
Configuración centralizada con soporte para SQLAlchemy ORM
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv  # AGREGAR ESTO

# Cargar .env automáticamente
load_dotenv()  # AGREGAR ESTO

@dataclass
class Settings:
    """
    Configuración híbrida que combina settings originales con soporte ORM
    """
    
    # === DATABASE CONFIGURATION ===
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL'))
    database_echo: bool = field(default_factory=lambda: os.getenv('DATABASE_ECHO', 'false').lower() == 'true')
    
    # === SEC API CONFIGURATION ===
    sec_api_user_agent: str = field(default_factory=lambda: os.getenv('SEC_USER_AGENT'))
    rate_limit_delay: float = field(default_factory=lambda: float(os.getenv('RATE_LIMIT_DELAY', '0.1')))
    
    # === TIERED PROCESSING THRESHOLDS ===
    SMALL_FILE_THRESHOLD: float = field(default_factory=lambda: float(os.getenv('SMALL_FILE_THRESHOLD', '10.0')))
    MEDIUM_FILE_THRESHOLD: float = field(default_factory=lambda: float(os.getenv('MEDIUM_FILE_THRESHOLD', '50.0')))
    LARGE_FILE_THRESHOLD: float = field(default_factory=lambda: float(os.getenv('LARGE_FILE_THRESHOLD', '100.0')))
    
    # === TIMEOUT CONFIGURATION ===
    TIMEOUT_STANDARD: int = field(default_factory=lambda: int(os.getenv('TIMEOUT_STANDARD', '300')))
    TIMEOUT_LIMITED: int = field(default_factory=lambda: int(os.getenv('TIMEOUT_LIMITED', '120')))
    TIMEOUT_MINIMAL: int = field(default_factory=lambda: int(os.getenv('TIMEOUT_MINIMAL', '60')))
    
    # === BATCH PROCESSING ===
    batch_size: int = field(default_factory=lambda: int(os.getenv('BATCH_SIZE', '100')))
    night_batch_size: int = field(default_factory=lambda: int(os.getenv('NIGHT_BATCH_SIZE', '50')))
    
    # === DEAD LETTER QUEUE ===
    DLQ_MAX_ATTEMPTS: int = field(default_factory=lambda: int(os.getenv('DLQ_MAX_ATTEMPTS', '5')))
    DLQ_RETRY_AFTER_HOURS: int = field(default_factory=lambda: int(os.getenv('DLQ_RETRY_AFTER_HOURS', '24')))
    DLQ_MAX_FILE_SIZE_MB: float = field(default_factory=lambda: float(os.getenv('DLQ_MAX_FILE_SIZE_MB', '50.0')))
    
    # === CLEANUP CONFIGURATION ===
    DATA_RETENTION_DAYS: int = field(default_factory=lambda: int(os.getenv('DATA_RETENTION_DAYS', '90')))
    
    def __post_init__(self):
        """Validación de configuración"""
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.sec_api_user_agent:
            raise ValueError("SEC_USER_AGENT environment variable is required")
        
        # Validar thresholds
        if not (0 < self.SMALL_FILE_THRESHOLD < self.MEDIUM_FILE_THRESHOLD < self.LARGE_FILE_THRESHOLD):
            raise ValueError("File size thresholds must be in ascending order")
    
    def get_timeout_for_tier(self, tier: str) -> int:
        """Obtiene timeout apropiado para el tier"""
        timeout_map = {
            'standard': self.TIMEOUT_STANDARD,
            'limited': self.TIMEOUT_LIMITED,
            'minimal': self.TIMEOUT_MINIMAL,
            'dead_letter': 0
        }
        return timeout_map.get(tier, self.TIMEOUT_STANDARD)
    
    def determine_processing_tier(self, file_size_mb: float) -> str:
        """Determina tier basado en tamaño de archivo"""
        if file_size_mb > self.LARGE_FILE_THRESHOLD:
            return 'dead_letter'
        elif file_size_mb > self.MEDIUM_FILE_THRESHOLD:
            return 'minimal'
        elif file_size_mb > self.SMALL_FILE_THRESHOLD:
            return 'limited'
        else:
            return 'standard'
    
    def get_database_config(self) -> Dict[str, any]:
        """Obtiene configuración de base de datos para SQLAlchemy"""
        return {
            'url': self.database_url,
            'echo': self.database_echo,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_pre_ping': True
        }

# Instancia global de configuración
settings = Settings()