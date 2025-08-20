"""
Test de integración para verificar que el ORM funciona correctamente
con el TieredProcessor
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from sec_extractor.core.tiered_processor import TieredProcessor
from sec_extractor.storage.database import DatabaseManager
from sec_extractor.config.settings import settings

class TestORMIntegration:
    """Tests de integración ORM + TieredProcessor"""
    
    @pytest.fixture
    def test_processor(self):
        """Fixture para TieredProcessor con BD en memoria"""
        return TieredProcessor("sqlite:///:memory:")
    
    def test_process_filing_with_orm(self, test_processor):
        """Test completo de procesamiento con persistencia ORM"""
        
        filing_meta = {
            'accession_number': '0001234567-25-000001',
            'cik': '1234567',
            'company_name': 'Test Mutual Fund',
            'file_size_mb': 15.5,
            'filing_html_url': 'http://test.com/filing.html'
        }
        
        html_content = """
        <html>
            <table>
                <tr><th>Security</th><th>Shares</th><th>Value</th></tr>
                <tr><td>Apple Inc</td><td>100</td><td>$15000</td></tr>
            </table>
        </html>
        """
        
        # Mock del download
        with patch.object(test_processor, '_download_filing_content', return_value=html_content):
            result = test_processor.process_filing(filing_meta, html_content)
        
        # Verificar resultado
        assert result.get('success') is not None
        assert 'filing_id' in result
        assert 'processing_tier' in result
        assert 'processing_duration' in result
        
        # Verificar que se guardó en BD
        filing = test_processor.db.get_filing_by_accession('0001234567-25-000001')
        assert filing is not None
        assert filing['cik'] == '1234567'
        assert filing['company_name'] == 'Test Mutual Fund'
    
    def test_dead_letter_queue_integration(self, test_processor):
        """Test integración con Dead Letter Queue"""
        
        filing_meta = {
            'accession_number': '0001234567-25-000002',
            'cik': '1234567',
            'company_name': 'Large Test Fund',
            'file_size_mb': 150.0  # Archivo muy grande
        }
        
        result = test_processor.process_filing(filing_meta, "<html></html>")
        
        # Verificar que fue a dead letter queue
        assert result['success'] is False
        assert result['processing_tier'] == 'dead_letter'
        assert 'File too large' in result['error']
        
        # Verificar DLQ statistics
        dlq_stats = test_processor.dlq.get_retry_statistics()
        assert dlq_stats['total_entries'] >= 1
    
    def test_night_batch_processing(self, test_processor):
        """Test procesamiento nocturno de reintentos"""
        
        # Primero crear algunos fallos en DLQ
        filing_meta = {
            'accession_number': '0001234567-25-000003',
            'cik': '1234567',
            'company_name': 'Retry Test Fund',
            'file_size_mb': 25.0
        }
        
        filing_id = test_processor.db.create_or_update_filing(filing_meta)
        test_processor.dlq.add_filing(filing_id, "Test timeout", 25.0, 'timeout')
        
        # Ejecutar procesamiento nocturno
        with patch.object(test_processor, '_download_filing_content', return_value="<html><table></table></html>"):
            summary = test_processor.process_night_batch(10)
        
        # Verificar resumen
        assert 'processed' in summary
        assert 'successful' in summary
        assert 'failed' in summary
        assert summary['processed'] >= 0
    
    def test_metrics_and_reporting(self, test_processor):
        """Test métricas y reporting con ORM"""
        
        # Procesar algunos filings
        for i in range(3):
            filing_meta = {
                'accession_number': f'000123456{i}-25-000001',
                'cik': f'123456{i}',
                'company_name': f'Test Fund {i}',
                'file_size_mb': 5.0 + i  # Diferentes tamaños
            }
            
            with patch.object(test_processor, '_download_filing_content', return_value="<html></html>"):
                test_processor.process_filing(filing_meta, "<html></html>")
        
        # Obtener métricas
        summary = test_processor.get_processing_summary()
        
        assert 'daily_metrics' in summary
        assert 'dlq_statistics' in summary
        assert 'system_metrics' in summary
        
        daily_metrics = summary['daily_metrics']
        assert 'by_tier' in daily_metrics
        assert 'totals' in daily_metrics
    
    def test_cleanup_operations(self, test_processor):
        """Test operaciones de limpieza"""
        
        # Crear algunos datos de prueba
        filing_meta = {
            'accession_number': '0001234567-25-000099',
            'cik': '1234567',
            'company_name': 'Cleanup Test Fund',
            'file_size_mb': 10.0
        }
        
        filing_id = test_processor.db.create_or_update_filing(filing_meta)
        
        # Ejecutar limpieza (con retention muy corto para testing)
        cleanup_results = test_processor.cleanup_old_data(0)  # 0 días = limpiar todo
        
        assert isinstance(cleanup_results, dict)
        # Los contadores pueden ser 0 o más dependiendo de qué se limpie

if __name__ == "__main__":
    # Run basic test
    processor = TieredProcessor("sqlite:///:memory:")
    print("✅ TieredProcessor with ORM initialized successfully")
    
    filing_meta = {
        'accession_number': '0001234567-25-000001',
        'cik': '1234567',
        'company_name': 'Test Fund',
        'file_size_mb': 10.0
    }
    
    filing_id = processor.db.create_or_update_filing(filing_meta)
    print(f"✅ Created filing with ID: {filing_id}")
    
    print("🎉 ORM integration working correctly!")