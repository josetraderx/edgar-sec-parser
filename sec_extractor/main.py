"""
SEC N-CSR Extractor - Main Application
Ejecuta el procesamiento diario de filings
"""

import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict

from core.tiered_processor import TieredProcessor
from storage.database import DatabaseManager
from storage.dead_letter_queue import DeadLetterQueueManager
from config.settings import settings

class SECExtractorApp:
    """Aplicación principal del extractor"""
    
    def __init__(self):
        self.processor = TieredProcessor()
        self.db = DatabaseManager()
        self.dlq = DeadLetterQueueManager()
    
    def initialize(self):
        """Inicializa la aplicación"""
        print("Initializing SEC Extractor...")
        self.db.initialize_tables()
        print("Database tables ready.")
    
    def process_daily_batch(self, filing_list: List[Dict]):
        """Procesa el batch diario de filings"""
        print(f"Starting daily processing of {len(filing_list)} filings...")
        
        successful = 0
        failed = 0
        
        for i, filing_meta in enumerate(filing_list):
            print(f"Processing filing {i+1}/{len(filing_list)}: CIK {filing_meta.get('cik')}")
            
            try:
                # Aquí iría la descarga del HTML desde SEC
                # html_content = self.download_filing(filing_meta)
                html_content = filing_meta.get('html_content', '')  # Placeholder
                
                if not html_content:
                    print(f"  Skipping - no content available")
                    continue
                
                # Procesar el filing
                result = self.processor.process_filing(filing_meta, html_content)
                
                # Guardar resultado
                if result['status'] == 'failed' or result.get('processing_tier') == 'dead_letter':
                    self.dlq.add_to_queue(result, filing_meta)
                    failed += 1
                    print(f"  FAILED: {result.get('failure_reason', 'unknown')}")
                else:
                    filing_id = self.db.save_filing_result(result)
                    successful += 1
                    print(f"  SUCCESS: {result['table_count']} tables, {result['processing_duration']:.1f}s")
                
                # Rate limiting para cumplir con SEC
                time.sleep(settings.SEC_RATE_LIMIT)
                
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                failed += 1
                continue
        
        print(f"Daily batch complete: {successful} successful, {failed} failed")
        return successful, failed
    
    def process_night_batch(self):
        """Procesa el batch nocturno de reintentos"""
        print("Starting night batch processing...")
        
        night_candidates = self.dlq.get_night_batch()
        if not night_candidates:
            print("No candidates for night processing")
            return
        
        print(f"Processing {len(night_candidates)} retry candidates...")
        
        recovered = 0
        for candidate in night_candidates:
            try:
                # Reintento con recursos completos
                # html_content = self.download_filing(candidate['original_metadata'])
                html_content = candidate.get('html_content', '')  # Placeholder
                
                if html_content:
                    result = self.processor.process_filing(
                        candidate['original_metadata'], 
                        html_content
                    )
                    
                    if result['status'] != 'failed':
                        self.db.save_filing_result(result)
                        self.dlq.mark_retry_attempt(candidate['id'], success=True)
                        recovered += 1
                        print(f"  RECOVERED: CIK {candidate['cik']}")
                    else:
                        self.dlq.mark_retry_attempt(candidate['id'], success=False)
                        print(f"  STILL FAILED: CIK {candidate['cik']}")
                
            except Exception as e:
                self.dlq.mark_retry_attempt(candidate['id'], success=False)
                print(f"  ERROR: CIK {candidate['cik']} - {str(e)}")
        
        print(f"Night batch complete: {recovered} recovered")
    
    def cleanup(self):
        """Limpia datos antiguos"""
        deleted = self.dlq.cleanup_old_entries()
        print(f"Cleaned up {deleted} old dead letter entries")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='SEC N-CSR Extractor')
    parser.add_argument('--mode', choices=['daily', 'night', 'init'], required=True,
                       help='Processing mode')
    parser.add_argument('--test', action='store_true', 
                       help='Run with test data')
    
    args = parser.parse_args()
    
    app = SECExtractorApp()
    
    if args.mode == 'init':
        app.initialize()
        print("Initialization complete")
        
    elif args.mode == 'daily':
        app.initialize()
        
        if args.test:
            # Usar datos de prueba
            test_filings = [
                {'cik': '1234567', 'html_content': '<html><table>Test</table></html>'},
                {'cik': '2345678', 'html_content': '<html><p>Large file content...</p></html>' * 1000}
            ]
            app.process_daily_batch(test_filings)
        else:
            # Aquí iría la lógica para obtener filings reales del día
            print("Daily mode - implement filing discovery logic")
            
    elif args.mode == 'night':
        app.process_night_batch()
        app.cleanup()
    
    print("Application finished")

if __name__ == "__main__":
    main()