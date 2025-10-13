# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install pyyaml
```

### 2. Run Analysis
```bash
# Analyze your project
python -m code_analysis app/
```

That's it! The system will scan your code and report any issues.

## Common Commands

### Analyze with JSON output
```bash
python -m code_analysis app/ --output report.json
```

### Analyze without colors (for CI/CD)
```bash
python -m code_analysis app/ --no-color
```

### Get help
```bash
python -m code_analysis --help
```

## Understanding the Output

### Unused Imports
```
app/main.py
  Line 5: from typing import Optional
    Unused: Optional
    Suggestion: Remove this import statement entirely
```

**What to do**: Remove the unused import from line 5.

### Type Errors
```
app/services/user.py
  Line 23: missing_import
    Symbol: UserModel
    Suggestion: Import the type: UserModel
```

**What to do**: Add `from app.models import UserModel` to the file.

## Exit Codes

- `0` = No issues found ✅
- `1` = Issues found (unused imports or type errors) ⚠️
- `2` = Analysis error ❌

## Configuration

Create `code_analysis/config.yaml` to customize:

```yaml
exclude_directories:
  - "migrations"
  - "tests"

analysis_rules:
  check_type_annotations: true
  fastapi_patterns:
    check_dependency_injection: true
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details
- Run `python example_code_analysis.py` for a programmatic example

## Support

For issues or questions, refer to the comprehensive documentation in README.md.
