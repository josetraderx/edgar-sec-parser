#!/usr/bin/env python3
"""
Finds all filings on or after a specific date and re-processes them.
Usage: python scripts/find_and_reprocess_after.py --date 2024-08-01
"""
import argparse
import os
import sys
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to path to resolve imports
sys.path.insert(0, os.getcwd())

from sec_extractor.storage.database import DatabaseManager
from sec_extractor.storage.models import Filing
from sec_extractor.core.tiered_processor import TieredProcessor
from sec_extractor.config.settings import settings

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def get_filings_to_reprocess(db_session: Session, after_date: datetime) -> list[dict]:
    """
    Queries the database for all filings on or after a given date.
    """
    logger.info(f"Querying database for filings on or after {after_date.date()}...")
    filings = db_session.query(Filing).filter(Filing.filing_date >= after_date).order_by(Filing.filing_date).all()
    
    if not filings:
        logger.warning(f"No filings found on or after {after_date.date()}.")
        return []

    filings_meta = []
    for f in filings:
        filings_meta.append({
            "accession_number": f.accession_number,
            "cik": f.cik,
            "company_name": f.company_name,
            "form_type": f.form_type,
            "filing_date": f.filing_date.isoformat() if f.filing_date else None,
            "period_of_report": f.period_of_report.isoformat() if f.period_of_report else None,
            "filing_html_url": f.filing_html_url,
            "file_size_mb": f.file_size_mb,
        })
    
    logger.info(f"Found {len(filings_meta)} filings to reprocess.")
    return filings_meta

def main():
    """
    Main function to drive the reprocessing script.
    """
    parser = argparse.ArgumentParser(
        description="Reprocess all filings on or after a specific date."
    )
    parser.add_argument('--date', required=True, help="The start date for reprocessing (YYYY-MM-DD).")
    args = parser.parse_args()

    try:
        start_date = datetime.fromisoformat(args.date)
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    logger.info(f"Starting reprocessing for filings on or after: {start_date.date()}")

    db_manager = DatabaseManager(settings.database_url)
    processor = TieredProcessor(settings.database_url)
    
    session = db_manager.get_session()
    try:
        filings_to_process = get_filings_to_reprocess(session, start_date)
        
        if not filings_to_process:
            return

        results = processor.process_batch(filings_to_process)
        
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        
        logger.info("--- Reprocessing Summary ---")
        logger.info(f"Total filings processed: {len(results)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info("--------------------------")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        session.close()
        logger.info("Reprocessing script finished.")

if __name__ == "__main__":
    main()
