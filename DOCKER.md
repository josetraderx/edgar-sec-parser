# 🐳 Docker Setup for Edgar SEC Parser

## Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/josetraderx/edgar-sec-parser.git
cd edgar-sec-parser
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. **Run with Docker Compose:**
```bash
docker-compose up -d
```

## Usage Examples

### Basic Commands
```bash
# Run smoke test
docker-compose run edgar python db_smoketest.py

# Process specific date
docker-compose run edgar python main.py --date 2024-01-15

# Process last 7 days
docker-compose run edgar python main.py --backfill 7
```

### Development Mode
```bash
# Run with live code reloading
docker-compose up edgar

# Access application logs
docker-compose logs -f edgar
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U edgar_user -d edgar

# View database logs
docker-compose logs -f db
```

## Environment Variables

See `.env.example` for all available configuration options.

Required variables:
- `PG_DSN`: Database connection string
- `SEC_USER_AGENT`: Your SEC API user agent
- `DATABASE_URL`: SQLAlchemy database URL

## Troubleshooting

### Health Check
```bash
docker-compose ps
```

### Reset Database
```bash
docker-compose down -v
docker-compose up -d
```

### View All Logs
```bash
docker-compose logs
```
