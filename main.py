#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main application entry point for the SEC Filing Extractor.

This script orchestrates the daily processing of SEC filings. It can be run for a specific date
or a backfill period. It discovers filings using the DailyFeed, checks for duplicates in the
database, and then passes new filings to the TieredProcessor for extraction and storage.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path to resolve imports if this script is run directly
sys.path.insert(0, os.getcwd())

from sqlalchemy.orm import Session

from sec_extractor.config.settings import settings
from sec_extractor.core.tiered_processor import TieredProcessor
from sec_extractor.discovery.daily_feed import DailyFeed
from sec_extractor.storage.database import DatabaseManager
from sec_extractor.storage.models import Filing

# --- Logging Setup ---
# Configure logging to write to a file and to the console
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
run_log_file = os.path.join(log_dir, f"run_{datetime.now():%Y-%m-%d_%H-%M-%S}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(run_log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def process_filings_for_date(
    db_session: Session,
    processor: TieredProcessor,
    target_date: datetime.date,
    max_filings: int = None
):
    """
    Discovers and processes all new N-CSR/S filings for a specific date.
    """
    logger.info(f"--- Starting processing for date: {target_date.isoformat()} ---")
    
    # 1. Discover filings for the target date
    feed = DailyFeed()
    form_types = ["N-CSR", "N-CSRS"]
    discovered_filings = feed.get_filings_for_date(target_date, form_types=form_types)

    if not discovered_filings:
        logger.warning(f"No filings of types {form_types} found for {target_date.isoformat()}.")
        return

    logger.info(f"Discovered {len(discovered_filings)} filings.")

    # 2. Filter out filings that are already in the database
    accession_numbers = [f['accession_number'] for f in discovered_filings]
    existing_filings = (
        db_session.query(Filing.accession_number)
        .filter(Filing.accession_number.in_(accession_numbers))
        .all()
    )
    existing_accession_numbers = {acc for (acc,) in existing_filings}
    
    new_filings = [
        f for f in discovered_filings 
        if f['accession_number'] not in existing_accession_numbers
    ]

    logger.info(f"Found {len(new_filings)} new filings to process.")

    if not new_filings:
        return

    # 3. Process new filings, respecting the max_filings limit
    filings_to_process = new_filings[:max_filings] if max_filings else new_filings
    logger.info(f"Processing a maximum of {len(filings_to_process)} filings.")

    for i, filing_meta in enumerate(filings_to_process):
        accession_number = filing_meta['accession_number']
        logger.info(f"Processing {i+1}/{len(filings_to_process)}: {accession_number} ({filing_meta['company_name']})")
        try:
            processor.process_filing(accession_number)
        except Exception:
            # The processor has its own internal error handling and DLQ.
            # This catch is for unexpected failures in the orchestration loop.
            logger.error(
                f"An unexpected error occurred while orchestrating processing for {accession_number}.",
                exc_info=True
            )

    logger.info(f"--- Finished processing for date: {target_date.isoformat()} ---")


def main():
    """Main function to drive the application."""
    parser = argparse.ArgumentParser(description="SEC N-CSR Filing Extractor.")
    parser.add_argument("--date", help="A specific date to process (YYYY-MM-DD).")
    parser.add_argument("--backfill", type=int, help="Number of past days to process (for catch-up).")
    parser.add_argument("--max-filings", type=int, help="Maximum number of filings to process per day.")
    args = parser.parse_args()

    db_manager = DatabaseManager(settings.database_url)
    session = db_manager.get_session()
    processor = TieredProcessor(settings.database_url)

    try:
        dates_to_process = []
        if args.date:
            try:
                dates_to_process.append(datetime.strptime(args.date, "%Y-%m-%d").date())
            except ValueError:
                logger.error("Invalid date format for --date. Please use YYYY-MM-DD.")
                return
        elif args.backfill:
            today = datetime.now().date()
            for i in range(args.backfill):
                dates_to_process.append(today - timedelta(days=i))
        else:
            # Default to processing yesterday's filings
            dates_to_process.append(datetime.now().date() - timedelta(days=1))
        
        logger.info(f"Processing for dates: {[d.isoformat() for d in dates_to_process]}")

        for target_date in dates_to_process:
            process_filings_for_date(session, processor, target_date, args.max_filings)

    except Exception:
        logger.critical("A critical error occurred in the main application loop.", exc_info=True)
    finally:
        logger.info("Closing database session.")
        session.close()
        logging.shutdown()


if __name__ == "__main__":
    main()
