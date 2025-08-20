"""
Test configuration and fixtures for parser tests.
"""

import pytest
import os
from pathlib import Path

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "fixtures"

# Sample SEC filing content for testing
SAMPLE_SGML_CONTENT = '''<SEC-DOCUMENT>0001193125-24-194739.txt : 20240731
<SEC-HEADER>0001193125-24-194739.hdr.sgml : 20240731
<ACCEPTANCE-DATETIME>20240731172538
ACCESSION-NUMBER:		0001193125-24-194739
CONFORMED-SUBMISSION-TYPE:	N-CSR
PUBLIC-DOCUMENT-COUNT:		1
CONFORMED-PERIOD-OF-REPORT:	20240531
FILED-AS-OF-DATE:		20240731
DATE-AS-OF-CHANGE:		20240731

FILER:
	COMPANY-DATA:
		COMPANY-CONFORMED-NAME:			TIAA-CREF FUNDS
		CENTRAL-INDEX-KEY:			0001084380
		STANDARD-INDUSTRIAL-CLASSIFICATION:	UNKNOWN SIC - 0000 [0000]
		IRS-NUMBER:				13-3985595
		STATE-OF-INCORPORATION:			MA
		FISCAL-YEAR-END:			0531

	FILING-VALUES:
		FORM-TYPE:		N-CSR
		SEC-ACT:		1940 Act
		SEC-FILE-NUMBER:	811-05632
		FILM-NUMBER:		241123734
</SEC-HEADER>

<DOCUMENT>
<TYPE>N-CSR
<SEQUENCE>1
<FILENAME>g33432gncsr.htm
<DESCRIPTION>N-CSR
<TEXT>
<?xml version='1.0' encoding='ASCII'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<head>
<title>N-CSR</title>
</head>
<body>
<ix:hidden>
<ix:nonFraction id="test_fact_1" name="oef:AcctVal" contextRef="test_context" unitRef="USD" decimals="INF" scale="0">12345</ix:nonFraction>
</ix:hidden>
</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>'''

SAMPLE_XBRL_INLINE = '''<?xml version='1.0' encoding='ASCII'?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL">
<head><title>Test XBRL</title></head>
<body>
<ix:hidden>
<ix:nonFraction id="fact1" name="oef:AcctVal" contextRef="ctx1" unitRef="USD" decimals="INF" scale="0">10000</ix:nonFraction>
<ix:nonFraction id="fact2" name="oef:PctOfTotalInv" contextRef="ctx2" unitRef="pure" decimals="4" scale="-2">25.5</ix:nonFraction>
</ix:hidden>
</body>
</html>'''

@pytest.fixture
def sample_sgml_content():
    """Provide sample SGML content for testing."""
    return SAMPLE_SGML_CONTENT

@pytest.fixture  
def sample_xbrl_content():
    """Provide sample XBRL content for testing."""
    return SAMPLE_XBRL_INLINE

@pytest.fixture
def temp_filing_file(tmp_path):
    """Create a temporary filing file for testing."""
    filing_file = tmp_path / "test_filing.txt"
    filing_file.write_text(SAMPLE_SGML_CONTENT)
    return filing_file

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    class MockHTTPClient:
        def get_text(self, url, retries=3):
            return SAMPLE_SGML_CONTENT
    
    return MockHTTPClient()

# Test fixtures directory setup
def ensure_test_fixtures():
    """Ensure test fixtures directory exists and has sample files."""
    TEST_DATA_DIR.mkdir(exist_ok=True)
    
    # Create sample files if they don't exist
    sample_files = {
        "sample_n_csr.txt": SAMPLE_SGML_CONTENT,
        "sample_xbrl.xml": SAMPLE_XBRL_INLINE,
        "malformed_filing.txt": "This is not a valid SEC filing format"
    }
    
    for filename, content in sample_files.items():
        file_path = TEST_DATA_DIR / filename
        if not file_path.exists():
            file_path.write_text(content)

# Ensure fixtures exist when module is imported
ensure_test_fixtures()
