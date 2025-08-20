# Tests Directory Structure

This directory contains comprehensive tests for the Edgar SEC Parser project.

## 📁 Directory Organization

### `performance/`
- **Purpose**: Performance benchmarking and load testing
- **Files**: Parser throughput, memory usage, stress tests
- **Run with**: `python tests/performance/test_parser_performance.py`

### `test_parsers/`
- **Purpose**: Integration tests for parsing functionality
- **Files**: Parser integration, end-to-end parsing workflows
- **Run with**: `pytest tests/test_parsers/ -v`

### `integration/`
- **Purpose**: End-to-end system integration tests
- **Files**: Database integration, full workflow validation
- **Run with**: `pytest tests/integration/ -v`

### `smoke/`
- **Purpose**: Basic system health and connectivity checks
- **Files**: Database connectivity, environment validation
- **Run with**: `python tests/smoke/db_smoketest.py`

## 🧪 Running Tests

### All Tests
```bash
pytest tests/ -v
```

### By Category
```bash
# Unit tests (fast)
pytest sec_extractor/tests/ -v

# Integration tests (slower)
pytest tests/integration/ -v

# Performance tests
python tests/performance/test_parser_performance.py

# Smoke tests
python tests/smoke/db_smoketest.py
```

### With Coverage
```bash
pytest tests/ --cov=sec_extractor --cov-report=html
```

## 📋 Test Guidelines

1. **Unit tests** go in `sec_extractor/tests/`
2. **Integration tests** go in `tests/integration/`
3. **Performance tests** go in `tests/performance/`
4. **Smoke tests** go in `tests/smoke/`
5. All tests should be independent and idempotent
6. Use fixtures for common test data
7. Mock external dependencies in unit tests
