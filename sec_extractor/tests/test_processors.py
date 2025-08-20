import unittest
import os
from core.tiered_processor import TieredProcessor
from extractors.standard_extractor import StandardExtractor
from extractors.limited_extractor import LimitedExtractor
from extractors.minimal_extractor import MinimalExtractor

class TestProcessors(unittest.TestCase):
    
    def setUp(self):
        self.processor = TieredProcessor()
        
        # HTML de prueba pequeño
        self.small_html = """
        <html>
            <head><title>Test Fund N-CSR</title></head>
            <body>
                <table class="schedule-of-investments">
                    <tr><th>Security</th><th>Value</th></tr>
                    <tr><td>Apple Inc</td><td>$1,000,000</td></tr>
                </table>
            </body>
        </html>
        """
        
        # HTML de prueba grande (simular archivo grande)
        self.large_html = "<html><body>" + "x" * 50000000 + "</body></html>"  # 50MB
        
        self.test_meta = {'cik': '1234567', 'filing_date': '2024-01-01'}
    
    def test_small_file_processing(self):
        """Test procesamiento de archivo pequeño"""
        result = self.processor.process_filing(self.test_meta, self.small_html)
        
        self.assertEqual(result['processing_tier'], 'standard')
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['file_size_mb'] < 10)
    
    def test_large_file_processing(self):
        """Test procesamiento de archivo grande"""
        result = self.processor.process_filing(self.test_meta, self.large_html)
        
        # Archivo grande debe ir a minimal o dead letter
        self.assertIn(result['processing_tier'], ['minimal', 'dead_letter'])
        self.assertTrue(result['file_size_mb'] > 40)
    
    def test_standard_extractor(self):
        """Test extractor estándar"""
        extractor = StandardExtractor(self.processor.timeout_manager)
        result = extractor.extract(self.small_html, self.test_meta)
        
        self.assertEqual(result['processing_tier'], 'standard')
        self.assertIn('metadata', result)
        self.assertIn('tables', result)
    
    def test_minimal_extractor(self):
        """Test extractor mínimo"""
        extractor = MinimalExtractor(self.processor.timeout_manager)
        result = extractor.extract(self.small_html, self.test_meta)
        
        self.assertEqual(result['processing_tier'], 'minimal')
        self.assertIn('key_metrics', result)
        self.assertIn('metadata', result)

if __name__ == '__main__':
    unittest.main()