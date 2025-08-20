# 🛡️ Edgar SEC Parser - Advanced Financial Document Processing System

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)
![Performance](https://img.shields.io/badge/Throughput-16.51MB/s-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**High-performance SEC filing extraction system powered by modern parsing technologies for identifying and processing financial document structures in regulatory filings**

🚀 [Quick Start](#-quick-start) • 📊 [Features](#-key-features) • 🔧 [Installation](#installation) • 📈 [Performance](#-performance-metrics) • 🧪 [Usage](#-testing)

## 🎯 Project Overview

Edgar is a production-ready SEC filing extraction and parsing system that intelligently processes regulatory documents using advanced parser integration. Built with John Friedman's specialized SEC parsing libraries (`secsgml` v0.3.1 and `secxbrl` v0.5.0), Edgar provides robust, scalable financial document processing capabilities.

## ✨ Key Features

- **🚀 High-Performance Processing**: Up to 16.51 MB/s document throughput with intelligent content detection
- **🔄 Hybrid Parser Architecture**: Seamlessly combines SGML and XBRL parsing with legacy system compatibility  
- **📊 Multi-Format Support**: Native processing of SGML, XBRL, and traditional SEC document formats
- **🛡️ Enterprise-Grade Reliability**: 100% error case handling with graceful fallback mechanisms
- **🏗️ Production-Ready Infrastructure**: Comprehensive testing, validation, and deployment capabilities
- **🔍 Intelligent Content Analysis**: Automatic document type detection and optimal parser selection
- **💾 Advanced Data Extraction**: Structured metadata and financial facts extraction from complex filings

## 🏗️ Architecture

```
Edgar/
├── sec_extractor/           # Core extraction system
│   ├── parsers/            # Integrated SEC parsers
│   ├── core/               # Processing engine
│   ├── storage/            # Database models
│   ├── discovery/          # SEC feed discovery
│   └── extractors/         # Content extractors
├── tests/                  # Test suites
│   ├── test_parsers/       # Parser unit tests
│   └── performance/        # Performance validation
├── scripts/                # Utility scripts
├── notebooks/              # Analysis notebooks
└── docs/                   # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Docker (optional)

### Installation

1. **Clone and setup environment:**
```bash
git clone https://github.com/josetraderx/edgar-sec-parser.git
cd edgar-sec-parser
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
# Create environment configuration
cp .env.example .env
# Edit .env with your database credentials and settings
```

3. **Database setup:**
```bash
# Initialize database schema
python -c "from sec_extractor.storage.database import DatabaseManager; DatabaseManager().create_tables()"
```

4. **Verify installation:**
```bash
python db_smoketest.py
```

### Docker Setup

```bash
docker-compose up -d
```

## 📊 Performance Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **Peak Throughput** | 16.51 MB/s | Maximum document processing speed |
| **Realistic Performance** | 1.77 MB/s | Average processing with real SEC content |
| **Error Recovery** | 100% | Successful handling of malformed documents |
| **Parser Coverage** | 3 engines | SGML, XBRL, and integrated parsing |
| **Database Integration** | ✅ Complete | Full metadata and facts storage |

## 🧪 Testing

### System Verification
```bash
# Quick system health check
python db_smoketest.py
```

### Full Test Suite
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=sec_extractor --cov-report=html
```

### Performance Benchmarking
```bash
# Parser performance validation
python tests/performance/test_parser_performance.py
```

### Specific Component Testing
```bash
# Test individual parsers
pytest tests/test_parsers/ -v

# Test database integration
pytest tests/test_storage/ -v
```

## 📚 Documentation & Resources

- **[Project Roadmap](roadmap.md)** - Complete development history and milestones
- **[Performance Reports](tests/performance/)** - Detailed benchmarking and validation results  
- **[Parser Documentation](sec_extractor/parsers/)** - Technical implementation details
- **[Database Schema](sec_extractor/storage/)** - Data models and relationships

## 🔧 Key Components

### Parsers
- **SGMLParser**: Handles legacy SGML SEC filings
- **XBRLParser**: Processes modern XBRL financial data
- **FilingParser**: Unified parser orchestrator

### Core Engine
- **TieredProcessor**: Main processing pipeline
- **ParserManager**: Parser coordination and selection
- **DatabaseResultManager**: Results storage and management

### Database Models
- **Filing**: Enhanced with SGML/XBRL fields
- **XbrlFact**: XBRL data points storage
- **Dead Letter Queue**: Failed processing tracking

## 🛠️ Development

### Project Structure
```
sec_extractor/
├── parsers/                # SEC parser integration
│   ├── base.py            # Parser interfaces
│   ├── sgml_parser.py     # SGML processing
│   ├── xbrl_parser.py     # XBRL processing
│   └── integrated_parser.py # Unified orchestrator
├── core/
│   ├── parser_integration.py # TieredProcessor bridge
│   └── tiered_processor.py   # Main processing engine
└── storage/
    └── models.py          # Database models
```

### Adding New Parsers

1. Implement `BaseParser` interface
2. Add to `ParserManager` 
3. Create appropriate tests
4. Update documentation

## 📈 Performance Optimization

The system has been optimized for:
- **High throughput processing**
- **Memory efficient parsing**
- **Graceful error handling**
- **Scalable architecture**

## 🐳 Production Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  edgar:
    build: .
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/edgar
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=edgar
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Add comprehensive tests** for new functionality
4. **Ensure all tests pass**: `pytest tests/ -v`
5. **Follow code style**: `black . && flake8`
6. **Submit a pull request** with detailed description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎉 Acknowledgments

- **[John Friedman](https://github.com/jfriedi)** - Creator of the exceptional `secsgml` and `secxbrl` parsing libraries
- **SEC EDGAR System** - For providing comprehensive financial data access
- **Python Community** - For robust tooling and ecosystem support

---

**�️ Edgar SEC Parser - Transforming regulatory document processing with intelligent parsing technology**
