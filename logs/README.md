# Logs Directory

This directory contains application logs and performance reports.

## 📁 Structure

- **Application logs** are written here during runtime
- **Performance reports** are generated during benchmarking
- **Debug logs** from various system components

## 📊 Examples

See `examples/` subdirectory for sample log formats and performance reports.

## 🔧 Configuration

Log level and format can be configured via environment variables:
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- Logs are automatically rotated and cleaned up

## ⚠️ Note

This directory is excluded from version control (see .gitignore) to prevent
sensitive production data from being committed.
