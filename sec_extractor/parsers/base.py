"""
Base classes and types for SEC filing parsers.

This module defines the common interfaces and data structures used by all parsers
in the sec_extractor.parsers package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsingResult:
    """
    Standard result structure for any parsing operation.
    
    This class provides a consistent interface for all parser results,
    including success status, timing information, and error handling.
    """
    success: bool
    parser_name: str
    metadata: Optional['FilingMetadata'] = None
    xbrl_facts: List['XBRLFact'] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    parsing_time: float = 0.0
    
    def __post_init__(self):
        """Validate the parsing result after initialization."""
        if self.success and self.error_message:
            logger.warning("Parsing marked as successful but has error message")
        
        if not self.success and not self.error_message:
            self.error_message = "Unknown parsing error"


@dataclass
class FilingMetadata:
    """
    Standardized filing metadata extracted from SEC documents.
    
    This class normalizes metadata across different filing types and sources.
    """
    accession_number: Optional[str] = None
    cik: Optional[str] = None
    company_name: Optional[str] = None
    form_type: Optional[str] = None
    filing_date: Optional[datetime] = None
    period_of_report: Optional[datetime] = None
    acceptance_datetime: Optional[datetime] = None
    sic: Optional[str] = None
    state_of_incorporation: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    business_address: Optional[str] = None
    business_phone: Optional[str] = None
    document_count: Optional[Union[str, int]] = None
    items: Optional[List[str]] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class XBRLFact:
    """
    Represents a single XBRL fact extracted from a filing.
    
    XBRL facts are the atomic data points in financial documents.
    """
    name: str
    value: Union[str, float, int]
    context_ref: Optional[str] = None
    unit: Optional[str] = None
    decimals: Optional[Union[str, int]] = None
    scale: Optional[Union[str, int]] = None
    additional_attributes: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fact to dictionary format."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class BaseParser(ABC):
    """
    Abstract base class for all SEC filing parsers.
    
    This class defines the standard interface that all parsers must implement,
    ensuring consistency across different parsing implementations.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return parser name."""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Return list of supported formats."""
        pass
    
    @property
    @abstractmethod
    def available(self) -> bool:
        """
        Check if the parser is available and functional.
        
        Returns:
            True if parser can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def is_compatible(self, content: Union[str, bytes]) -> bool:
        """
        Check if content is compatible with this parser.
        
        Args:
            content: Raw content to check
            
        Returns:
            True if content appears to be compatible
        """
        pass
    
    @abstractmethod
    def parse(self, content: Union[str, bytes], **kwargs) -> ParsingResult:
        """
        Parse filing content and return structured result.
        
        Args:
            content: Raw filing content
            **kwargs: Additional parsing options
            
        Returns:
            ParsingResult with parsed data and metadata
        """
        pass


class ParseError(Exception):
    """Custom exception for parsing errors."""
    
    def __init__(self, message: str, parser_name: str = None, original_error: Exception = None):
        """
        Initialize parsing error.
        
        Args:
            message: Error description
            parser_name: Name of parser that failed
            original_error: Original exception that caused this error
        """
        self.parser_name = parser_name
        self.original_error = original_error
        
        full_message = message
        if parser_name:
            full_message = f"{parser_name}: {message}"
        
        super().__init__(full_message)


def safe_decode(data: Union[str, bytes], encoding: str = 'utf-8') -> str:
    """
    Safely decode bytes to string with fallback handling.
    
    Args:
        data: Data to decode
        encoding: Target encoding
        
    Returns:
        Decoded string
    """
    if isinstance(data, str):
        return data
    
    if isinstance(data, bytes):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            # Fallback to latin-1 which accepts any byte sequence
            return data.decode('latin-1', errors='replace')
    
    return str(data)


def normalize_key(key: Union[str, bytes]) -> str:
    """
    Normalize dictionary keys to consistent string format.
    
    Args:
        key: Key to normalize
        
    Returns:
        Normalized string key
    """
    if isinstance(key, bytes):
        try:
            return key.decode('utf-8')
        except UnicodeDecodeError:
            return key.decode('latin-1', errors='replace')
    
    return str(key).strip()


def measure_parsing_time(func):
    """
    Decorator to measure parsing time and add to result.
    
    This decorator automatically measures the execution time of parsing
    functions and includes it in the ParsingResult.
    """
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            if isinstance(result, ParsingResult):
                result.parsing_time = time.time() - start_time
            return result
        except Exception as e:
            parsing_time = time.time() - start_time
            if len(args) > 0 and hasattr(args[0], 'logger'):
                args[0].logger.error(f"Parsing failed after {parsing_time:.3f}s: {e}")
            raise
    
    return wrapper
