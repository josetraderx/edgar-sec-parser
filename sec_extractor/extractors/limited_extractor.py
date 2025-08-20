import pandas as pd
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from config.table_patterns import CRITICAL_TABLE_PATTERNS
from core.timeout_manager import timeout_context, TimeoutError

class LimitedExtractor:
    """Extractor para archivos medianos (10-50MB) - Solo tablas críticas"""
    
    def __init__(self, timeout_manager):
        self.timeout_manager = timeout_manager
    
    def extract(self, html: str, meta_row: Dict) -> Dict[str, Any]:
        """Extrae solo las 5 tablas más críticas"""
        result = {
            'processing_tier': 'limited',
            'metadata': self._extract_metadata(html),
            'tables': {},
            'table_count': 0,
            'status': 'success'
        }
        
        # Solo procesar top 5 tablas críticas
        critical_tables = {k: v for k, v in CRITICAL_TABLE_PATTERNS.items() if k <= 5}
        
        try:
            for priority, table_info in critical_tables.items():
                try:
                    with timeout_context(60):  # 1 min por tabla
                        tables = self._extract_selective_tables(html, table_info)
                        if tables:
                            result['tables'][table_info['name']] = tables
                            result['table_count'] += len(tables)
                except TimeoutError:
                    # Skip esta tabla y continuar
                    continue
                    
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result
    
    def _extract_metadata(self, html: str) -> Dict[str, str]:
        """Extrae metadatos básicos más rápido"""
        metadata = {}
        
        # Solo buscar los primeros 50KB del HTML
        html_sample = html[:50000]
        
        # Fund name - búsqueda simple
        fund_pattern = r'<title[^>]*>([^<]*fund[^<]*)</title>'
        fund_match = re.search(fund_pattern, html_sample, re.IGNORECASE)
        if fund_match:
            metadata['fund_name'] = fund_match.group(1).strip()
        
        # Reporting period
        period_pattern = r'period.*?ended?\s*([A-Za-z]+ \d{1,2},? \d{4})'
        period_match = re.search(period_pattern, html_sample, re.IGNORECASE)
        if period_match:
            metadata['reporting_period'] = period_match.group(1)
        
        return metadata
    
    def _extract_selective_tables(self, html: str, table_info: Dict) -> List[pd.DataFrame]:
        """Extrae tablas de forma más selectiva y rápida"""
        tables = []
        
        # Solo usar el primer patrón de cada tipo
        pattern = table_info['patterns'][0]
        
        try:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches[:2]:  # Max 2 por patrón
                # Verificar tamaño del match
                if len(match) > 100000:  # Skip tablas muy grandes (>100KB)
                    continue
                    
                try:
                    df_list = pd.read_html(match, header=0)
                    for df in df_list[:1]:  # Solo la primera tabla del match
                        if len(df) > 3:  # Skip tablas muy pequeñas
                            tables.append(df)
                except Exception:
                    continue
                    
        except Exception:
            pass
            
        return tables