"""
Tests for the SGMLParser class.
"""

import pytest
from unittest.mock import Mock, patch

from sec_extractor.parsers.base import ParsingResult, FilingMetadata
from sec_extractor.parsers.sgml_parser import SGMLParser, SECSGML_AVAILABLE


@pytest.mark.skipif(not SECSGML_AVAILABLE, reason="secsgml library not available")
class TestSGMLParser:
    """Test cases for SGMLParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SGMLParser()
    
    def test_parser_initialization(self):
        """Test parser can be initialized with options."""
        parser = SGMLParser(validate_xbrl=False, extract_tables=True)
        assert parser.validate_xbrl == False
        assert parser.extract_tables == True
        assert parser.name == "SGMLParser"
    
    def test_supported_formats(self):
        """Test parser reports correct supported formats."""
        formats = self.parser.supported_formats
        assert "sgml" in formats
        assert "txt" in formats
        assert "sec" in formats
    
    def test_is_compatible_valid_sgml(self, sample_sgml_content):
        """Test compatibility check with valid SGML content."""
        assert self.parser.is_compatible(sample_sgml_content)
    
    def test_is_compatible_invalid_content(self):
        """Test compatibility check with invalid content."""
        invalid_content = "This is just plain text without SGML markers"
        assert not self.parser.is_compatible(invalid_content)
    
    def test_is_compatible_bytes_input(self, sample_sgml_content):
        """Test compatibility check with bytes input."""
        content_bytes = sample_sgml_content.encode('utf-8')
        assert self.parser.is_compatible(content_bytes)
    
    def test_is_compatible_malformed_content(self):
        """Test compatibility check handles malformed content gracefully."""
        malformed = b'\x80\x81\x82'  # Invalid UTF-8
        # Should not crash and should return False
        assert not self.parser.is_compatible(malformed)
    
    @patch('sec_extractor.parsers.sgml_parser.secsgml')
    def test_parse_success(self, mock_secsgml, sample_sgml_content):
        """Test successful SGML parsing."""
        # Mock secsgml.parse_sgml return value
        mock_metadata = {
            "accession_number": "0001193125-24-194739",
            "central_index_key": "0001084380",
            "company_conformed_name": "TIAA-CREF FUNDS",
            "conformed_submission_type": "N-CSR"
        }
        mock_xbrl_content = ["<ix:nonFraction>12345</ix:nonFraction>"]
        mock_secsgml.parse_sgml.return_value = (mock_metadata, mock_xbrl_content)
        
        result = self.parser.parse(sample_sgml_content)
        
        assert isinstance(result, ParsingResult)
        assert result.success
        assert result.parser_name == "SGMLParser"
        assert result.metadata is not None
        assert len(result.xbrl_facts) > 0
        assert result.error_message is None
        
        # Check metadata extraction
        assert result.metadata.accession_number == "0001193125-24-194739"
        assert result.metadata.cik == "0001084380"
        assert result.metadata.company_name == "TIAA-CREF FUNDS"
        assert result.metadata.form_type == "N-CSR"
    
    @patch('sec_extractor.parsers.sgml_parser.secsgml')
    def test_parse_secsgml_error(self, mock_secsgml, sample_sgml_content):
        """Test parsing handles secsgml errors gracefully."""
        mock_secsgml.parse_sgml.side_effect = Exception("Parse error")
        
        result = self.parser.parse(sample_sgml_content)
        
        assert isinstance(result, ParsingResult)
        assert not result.success
        assert result.parser_name == "SGMLParser"
        assert "Parse error" in result.error_message
        assert result.metadata is None
        assert len(result.xbrl_facts) == 0
    
    @patch('sec_extractor.parsers.sgml_parser.secsgml')
    def test_parse_unexpected_format(self, mock_secsgml, sample_sgml_content):
        """Test parsing handles unexpected secsgml return format."""
        # Return unexpected format instead of tuple
        mock_secsgml.parse_sgml.return_value = "unexpected"
        
        result = self.parser.parse(sample_sgml_content)
        
        assert not result.success
        assert "Unexpected secsgml result format" in result.error_message
    
    def test_parse_incompatible_content(self):
        """Test parsing rejects incompatible content."""
        invalid_content = "This is not SGML content"
        
        result = self.parser.parse(invalid_content)
        
        assert not result.success
        assert "does not appear to be SEC SGML format" in result.error_message
    
    def test_parse_file_success(self, temp_filing_file):
        """Test successful file parsing."""
        with patch.object(self.parser, 'parse') as mock_parse:
            mock_result = ParsingResult(
                metadata=None, xbrl_facts=[], success=True, 
                parser_name="SGMLParser", raw_data=None, error_message=None
            )
            mock_parse.return_value = mock_result
            
            result = self.parser.parse_file(temp_filing_file)
            
            assert result.success
            mock_parse.assert_called_once()
    
    def test_parse_file_not_found(self):
        """Test file parsing handles missing files."""
        result = self.parser.parse_file("/nonexistent/file.txt")
        
        assert not result.success
        assert "File not found" in result.error_message
    
    def test_get_parser_info(self):
        """Test parser info retrieval."""
        info = self.parser.get_parser_info()
        
        assert info["name"] == "SGMLParser"
        assert "SEC SGML parsing" in info["capabilities"]
        assert info["available"] == SECSGML_AVAILABLE
        assert "supported_formats" in info
        assert "configuration" in info


@pytest.mark.skipif(SECSGML_AVAILABLE, reason="Test for missing secsgml library")
class TestSGMLParserUnavailable:
    """Test behavior when secsgml library is not available."""
    
    def test_initialization_fails(self):
        """Test parser initialization fails when secsgml unavailable."""
        with pytest.raises(ImportError) as exc_info:
            SGMLParser()
        assert "secsgml library is not available" in str(exc_info.value)


class TestSGMLParserMetadataExtraction:
    """Test metadata extraction functionality."""
    
    @pytest.mark.skipif(not SECSGML_AVAILABLE, reason="secsgml library not available")
    def test_extract_metadata_complete(self):
        """Test metadata extraction with complete data."""
        parser = SGMLParser()
        
        metadata_dict = {
            "accession_number": "0001193125-24-194739",
            "central_index_key": "0001084380",
            "company_conformed_name": "TIAA-CREF FUNDS",
            "conformed_submission_type": "N-CSR",
            "filed_as_of_date": "20240731",
            "conformed_period_of_report": "20240531",
            "standard_industrial_classification": "Investment Company",
            "state_of_incorporation": "MA",
            "fiscal_year_end": "0531"
        }
        
        result = parser._extract_metadata(metadata_dict)
        
        assert isinstance(result, FilingMetadata)
        assert result.accession_number == "0001193125-24-194739"
        assert result.cik == "0001084380"
        assert result.company_name == "TIAA-CREF FUNDS"
        assert result.form_type == "N-CSR"
        assert result.filing_date == "20240731"
        assert result.period_of_report == "20240531"
    
    @pytest.mark.skipif(not SECSGML_AVAILABLE, reason="secsgml library not available")
    def test_extract_metadata_minimal(self):
        """Test metadata extraction with minimal data."""
        parser = SGMLParser()
        
        metadata_dict = {
            "accession_number": "0001234567-24-123456"
        }
        
        result = parser._extract_metadata(metadata_dict)
        
        assert isinstance(result, FilingMetadata)
        assert result.accession_number == "0001234567-24-123456"
        assert result.cik is None
        assert result.company_name is None
    
    @pytest.mark.skipif(not SECSGML_AVAILABLE, reason="secsgml library not available")
    def test_extract_metadata_error_handling(self):
        """Test metadata extraction handles errors gracefully."""
        parser = SGMLParser()
        
        # Pass invalid data type
        result = parser._extract_metadata("not a dict")
        
        assert result is None
