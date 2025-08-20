"""
Módulo de parsers para extraer información detallada de filings N-CSR.

Este módulo contiene funciones para:
- Extraer metadatos del fondo.
- Parsear la fecha del período de reporte.
- Extraer y clasificar secciones de texto.
- Extraer, clasificar y normalizar tablas.
- Parsear datos básicos de documentos XBRL.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

def extract_period_of_report(soup: BeautifulSoup) -> Optional[datetime]:
    """Extrae la fecha del período de reporte del documento."""
    try:
        # Búsqueda más robusta, insensible a mayúsculas y variaciones
        text_patterns = [
            re.compile(r"period\s+of\s+report", re.I),
            re.compile(r"for\s+the\s+period\s+ended", re.I)
        ]
        for pattern in text_patterns:
            for text_node in soup.find_all(string=pattern):
                parent = text_node.find_parent()
                if parent:
                    # Buscar en el texto cercano al nodo encontrado
                    search_text = parent.get_text()
                    # Patrón para encontrar fechas en varios formatos
                    date_match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})|(\d{4}-\d{2}-\d{2})', search_text)
                    if date_match:
                        date_str = date_match.group(0)
                        for fmt in ("%B %d, %Y", "%Y-%m-%d"):
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue
    except Exception as e:
        logger.warning(f"Error extracting period_of_report: {e}")
    return None

def extract_fund_metadata(soup: BeautifulSoup) -> Dict:
    """Extrae metadatos clave del fondo desde el HTML."""
    metadata = {}
    try:
        text = soup.get_text().lower()
        
        # Extraer nombre del fondo
        for h in soup.find_all(['h1', 'h2', 'title']):
            title_text = h.get_text(strip=True)
            if any(word in title_text.lower() for word in ['fund', 'trust', 'portfolio']):
                metadata['fund_name'] = title_text[:500]
                break
        
        # Extraer Total Net Assets
        patterns = [
            r'total\s+net\s+assets[:\s$]*([0-9,]+(?:\.[0-9]+)?)',
            r'net\s+assets[:\s$]*([0-9,]+(?:\.[0-9]+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    assets_str = match.group(1).replace(',', '')
                    metadata['total_net_assets'] = float(assets_str)
                    break
                except (ValueError, IndexError):
                    continue
                    
    except Exception as e:
        logger.warning(f"Error extracting fund metadata: {e}")
    return metadata

def extract_sections(html_text: str) -> List[Dict]:
    """Extrae y clasifica secciones de texto del HTML."""
    if not html_text:
        return []
    try:
        soup = BeautifulSoup(html_text, "lxml")
        sections = []
        # Usar etiquetas de encabezado como delimitadores de sección
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            section_name = header.get_text(strip=True)
            if not section_name:
                continue
            
            content = []
            for sibling in header.find_next_siblings():
                # Detenerse al encontrar el próximo encabezado del mismo nivel o superior
                if sibling.name in ['h1', 'h2', 'h3', 'h4'] and sibling.name <= header.name:
                    break
                content.append(sibling.get_text(" ", strip=True))
            
            text_clean = " ".join(content).strip()
            if text_clean:
                sections.append({
                    "section_name": section_name[:250],
                    "section_type": _classify_section_type(section_name),
                    "text_clean": text_clean,
                    "word_count": len(text_clean.split())
                })
        return sections
    except Exception as e:
        logger.error(f"Error extracting sections: {e}")
        return []

def extract_tables(html_text: str) -> List[Dict]:
    """Extrae, clasifica y normaliza tablas del HTML."""
    if not html_text:
        return []
    try:
        tables = []
        soup = BeautifulSoup(html_text, "lxml")
        for i, table_tag in enumerate(soup.find_all("table")):
            try:
                # Buscar caption de forma más robusta
                caption_tag = table_tag.find("caption")
                caption = caption_tag.get_text(strip=True) if caption_tag else None
                if not caption:
                    prev_header = table_tag.find_previous(['h1', 'h2', 'h3', 'h4', 'p'])
                    if prev_header:
                        caption = prev_header.get_text(strip=True)

                df = pd.read_html(str(table_tag), flavor='lxml')[0]
                df.columns = [str(c) for c in df.columns] # Asegurar que las columnas son strings
                
                # Normalizar filas
                rows_data = []
                for row_idx, row in df.iterrows():
                    for col_name, col_value in row.items():
                        if pd.notna(col_value):
                            rows_data.append({
                                "row_index": row_idx,
                                "col_name": str(col_name)[:250],
                                "col_value": str(col_value),
                                "col_type": _infer_column_type(col_value)
                            })

                tables.append({
                    "table_type": _classify_table_type(caption or "", df),
                    "caption": caption[:500] if caption else f"Table {i+1}",
                    "table_html": table_tag.prettify(),
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "rows": rows_data
                })
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse table {i}: {e}")
                continue
        logger.info(f"Extracted {len(tables)} tables")
        return tables
    except Exception as e:
        logger.error(f"Error extracting tables: {e}")
        return []

def extract_xbrl_metrics(xml_text: str) -> Dict:
    """Extrae métricas clave de un documento XBRL."""
    if not xml_text:
        return {}
    try:
        # Eliminar el namespace por defecto para simplificar la búsqueda
        xml_text = re.sub(r'\sxmlns="[^"]+"', '', xml_text, count=1)
        root = ET.fromstring(xml_text)
        metrics = {}
        # Tags comunes en N-CSR XBRL (sin namespace)
        for tag in [
            'NetAssets',
            'NetAssetValuePerShare',
            'TotalExpenseRatio',
            'SharesOutstanding'
        ]:
            elements = root.findall(f".//{tag}")
            if elements:
                metrics[tag] = elements[0].text
        return metrics
    except Exception as e:
        logger.warning(f"Error parsing XBRL: {e}")
        return {}

# --- Funciones de ayuda privadas ---

def _classify_section_type(section_name: str) -> str:
    """Clasifica el tipo de sección basado en su nombre."""
    section_lower = section_name.lower()
    if any(word in section_lower for word in ['portfolio', 'holding', 'investment']):
        return 'portfolio'
    elif any(word in section_lower for word in ['performance', 'return', 'yield']):
        return 'performance'
    elif any(word in section_lower for word in ['expense', 'fee', 'cost']):
        return 'expenses'
    elif any(word in section_lower for word in ['risk', 'factor']):
        return 'risk_factors'
    elif any(word in section_lower for word in ['financial', 'statement', 'balance']):
        return 'financials'
    return 'other'

def _classify_table_type(caption: str, df: pd.DataFrame) -> str:
    """Clasifica el tipo de tabla basado en su caption y columnas."""
    caption_lower = caption.lower()
    columns_lower = [str(col).lower() for col in df.columns]
    
    if any(word in caption_lower for word in ['portfolio', 'holding', 'investment']):
        return 'portfolio_holdings'
    if any(word in ' '.join(columns_lower) for word in ['security', 'shares', 'market value', 'principal amount']):
        return 'portfolio_holdings'
    if any(word in caption_lower for word in ['performance', 'return', 'yield']):
        return 'performance_data'
    if any(word in caption_lower for word in ['financial', 'statement', 'assets', 'liabilities', 'operations']):
        return 'financial_summary'
    return 'other'

def _infer_column_type(value) -> str:
    """Infiere el tipo de dato de un valor en una tabla."""
    if pd.isna(value):
        return 'null'
    value_str = str(value).strip()
    if '%' in value_str:
        return 'percentage'
    if '$' in value_str or '€' in value_str or '£' in value_str:
        return 'currency'
    # Regex para números, incluyendo negativos y con comas
    if re.match(r'^\(?-?[\d,]+\.?\d*\)?$', value_str.replace('$', '').replace('(', '-').replace(')', '')):
        return 'number'
    if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value_str) or re.match(r'\w+\s\d{1,2},\s\d{4}', value_str):
        return 'date'
    return 'text'
