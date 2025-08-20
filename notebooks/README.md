# Notebooks Directory

This directory contains Jupyter notebooks for development, analysis, and testing.

## 📓 Available Notebooks

### `01-test-datamule-parsers.ipynb`
- **Purpose**: Testing and validation of SEC parser libraries
- **Content**: Parser integration testing, performance analysis
- **Usage**: Development and debugging of parsing functionality

## 🗂️ Outputs

The `notebook_outputs/` directory contains example outputs and test data:
- Sample filing extracts (anonymized)
- Parser test results
- Performance benchmarks

## 🚀 Getting Started

1. **Install Jupyter dependencies:**
```bash
pip install -r requirements-dev.txt
```

2. **Start Jupyter Lab:**
```bash
jupyter lab notebooks/
```

3. **Run notebooks:**
- Open desired notebook
- Run cells sequentially
- Outputs are saved to `notebook_outputs/`

## 🔧 Development Notes

- Notebooks automatically add project root to Python path
- Use for prototyping new parsing features
- Test real SEC filing data interactively
- Generate performance reports and visualizations

## ⚠️ Security

Notebook outputs may contain sensitive data and are excluded from version control.
