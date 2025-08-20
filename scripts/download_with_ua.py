#!/usr/bin/env python3
"""
Downloads a single filing from the SEC EDGAR database using the SECHTTPClient.
Usage: python scripts/download_with_ua.py <accession_number> [--output-dir logs]
Example: python scripts/download_with_ua.py 0001193125-24-194739
"""
import argparse
import os
import sys
import logging
import time

# Add project root to path to resolve imports
sys.path.insert(0, os.getcwd())

from sec_extractor.core.http_client import SECHTTPClient

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def download_filing(accession_number: str, output_dir: str):
    """
    Downloads a filing using the SECHTTPClient and saves it to a file.
    """
    logger.info(f"Initializing HTTP client to download {accession_number}...")
    
    client = SECHTTPClient()
    
    # Construct the URL from the accession number
    # First, remove dashes from the accession number
    acc_no_parts = accession_number.split('-')
    if len(acc_no_parts) != 3:
        logger.error(f"Invalid accession number format: {accession_number}")
        return
        
    cik = acc_no_parts[0].lstrip('0')
    acc_no_no_dashes = "".join(acc_no_parts)

    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_no_dashes}/{accession_number}.txt"
    
    logger.info(f"Requesting URL: {url}")
    
    t0 = time.time()
    try:
        response = client.get(url)
        response.raise_for_status()
        content = response.text
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_path = os.path.join(output_dir, f"{accession_number}.txt")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        total_bytes = len(content.encode('utf-8'))
        duration = time.time() - t0
        
        logger.info(f"Successfully downloaded {total_bytes / 1024:.2f} KB in {duration:.2f}s.")
        logger.info(f"Filing saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to download filing: {e}", exc_info=True)

def main():
    """
    Main function to drive the script.
    """
    parser = argparse.ArgumentParser(
        description="Download a single SEC filing using the project's HTTP client."
    )
    parser.add_argument(
        'accession_number',
        help="The accession number of the filing to download (e.g., '0001193125-24-194739')."
    )
    parser.add_argument(
        '--output-dir',
        default='logs',
        help="The directory to save the downloaded file to. Defaults to 'logs'."
    )
    args = parser.parse_args()

    download_filing(args.accession_number, args.output_dir)

if __name__ == "__main__":
    main()