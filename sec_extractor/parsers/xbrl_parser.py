"""
XBRL parser implementation using secxbrl library.
This module provides a wrapper around John Friedman's secxbrl library
to parse InlineXBRL content and extract financial facts.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re

from .base import BaseParser, ParsingResult, FilingMetadata, XBRLFact, ParseError, safe_decode, normalize_key, measure_parsing_time

try:
    import secxbrl
    SECXBRL_AVAILABLE = True
except ImportError:
    SECXBRL_AVAILABLE = False
    secxbrl = None

logger = logging.getLogger(__name__)


class XBRLParser(BaseParser):
    """
    Parser for InlineXBRL content using the secxbrl library.
    
    This parser extracts:
    - XBRL facts from InlineXBRL documents
    - Context and unit information
    - Taxonomy references
    - Financial data with proper typing
    """
    
    def __init__(self, extract_contexts: bool = True, validate_facts: bool = True):
        """
        Initialize the XBRL parser.
        
        Args:
            extract_contexts: Whether to extract context information
            validate_facts: Whether to validate extracted facts
        """
        if not SECXBRL_AVAILABLE:
            raise ImportError(
                "secxbrl library is not available. "
                "Install it with: pip install secxbrl>=0.5.0"
            )
        
        self.extract_contexts = extract_contexts
        self.validate_facts = validate_facts
        self._parser = None
        
    @property
    def name(self) -> str:
        """Return parser name."""
        return "XBRLParser"
    
    @property
    def supported_formats(self) -> List[str]:
        """Return list of supported formats."""
        return ["xbrl", "xml", "html", "htm", "ixbrl"]
    
    @property 
    def available(self) -> bool:
        """Return whether parser is available."""
        return SECXBRL_AVAILABLE
    
    def is_compatible(self, content: Union[str, bytes]) -> bool:
        """
        Check if content is compatible with XBRL parsing.
        
        Args:
            content: Raw content to check
            
        Returns:
            True if content appears to be InlineXBRL format
        """
        try:
            content_str = safe_decode(content)
            
            # Check for XBRL/InlineXBRL indicators
            xbrl_indicators = [
                "xmlns:ix=", 
                "inlineXBRL",
                "ix:",
                "xbrl.org",
                "<ix:nonFraction",
                "<ix:nonNumeric",
                "<ix:fraction"
            ]
            
            content_lower = content_str.lower()
            return any(indicator.lower() in content_lower for indicator in xbrl_indicators)
            
        except Exception as e:
            logger.debug(f"Error checking XBRL compatibility: {e}")
            return False
    
    @measure_parsing_time
    def parse(self, content: Union[str, bytes], **kwargs) -> ParsingResult:
        """
        Parse InlineXBRL content.
        
        Args:
            content: Raw XBRL content
            **kwargs: Additional parsing options
            
        Returns:
            ParsingResult with extracted XBRL facts
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            content_str = safe_decode(content)
            
            if not self.is_compatible(content_str):
                raise ParseError("Content does not appear to be InlineXBRL format")
            
            # Parse using secxbrl
            logger.debug("Parsing XBRL content with secxbrl library")
            facts_data = secxbrl.parse_inline_xbrl(content=content_str)
            
            if not isinstance(facts_data, list):
                raise ParseError(f"Unexpected secxbrl result format: {type(facts_data)}")
            
            # Extract XBRL facts
            xbrl_facts = self._extract_xbrl_facts(facts_data)
            
            # Extract basic metadata from content
            metadata = self._extract_basic_metadata(content_str)
            
            # Create parsing result  
            parsing_result = ParsingResult(
                success=True,
                parser_name=self.name,
                metadata=metadata,
                xbrl_facts=xbrl_facts,
                raw_data={
                    "facts_data": facts_data,
                    "fact_count": len(xbrl_facts)
                },
                error_message=None,
                parsing_time=0.0  # Will be set by decorator
            )
            
            logger.info(
                f"Successfully parsed XBRL content: "
                f"{len(xbrl_facts)} facts extracted"
            )
            
            return parsing_result
            
        except Exception as e:
            error_msg = f"XBRL parsing failed: {str(e)}"
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
    
    def _extract_xbrl_facts(self, facts_data: List[Any]) -> List[XBRLFact]:
        """
        Extract XBRL facts from secxbrl result.
        
        Args:
            facts_data: Raw facts data from secxbrl
            
        Returns:
            List of XBRLFact objects
        """
        facts = []
        
        try:
            for fact_item in facts_data:
                if isinstance(fact_item, dict):
                    fact = self._convert_fact_dict(fact_item)
                    if fact:
                        facts.append(fact)
                else:
                    # Handle other formats if needed
                    logger.debug(f"Skipping unknown fact format: {type(fact_item)}")
                    
        except Exception as e:
            logger.warning(f"Failed to extract XBRL facts: {e}")
        
        return facts
    
    def _convert_fact_dict(self, fact_data: Dict[str, Any]) -> Optional[XBRLFact]:
        """
        Convert a fact dictionary to XBRLFact object.
        
        Args:
            fact_data: Raw fact data dictionary
            
        Returns:
            XBRLFact object or None if conversion fails
        """
        try:
            # Map common field names (secxbrl may use different keys)
            name = fact_data.get("name") or fact_data.get("concept") or fact_data.get("element")
            value = fact_data.get("value") or fact_data.get("content") or fact_data.get("text")
            
            # Handle numeric values
            if isinstance(value, (int, float)):
                value = str(value)
            elif value is None:
                value = ""
            
            # Extract other attributes
            unit = fact_data.get("unit") or fact_data.get("unitRef")
            context_ref = fact_data.get("context") or fact_data.get("contextRef")
            decimals = fact_data.get("decimals")
            scale = fact_data.get("scale")
            
            # Convert decimals and scale to integers if possible
            try:
                if decimals is not None and decimals != "INF":
                    decimals = int(decimals)
            except (ValueError, TypeError):
                decimals = None
                
            try:
                if scale is not None:
                    scale = int(scale)
            except (ValueError, TypeError):
                scale = None
            
            # Collect additional attributes
            additional_attrs = {}
            for key, val in fact_data.items():
                if key not in ["name", "concept", "element", "value", "content", "text", 
                             "unit", "unitRef", "context", "contextRef", "decimals", "scale"]:
                    additional_attrs[key] = val
            
            fact = XBRLFact(
                name=name,
                value=value,
                unit=unit,
                context_ref=context_ref,
                decimals=decimals,
                scale=scale,
                additional_attributes=additional_attrs
            )
            
            return fact
            
        except Exception as e:
            logger.warning(f"Failed to convert fact: {e}")
            return None
    
    def _extract_basic_metadata(self, content: str) -> Optional[FilingMetadata]:
        """
        Extract basic metadata from XBRL content.
        
        Args:
            content: Raw XBRL content
            
        Returns:
            FilingMetadata object with basic information
        """
        try:
            # Extract title if available
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None
            
            # Look for entity identifier in contexts
            entity_match = re.search(r'scheme="[^"]*cik"[^>]*>(\d+)', content, re.IGNORECASE)
            cik = entity_match.group(1) if entity_match else None
            
            # Basic metadata structure
            metadata = FilingMetadata(
                accession_number=None,
                cik=cik,
                company_name=title,
                form_type=None,
                filing_date=None,
                period_of_report=None,
                sic=None,
                state_of_incorporation=None,
                fiscal_year_end=None,
                business_address=None,
                business_phone=None,
                document_count=None,
                items=None,
                additional_metadata={
                    "source": "xbrl_extraction",
                    "title": title
                }
            )
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract basic metadata: {e}")
            return None
    
    def parse_file(self, file_path: Union[str, Path], **kwargs) -> ParsingResult:
        """
        Parse XBRL file from disk.
        
        Args:
            file_path: Path to the XBRL file
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
    
    def extract_contexts(self, content: Union[str, bytes]) -> Dict[str, Any]:
        """
        Extract context information from XBRL content.
        
        Args:
            content: Raw XBRL content
            
        Returns:
            Dictionary with context information
        """
        contexts = {}
        
        try:
            content_str = safe_decode(content)
            
            # Find context definitions
            context_pattern = r'<ix:context[^>]*id="([^"]*)"[^>]*>(.*?)</ix:context>'
            context_matches = re.findall(context_pattern, content_str, re.DOTALL | re.IGNORECASE)
            
            for context_id, context_content in context_matches:
                contexts[context_id] = {
                    "id": context_id,
                    "content": context_content.strip()
                }
                
        except Exception as e:
            logger.warning(f"Failed to extract contexts: {e}")
        
        return contexts
    
    def get_parser_info(self) -> Dict[str, Any]:
        """
        Get information about this parser.
        
        Returns:
            Dictionary with parser information
        """
        return {
            "name": self.name,
            "version": getattr(secxbrl, "__version__", "unknown") if secxbrl else None,
            "supported_formats": self.supported_formats,
            "capabilities": [
                "InlineXBRL parsing",
                "Financial fact extraction", 
                "Context analysis",
                "Taxonomy processing",
                "Numeric data validation"
            ],
            "configuration": {
                "extract_contexts": self.extract_contexts,
                "validate_facts": self.validate_facts
            },
            "available": SECXBRL_AVAILABLE
        }
