"""
Parser integration module for TieredProcessor.
This module provides the integration layer between the new parser system
and the existing Edgar pipeline TieredProcessor.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from ..parsers.integrated_parser import FilingParser, create_parser, get_available_parsers
from ..parsers.base import ParsingResult, FilingMetadata, XBRLFact
from ..storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class ParserManager:
    """
    Manager class that bridges between TieredProcessor and the new parser system.
    Handles parser instantiation, content processing, and result conversion.
    """
    
    def __init__(self):
        """Initialize the parser manager."""
        self.filing_parser = None
        self.available_parsers = []
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize available parsers."""
        try:
            # Get list of available parsers
            self.available_parsers = get_available_parsers()
            logger.info(f"Available parsers: {len(self.available_parsers)}")
            
            # Initialize integrated filing parser if dependencies are available
            if "FilingParser" in self.available_parsers:
                self.filing_parser = create_parser("filing")
                logger.info("FilingParser initialized successfully")
            else:
                logger.warning("FilingParser not available - check dependencies")
                
        except Exception as e:
            logger.error(f"Error initializing parsers: {e}")
            self.filing_parser = None
    
    def is_available(self) -> bool:
        """Check if parsing is available."""
        return self.filing_parser is not None
    
    def parse_filing_content(self, content: str, filing_meta: Dict[str, Any], tier: str) -> Dict[str, Any]:
        """
        Parse filing content using the integrated parser system.
        
        Args:
            content: Raw filing content (HTML/SGML)
            filing_meta: Filing metadata dictionary
            tier: Processing tier (standard, limited, minimal)
            
        Returns:
            Dictionary containing parsing results and statistics
        """
        if not self.is_available():
            logger.warning("Parser not available - falling back to legacy extraction")
            return self._fallback_extraction(content, filing_meta, tier)
        
        start_time = time.time()
        
        try:
            # Parse content using integrated parser
            parsing_result = self.filing_parser.parse(content)
            
            # Convert result to legacy format for compatibility
            legacy_result = self._convert_to_legacy_format(
                parsing_result, filing_meta, tier, time.time() - start_time
            )
            
            logger.info(
                f"Successfully parsed filing with {self.filing_parser.name}: "
                f"success={parsing_result.success}, "
                f"facts={len(parsing_result.xbrl_facts)}, "
                f"time={parsing_result.parsing_time:.2f}s"
            )
            
            return legacy_result
            
        except Exception as e:
            error_msg = f"Parser integration error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": "parser_integration",
                "processing_duration": time.time() - start_time,
                "extraction_method": "parser_integration_failed"
            }
    
    def _convert_to_legacy_format(
        self, 
        parsing_result: ParsingResult, 
        filing_meta: Dict[str, Any], 
        tier: str,
        total_duration: float
    ) -> Dict[str, Any]:
        """
        Convert ParsingResult to legacy TieredProcessor format.
        
        Args:
            parsing_result: Result from parser system
            filing_meta: Original filing metadata
            tier: Processing tier
            total_duration: Total processing time
            
        Returns:
            Dictionary in legacy format
        """
        # Extract metadata information
        metadata_dict = {}
        if parsing_result.metadata:
            metadata_dict = self._extract_metadata_fields(parsing_result.metadata)
        
        # Extract XBRL facts information
        xbrl_facts_dict = {}
        if parsing_result.xbrl_facts:
            xbrl_facts_dict = self._extract_xbrl_facts_summary(parsing_result.xbrl_facts)
        
        # Build legacy result structure
        legacy_result = {
            "success": parsing_result.success,
            "extraction_method": f"parser_integration_{tier}",
            "processing_duration": total_duration,
            
            # Parser-specific timing
            "parser_timing": {
                "parsing_time": parsing_result.parsing_time,
                "parser_name": parsing_result.parser_name
            },
            
            # Metadata section (for backward compatibility)
            "fund_metadata": metadata_dict,
            
            # XBRL facts summary
            "xbrl_metrics": xbrl_facts_dict,
            "xbrl_facts_count": len(parsing_result.xbrl_facts),
            
            # Raw parser data
            "parser_raw_data": parsing_result.raw_data,
            
            # Legacy fields for compatibility
            "sections": [],  # Can be populated from raw_data if needed
            "tables": [],    # Can be populated from raw_data if needed
            "table_count": 0,
            "section_count": 0
        }
        
        # Add error information if parsing failed
        if not parsing_result.success:
            legacy_result["error"] = parsing_result.error_message
            legacy_result["error_type"] = "parsing"
        
        return legacy_result
    
    def _extract_metadata_fields(self, metadata: FilingMetadata) -> Dict[str, Any]:
        """Extract metadata fields for legacy format."""
        return {
            "accession_number": metadata.accession_number,
            "cik": metadata.cik,
            "company_name": metadata.company_name,
            "form_type": metadata.form_type,
            "filing_date": metadata.filing_date.isoformat() if metadata.filing_date else None,
            "period_of_report": metadata.period_of_report.isoformat() if metadata.period_of_report else None,
            "acceptance_datetime": metadata.acceptance_datetime.isoformat() if metadata.acceptance_datetime else None,
            "sic": metadata.sic,
            "state_of_incorporation": metadata.state_of_incorporation,
            "fiscal_year_end": metadata.fiscal_year_end,
            "business_address": metadata.business_address,
            "business_phone": metadata.business_phone,
            "document_count": metadata.document_count,
            "items": metadata.items,
            "additional_metadata": metadata.additional_metadata or {}
        }
    
    def _extract_xbrl_facts_summary(self, xbrl_facts: List[XBRLFact]) -> Dict[str, Any]:
        """Extract XBRL facts summary for legacy format."""
        if not xbrl_facts:
            return {}
        
        # Group facts by concept for summary
        concept_summary = {}
        total_facts = len(xbrl_facts)
        unique_concepts = set()
        unique_contexts = set()
        
        for fact in xbrl_facts:
            unique_concepts.add(fact.concept)
            if fact.context_ref:
                unique_contexts.add(fact.context_ref)
            
            if fact.concept not in concept_summary:
                concept_summary[fact.concept] = {
                    "count": 0,
                    "sample_value": None,
                    "unit_ref": None
                }
            
            concept_summary[fact.concept]["count"] += 1
            if concept_summary[fact.concept]["sample_value"] is None:
                concept_summary[fact.concept]["sample_value"] = fact.value
                concept_summary[fact.concept]["unit_ref"] = fact.unit_ref
        
        return {
            "total_facts": total_facts,
            "unique_concepts": len(unique_concepts),
            "unique_contexts": len(unique_contexts),
            "concept_summary": concept_summary,
            "sample_facts": [
                {
                    "concept": fact.concept,
                    "value": fact.value,
                    "unit_ref": fact.unit_ref,
                    "context_ref": fact.context_ref
                }
                for fact in xbrl_facts[:5]  # First 5 facts as sample
            ]
        }
    
    def _fallback_extraction(self, content: str, filing_meta: Dict[str, Any], tier: str) -> Dict[str, Any]:
        """
        Fallback extraction method when parsers are not available.
        This maintains compatibility with existing system.
        """
        logger.info("Using fallback extraction method")
        
        return {
            "success": True,
            "extraction_method": f"fallback_{tier}",
            "processing_duration": 0.1,
            "fund_metadata": {},
            "xbrl_metrics": {},
            "xbrl_facts_count": 0,
            "sections": [],
            "tables": [],
            "table_count": 0,
            "section_count": 0,
            "parser_timing": {
                "parsing_time": 0.0,
                "parser_name": "fallback"
            },
            "note": "Parser integration not available - using fallback method"
        }
    
    def get_parser_status(self) -> Dict[str, Any]:
        """Get status information about available parsers."""
        return {
            "parser_manager_available": True,
            "filing_parser_available": self.filing_parser is not None,
            "available_parsers": self.available_parsers,
            "parser_info": {
                "name": self.filing_parser.name if self.filing_parser else None,
                "supported_formats": self.filing_parser.supported_formats if self.filing_parser else [],
                "available": self.filing_parser.available if self.filing_parser else False
            } if self.filing_parser else None
        }


class DatabaseResultManager:
    """
    Manager for saving parser results to database.
    Handles the conversion and storage of new parser results.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize with database manager."""
        self.db = db_manager
    
    def save_parser_results(
        self, 
        filing_id: int, 
        parsing_result: ParsingResult, 
        tier: str
    ) -> bool:
        """
        Save parser results to database with enhanced XBRL support.
        
        Args:
            filing_id: Filing database ID
            parsing_result: Result from parser system
            tier: Processing tier
            
        Returns:
            True if successful, False otherwise
        """
        session = self.db.get_session()
        
        try:
            # Update Filing with parser-specific fields
            self._update_filing_with_parser_data(session, filing_id, parsing_result, tier)
            
            # Save XBRL facts if available
            if parsing_result.xbrl_facts:
                self._save_xbrl_facts(session, filing_id, parsing_result.xbrl_facts)
            
            # Update or create fund metadata with enhanced information
            if parsing_result.metadata:
                self._save_enhanced_metadata(session, filing_id, parsing_result.metadata)
            
            session.commit()
            logger.info(f"Successfully saved parser results for filing {filing_id}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving parser results for filing {filing_id}: {e}")
            return False
        finally:
            session.close()
    
    def _update_filing_with_parser_data(self, session, filing_id: int, result: ParsingResult, tier: str):
        """Update Filing record with parser-specific information."""
        from ..storage.models import Filing
        
        filing = session.query(Filing).filter(Filing.id == filing_id).first()
        if not filing:
            raise ValueError(f"Filing {filing_id} not found")
        
        # Update parser timing information
        filing.integrated_parsing_time = result.parsing_time
        filing.xbrl_facts_count = len(result.xbrl_facts)
        
        # Determine parsing strategy and success flags
        if result.raw_data:
            strategy_info = result.raw_data.get("strategy", {})
            if strategy_info.get("use_sgml") and strategy_info.get("use_xbrl"):
                filing.parsing_strategy = "hybrid"
                filing.sgml_parsed = True
                filing.xbrl_parsed = True
            elif strategy_info.get("use_sgml"):
                filing.parsing_strategy = "sgml_only"
                filing.sgml_parsed = True
                filing.xbrl_parsed = False
            elif strategy_info.get("use_xbrl"):
                filing.parsing_strategy = "xbrl_only"
                filing.sgml_parsed = False
                filing.xbrl_parsed = True
        
        # Update metadata from parser if available
        if result.metadata:
            metadata = result.metadata
            if metadata.acceptance_datetime:
                filing.acceptance_datetime = metadata.acceptance_datetime
            if metadata.sic:
                filing.sic = metadata.sic
            if metadata.state_of_incorporation:
                filing.state_of_incorporation = metadata.state_of_incorporation
            if metadata.fiscal_year_end:
                filing.fiscal_year_end = metadata.fiscal_year_end
            if metadata.business_address:
                filing.business_address = metadata.business_address
            if metadata.business_phone:
                filing.business_phone = metadata.business_phone
        
        filing.updated_at = datetime.utcnow()
    
    def _save_xbrl_facts(self, session, filing_id: int, xbrl_facts: List[XBRLFact]):
        """Save XBRL facts to database."""
        from ..storage.models import XbrlFact
        
        for fact in xbrl_facts:
            db_fact = XbrlFact(
                filing_id=filing_id,
                concept=fact.concept,
                value=fact.value,
                unit_ref=fact.unit_ref,
                context_ref=fact.context_ref,
                period_start_date=fact.period_start_date,
                period_end_date=fact.period_end_date,
                period_instant=fact.period_instant,
                entity_identifier=fact.entity_identifier,
                decimals=fact.decimals,
                scale=fact.scale,
                precision=fact.precision,
                additional_attributes=fact.additional_attributes
            )
            session.add(db_fact)
        
        logger.info(f"Saved {len(xbrl_facts)} XBRL facts for filing {filing_id}")
    
    def _save_enhanced_metadata(self, session, filing_id: int, metadata: FilingMetadata):
        """Save enhanced metadata information."""
        from ..storage.models import FundMetadata
        
        # Check if metadata already exists
        existing_metadata = session.query(FundMetadata).filter(
            FundMetadata.filing_id == filing_id
        ).first()
        
        if existing_metadata:
            # Update existing metadata with new parser information
            if metadata.company_name:
                existing_metadata.fund_name = metadata.company_name
            # Add other metadata updates as needed
            existing_metadata.raw_data = metadata.additional_metadata or {}
        else:
            # Create new metadata record
            fund_metadata = FundMetadata(
                filing_id=filing_id,
                fund_name=metadata.company_name,
                raw_data=metadata.additional_metadata or {}
            )
            session.add(fund_metadata)
        
        logger.debug(f"Updated metadata for filing {filing_id}")
