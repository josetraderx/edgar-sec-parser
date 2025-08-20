"""
Integrated parser that combines SGML and XBRL parsing capabilities.
This module provides a unified interface for parsing SEC filings that
may contain both SGML structure and XBRL content.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import time

from .base import BaseParser, ParsingResult, FilingMetadata, XBRLFact, ParseError, safe_decode, measure_parsing_time
from .sgml_parser import SGMLParser, SECSGML_AVAILABLE
from .xbrl_parser import XBRLParser, SECXBRL_AVAILABLE

logger = logging.getLogger(__name__)


class FilingParser(BaseParser):
    """
    Integrated parser that combines SGML and XBRL parsing capabilities.
    
    This parser intelligently determines the content type and applies the
    appropriate parsing strategy. It can handle:
    - Pure SGML filings
    - Pure XBRL documents
    - Mixed SGML filings containing XBRL content
    - Sequential parsing with multiple parsers
    """
    
    def __init__(self, 
                 enable_sgml: bool = True,
                 enable_xbrl: bool = True,
                 sequential_parsing: bool = True,
                 combine_results: bool = True):
        """
        Initialize the integrated filing parser.
        
        Args:
            enable_sgml: Whether to enable SGML parsing
            enable_xbrl: Whether to enable XBRL parsing
            sequential_parsing: Whether to try both parsers sequentially
            combine_results: Whether to combine results from multiple parsers
        """
        self.enable_sgml = enable_sgml and SECSGML_AVAILABLE
        self.enable_xbrl = enable_xbrl and SECXBRL_AVAILABLE
        self.sequential_parsing = sequential_parsing
        self.combine_results = combine_results
        
        # Initialize sub-parsers
        self.sgml_parser = SGMLParser() if self.enable_sgml else None
        self.xbrl_parser = XBRLParser() if self.enable_xbrl else None
        
        if not (self.enable_sgml or self.enable_xbrl):
            raise RuntimeError(
                "No parsers available. Install secsgml>=0.3.0 and/or secxbrl>=0.5.0"
            )
    
    @property
    def name(self) -> str:
        """Return parser name."""
        return "FilingParser"
    
    @property
    def supported_formats(self) -> List[str]:
        """Return list of supported formats."""
        formats = []
        if self.sgml_parser:
            formats.extend(self.sgml_parser.supported_formats)
        if self.xbrl_parser:
            formats.extend(self.xbrl_parser.supported_formats)
        return list(set(formats))  # Remove duplicates
    
    @property 
    def available(self) -> bool:
        """Return whether parser is available."""
        return self.enable_sgml or self.enable_xbrl
    
    def is_compatible(self, content: Union[str, bytes]) -> bool:
        """
        Check if content is compatible with any available parser.
        
        Args:
            content: Raw content to check
            
        Returns:
            True if any sub-parser can handle the content
        """
        try:
            if self.sgml_parser and self.sgml_parser.is_compatible(content):
                return True
            if self.xbrl_parser and self.xbrl_parser.is_compatible(content):
                return True
            return False
        except Exception as e:
            logger.debug(f"Error checking compatibility: {e}")
            return False
    
    def determine_parser_strategy(self, content: Union[str, bytes]) -> Dict[str, bool]:
        """
        Determine which parsers should be used for the given content.
        
        Args:
            content: Raw content to analyze
            
        Returns:
            Dictionary with parser usage flags
        """
        strategy = {
            "use_sgml": False,
            "use_xbrl": False,
            "primary_parser": None
        }
        
        if self.sgml_parser and self.sgml_parser.is_compatible(content):
            strategy["use_sgml"] = True
            strategy["primary_parser"] = "sgml"
        
        if self.xbrl_parser and self.xbrl_parser.is_compatible(content):
            strategy["use_xbrl"] = True
            if not strategy["primary_parser"]:
                strategy["primary_parser"] = "xbrl"
        
        return strategy
    
    @measure_parsing_time
    def parse(self, content: Union[str, bytes], **kwargs) -> ParsingResult:
        """
        Parse filing content using appropriate parser(s).
        
        Args:
            content: Raw filing content
            **kwargs: Additional parsing options
            
        Returns:
            ParsingResult with integrated data from all applicable parsers
        """
        try:
            content_str = safe_decode(content)
            
            if not self.is_compatible(content_str):
                raise ParseError("Content is not compatible with any available parser")
            
            # Determine parsing strategy
            strategy = self.determine_parser_strategy(content_str)
            logger.debug(f"Parser strategy: {strategy}")
            
            results = []
            combined_metadata = None
            combined_xbrl_facts = []
            combined_raw_data = {}
            
            # Parse with SGML parser if applicable
            if strategy["use_sgml"] and self.sgml_parser:
                logger.debug("Parsing with SGML parser")
                sgml_result = self.sgml_parser.parse(content_str, **kwargs)
                results.append(("sgml", sgml_result))
                
                if sgml_result.success:
                    if sgml_result.metadata:
                        combined_metadata = sgml_result.metadata
                    combined_xbrl_facts.extend(sgml_result.xbrl_facts)
                    if sgml_result.raw_data:
                        combined_raw_data["sgml"] = sgml_result.raw_data
            
            # Parse with XBRL parser if applicable  
            if strategy["use_xbrl"] and self.xbrl_parser:
                # For SGML content with XBRL, extract XBRL parts first
                xbrl_content = self._extract_xbrl_content(content_str, strategy)
                
                if xbrl_content:
                    logger.debug("Parsing extracted XBRL content")
                    xbrl_result = self.xbrl_parser.parse(xbrl_content, **kwargs)
                    results.append(("xbrl", xbrl_result))
                    
                    if xbrl_result.success:
                        # Merge metadata (SGML takes precedence)
                        if not combined_metadata and xbrl_result.metadata:
                            combined_metadata = xbrl_result.metadata
                        combined_xbrl_facts.extend(xbrl_result.xbrl_facts)
                        if xbrl_result.raw_data:
                            combined_raw_data["xbrl"] = xbrl_result.raw_data
            
            # Determine overall success
            success = any(result.success for _, result in results)
            
            # Collect errors from failed parsers
            errors = [result.error_message for _, result in results if not result.success]
            error_message = "; ".join(errors) if errors else None
            
            # Create combined result
            parsing_result = ParsingResult(
                success=success,
                parser_name=self.name,
                metadata=combined_metadata,
                xbrl_facts=combined_xbrl_facts,
                raw_data={
                    "strategy": strategy,
                    "parser_results": combined_raw_data,
                    "individual_results": [
                        {"parser": parser_name, "success": result.success, "facts_count": len(result.xbrl_facts)}
                        for parser_name, result in results
                    ]
                },
                error_message=error_message,
                parsing_time=0.0  # Will be set by decorator
            )
            
            logger.info(
                f"Integrated parsing completed: {len(combined_xbrl_facts)} total facts from "
                f"{len([r for _, r in results if r.success])} successful parsers"
            )
            
            return parsing_result
            
        except Exception as e:
            error_msg = f"Integrated parsing failed: {str(e)}"
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
    
    def _extract_xbrl_content(self, content: str, strategy: Dict[str, bool]) -> Optional[str]:
        """
        Extract XBRL content from mixed SGML/XBRL filing.
        
        Args:
            content: Full filing content
            strategy: Parsing strategy
            
        Returns:
            Extracted XBRL content or None
        """
        try:
            # If SGML parser was used and found XBRL content
            if strategy["use_sgml"] and self.sgml_parser:
                # Parse with SGML to get XBRL content
                sgml_result = self.sgml_parser.parse(content)
                if sgml_result.success and sgml_result.raw_data:
                    xbrl_content_list = sgml_result.raw_data.get("xbrl_content", [])
                    if xbrl_content_list:
                        # Join XBRL content pieces
                        return "\n".join(safe_decode(item) for item in xbrl_content_list)
            
            # If content appears to be pure XBRL
            if strategy["use_xbrl"] and not strategy["use_sgml"]:
                return content
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract XBRL content: {e}")
            return None
    
    def parse_file(self, file_path: Union[str, Path], **kwargs) -> ParsingResult:
        """
        Parse filing file from disk.
        
        Args:
            file_path: Path to the filing file
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
        Get information about this integrated parser.
        
        Returns:
            Dictionary with parser information
        """
        sub_parsers = {}
        if self.sgml_parser:
            sub_parsers["sgml"] = self.sgml_parser.get_parser_info()
        if self.xbrl_parser:
            sub_parsers["xbrl"] = self.xbrl_parser.get_parser_info()
        
        return {
            "name": self.name,
            "version": "1.0.0",
            "supported_formats": self.supported_formats,
            "capabilities": [
                "Integrated SGML + XBRL parsing",
                "Intelligent content detection",
                "Sequential parser execution",
                "Result combination and merging",
                "Comprehensive error handling"
            ],
            "configuration": {
                "enable_sgml": self.enable_sgml,
                "enable_xbrl": self.enable_xbrl,
                "sequential_parsing": self.sequential_parsing,
                "combine_results": self.combine_results
            },
            "sub_parsers": sub_parsers,
            "available": self.available
        }


# Factory functions for parser integration

def create_parser(parser_type: str, **kwargs) -> Optional[BaseParser]:
    """
    Factory function to create parser instances.
    
    Args:
        parser_type: Type of parser ("sgml", "xbrl", "filing")
        **kwargs: Additional arguments for parser initialization
        
    Returns:
        Parser instance or None if not available
    """
    parser_type = parser_type.lower()
    
    try:
        if parser_type in ["sgml", "sgmlparser"]:
            if SECSGML_AVAILABLE:
                return SGMLParser(**kwargs)
            else:
                logger.warning("SGML parser requested but secsgml not available")
                return None
                
        elif parser_type in ["xbrl", "xbrlparser"]:
            if SECXBRL_AVAILABLE:
                return XBRLParser(**kwargs)
            else:
                logger.warning("XBRL parser requested but secxbrl not available")
                return None
                
        elif parser_type in ["filing", "filingparser", "integrated"]:
            return FilingParser(**kwargs)
            
        else:
            logger.error(f"Unknown parser type: {parser_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating parser {parser_type}: {e}")
        return None


def get_available_parsers() -> List[str]:
    """
    Get list of available parser types.
    
    Returns:
        List of available parser names
    """
    available = []
    
    # Check SGML parser
    if SECSGML_AVAILABLE:
        available.append("SGMLParser")
    
    # Check XBRL parser  
    if SECXBRL_AVAILABLE:
        available.append("XBRLParser")
    
    # FilingParser is always available (uses fallbacks)
    available.append("FilingParser")
    
    return available


def get_parser_info() -> Dict[str, Any]:
    """
    Get detailed information about all available parsers.
    
    Returns:
        Dictionary with parser information
    """
    info = {
        "available_parsers": get_available_parsers(),
        "dependencies": {
            "secsgml": SECSGML_AVAILABLE,
            "secxbrl": SECXBRL_AVAILABLE
        },
        "parser_details": {}
    }
    
    # Get info for each available parser
    for parser_name in info["available_parsers"]:
        try:
            if parser_name == "SGMLParser" and SECSGML_AVAILABLE:
                parser = SGMLParser()
                info["parser_details"]["SGMLParser"] = parser.get_parser_info()
                
            elif parser_name == "XBRLParser" and SECXBRL_AVAILABLE:
                parser = XBRLParser()
                info["parser_details"]["XBRLParser"] = parser.get_parser_info()
                
            elif parser_name == "FilingParser":
                parser = FilingParser()
                info["parser_details"]["FilingParser"] = parser.get_parser_info()
                
        except Exception as e:
            logger.warning(f"Error getting info for {parser_name}: {e}")
    
    return info
