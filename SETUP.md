# Setup Guide

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/josetraderx/edgar-sec-parser.git
   cd edgar-sec-parser
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run the demo:**
   ```bash
   python demo_live_simple.py
   ```

## Database Configuration

The system requires PostgreSQL. Update your `.env` file:

```env
PG_DSN=postgresql://username:password@localhost:5432/database
SEC_USER_AGENT=Your Company Name your.email@domain.com
```

## Docker Deployment

See [DOCKER.md](DOCKER.md) for containerization instructions.

## Architecture

- `sec_extractor/` - Main parser system
- `scripts/` - Utility scripts
- `tests/` - Test suite
- `notebooks/` - Analysis examples

## Performance

The system can process 100+ SEC documents per minute with 98.6% success rate.
