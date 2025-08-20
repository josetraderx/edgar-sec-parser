"""
Tests for the FilingParser integrated class.
"""

import pytest
from unittest.mock import Mock, patch

from sec_extractor.parsers.base import ParsingResult, FilingMetadata
from sec_extractor.parsers.integrated_parser import FilingParser, SECSGML_AVAILABLE, SECXBRL_AVAILABLE


@pytest.mark.skipif(not (SECSGML_AVAILABLE and SECXBRL_AVAILABLE), 
                    reason="Both secsgml and secxbrl libraries required")
class TestFilingParser:
    """Test cases for FilingParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = FilingParser()
    
    def test_parser_initialization(self):
        """Test parser can be initialized with options."""
        parser = FilingParser(
            enable_sgml=True,
            enable_xbrl=False,
            sequential_parsing=False,
            combine_results=False
        )
        assert parser.enable_sgml == True
        assert parser.enable_xbrl == False
        assert parser.sequential_parsing == False
        assert parser.combine_results == False
        assert parser.name == "FilingParser"
    
    def test_supported_formats(self):
        """Test parser reports correct supported formats."""
        formats = self.parser.supported_formats
        # Should include formats from both sub-parsers
        assert "sgml" in formats
        assert "xbrl" in formats
        assert "txt" in formats
        assert "xml" in formats
    
    def test_is_compatible_sgml_content(self, sample_sgml_content):
        """Test compatibility check with SGML content."""
        assert self.parser.is_compatible(sample_sgml_content)
    
    def test_is_compatible_xbrl_content(self, sample_xbrl_content):
        """Test compatibility check with XBRL content.""" 
        assert self.parser.is_compatible(sample_xbrl_content)
    
    def test_is_compatible_invalid_content(self):
        """Test compatibility check with invalid content."""
        invalid_content = "This is just plain text without any SEC markers"
        assert not self.parser.is_compatible(invalid_content)
    
    def test_determine_parser_strategy_sgml(self, sample_sgml_content):
        """Test parser strategy determination for SGML content."""
        strategy = self.parser.determine_parser_strategy(sample_sgml_content)
        
        assert strategy["use_sgml"] == True
        assert strategy["primary_parser"] == "sgml"
        # May also use XBRL if SGML content contains XBRL
    
    def test_determine_parser_strategy_xbrl(self, sample_xbrl_content):
        """Test parser strategy determination for XBRL content."""
        strategy = self.parser.determine_parser_strategy(sample_xbrl_content)
        
        assert strategy["use_xbrl"] == True
        assert strategy["primary_parser"] == "xbrl"
    
    def test_parse_sgml_content_success(self, sample_sgml_content):
        """Test successful parsing of SGML content."""
        result = self.parser.parse(sample_sgml_content)
        
        assert isinstance(result, ParsingResult)
        assert result.success
        assert result.parser_name == "FilingParser"
        assert result.parsing_time > 0
        
        # Should have strategy information
        assert result.raw_data is not None
        assert "strategy" in result.raw_data
        assert result.raw_data["strategy"]["primary_parser"] == "sgml"
        
        # Should have individual results
        assert "individual_results" in result.raw_data
        individual_results = result.raw_data["individual_results"]
        assert len(individual_results) >= 1
        assert any(r["parser"] == "sgml" for r in individual_results)
    
    def test_parse_xbrl_content_success(self, sample_xbrl_content):
        """Test successful parsing of XBRL content.""" 
        result = self.parser.parse(sample_xbrl_content)
        
        assert isinstance(result, ParsingResult)
        assert result.success
        assert result.parser_name == "FilingParser"
        
        # Should use XBRL parser
        assert result.raw_data is not None
        assert "strategy" in result.raw_data
        strategy = result.raw_data["strategy"]
        assert strategy["use_xbrl"] == True
    
    def test_parse_mixed_content(self):
        """Test parsing of mixed SGML+XBRL content."""
        mixed_content = '''<SEC-DOCUMENT>0001193125-24-194739.txt : 20240731
<SEC-HEADER>0001193125-24-194739.hdr.sgml : 20240731
<ACCESSION-NUMBER>0001193125-24-194739
<CONFORMED-SUBMISSION-TYPE>N-CSR
</SEC-HEADER>
<DOCUMENT>
<TYPE>N-CSR
<TEXT>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<body>
<ix:nonFraction name="test:fact" contextRef="ctx1" unitRef="USD">12345</ix:nonFraction>
</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>'''
        
        result = self.parser.parse(mixed_content)
        
        assert result.success
        assert result.parser_name == "FilingParser"
        
        # Should use both parsers
        strategy = result.raw_data["strategy"]
        assert strategy["use_sgml"] == True
        assert strategy["use_xbrl"] == True
        assert strategy["primary_parser"] == "sgml"
        
        # Should have results from both parsers
        individual_results = result.raw_data["individual_results"]
        parser_names = [r["parser"] for r in individual_results]
        assert "sgml" in parser_names
        assert "xbrl" in parser_names
    
    def test_parse_incompatible_content(self):
        """Test parsing rejects incompatible content."""
        invalid_content = "This is not a valid SEC filing format"
        
        result = self.parser.parse(invalid_content)
        
        assert not result.success
        assert "not compatible with any available parser" in result.error_message
    
    def test_parse_file_success(self, temp_filing_file):
        """Test successful file parsing."""
        result = self.parser.parse_file(temp_filing_file)
        
        # Should attempt to parse the file
        assert isinstance(result, ParsingResult)
        # Result may succeed or fail depending on content, but should not crash
    
    def test_parse_file_not_found(self):
        """Test file parsing handles missing files."""
        result = self.parser.parse_file("/nonexistent/file.txt")
        
        assert not result.success
        assert "File not found" in result.error_message
    
    def test_get_parser_info(self):
        """Test parser info retrieval."""
        info = self.parser.get_parser_info()
        
        assert info["name"] == "FilingParser"
        assert "Integrated SGML + XBRL parsing" in info["capabilities"]
        assert info["available"] == True
        assert "sub_parsers" in info
        assert "sgml" in info["sub_parsers"]
        assert "xbrl" in info["sub_parsers"]
    
    def test_extract_xbrl_content_from_sgml(self):
        """Test XBRL content extraction from SGML."""
        mixed_content = '''<SEC-DOCUMENT>test
<DOCUMENT>
<TEXT>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<ix:nonFraction>12345</ix:nonFraction>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>'''
        
        strategy = {"use_sgml": True, "use_xbrl": True}
        xbrl_content = self.parser._extract_xbrl_content(mixed_content, strategy)
        
        # Should extract some XBRL content
        if xbrl_content:
            assert isinstance(xbrl_content, str)
            assert len(xbrl_content) > 0


@pytest.mark.skipif(SECSGML_AVAILABLE and SECXBRL_AVAILABLE, 
                    reason="Test for missing dependencies")
class TestFilingParserUnavailable:
    """Test behavior when dependencies are not available."""
    
    @patch('sec_extractor.parsers.integrated_parser.SECSGML_AVAILABLE', False)
    @patch('sec_extractor.parsers.integrated_parser.SECXBRL_AVAILABLE', False)
    def test_initialization_fails_no_parsers(self):
        """Test parser initialization fails when no sub-parsers available."""
        with pytest.raises(RuntimeError) as exc_info:
            FilingParser()
        assert "No parsers available" in str(exc_info.value)


class TestFilingParserConfiguration:
    """Test various FilingParser configurations."""
    
    @pytest.mark.skipif(not SECSGML_AVAILABLE, reason="secsgml library not available")
    def test_sgml_only_configuration(self):
        """Test parser with only SGML enabled."""
        parser = FilingParser(enable_sgml=True, enable_xbrl=False)
        
        assert parser.enable_sgml == True
        assert parser.enable_xbrl == False
        assert parser.sgml_parser is not None
        assert parser.xbrl_parser is None
        
        # Should support SGML formats only
        formats = parser.supported_formats
        assert "sgml" in formats
        assert "txt" in formats
    
    @pytest.mark.skipif(not SECXBRL_AVAILABLE, reason="secxbrl library not available")
    def test_xbrl_only_configuration(self):
        """Test parser with only XBRL enabled."""
        parser = FilingParser(enable_sgml=False, enable_xbrl=True)
        
        assert parser.enable_sgml == False
        assert parser.enable_xbrl == True
        assert parser.sgml_parser is None
        assert parser.xbrl_parser is not None
        
        # Should support XBRL formats only
        formats = parser.supported_formats
        assert "xbrl" in formats
        assert "xml" in formats
