# Integration Guide: Code Analysis System

## System Overview

The Code Analysis System has been successfully integrated into the GigaOffice Server project. This document provides guidance on using the system effectively.

## What Has Been Implemented

### Complete Feature Set
✅ Unused import detection with multi-phase analysis  
✅ Type annotation validation and error detection  
✅ FastAPI-specific pattern recognition  
✅ Parallel processing for performance  
✅ Multiple output formats (Console, JSON)  
✅ Configurable analysis rules  
✅ Comprehensive CLI interface  

## Quick Start

### 1. Installation
The system is already integrated. Just install the dependency:
```bash
pip install pyyaml
```

### 2. Run Analysis
```bash
# Analyze the app directory
python -m code_analysis app/

# Or use the quick start script
bash run_code_analysis.sh
```

### 3. Review Results
The system will output a color-coded report showing:
- Unused imports with line numbers
- Type errors with suggestions
- Summary statistics

## Integration with Development Workflow

### Pre-commit Checks
Add to your pre-commit hook:
```bash
#!/bin/bash
python -m code_analysis app/ --no-color --quiet
exit_code=$?
if [ $exit_code -eq 1 ]; then
    echo "⚠️  Code quality issues found. Please review."
fi
exit 0  # Don't block commits, just warn
```

### CI/CD Pipeline
Add to your CI/CD configuration:
```yaml
- name: Code Analysis
  run: |
    python -m code_analysis app/ --output report.json --no-color
  continue-on-error: true

- name: Upload Report
  uses: actions/upload-artifact@v2
  with:
    name: code-analysis-report
    path: report.json
```

### IDE Integration
For VS Code, add to `.vscode/tasks.json`:
```json
{
  "label": "Run Code Analysis",
  "type": "shell",
  "command": "python -m code_analysis app/",
  "group": "test",
  "presentation": {
    "reveal": "always",
    "panel": "new"
  }
}
```

## Customization

### Project-Specific Configuration

Edit `code_analysis/config.yaml` to customize for your project:

```yaml
# Exclude test files
exclude_directories:
  - "tests"
  - "migrations"
  - "__pycache__"

# Adjust FastAPI checking
analysis_rules:
  fastapi_patterns:
    check_dependency_injection: true
    check_router_registration: true
    check_pydantic_models: true

# Performance tuning
performance:
  parallel_processing: true
  max_workers: 8  # Increase for larger projects
```

### Ignoring False Positives

For legitimate cases where imports appear unused:

1. **Use comments** (for human reference):
```python
# Used in type checking only
from typing import TYPE_CHECKING
```

2. **Configure exclusions** in `config.yaml`:
```yaml
exclusions:
  - "*/conftest.py"  # pytest fixtures
  - "*/migrations/*"  # database migrations
```

## Understanding Results

### Unused Import Example
```
app/main.py
  Line 5: from typing import Optional
    Type: standard
    Unused: Optional
    Suggestions:
      - Remove this import statement entirely
```

**Action**: Remove line 5 or use `Optional` in the code.

### Type Error Example
```
app/services/user.py
  Line 23: missing_import
    Symbol: UserModel
    Context: Return type of function 'get_user'
    Suggestion: Import the type: UserModel
```

**Action**: Add `from app.models.user import UserModel`

### False Positive Handling

If the system incorrectly flags an import as unused:

1. Check if it's used in:
   - Decorators
   - Type annotations
   - String literals
   - `__all__` declarations

2. If it's a framework-specific pattern not yet recognized, add it to the configuration or report as an enhancement.

## Performance Considerations

### Large Codebases
For projects with 100+ files:

```bash
# Use parallel processing (default)
python -m code_analysis app/

# Or adjust worker count
python -m code_analysis app/ --config custom_config.yaml
# (Set max_workers in config)
```

### Incremental Analysis
For daily development, analyze specific modules:
```bash
# Just the services directory
python -m code_analysis app/services/

# Single file
python -m code_analysis app/main.py
```

## Reporting

### Console Reports
Best for:
- Daily development
- Quick checks
- Interactive analysis

```bash
python -m code_analysis app/
```

### JSON Reports
Best for:
- CI/CD integration
- Programmatic processing
- Long-term tracking

```bash
python -m code_analysis app/ --output report.json
```

### Both Formats
```bash
python -m code_analysis app/ --format both --output report.json
```

## Common Use Cases

### 1. Clean Up Before Release
```bash
python -m code_analysis app/ --verbose
# Review and fix all issues
```

### 2. Check Specific Module
```bash
python -m code_analysis app/services/
```

### 3. Generate Reports for Team
```bash
python -m code_analysis app/ --output weekly-report.json
# Share report.json with team
```

### 4. Quick Health Check
```bash
python -m code_analysis app/ --quiet
echo $?  # 0 = clean, 1 = issues found
```

## Maintenance

### Updating Configuration
When project structure changes:

1. Update `exclude_directories` in config.yaml
2. Add new framework patterns if needed
3. Adjust performance settings

### Regular Analysis
Recommended schedule:
- **Daily**: Run on changed files during development
- **Weekly**: Full project analysis
- **Pre-release**: Comprehensive check with cleanup

## Troubleshooting

### Issue: Too many false positives
**Solution**: Adjust configuration, particularly `check_string_imports` and `check_docstrings`

### Issue: Analysis is slow
**Solution**: 
- Enable parallel processing
- Increase `max_workers`
- Analyze smaller modules

### Issue: Missing dependencies
**Solution**: 
```bash
pip install pyyaml
```

### Issue: Type errors in generated code
**Solution**: Exclude generated directories in config.yaml

## Best Practices

1. **Run regularly**: Make it part of your development routine
2. **Fix incrementally**: Don't try to fix everything at once
3. **Review suggestions**: Not all suggestions may apply to your use case
4. **Keep config updated**: Adjust as your project evolves
5. **Share reports**: Use JSON reports for team collaboration

## Support

For detailed information, see:
- `README.md` - Full documentation
- `QUICK_START.md` - Quick reference
- `IMPLEMENTATION_SUMMARY.md` - Technical details

## Next Steps

1. Run initial analysis: `python -m code_analysis app/`
2. Review the results
3. Fix critical issues (type errors first)
4. Clean up unused imports
5. Integrate into your workflow
6. Configure for your team's needs

## Success Metrics

After integration, you should see:
- ✅ Cleaner imports
- ✅ Better type safety
- ✅ Reduced code bloat
- ✅ Improved IDE performance
- ✅ Easier code reviews

---

**The system is ready to use immediately. Start with a quick analysis and build from there!**
