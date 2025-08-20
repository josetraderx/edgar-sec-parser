"""
Utility functions for SEC filing parsers.
This module provides helper functions for data processing, validation,
and common operations across all parsers.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


def clean_filing_content(content: str) -> str:
    """
    Clean and normalize filing content for parsing.
    
    Args:
        content: Raw filing content
        
    Returns:
        Cleaned content string
    """
    if not content:
        return ""
    
    # Remove excessive whitespace while preserving structure
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove null bytes and other problematic characters
    content = content.replace('\x00', '').replace('\x0c', '')
    
    return content.strip()


def extract_document_sections(content: str) -> Dict[str, str]:
    """
    Extract different sections from SEC filing content.
    
    Args:
        content: Full filing content
        
    Returns:
        Dictionary with extracted sections
    """
    sections = {}
    
    # Extract SEC header
    header_match = re.search(
        r'<SEC-HEADER>(.*?)</SEC-HEADER>', 
        content, 
        re.DOTALL | re.IGNORECASE
    )
    if header_match:
        sections['header'] = header_match.group(1).strip()
    
    # Extract documents
    document_pattern = r'<DOCUMENT>\s*<TYPE>([^<\n]+)\s*<SEQUENCE>([^<\n]+).*?<TEXT>(.*?)</TEXT>\s*</DOCUMENT>'
    document_matches = re.findall(document_pattern, content, re.DOTALL | re.IGNORECASE)
    
    documents = []
    for doc_type, sequence, text in document_matches:
        documents.append({
            'type': doc_type.strip(),
            'sequence': sequence.strip(),
            'text': text.strip()
        })
    
    sections['documents'] = documents
    
    return sections


def validate_accession_number(accession_number: str) -> bool:
    """
    Validate SEC accession number format.
    
    Args:
        accession_number: Accession number to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not accession_number:
        return False
    
    # Standard format: 0000000000-00-000000 (10-2-6 digits with hyphens)
    pattern = r'^\d{10}-\d{2}-\d{6}$'
    return bool(re.match(pattern, accession_number))


def validate_cik(cik: Union[str, int]) -> bool:
    """
    Validate Central Index Key (CIK) format.
    
    Args:
        cik: CIK to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not cik:
        return False
    
    try:
        # Convert to string and remove leading zeros
        cik_str = str(cik).lstrip('0')
        
        # Should be 1-10 digits
        if not cik_str.isdigit():
            return False
        
        cik_int = int(cik_str)
        return 1 <= cik_int <= 9999999999
        
    except (ValueError, TypeError):
        return False


def normalize_form_type(form_type: str) -> str:
    """
    Normalize SEC form type.
    
    Args:
        form_type: Raw form type
        
    Returns:
        Normalized form type
    """
    if not form_type:
        return ""
    
    # Convert to uppercase and remove extra whitespace
    normalized = form_type.upper().strip()
    
    # Remove common prefixes/suffixes
    normalized = re.sub(r'^FORM\s+', '', normalized)
    normalized = re.sub(r'/A$', '', normalized)  # Remove amendment indicator
    
    return normalized


def extract_filing_date(content: str) -> Optional[datetime]:
    """
    Extract filing date from content.
    
    Args:
        content: Filing content
        
    Returns:
        Filing date as datetime object or None
    """
    # Look for various date formats
    date_patterns = [
        r'FILED-AS-OF-DATE:\s*(\d{8})',
        r'FILING-DATE:\s*(\d{8})',
        r'<FILING-DATE>(\d{8})',
        r'FILED AS OF DATE:\s*(\d{8})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                continue
    
    return None


def calculate_content_hash(content: Union[str, bytes]) -> str:
    """
    Calculate MD5 hash of content for deduplication.
    
    Args:
        content: Content to hash
        
    Returns:
        MD5 hash as hex string
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    return hashlib.md5(content).hexdigest()


def detect_content_type(content: str) -> str:
    """
    Detect the type of SEC filing content.
    
    Args:
        content: Filing content
        
    Returns:
        Detected content type
    """
    content_lower = content.lower()
    
    # Check for SGML markers
    sgml_indicators = [
        '<sec-document>',
        '<sec-header>',
        'accession-number:',
        '<document>'
    ]
    
    if any(indicator in content_lower for indicator in sgml_indicators):
        # Check if it also contains XBRL
        xbrl_indicators = [
            'xmlns:ix=',
            'inlinexbrl',
            'ix:',
            'xbrl.org'
        ]
        
        if any(indicator in content_lower for indicator in xbrl_indicators):
            return 'sgml_with_xbrl'
        else:
            return 'sgml'
    
    # Check for pure XBRL
    xbrl_indicators = [
        'xmlns:ix=',
        'inlinexbrl',
        'ix:nonfraction',
        'ix:nonnumeric'
    ]
    
    if any(indicator in content_lower for indicator in xbrl_indicators):
        return 'xbrl'
    
    # Check for HTML
    if '<html' in content_lower and '<body' in content_lower:
        return 'html'
    
    # Check for XML
    if content.strip().startswith('<?xml'):
        return 'xml'
    
    return 'unknown'


def extract_company_info(content: str) -> Dict[str, Optional[str]]:
    """
    Extract basic company information from filing content.
    
    Args:
        content: Filing content
        
    Returns:
        Dictionary with company information
    """
    info = {
        'cik': None,
        'company_name': None,
        'sic': None,
        'state_of_incorporation': None
    }
    
    # Extract CIK
    cik_match = re.search(r'CENTRAL-INDEX-KEY:\s*(\d+)', content, re.IGNORECASE)
    if cik_match:
        info['cik'] = cik_match.group(1).lstrip('0')
    
    # Extract company name
    name_match = re.search(r'COMPANY-CONFORMED-NAME:\s*([^\n\r]+)', content, re.IGNORECASE)
    if name_match:
        info['company_name'] = name_match.group(1).strip()
    
    # Extract SIC
    sic_match = re.search(r'STANDARD-INDUSTRIAL-CLASSIFICATION:\s*([^\n\r]+)', content, re.IGNORECASE)
    if sic_match:
        info['sic'] = sic_match.group(1).strip()
    
    # Extract state of incorporation
    state_match = re.search(r'STATE-OF-INCORPORATION:\s*([^\n\r]+)', content, re.IGNORECASE)
    if state_match:
        info['state_of_incorporation'] = state_match.group(1).strip()
    
    return info


def measure_performance(func):
    """
    Decorator to measure function performance.
    
    Args:
        func: Function to measure
        
    Returns:
        Wrapped function with performance measurement
    """
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = None
        
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            start_memory = process.memory_info().rss
        except ImportError:
            pass
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            end_memory = None
            memory_usage = None
            
            if start_memory:
                try:
                    end_memory = process.memory_info().rss
                    memory_usage = end_memory - start_memory
                except:
                    pass
            
            # Log performance metrics
            logger.debug(
                f"Performance: {func.__name__} took {execution_time:.3f}s"
                + (f", memory: {memory_usage/1024/1024:.1f}MB" if memory_usage else "")
            )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


class ParsingStats:
    """
    Class to track parsing statistics and performance metrics.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all statistics."""
        self.total_files = 0
        self.successful_parses = 0
        self.failed_parses = 0
        self.total_processing_time = 0.0
        self.total_facts_extracted = 0
        self.parser_usage = {}
        self.error_types = {}
    
    def record_parse(self, success: bool, processing_time: float, 
                    facts_count: int = 0, parser_name: str = None, 
                    error_type: str = None):
        """
        Record the results of a parsing operation.
        
        Args:
            success: Whether parsing was successful
            processing_time: Time taken for parsing
            facts_count: Number of facts extracted
            parser_name: Name of parser used
            error_type: Type of error if failed
        """
        self.total_files += 1
        self.total_processing_time += processing_time
        
        if success:
            self.successful_parses += 1
            self.total_facts_extracted += facts_count
        else:
            self.failed_parses += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        if parser_name:
            self.parser_usage[parser_name] = self.parser_usage.get(parser_name, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary with summary statistics
        """
        success_rate = (self.successful_parses / self.total_files * 100) if self.total_files > 0 else 0
        avg_processing_time = (self.total_processing_time / self.total_files) if self.total_files > 0 else 0
        avg_facts_per_file = (self.total_facts_extracted / self.successful_parses) if self.successful_parses > 0 else 0
        
        return {
            'total_files': self.total_files,
            'successful_parses': self.successful_parses,
            'failed_parses': self.failed_parses,
            'success_rate_percent': round(success_rate, 2),
            'total_processing_time': round(self.total_processing_time, 3),
            'average_processing_time': round(avg_processing_time, 3),
            'total_facts_extracted': self.total_facts_extracted,
            'average_facts_per_file': round(avg_facts_per_file, 1),
            'parser_usage': self.parser_usage,
            'error_types': self.error_types
        }
