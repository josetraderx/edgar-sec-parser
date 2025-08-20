import re
from typing import Dict, Any
from config.table_patterns import KEY_METRICS_PATTERNS
from core.timeout_manager import timeout_context, TimeoutError

class MinimalExtractor:
    """Extractor para archivos grandes (>50MB) - Solo métricas clave"""
    
    def __init__(self, timeout_manager):
        self.timeout_manager = timeout_manager
    
    def extract(self, html: str, meta_row: Dict) -> Dict[str, Any]:
        """Extrae solo métricas clave sin parsear tablas completas"""
        result = {
            'processing_tier': 'minimal',
            'metadata': self._extract_metadata(html),
            'key_metrics': {},
            'critical_sections': {},
            'table_count': 0,
            'status': 'success'
        }
        
        try:
            with timeout_context(30):  # 30 segundos para métricas
                result['key_metrics'] = self._extract_key_metrics(html)
                
            with timeout_context(30):  # 30 segundos para secciones
                result['critical_sections'] = self._extract_critical_sections(html)
                
        except TimeoutError as e:
            result['status'] = 'partial'
            result['error'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result
    
    def _extract_metadata(self, html: str) -> Dict[str, str]:
        """Extrae metadatos de los primeros 20KB únicamente"""
        metadata = {}
        
        # Solo buscar en el inicio del documento
        html_header = html[:20000]
        
        # Patrones simples y rápidos
        patterns = {
            'fund_name': r'<title[^>]*>([^<]*)</title>',
            'cik': r'cik[:\s]*(\d+)',
            'period_end': r'period.*?ended?\s*([A-Za-z]+ \d{1,2},? \d{4})'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, html_header, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()
        
        return metadata
    
    def _extract_key_metrics(self, html: str) -> Dict[str, str]:
        """Extrae métricas clave usando regex patterns"""
        metrics = {}
        
        # Buscar solo en los primeros 200KB
        html_sample = html[:200000]
        
        for metric_name, pattern in KEY_METRICS_PATTERNS.items():
            matches = re.findall(pattern, html_sample, re.IGNORECASE)
            if matches:
                # Tomar el primer match válido
                metrics[metric_name] = matches[0]
        
        return metrics
    
    def _extract_critical_sections(self, html: str) -> Dict[str, str]:
        """Extrae secciones críticas como texto plano"""
        sections = {}
        
        # Patrones para secciones importantes
        section_patterns = {
            'investment_objective': r'(?:investment\s+objective|objective)[:\s]*([^\.]{50,300})',
            'fund_summary': r'(?:fund\s+summary|summary)[:\s]*([^\.]{100,500})',
            'performance_summary': r'(?:performance\s+summary|total\s+return)[:\s]*([^\.]{50,300})'
        }
        
        html_sample = html[:300000]  # Primeros 300KB
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, html_sample, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()
        
        return sections