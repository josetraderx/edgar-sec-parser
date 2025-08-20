"""
SEC Filing Parsers Module

This module provides comprehensive parsing capabilities for SEC filings,
integrating multiple specialized parsers for different content types.

The module includes:
- SGML parser for document structure and metadata
- XBRL parser for financial data facts
- Integrated parser that combines both approaches
- Utilities for data processing and normalization

Usage:
    from sec_extractor.parsers import FilingParser
    
    parser = FilingParser()
    result = parser.parse_filing(filing_content)
    
    if result.success:
        print(f"Extracted {len(result.xbrl_facts)} XBRL facts")
        print(f"Metadata: {result.metadata}")
"""

from .base import (
    ParsingResult,
    FilingMetadata,
    XBRLFact,
    BaseParser,
    ParseError,
    safe_decode,
    normalize_key,
    measure_parsing_time
)

# Parser implementations will be imported when available
try:
    from .sgml_parser import SGMLParser
    SGML_AVAILABLE = True
except ImportError:
    SGML_AVAILABLE = False
    SGMLParser = None

try:
    from .xbrl_parser import XBRLParser
    XBRL_AVAILABLE = True
except ImportError:
    XBRL_AVAILABLE = False
    XBRLParser = None

try:
    from .integrated_parser import FilingParser
    INTEGRATED_AVAILABLE = True
except ImportError:
    INTEGRATED_AVAILABLE = False
    FilingParser = None

# Export availability flags for runtime checks
PARSER_AVAILABILITY = {
    'sgml': SGML_AVAILABLE,
    'xbrl': XBRL_AVAILABLE,
    'integrated': INTEGRATED_AVAILABLE
}

def get_available_parsers():
    """Get list of available parser classes."""
    parsers = []
    if SGML_AVAILABLE and SGMLParser:
        parsers.append(SGMLParser)
    if XBRL_AVAILABLE and XBRLParser:
        parsers.append(XBRLParser)
    if INTEGRATED_AVAILABLE and FilingParser:
        parsers.append(FilingParser)
    return parsers

def create_parser(parser_type: str, **kwargs):
    """
    Create a parser instance of the specified type.
    
    Args:
        parser_type: Type of parser ("sgml", "xbrl", "integrated")
        **kwargs: Additional arguments for parser initialization
        
    Returns:
        Parser instance
        
    Raises:
        ValueError: If parser type is not available
    """
    parser_type = parser_type.lower()
    
    if parser_type == "sgml":
        if not SGML_AVAILABLE or not SGMLParser:
            raise ValueError("SGML parser is not available. Install secsgml>=0.3.0")
        return SGMLParser(**kwargs)
    
    elif parser_type == "xbrl":
        if not XBRL_AVAILABLE or not XBRLParser:
            raise ValueError("XBRL parser is not available. Install secxbrl>=0.5.0")
        return XBRLParser(**kwargs)
    
    elif parser_type == "integrated":
        if not INTEGRATED_AVAILABLE or not FilingParser:
            raise ValueError("Integrated parser is not available")
        return FilingParser(**kwargs)
    
    else:
        raise ValueError(f"Unknown parser type: {parser_type}")

# Main exports
__all__ = [
    # Base types and classes
    'ParsingResult',
    'FilingMetadata', 
    'XBRLFact',
    'BaseParser',
    'ParseError',
    
    # Utility functions
    'safe_decode',
    'normalize_key',
    'measure_parsing_time',
    
    # Parser classes (may be None if not available)
    'SGMLParser',
    'XBRLParser',
    'FilingParser',
    
    # Availability information
    'PARSER_AVAILABILITY',
    'SGML_AVAILABLE',
    'XBRL_AVAILABLE',
    'INTEGRATED_AVAILABLE',
    
    # Factory functions
    'get_available_parsers',
    'create_parser'
]

# Version information
__version__ = '1.0.0'
__author__ = 'Edgar SEC Extractor Team'
