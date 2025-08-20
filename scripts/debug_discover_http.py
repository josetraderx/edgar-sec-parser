#!/usr/bin/env python3
"""
Debugs the filing discovery process for a specific date.

This script initializes the DailyFeed and fetches filings for a given date,
printing the results to the console. It's useful for testing the discovery
mechanism without running the full processing pipeline.

Usage: python scripts/debug_discover_http.py [YYYY-MM-DD]
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

# Add project root to path to resolve imports
sys.path.insert(0, os.getcwd())

from sec_extractor.discovery.daily_feed import DailyFeed

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def debug_discovery(target_date: datetime.date):
    """
    Uses DailyFeed to discover filings and prints them.
    """
    logger.info(f"--- Debugging discovery for date: {target_date.isoformat()} ---")
    
    feed = DailyFeed()
    form_types = ["N-CSR", "N-CSRS"]
    
    try:
        filings = feed.get_filings_for_date(target_date, form_types=form_types)
        
        if not filings:
            logger.warning(f"No filings of types {form_types} found for this date.")
            return
            
        logger.info(f"Successfully discovered {len(filings)} filings.")
        print("\n--- Discovered Filings (sample) ---")
        print(f"{'CIK':<12} | {'Accession Number':<20} | {'Form':<10} | {'Company Name':<60}")
        print("-" * 110)
        
        for f in filings[:20]:  # Print a sample of up to 20 filings
            print(
                f"{f['cik']:<12} | "
                f"{f['accession_number']:<20} | "
                f"{f['form_type']:<10} | "
                f"{f['company_name'][:58]:<60}"
            )
        
        if len(filings) > 20:
            print(f"... and {len(filings) - 20} more.")
            
    except Exception as e:
        logger.error(f"An error occurred during discovery: {e}", exc_info=True)

def main():
    """Main function to drive the script."""
    parser = argparse.ArgumentParser(
        description="Debug the SEC filing discovery process for a specific date."
    )
    parser.add_argument(
        'date',
        nargs='?',
        default=(datetime.now().date() - timedelta(days=1)).isoformat(),
        help="The date to check for filings (YYYY-MM-DD). Defaults to yesterday."
    )
    args = parser.parse_args()

    try:
        target_date = datetime.fromisoformat(args.date).date()
    except ValueError:
        logger.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    debug_discovery(target_date)

if __name__ == "__main__":
    main()