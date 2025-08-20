#!/usr/bin/env python3
"""
Runs the TieredProcessor for a single filing accession number.
Usage: python scripts/process_one_runner.py <accession_number>
Example: python scripts/process_one_runner.py 0001193125-24-194739
"""
import argparse
import os
import sys
import logging

# Add project root to path to resolve imports
sys.path.insert(0, os.getcwd())

from sec_extractor.core.tiered_processor import TieredProcessor
from sec_extractor.config.settings import settings
from sec_extractor.storage.database import DatabaseManager

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def run_processor(accession_number: str):
    """
    Initializes and runs the TieredProcessor for a single accession number.
    """
    logger.info(f"Initializing TieredProcessor for accession number: {accession_number}")
    
    # The processor requires a database session for its operations
    db_manager = DatabaseManager(settings.database_url)
    session = db_manager.get_session()
    
    try:
        processor = TieredProcessor(session)
        result = processor.process_filing(accession_number)
        
        if result:
            logger.info(f"Successfully processed and saved filing.")
            logger.info(f"Result: {result.dict()}")
        else:
            logger.warning(f"Processing may have failed or filing was skipped. Check logs for details.")
            
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)
    finally:
        logger.info("Closing database session.")
        session.close()

def main():
    """
    Main function to drive the script.
    """
    parser = argparse.ArgumentParser(
        description="Run the SEC filing processor for a single accession number."
    )
    parser.add_argument(
        'accession_number',
        help="The accession number of the filing to process (e.g., '0001193125-24-194739')."
    )
    args = parser.parse_args()

    accession_number = args.accession_number.strip()
    if not accession_number:
        logger.error("Accession number cannot be empty.")
        return

    run_processor(accession_number)

if __name__ == "__main__":
    main()
