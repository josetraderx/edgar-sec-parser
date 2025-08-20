# Scripts Directory

This directory contains utility scripts for system administration, debugging, and data processing.

## 🛠️ Available Scripts

### Database & Filing Management

#### `list_filings_by_date.py`
- **Purpose**: Query and list filings by date range
- **Usage**: `python scripts/list_filings_by_date.py --start-date 2024-08-01 --end-date 2024-08-07`
- **Features**: Date filtering, summary statistics

#### `reprocess_by_cik.py`
- **Purpose**: Reprocess filings for specific CIK numbers
- **Usage**: `python scripts/reprocess_by_cik.py --cik 1234567890`
- **Features**: Selective reprocessing, error recovery

#### `find_and_reprocess_after.py`
- **Purpose**: Find and reprocess filings after a specific date
- **Usage**: `python scripts/find_and_reprocess_after.py --after-date 2024-08-01`
- **Features**: Bulk reprocessing, progress tracking

### Development & Testing

#### `process_one_runner.py`
- **Purpose**: Process a single filing for testing
- **Usage**: `python scripts/process_one_runner.py --accession 0001234567-24-000001`
- **Features**: Single filing processing, detailed logging

#### `debug_discover_http.py`
- **Purpose**: Debug HTTP discovery and download issues
- **Usage**: `python scripts/debug_discover_http.py --url <filing_url>`
- **Features**: Network debugging, request/response analysis

#### `download_with_ua.py`
- **Purpose**: Download filings with proper User-Agent headers
- **Usage**: `python scripts/download_with_ua.py --accession 0001234567-24-000001`
- **Features**: SEC-compliant downloading, retry logic

## 🚀 Usage Guidelines

### Prerequisites
```bash
# Ensure environment is configured
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Setup
```bash
# Scripts use the same .env configuration as main application
cp .env.example .env
# Edit .env with your database credentials
```

### Common Workflows

#### Daily Operations
```bash
# List today's filings
python scripts/list_filings_by_date.py --start-date $(date +%Y-%m-%d)

# Reprocess failed filings
python scripts/find_and_reprocess_after.py --after-date $(date -d '1 day ago' +%Y-%m-%d)
```

#### Development & Debugging
```bash
# Test single filing
python scripts/process_one_runner.py --accession 0001234567-24-000001

# Debug network issues
python scripts/debug_discover_http.py --url https://www.sec.gov/Archives/edgar/data/...
```

#### Maintenance
```bash
# Reprocess by company
python scripts/reprocess_by_cik.py --cik 1234567890

# Download specific filing
python scripts/download_with_ua.py --accession 0001234567-24-000001
```

## 📋 Script Details

All scripts include:
- ✅ Comprehensive help via `--help` flag
- ✅ Logging and progress indicators
- ✅ Error handling and recovery
- ✅ Database transaction safety
- ✅ SEC API compliance (rate limiting, User-Agent)

## ⚠️ Notes

- Scripts require proper database configuration in `.env`
- Some scripts may take significant time for large datasets
- Always test scripts on small datasets first
- Monitor logs for errors and warnings
