import pandas as pd
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from config.table_patterns import CRITICAL_TABLE_PATTERNS
from core.timeout_manager import timeout_context, TimeoutError

class StandardExtractor:
    """Extractor para archivos pequeños (<10MB) - Procesamiento completo"""
    
    def __init__(self, timeout_manager):
        self.timeout_manager = timeout_manager
    
    def extract(self, html: str, meta_row: Dict) -> Dict[str, Any]:
        """Extrae todas las tablas disponibles"""
        result = {
            'processing_tier': 'standard',
            'metadata': self._extract_metadata(html),
            'tables': {},
            'table_count': 0,
            'status': 'success'
        }
        
        try:
            # Extraer todas las tablas críticas
            for priority, table_info in CRITICAL_TABLE_PATTERNS.items():
                with timeout_context(120):  # 2 min por tabla
                    tables = self._extract_table_type(html, table_info)
                    if tables:
                        result['tables'][table_info['name']] = tables
                        result['table_count'] += len(tables)
                        
            # Intentar pandas.read_html para tablas adicionales
            with timeout_context(300):  # 5 min para pandas
                additional_tables = self._extract_with_pandas(html)
                if additional_tables:
                    result['tables']['additional_tables'] = additional_tables
                    result['table_count'] += len(additional_tables)
                    
        except TimeoutError as e:
            result['status'] = 'partial'
            result['error'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result
    
    def _extract_metadata(self, html: str) -> Dict[str, str]:
        """Extrae metadatos básicos del documento"""
        soup = BeautifulSoup(html, 'lxml')
        
        metadata = {}
        
        # Fund name
        title_tags = soup.find_all(['title', 'h1', 'h2'])
        for tag in title_tags:
            if 'fund' in tag.get_text().lower():
                metadata['fund_name'] = tag.get_text().strip()
                break
        
        # Reporting period
        period_pattern = r'(?:period|quarter|year).*?ended?\s*([A-Za-z]+ \d{1,2},? \d{4})'
        period_match = re.search(period_pattern, html, re.IGNORECASE)
        if period_match:
            metadata['reporting_period'] = period_match.group(1)
        
        return metadata
    
    def _extract_table_type(self, html: str, table_info: Dict) -> List[pd.DataFrame]:
        """Extrae un tipo específico de tabla usando patrones"""
        tables = []
        
        for pattern in table_info['patterns']:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches[:3]:  # Max 3 por patrón
                try:
                    df_list = pd.read_html(match)
                    tables.extend(df_list)
                except Exception:
                    continue
                    
        return tables
    
    def _extract_with_pandas(self, html: str) -> List[pd.DataFrame]:
        """Extrae tablas adicionales con pandas.read_html"""
        try:
            all_tables = pd.read_html(html)
            # Filtrar tablas muy pequeñas
            filtered_tables = [df for df in all_tables if len(df) > 3 and len(df.columns) > 2]
            return filtered_tables[:20]  # Max 20 tablas adicionales
        except Exception:
            return []