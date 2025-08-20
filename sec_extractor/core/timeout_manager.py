import signal
import time
from contextlib import contextmanager
from typing import Optional

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

@contextmanager
def timeout_context(seconds: int):
    """Context manager para timeouts en operaciones"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Solo funciona en Unix/Linux
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Fallback para Windows (sin timeout real)
        yield

class TimeoutManager:
    """Maneja timeouts para diferentes operaciones"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def get_parse_timeout(self, file_size_mb: float) -> int:
        """Determina timeout based en tamaño de archivo"""
        if file_size_mb < self.settings.SMALL_FILE_THRESHOLD:
            return self.settings.STANDARD_PARSE_TIMEOUT
        elif file_size_mb < self.settings.MEDIUM_FILE_THRESHOLD:
            return self.settings.LIMITED_PARSE_TIMEOUT
        else:
            return self.settings.MINIMAL_PARSE_TIMEOUT
    
    def get_processing_tier(self, file_size_mb: float) -> str:
        """Determina qué tier usar para procesar"""
        if file_size_mb < self.settings.SMALL_FILE_THRESHOLD:
            return 'standard'
        elif file_size_mb < self.settings.MEDIUM_FILE_THRESHOLD:
            return 'limited'
        else:
            return 'minimal'