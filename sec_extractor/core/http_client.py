"""
Cliente HTTP mejorado para interactuar con la SEC.

Incluye rate limiting, reintentos y gestión de User-Agent,
basado en las mejores prácticas de ncsr_extractor.
"""

import logging
import time
import threading
import requests
from ..config.settings import settings

logger = logging.getLogger(__name__)

class SECHTTPClient:
    """
    Cliente HTTP robusto para realizar solicitudes a la SEC.
    """
    BASE_URL = "https://www.sec.gov"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.sec_api_user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        })
        self.last_request_time = 0
        self.lock = threading.Lock()

    def _rate_limit(self):
        """Asegura no exceder el límite de 10 req/s de la SEC."""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < settings.rate_limit_delay:
                time.sleep(settings.rate_limit_delay - time_since_last)
            self.last_request_time = time.time()

    def get(self, url: str, retries: int = 3):
        """
        Obtiene contenido de una URL con reintentos.
        """
        for attempt in range(retries):
            try:
                self._rate_limit()
                logger.debug(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All retries failed for {url}")
                    raise
                # Exponential backoff
                time.sleep(2 ** attempt)

    def get_text(self, url: str, retries: int = 3) -> str:
        """
        Obtiene el contenido de texto de una URL con reintentos.

        Args:
            url: La URL a la que se va a hacer la solicitud.
            retries: El número de reintentos en caso de fallo.

        Returns:
            El contenido de texto de la respuesta, o una cadena vacía si falla.
        """
        for attempt in range(retries):
            try:
                self._rate_limit()
                logger.debug(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == retries - 1:
                    logger.error(f"All retries failed for {url}")
                    return ""
                # Exponential backoff
                time.sleep(2 ** attempt)
        return ""

# Instancia singleton para ser usada en la aplicación
http_client = SECHTTPClient()
