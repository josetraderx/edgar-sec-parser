#!/usr/bin/env python3
"""
Fase 4: Performance & Validation Tests (Sin Base de Datos)
Tests enfocados en validar performance y funcionalidad de parsers sin requerir BD.
"""

import sys
import os
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import json
import gc

# Add project root to path
sys.path.insert(0, os.getcwd())

from sec_extractor.core.parser_integration import ParserManager
from sec_extractor.parsers.integrated_parser import create_parser, get_available_parsers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParserPerformanceTests:
    """
    Suite de tests de performance y validación para el sistema de parsers.
    """
    
    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
        self.parser_manager = None
        
    def setup(self):
        """Configurar el entorno de testing."""
        logger.info("=== Setting up Parser Performance Tests ===")
        
        try:
            # Initialize ParserManager
            self.parser_manager = ParserManager()
            logger.info("✓ ParserManager initialized")
            
            # Check available parsers
            available = get_available_parsers()
            logger.info(f"✓ Available parsers: {available}")
            
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}", exc_info=True)
            return False
    
    def test_realistic_ncsr_parsing(self) -> bool:
        """Test parsing with realistic N-CSR content."""
        logger.info("--- Testing Realistic N-CSR Parsing ---")
        
        try:
            # Realistic N-CSR content based on actual filing structure
            ncsr_content = """
<SEC-DOCUMENT>
<SEC-HEADER>
ACCESSION-NUMBER:		0001193125-24-194739
CONFORMED-SUBMISSION-TYPE:	N-CSR
PUBLIC-DOCUMENT-COUNT:		1
CONFORMED-PERIOD-OF-REPORT:	20240630
FILED-AS-OF-DATE:		20240829
DATE-AS-OF-CHANGE:		20240829

FILER:
	COMPANY-DATA:
		COMPANY-CONFORMED-NAME:			VANGUARD TOTAL STOCK MARKET ETF
		CENTRAL-INDEX-KEY:			0001232594
		STANDARD-INDUSTRIAL-CLASSIFICATION:	INVESTMENT COMPANIES [6722]
		IRS-NUMBER:				206772904
		STATE-OF-INCORPORATION:			PA
		FISCAL-YEAR-END:			1031

	FILING-VALUES:
		FORM-TYPE:		N-CSR
		SEC-ACT:		1940 Act
		SEC-FILE-NUMBER:	811-21253
		FILM-NUMBER:		241191574

	BUSINESS-ADDRESS:
		STREET-1:		100 VANGUARD BLVD
		CITY:			MALVERN
		STATE:			PA
		ZIP:			19355
		BUSINESS-PHONE:		6106699000

	MAIL-ADDRESS:
		STREET-1:		100 VANGUARD BLVD
		CITY:			MALVERN
		STATE:			PA
		ZIP:			19355

</SEC-HEADER>
<DOCUMENT>
<TYPE>N-CSR
<SEQUENCE>1
<FILENAME>vanguard-ncsr-20240630.htm
<DESCRIPTION>ANNUAL REPORT
<TEXT>
<html>
<head>
<title>VANGUARD TOTAL STOCK MARKET ETF - Annual Report</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<style type="text/css">
.fund-name { font-weight: bold; font-size: 18px; color: #1f4e79; }
.financial-data { margin: 10px 0; padding: 5px; }
.holdings-table { border-collapse: collapse; width: 100%; margin: 20px 0; }
.holdings-table th, .holdings-table td { border: 1px solid #ccc; padding: 8px; text-align: left; }
.holdings-table th { background-color: #f2f2f2; font-weight: bold; }
</style>
</head>
<body>

<!-- Fund Header -->
<div class="fund-name">VANGUARD TOTAL STOCK MARKET ETF</div>
<div class="financial-data">Annual Report for the period ended June 30, 2024</div>

<!-- Fund Summary -->
<table class="holdings-table">
<tr><th colspan="2">FUND SUMMARY</th></tr>
<tr><td>Fund Name</td><td>Vanguard Total Stock Market ETF</td></tr>
<tr><td>Ticker Symbol</td><td>VTI</td></tr>
<tr><td>Total Net Assets</td><td><ix:nonFraction contextRef="FundContext" name="invco:NetAssets" unitRef="USD">$345,678,901,234</ix:nonFraction></td></tr>
<tr><td>Net Asset Value per Share</td><td><ix:nonFraction contextRef="FundContext" name="invco:NetAssetValuePerShare" unitRef="USD" decimals="2">$267.45</ix:nonFraction></td></tr>
<tr><td>Shares Outstanding</td><td><ix:nonFraction contextRef="FundContext" name="dei:EntityCommonStockSharesOutstanding" unitRef="shares">1,292,345,678</ix:nonFraction></td></tr>
</table>

<!-- Portfolio Holdings -->
<table class="holdings-table">
<tr><th colspan="5">TOP 25 HOLDINGS (as of June 30, 2024)</th></tr>
<tr>
<th>Security</th>
<th>Shares</th>
<th>Market Value</th>
<th>% of Net Assets</th>
<th>CUSIP</th>
</tr>
<tr>
<td>Microsoft Corp</td>
<td>8,543,891</td>
<td>$24,563,847,123</td>
<td>7.1%</td>
<td>594918104</td>
</tr>
<tr>
<td>Apple Inc</td>
<td>14,321,456</td>
<td>$20,904,567,890</td>
<td>6.0%</td>
<td>037833100</td>
</tr>
<tr>
<td>Amazon.com Inc</td>
<td>1,567,234</td>
<td>$15,109,234,567</td>
<td>4.4%</td>
<td>023135106</td>
</tr>
<tr>
<td>NVIDIA Corp</td>
<td>2,123,456</td>
<td>$13,567,890,123</td>
<td>3.9%</td>
<td>67066G104</td>
</tr>
<tr>
<td>Alphabet Inc Class A</td>
<td>5,789,012</td>
<td>$12,456,789,012</td>
<td>3.6%</td>
<td>02079K305</td>
</tr>
<tr>
<td>Meta Platforms Inc</td>
<td>3,234,567</td>
<td>$11,234,567,890</td>
<td>3.2%</td>
<td>30303M102</td>
</tr>
<tr>
<td>Tesla Inc</td>
<td>4,567,890</td>
<td>$10,123,456,789</td>
<td>2.9%</td>
<td>88160R101</td>
</tr>
</table>

<!-- Financial Performance -->
<div class="financial-data">
<h3>Financial Performance</h3>
<table class="holdings-table">
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Expense Ratio</td><td><ix:nonFraction contextRef="FundContext" name="invco:ExpenseRatio" unitRef="pure" decimals="4">0.0003</ix:nonFraction></td></tr>
<tr><td>Portfolio Turnover Rate</td><td><ix:nonFraction contextRef="FundContext" name="invco:PortfolioTurnoverRate" unitRef="pure" decimals="2">0.04</ix:nonFraction></td></tr>
<tr><td>Total Return (1 Year)</td><td><ix:nonFraction contextRef="FundContext" name="invco:TotalReturn1Yr" unitRef="pure" decimals="4">0.2845</ix:nonFraction></td></tr>
<tr><td>Dividend Yield</td><td><ix:nonFraction contextRef="FundContext" name="invco:DividendYield" unitRef="pure" decimals="4">0.0134</ix:nonFraction></td></tr>
</table>
</div>

<!-- Additional XBRL Hidden Facts -->
<div style="display: none;">
<ix:nonFraction contextRef="FundContext" name="invco:TotalAssets" unitRef="USD">$346,123,456,789</ix:nonFraction>
<ix:nonFraction contextRef="FundContext" name="invco:TotalLiabilities" unitRef="USD">$445,123,456</ix:nonFraction>
<ix:nonFraction contextRef="FundContext" name="invco:CashAndCashEquivalents" unitRef="USD">$2,345,678,901</ix:nonFraction>
<ix:nonFraction contextRef="FundContext" name="invco:NumberOfPortfolioCompanies" unitRef="shares">3847</ix:nonFraction>
<ix:nonFraction contextRef="FundContext" name="invco:AverageMaturity" unitRef="years" decimals="1">8.5</ix:nonFraction>
</div>

<!-- Investment Objectives -->
<div class="financial-data">
<h3>Investment Objective</h3>
<p>The Fund seeks to track the performance of the CRSP US Total Market Index,
which measures the investment return of the overall stock market.</p>

<h3>Investment Strategy</h3>
<p>The Fund employs an indexing investment approach designed to track the performance
of the CRSP US Total Market Index. The Fund attempts to replicate the target index by
investing all, or substantially all, of its assets in the stocks that make up the index.</p>
</div>

</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
            """
            
            filing_meta = {
                "accession_number": "0001193125-24-194739",
                "cik": "0001232594",
                "company_name": "VANGUARD TOTAL STOCK MARKET ETF",
                "form_type": "N-CSR"
            }
            
            # Test with ParserManager
            start_time = time.time()
            
            result = self.parser_manager.parse_filing_content(
                ncsr_content, filing_meta, "standard"
            )
            
            parsing_time = time.time() - start_time
            
            # Analyze results
            success = result.get("success", False)
            extraction_method = result.get("extraction_method", "unknown")
            xbrl_facts_count = result.get("xbrl_facts_count", 0)
            
            logger.info(f"✓ Parsing success: {success}")
            logger.info(f"✓ Extraction method: {extraction_method}")
            logger.info(f"✓ Parsing time: {parsing_time:.3f}s")
            logger.info(f"✓ XBRL facts extracted: {xbrl_facts_count}")
            
            # Check for expected content
            if result.get("fund_metadata"):
                logger.info("✓ Fund metadata extracted")
            
            if "parser_timing" in result:
                parser_timing = result["parser_timing"]
                logger.info(f"✓ Parser timing: {parser_timing}")
            
            # Record metrics
            self.performance_metrics["realistic_ncsr"] = {
                "success": success,
                "parsing_time": parsing_time,
                "content_size": len(ncsr_content),
                "xbrl_facts_count": xbrl_facts_count,
                "extraction_method": extraction_method,
                "throughput_kb_per_sec": (len(ncsr_content) / 1024) / parsing_time if parsing_time > 0 else 0
            }
            
            self.test_results.append({
                "test": "realistic_ncsr_parsing",
                "success": success,
                "details": f"Parsed {len(ncsr_content)} chars in {parsing_time:.3f}s"
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Realistic N-CSR test failed: {e}", exc_info=True)
            self.test_results.append({
                "test": "realistic_ncsr_parsing",
                "success": False,
                "details": str(e)
            })
            return False
    
    def test_performance_scalability(self) -> bool:
        """Test performance with different content sizes."""
        logger.info("--- Testing Performance Scalability ---")
        
        try:
            # Create base SGML template
            base_template = """
<SEC-DOCUMENT>
<SEC-HEADER>
ACCESSION-NUMBER: 0000000000-24-{size}
CONFORMED-SUBMISSION-TYPE: N-CSR
PUBLIC-DOCUMENT-COUNT: 1
CONFORMED-PERIOD-OF-REPORT: 20240630
FILED-AS-OF-DATE: 20240829
FILER:
    COMPANY-DATA:
        COMPANY-CONFORMED-NAME: TEST FUND {size}
        CENTRAL-INDEX-KEY: 0001234567
</SEC-HEADER>
<DOCUMENT>
<TYPE>N-CSR
<TEXT>
<html>
<head><title>Test Fund {size}</title></head>
<body>
{content}
</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
            """
            
            # Test different sizes
            size_tests = [
                ("small", 1024, 10),       # 1KB, 10 holdings
                ("medium", 51200, 100),    # 50KB, 100 holdings 
                ("large", 512000, 500),    # 500KB, 500 holdings
                ("xlarge", 1048576, 1000)  # 1MB, 1000 holdings
            ]
            
            scalability_results = {}
            
            for size_name, target_bytes, num_holdings in size_tests:
                logger.info(f"Testing {size_name} content (~{target_bytes/1024:.0f}KB)...")
                
                # Generate holdings table
                holdings_content = """
                <table>
                <tr><th>Security</th><th>Shares</th><th>Value</th><th>% Assets</th></tr>
                """
                
                for i in range(num_holdings):
                    holdings_content += f"""
                    <tr>
                    <td>Security {i+1:04d}</td>
                    <td>{1000000 + i * 1000:,}</td>
                    <td><ix:nonFraction contextRef="ctx{i}" name="test:MarketValue" unitRef="USD">${50000000 + i * 10000:,}</ix:nonFraction></td>
                    <td>{0.1 + i * 0.001:.3f}%</td>
                    </tr>
                    """
                
                holdings_content += "</table>"
                
                # Pad to target size if needed
                content_so_far = base_template.format(size=size_name, content=holdings_content)
                current_size = len(content_so_far)
                
                if current_size < target_bytes:
                    padding = "<!-- " + "x" * (target_bytes - current_size - 10) + " -->"
                    final_content = base_template.format(
                        size=size_name, 
                        content=holdings_content + padding
                    )
                else:
                    final_content = content_so_far
                
                # Measure performance
                filing_meta = {
                    "accession_number": f"test-{size_name}",
                    "file_size_mb": len(final_content) / (1024 * 1024)
                }
                
                # Force garbage collection before test
                gc.collect()
                
                start_time = time.time()
                memory_before = self._get_memory_usage()
                
                result = self.parser_manager.parse_filing_content(
                    final_content, filing_meta, "standard"
                )
                
                end_time = time.time()
                memory_after = self._get_memory_usage()
                
                processing_time = end_time - start_time
                memory_used = memory_after - memory_before
                throughput_mb_per_sec = (len(final_content) / (1024 * 1024)) / processing_time if processing_time > 0 else 0
                
                scalability_results[size_name] = {
                    "content_size_bytes": len(final_content),
                    "content_size_mb": len(final_content) / (1024 * 1024),
                    "num_holdings": num_holdings,
                    "processing_time": processing_time,
                    "memory_used_mb": memory_used,
                    "throughput_mb_per_sec": throughput_mb_per_sec,
                    "success": result.get("success", False),
                    "xbrl_facts": result.get("xbrl_facts_count", 0)
                }
                
                logger.info(f"  {size_name}: {processing_time:.3f}s, {throughput_mb_per_sec:.2f} MB/s, {memory_used:.1f}MB mem")
            
            self.performance_metrics["scalability"] = scalability_results
            
            # Analyze scalability
            large_perf = scalability_results.get("large", {})
            xlarge_perf = scalability_results.get("xlarge", {})
            
            # Check if performance degrades significantly with size
            scalability_good = True
            if large_perf.get("throughput_mb_per_sec", 0) > 0:
                if xlarge_perf.get("throughput_mb_per_sec", 0) < large_perf["throughput_mb_per_sec"] * 0.5:
                    scalability_good = False
                    logger.warning("⚠ Significant performance degradation with larger files")
            
            self.test_results.append({
                "test": "performance_scalability",
                "success": scalability_good,
                "details": f"Tested {len(size_tests)} size categories"
            })
            
            return scalability_good
            
        except Exception as e:
            logger.error(f"Scalability test failed: {e}", exc_info=True)
            self.test_results.append({
                "test": "performance_scalability",
                "success": False,
                "details": str(e)
            })
            return False
    
    def test_xbrl_fact_extraction(self) -> bool:
        """Test specific XBRL fact extraction capabilities."""
        logger.info("--- Testing XBRL Fact Extraction ---")
        
        try:
            # Content with various XBRL fact types
            xbrl_test_content = """
<SEC-DOCUMENT>
<SEC-HEADER>
ACCESSION-NUMBER: 0000000000-24-XBRL
CONFORMED-SUBMISSION-TYPE: N-CSR
</SEC-HEADER>
<DOCUMENT>
<TYPE>N-CSR
<TEXT>
<html>
<body>
<!-- Monetary values -->
<ix:nonFraction contextRef="fund_2024" name="invco:NetAssets" unitRef="USD">15234567890</ix:nonFraction>
<ix:nonFraction contextRef="fund_2024" name="invco:TotalAssets" unitRef="USD" decimals="0">15679123456</ix:nonFraction>

<!-- Percentages -->
<ix:nonFraction contextRef="fund_2024" name="invco:ExpenseRatio" unitRef="pure" decimals="4">0.0003</ix:nonFraction>
<ix:nonFraction contextRef="fund_2024" name="invco:PortfolioTurnover" unitRef="pure" decimals="2">0.04</ix:nonFraction>

<!-- Share counts -->
<ix:nonFraction contextRef="fund_2024" name="dei:SharesOutstanding" unitRef="shares">567890123</ix:nonFraction>

<!-- Per-share values -->
<ix:nonFraction contextRef="fund_2024" name="invco:NetAssetValuePerShare" unitRef="USD" decimals="2">267.45</ix:nonFraction>

<!-- Dates in XBRL -->
<ix:nonFraction contextRef="fund_2024" name="invco:ReportingPeriodEnd" format="ixt:dateslashus">06/30/2024</ix:nonFraction>

<!-- Text facts -->
<ix:nonNumeric contextRef="fund_2024" name="dei:EntityRegistrantName">Test Investment Fund</ix:nonNumeric>
<ix:nonNumeric contextRef="fund_2024" name="invco:FundFamily">Test Fund Family</ix:nonNumeric>

<!-- Boolean facts -->
<ix:nonFraction contextRef="fund_2024" name="invco:IsIndexFund" unitRef="pure">true</ix:nonFraction>
</body>
</html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
            """
            
            filing_meta = {
                "accession_number": "0000000000-24-XBRL",
                "form_type": "N-CSR"
            }
            
            # Parse content
            result = self.parser_manager.parse_filing_content(
                xbrl_test_content, filing_meta, "standard"
            )
            
            success = result.get("success", False)
            xbrl_facts_count = result.get("xbrl_facts_count", 0)
            
            logger.info(f"✓ XBRL parsing success: {success}")
            logger.info(f"✓ XBRL facts extracted: {xbrl_facts_count}")
            
            # Check for expected fact types
            expected_fact_types = [
                "monetary", "percentage", "shares", "per_share", "date", "text", "boolean"
            ]
            
            # If we extracted a reasonable number of facts, consider it successful
            facts_threshold = 8  # Expected at least 8 XBRL facts from the content
            extraction_success = xbrl_facts_count >= facts_threshold
            
            if extraction_success:
                logger.info(f"✓ XBRL fact extraction successful ({xbrl_facts_count} >= {facts_threshold})")
            else:
                logger.warning(f"⚠ Low XBRL fact extraction ({xbrl_facts_count} < {facts_threshold})")
            
            # Check for XBRL-specific metrics in result
            xbrl_metrics = result.get("xbrl_metrics", {})
            if xbrl_metrics:
                logger.info(f"✓ XBRL metrics available: {len(xbrl_metrics)} types")
            
            self.performance_metrics["xbrl_extraction"] = {
                "success": success,
                "facts_extracted": xbrl_facts_count,
                "content_size": len(xbrl_test_content),
                "extraction_rate": xbrl_facts_count / len(xbrl_test_content) * 1000  # facts per 1000 chars
            }
            
            self.test_results.append({
                "test": "xbrl_fact_extraction",
                "success": extraction_success,
                "details": f"Extracted {xbrl_facts_count} XBRL facts"
            })
            
            return extraction_success
            
        except Exception as e:
            logger.error(f"XBRL extraction test failed: {e}", exc_info=True)
            self.test_results.append({
                "test": "xbrl_fact_extraction",
                "success": False,
                "details": str(e)
            })
            return False
    
    def test_error_resilience(self) -> bool:
        """Test parser resilience to various error conditions."""
        logger.info("--- Testing Error Resilience ---")
        
        try:
            error_cases = [
                ("empty_content", ""),
                ("malformed_sgml", "<SEC-DOCUMENT><INVALID-TAG>broken"),
                ("malformed_html", "<html><body><table><tr><td>unclosed table"),
                ("invalid_xbrl", "<ix:nonFraction>invalid xbrl content</invalid>"),
                ("mixed_encoding", "Cañón <ix:nonFraction>123</ix:nonFraction> résumé"),
                ("very_long_line", "x" * 100000),  # 100K character line
                ("unicode_issues", "Test 🚀 with emojis 💰 and unicode ñáéíóú"),
                ("nested_malformed", "<html><body><div><table><tr><td><p>deeply nested unclosed")
            ]
            
            resilience_results = {}
            successful_handling = 0
            
            for case_name, test_content in error_cases:
                logger.info(f"Testing error case: {case_name}")
                
                filing_meta = {
                    "accession_number": f"error-{case_name}",
                    "form_type": "N-CSR"
                }
                
                try:
                    start_time = time.time()
                    result = self.parser_manager.parse_filing_content(
                        test_content, filing_meta, "standard"
                    )
                    processing_time = time.time() - start_time
                    
                    # Parser should handle errors gracefully
                    handled_gracefully = True
                    error_info = None
                    
                    # Even with errors, parser should return a result structure
                    if not isinstance(result, dict):
                        handled_gracefully = False
                        error_info = "Invalid result type"
                    elif "success" not in result:
                        handled_gracefully = False
                        error_info = "Missing success field"
                    elif processing_time > 10.0:  # Shouldn't take more than 10 seconds
                        handled_gracefully = False
                        error_info = "Excessive processing time"
                    
                    if handled_gracefully:
                        successful_handling += 1
                        logger.info(f"  ✓ {case_name}: Handled gracefully")
                    else:
                        logger.warning(f"  ⚠ {case_name}: {error_info}")
                    
                    resilience_results[case_name] = {
                        "handled_gracefully": handled_gracefully,
                        "processing_time": processing_time,
                        "result_success": result.get("success", False),
                        "error_info": error_info
                    }
                    
                except Exception as e:
                    # Unhandled exceptions are bad
                    logger.warning(f"  ❌ {case_name}: Unhandled exception - {e}")
                    resilience_results[case_name] = {
                        "handled_gracefully": False,
                        "exception": str(e)
                    }
            
            self.performance_metrics["error_resilience"] = resilience_results
            
            # Success if most cases handled gracefully
            resilience_rate = successful_handling / len(error_cases)
            resilience_success = resilience_rate >= 0.8  # 80% should be handled gracefully
            
            logger.info(f"Error resilience: {successful_handling}/{len(error_cases)} ({resilience_rate:.1%})")
            
            self.test_results.append({
                "test": "error_resilience",
                "success": resilience_success,
                "details": f"{successful_handling}/{len(error_cases)} error cases handled gracefully"
            })
            
            return resilience_success
            
        except Exception as e:
            logger.error(f"Error resilience test failed: {e}", exc_info=True)
            self.test_results.append({
                "test": "error_resilience",
                "success": False,
                "details": str(e)
            })
            return False
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        logger.info("=== Generating Performance Report ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        
        # Calculate overall performance metrics
        overall_metrics = {}
        
        if "realistic_ncsr" in self.performance_metrics:
            ncsr_metrics = self.performance_metrics["realistic_ncsr"]
            overall_metrics["realistic_content"] = {
                "throughput_kb_per_sec": ncsr_metrics.get("throughput_kb_per_sec", 0),
                "xbrl_extraction_rate": ncsr_metrics.get("xbrl_facts_count", 0)
            }
        
        if "scalability" in self.performance_metrics:
            scalability = self.performance_metrics["scalability"]
            overall_metrics["scalability"] = {
                "max_throughput_mb_per_sec": max(
                    (result.get("throughput_mb_per_sec", 0) for result in scalability.values()),
                    default=0
                ),
                "avg_throughput_mb_per_sec": sum(
                    result.get("throughput_mb_per_sec", 0) for result in scalability.values()
                ) / len(scalability) if scalability else 0
            }
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "overall_metrics": overall_metrics,
            "system_info": {
                "available_parsers": get_available_parsers(),
                "parser_manager_available": self.parser_manager.is_available(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return report
    
    def run_all_tests(self) -> bool:
        """Run all performance and validation tests."""
        logger.info("🚀 Starting Parser Performance & Validation Tests")
        
        if not self.setup():
            logger.error("❌ Setup failed - aborting tests")
            return False
        
        # Define test sequence
        tests = [
            ("Realistic N-CSR Parsing", self.test_realistic_ncsr_parsing),
            ("Performance Scalability", self.test_performance_scalability),
            ("XBRL Fact Extraction", self.test_xbrl_fact_extraction),
            ("Error Resilience", self.test_error_resilience)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            test_func()
        
        # Generate report
        report = self.generate_performance_report()
        
        # Save report
        report_file = f"logs/parser_performance_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        os.makedirs("logs", exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Performance report saved: {report_file}")
        
        # Summary
        success_rate = report["summary"]["success_rate"]
        logger.info(f"\n📈 Performance Test Summary:")
        logger.info(f"Tests Passed: {report['summary']['passed_tests']}/{report['summary']['total_tests']}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        # Performance highlights
        if "overall_metrics" in report:
            metrics = report["overall_metrics"]
            if "realistic_content" in metrics:
                throughput = metrics["realistic_content"]["throughput_kb_per_sec"]
                logger.info(f"Realistic Content Throughput: {throughput:.1f} KB/s")
            
            if "scalability" in metrics:
                max_throughput = metrics["scalability"]["max_throughput_mb_per_sec"]
                logger.info(f"Max Throughput: {max_throughput:.2f} MB/s")
        
        if success_rate >= 75:
            logger.info("🎉 Parser Performance Tests PASSED!")
            return True
        else:
            logger.error("❌ Parser Performance Tests FAILED!")
            return False


def main():
    """Run the parser performance test suite."""
    test_suite = ParserPerformanceTests()
    success = test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
