"""
SGML parser implementation using secsgml library.
This module provides a wrapper around John Friedman's secsgml library
to parse SEC SGML filings and extract metadata and XBRL content.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .base import BaseParser, ParsingResult, FilingMetadata, XBRLFact, ParseError, safe_decode, normalize_key, measure_parsing_time

try:
    import secsgml
    SECSGML_AVAILABLE = True
except ImportError:
    SECSGML_AVAILABLE = False
    secsgml = None

logger = logging.getLogger(__name__)


class SGMLParser(BaseParser):
    """
    Parser for SEC SGML filings using the secsgml library.
    
    This parser extracts:
    - Filing metadata from SEC headers
    - XBRL/InlineXBRL content from embedded documents
    - Document structure and relationships
    """
    
    def __init__(self, validate_xbrl: bool = True, extract_tables: bool = False):
        """
        Initialize the SGML parser.
        
        Args:
            validate_xbrl: Whether to validate extracted XBRL content
            extract_tables: Whether to extract tabular data from documents
        """
        if not SECSGML_AVAILABLE:
            raise ImportError(
                "secsgml library is not available. "
                "Install it with: pip install secsgml>=0.3.0"
            )
        
        self.validate_xbrl = validate_xbrl
        self.extract_tables = extract_tables
        self._parser = None
        
    @property
    def name(self) -> str:
        """Return parser name."""
        return "SGMLParser"
    
    @property
    def supported_formats(self) -> List[str]:
        """Return list of supported formats."""
        return ["sgml", "txt", "sec"]
    
    @property 
    def available(self) -> bool:
        """Return whether parser is available."""
        return SECSGML_AVAILABLE
    
    def is_compatible(self, content: Union[str, bytes]) -> bool:
        """
        Check if content is compatible with SGML parsing.
        
        Args:
            content: Raw content to check
            
        Returns:
            True if content appears to be SEC SGML format
        """
        try:
            content_str = safe_decode(content)
            
            # Check for SEC document markers
            sgml_indicators = [
                "<SEC-DOCUMENT>",
                "<SEC-HEADER>",
                "ACCESSION-NUMBER:",
                "CONFORMED-SUBMISSION-TYPE:",
                "<DOCUMENT>"
            ]
            
            content_upper = content_str.upper()
            return any(indicator in content_upper for indicator in sgml_indicators)
            
        except Exception as e:
            logger.debug(f"Error checking SGML compatibility: {e}")
            return False
    
    @measure_parsing_time
    def parse(self, content: Union[str, bytes], **kwargs) -> ParsingResult:
        """
        Parse SEC SGML filing content.
        
        Args:
            content: Raw SGML content
            **kwargs: Additional parsing options
            
        Returns:
            ParsingResult with metadata and XBRL facts
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            # Convert to bytes if needed
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
                content_str = content
            else:
                content_bytes = content
                content_str = safe_decode(content)
            
            if not self.is_compatible(content_str):
                raise ParseError("Content does not appear to be SEC SGML format")
            
            # Parse using secsgml (expects bytes)
            logger.debug("Parsing SGML content with secsgml library")
            result = secsgml.parse_sgml_content_into_memory(content_bytes)
            
            if not isinstance(result, tuple) or len(result) != 2:
                raise ParseError(f"Unexpected secsgml result format: {type(result)}")
            
            metadata_dict, xbrl_content_list = result
            
            # Extract metadata
            metadata = self._extract_metadata(metadata_dict)
            
            # Extract XBRL facts
            xbrl_facts = self._extract_xbrl_facts(xbrl_content_list)
            
            # Create parsing result
            parsing_result = ParsingResult(
                success=True,
                parser_name=self.name,
                metadata=metadata,
                xbrl_facts=xbrl_facts,
                raw_data={
                    "sgml_metadata": metadata_dict,
                    "xbrl_content": xbrl_content_list
                },
                error_message=None,
                parsing_time=0.0  # Will be set by decorator
            )
            
            logger.info(
                f"Successfully parsed SGML filing: "
                f"{len(xbrl_facts)} XBRL facts extracted"
            )
            
            return parsing_result
            
        except Exception as e:
            error_msg = f"SGML parsing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ParsingResult(
                success=False,
                parser_name=self.name,
                metadata=None,
                xbrl_facts=[],
                raw_data=None,
                error_message=error_msg,
                parsing_time=0.0  # Will be set by decorator
            )
    
    def _extract_metadata(self, metadata_dict: Dict[str, Any]) -> Optional[FilingMetadata]:
        """
        Extract filing metadata from secsgml result.
        
        Args:
            metadata_dict: Raw metadata from secsgml
            
        Returns:
            FilingMetadata object or None if extraction fails
        """
        try:
            # Normalize keys (secsgml returns bytes keys) and extract known fields
            normalized = {}
            for key, val in metadata_dict.items():
                # Convert bytes key to string and normalize
                str_key = normalize_key(key).lower().replace('-', '_')
                # Convert bytes value to string if needed
                if isinstance(val, bytes):
                    str_val = safe_decode(val)
                else:
                    str_val = val
                normalized[str_key] = str_val
            
            # Map secsgml fields to our metadata structure
            metadata = FilingMetadata(
                accession_number=normalized.get("accession_number"),
                cik=normalized.get("central_index_key") or normalized.get("cik"),
                company_name=normalized.get("company_conformed_name"),
                form_type=normalized.get("conformed_submission_type") or normalized.get("form_type"),
                filing_date=normalized.get("filed_as_of_date"),
                period_of_report=normalized.get("conformed_period_of_report"),
                sic=normalized.get("standard_industrial_classification"),
                state_of_incorporation=normalized.get("state_of_incorporation"),
                fiscal_year_end=normalized.get("fiscal_year_end"),
                business_address=None,  # Would need to parse from complex structure
                business_phone=normalized.get("business_phone"),
                document_count=normalized.get("public_document_count"),
                items=None,  # Would need additional parsing
                additional_metadata=metadata_dict  # Store raw data
            )
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return None
    
    def _extract_xbrl_facts(self, xbrl_content_list: List[Any]) -> List[XBRLFact]:
        """
        Extract XBRL facts from secsgml content list.
        
        Args:
            xbrl_content_list: List of XBRL content from secsgml
            
        Returns:
            List of XBRLFact objects
        """
        facts = []
        
        try:
            for idx, content in enumerate(xbrl_content_list):
                if isinstance(content, str) and content.strip():
                    # This is simplified - in practice, we might need
                    # additional XBRL parsing here or integration with
                    # the XBRL parser
                    fact = XBRLFact(
                        name=f"sgml_content_{idx}",
                        value=content,
                        unit=None,
                        context_ref=None,
                        decimals=None,
                        scale=None,
                        additional_attributes={
                            "source": "sgml_extraction",
                            "content_index": idx
                        }
                    )
                    facts.append(fact)
                    
        except Exception as e:
            logger.warning(f"Failed to extract XBRL facts: {e}")
        
        return facts
    
    def parse_file(self, file_path: Union[str, Path], **kwargs) -> ParsingResult:
        """
        Parse SGML file from disk.
        
        Args:
            file_path: Path to the SGML file
            **kwargs: Additional parsing options
            
        Returns:
            ParsingResult with extracted data
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise ParseError(f"File not found: {file_path}")
            
            content = path.read_text(encoding='utf-8', errors='ignore')
            return self.parse(content, **kwargs)
            
        except Exception as e:
            error_msg = f"Failed to parse file {file_path}: {str(e)}"
            logger.error(error_msg)
            
            return ParsingResult(
                success=False,
                parser_name=self.name,
                metadata=None,
                xbrl_facts=[],
                raw_data=None,
                error_message=error_msg,
                parsing_time=0.0
            )
    
    def get_parser_info(self) -> Dict[str, Any]:
        """
        Get information about this parser.
        
        Returns:
            Dictionary with parser information
        """
        return {
            "name": self.name,
            "version": getattr(secsgml, "__version__", "unknown") if secsgml else None,
            "supported_formats": self.supported_formats,
            "capabilities": [
                "SEC SGML parsing",
                "Metadata extraction",
                "XBRL content extraction",
                "Document structure analysis"
            ],
            "configuration": {
                "validate_xbrl": self.validate_xbrl,
                "extract_tables": self.extract_tables
            },
            "available": SECSGML_AVAILABLE
        }
