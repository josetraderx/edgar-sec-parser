#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Descubrimiento de Filings.

Este módulo se encarga de interactuar con los índices diarios de la SEC
para descubrir nuevos filings que necesitan ser procesados.
"""
import logging
import re
from datetime import date
from typing import List, Dict, Optional

from sec_extractor.core.http_client import SECHTTPClient

logger = logging.getLogger(__name__)

# Expresión regular para parsear las líneas del índice maestro de la SEC.
# Captura: CIK, Company Name, Form Type, Date Filed, File Name (URL)
MASTER_INDEX_REGEX = re.compile(
    r"^(?P<cik>\d+)\|"
    r"(?P<company_name>.+?)\|"
    r"(?P<form_type>[-A-Z0-9/ ]+?)\|"
    r"(?P<date_filed>\d{4}-\d{2}-\d{2})\|"
    r"edgar/data/(?P<file_name>.*)$"
)

class DailyFeed:
    """
    Gestiona la descarga y el análisis de los índices diarios de la SEC.
    """
    def __init__(self, http_client: Optional[SECHTTPClient] = None):
        self.client = http_client or SECHTTPClient()

    def get_filings_for_date(self, target_date: date, form_types: List[str] = None) -> List[Dict]:
        """
        Obtiene la lista de filings para una fecha específica.

        Args:
            target_date: La fecha para la cual se quieren obtener los filings.
            form_types: Una lista de tipos de formulario a filtrar (e.g., ['N-CSR', 'N-CSRS']).
                        Si es None, se devuelven todos los filings.

        Returns:
            Una lista de diccionarios, donde cada diccionario representa los metadatos de un filing.
        """
        url = self._build_index_url(target_date)
        logger.info(f"Descargando índice maestro desde: {url}")

        try:
            response = self.client.get(url)
            response.raise_for_status()
            content = response.text
        except Exception:
            logger.error(f"No se pudo descargar o encontrar el índice para la fecha {target_date.isoformat()}.", exc_info=True)
            return []

        return self._parse_master_index(content, form_types)

    def _build_index_url(self, target_date: date) -> str:
        """Construye la URL del índice maestro para una fecha dada."""
        quarter = (target_date.month - 1) // 3 + 1
        return (
            f"{self.client.BASE_URL}/Archives/edgar/daily-index/"
            f"{target_date.year}/QTR{quarter}/master.{target_date.strftime('%Y%m%d')}.idx"
        )

    def _parse_master_index(self, index_content: str, form_types: Optional[List[str]]) -> List[Dict]:
        """
        Analiza el contenido de un índice maestro y extrae los metadatos de los filings.
        """
        filings = []
        # Omitir el encabezado del archivo de índice
        lines = index_content.splitlines()[11:]

        for line in lines:
            match = MASTER_INDEX_REGEX.match(line.strip())
            if not match:
                continue

            filing_data = match.groupdict()
            
            # Filtrar por tipo de formulario si se especifica
            if form_types and filing_data['form_type'].strip() not in form_types:
                continue

            # Extraer el número de acceso del nombre del archivo
            # edgar/data/CIK/ACCESSION-NUMBER.txt -> ACCESSION-NUMBER
            accession_number_txt = filing_data['file_name'].split('/')[-1]
            accession_number = accession_number_txt.replace('.txt', '')
            
            filings.append({
                "cik": filing_data['cik'],
                "company_name": filing_data['company_name'].strip(),
                "form_type": filing_data['form_type'].strip(),
                "filing_date": filing_data['date_filed'],
                "accession_number": accession_number,
            })
        
        logger.info(f"Encontrados {len(filings)} filings para los tipos {form_types or 'todos'}.")
        return filings
