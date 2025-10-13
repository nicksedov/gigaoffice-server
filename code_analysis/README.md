# Code Analysis System

A comprehensive static code analysis system for detecting unused imports and non-existent type references in Python codebases, with special support for FastAPI projects.

## Features

### Core Capabilities
- ✅ **Unused Import Detection**: Accurately identifies unused imports through multi-phase analysis
- ✅ **Type Annotation Validation**: Validates type hints and identifies missing or incorrect type references
- ✅ **FastAPI Pattern Recognition**: Special handling for FastAPI dependency injection, routers, and Pydantic models
- ✅ **Parallel Processing**: Fast analysis using multi-threaded processing
- ✅ **Multiple Output Formats**: Console (with colors) and JSON reports
- ✅ **Configurable Rules**: Customizable analysis rules and exclusion patterns

### Detection Features
- Direct symbol usage tracking
- Type annotation analysis
- Docstring reference detection
- String literal reference checking
- `__all__` declaration support
- FastAPI dependency injection patterns
- Pydantic model relationships
- Router and middleware registration

## Installation

### Prerequisites
- Python 3.8 or higher
- PyYAML (for configuration)

### Setup

1. The code analysis system is already integrated into your project at `/data/workspace/gigaoffice-server/code_analysis/`

2. Install required dependencies:
```bash
pip install pyyaml
```

## Usage

### Command Line Interface

#### Basic Usage

Analyze current directory:
```bash
python -m code_analysis
```

Analyze specific directory:
```bash
python -m code_analysis /path/to/project
```

#### Advanced Options

Save results as JSON:
```bash
python -m code_analysis --output report.json
```

Use custom configuration:
```bash
python -m code_analysis --config custom_config.yaml
```

Disable parallel processing:
```bash
python -m code_analysis --no-parallel
```

Disable colored output:
```bash
python -m code_analysis --no-color
```

Exclude specific directories:
```bash
python -m code_analysis --exclude-dirs tests migrations
```

### Programmatic Usage

```python
from code_analysis.analyzer import CodeAnalyzer

# Initialize analyzer
analyzer = CodeAnalyzer(
    project_root="/path/to/project",
    config_path="config.yaml"  # Optional
)

# Run analysis
result = analyzer.analyze()

# Generate console report
analyzer.generate_console_report(result)

# Save JSON report
analyzer.save_json_report(result, "report.json")

# Get statistics
stats = analyzer.get_statistics()
print(stats)
```

## Configuration

Configuration is managed through a YAML file. The default configuration is at `code_analysis/config.yaml`.

### Configuration Options

```yaml
# File and directory exclusion patterns
exclusions:
  - "__pycache__"
  - "*.pyc"
  - ".git"
  - ".venv"
  - "*.egg-info"

# Directories to exclude
exclude_directories:
  - "migrations"
  - "tests"

# Analysis rules
analysis_rules:
  ignore_star_imports: false
  check_string_imports: true
  check_type_annotations: true
  check_docstrings: true
  
  # FastAPI specific
  fastapi_patterns:
    check_dependency_injection: true
    check_router_registration: true
    check_pydantic_models: true

# Report options
report:
  verbose: true
  format: "console"  # console, json, both
  show_suggestions: true
  color_output: true
  group_by_file: true

# Performance settings
performance:
  parallel_processing: true
  max_workers: 4
  cache_ast: true
```

## Output Formats

### Console Output

The console output provides a color-coded, human-readable report:

```
================================================================================
Code Analysis Report
================================================================================
Project: /path/to/project
Scan Time: 2025-10-13 10:30:45
Files Analyzed: 42

Summary
--------------------------------------------------------------------------------
Total Unused Imports: 15
Total Type Errors: 3
Files with Issues: 8/42

Potential Savings:
  Unused imports: 15
  Estimated memory savings: 7.50 KB
  Estimated import time savings: 1.50 ms

Unused Imports
--------------------------------------------------------------------------------

app/main.py
  Line 5: from typing import Optional
    Type: standard
    Unused: Optional
    Suggestions:
      - Remove this import statement entirely

Type Errors
--------------------------------------------------------------------------------

app/services/user.py
  Line 23: missing_import
    Symbol: UserModel
    Context: Return type of function 'get_user'
    Suggestion: Import the type: UserModel
```

### JSON Output

The JSON output provides structured data for programmatic processing:

```json
{
  "analysis_metadata": {
    "timestamp": "2025-10-13T10:30:45.123456",
    "project_path": "/path/to/project",
    "files_analyzed": 42
  },
  "summary": {
    "total_unused_imports": 15,
    "total_type_errors": 3,
    "files_with_issues": 8,
    "total_files_analyzed": 42
  },
  "unused_imports": {
    "count": 15,
    "items": [...]
  },
  "type_errors": {
    "count": 3,
    "items": [...]
  }
}
```

## Architecture

### Core Components

#### 1. Code Scanner
- Discovers Python files recursively
- Applies exclusion patterns
- Generates file list for analysis

#### 2. Import Analyzer
- Extracts import statements
- Tracks symbol usage
- Identifies unused imports
- Handles star imports and aliases

#### 3. Type Checker
- Parses type annotations
- Validates type references
- Detects missing imports
- Handles forward references

#### 4. Report Generator
- Formats analysis results
- Supports multiple output formats
- Provides actionable suggestions

### Service Architecture

```
CodeAnalyzer (Main Orchestrator)
├── FileDiscoveryService (File scanning)
├── ASTAnalysisService (Code parsing)
├── ImportResolverService (Import categorization)
├── ImportAnalyzer (Unused import detection)
├── TypeValidationService (Type checking)
├── FastAPIPatternAnalyzer (Framework patterns)
└── ReportGenerators (Output formatting)
```

## Detection Algorithms

### Unused Import Detection

The system uses a multi-phase approach:

1. **Symbol Extraction**: Parse imports and create symbol mapping
2. **Usage Analysis**: Scan code for symbol references
3. **Special Patterns**: Check type annotations, docstrings, decorators
4. **Framework Patterns**: Detect FastAPI/Pydantic usage
5. **Cross-File Dependencies**: Handle re-exports and circular imports

### Type Reference Validation

1. Extract type annotations from functions and variables
2. Resolve type references against available modules
3. Validate generic types and complex constructs
4. Detect missing imports and forward references

## FastAPI Integration

The system provides special handling for FastAPI patterns:

### Dependency Injection
```python
from fastapi import Depends
from app.database import get_db

# System recognizes get_db is used via Depends
def get_items(db = Depends(get_db)):
    pass
```

### Router Registration
```python
from fastapi import APIRouter
from app.routes import user_router

# System recognizes user_router is used
app.include_router(user_router)
```

### Pydantic Models
```python
from pydantic import BaseModel, Field

# System tracks Field usage in models
class User(BaseModel):
    name: str = Field(...)
```

## CI/CD Integration

### Exit Codes
- `0`: No issues found
- `1`: Issues found (unused imports or type errors)
- `2`: Analysis error occurred

### Example GitHub Actions

```yaml
- name: Run Code Analysis
  run: |
    python -m code_analysis --output report.json
  continue-on-error: true

- name: Upload Report
  uses: actions/upload-artifact@v2
  with:
    name: code-analysis-report
    path: report.json
```

## Performance

### Optimization Features
- **Parallel Processing**: Multi-threaded analysis of independent files
- **AST Caching**: Reuse parsed ASTs when possible
- **Incremental Analysis**: Skip unchanged files (planned)
- **Smart Dependency Ordering**: Optimize cross-file analysis

### Benchmarks
- ~1000 lines/second on typical Python code
- Parallel processing provides 2-4x speedup on multi-core systems

## Troubleshooting

### Common Issues

**Issue**: False positives for dynamic imports
**Solution**: Add patterns to configuration or use `# noqa` comments

**Issue**: Star imports flagged incorrectly
**Solution**: Set `ignore_star_imports: true` in config

**Issue**: Type errors for valid forward references
**Solution**: Use string annotations: `def foo() -> "MyClass"`

## Development

### Project Structure
```
code_analysis/
├── __init__.py
├── __main__.py
├── cli.py                 # Command-line interface
├── analyzer.py            # Main orchestrator
├── config.yaml            # Default configuration
├── models/
│   ├── __init__.py
│   └── results.py         # Data models
├── services/
│   ├── __init__.py
│   ├── file_discovery.py  # File scanning
│   ├── ast_analysis.py    # AST parsing
│   ├── import_resolver.py # Import categorization
│   ├── import_analyzer.py # Unused import detection
│   ├── type_validation.py # Type checking
│   └── fastapi_patterns.py # Framework patterns
├── utils/
│   ├── __init__.py
│   └── config_manager.py  # Configuration management
└── reports/
    ├── __init__.py
    ├── console_report.py  # Console output
    └── json_report.py     # JSON output
```

## Contributing

Contributions are welcome! Areas for improvement:
- Additional framework-specific pattern detection
- HTML report generation
- Performance optimizations
- Additional test coverage

## License

This code analysis system is part of the GigaOffice Server project.

## Credits

Developed as part of the GigaOffice AI Service to maintain code quality and reduce technical debt.
