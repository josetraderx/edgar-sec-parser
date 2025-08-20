#!/usr/bin/env python3
"""
Lists all filings in the database for a specific date range.
Usage: python scripts/list_filings_by_date.py --start-date 2024-08-01 --end-date 2024-08-07
"""
import argparse
import os
import sys
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Add project root to path to resolve imports
sys.path.insert(0, os.getcwd())

from sec_extractor.storage.database import DatabaseManager
from sec_extractor.storage.models import Filing
from sec_extractor.config.settings import settings

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def list_filings(db_session: Session, start_date: datetime, end_date: datetime):
    """
    Queries and prints filings within a given date range.
    """
    logger.info(f"Querying filings from {start_date.date()} to {end_date.date()}...")
    
    filings = (
        db_session.query(Filing)
        .filter(and_(Filing.filing_date >= start_date, Filing.filing_date <= end_date))
        .order_by(Filing.filing_date, Filing.company_name)
        .all()
    )

    if not filings:
        logger.warning(f"No filings found in the specified date range.")
        return

    print("\n--- Filings Found ---")
    print(f"{'Filing Date':<12} | {'CIK':<12} | {'Accession Number':<20} | {'Company Name':<50} | {'Status':<15}")
    print("-" * 120)

    for f in filings:
        print(
            f"{f.filing_date.strftime('%Y-%m-%d'):<12} | "
            f"{f.cik:<12} | "
            f"{f.accession_number:<20} | "
            f"{f.company_name[:48]:<50} | "
            f"{f.processing_status:<15}"
        )
    
    print("-" * 120)
    logger.info(f"Listed {len(filings)} filings.")

def main():
    """
    Main function to drive the listing script.
    """
    parser = argparse.ArgumentParser(
        description="List filings stored in the database for a given date range."
    )
    parser.add_argument('--start-date', required=True, help="Start date (YYYY-MM-DD).")
    parser.add_argument('--end-date', help="End date (YYYY-MM-DD). Defaults to start date.")
    args = parser.parse_args()

    try:
        start_date = datetime.fromisoformat(args.start_date)
        end_date = datetime.fromisoformat(args.end_date) if args.end_date else start_date
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    db_manager = DatabaseManager(settings.database_url)
    session = db_manager.get_session()
    try:
        list_filings(session, start_date, end_date)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        session.close()

if __name__ == "__main__":
    main()