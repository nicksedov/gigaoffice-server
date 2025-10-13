# Chart Generation Test Suite

This directory contains comprehensive test suites for the chart generation structured response system.

## Test Organization

```
tests/
├── unit/
│   └── services/
│       └── chart/
│           ├── test_prompt_builder.py       # Template processing tests
│           ├── test_validation.py           # Validation service tests
│           ├── test_formatter.py            # Response formatting tests (TODO)
│           └── test_intelligence.py         # AI intelligence tests (TODO)
├── integration/
│   └── test_chart_generation_flow.py       # End-to-end flow tests (TODO)
├── performance/
│   └── test_chart_generation_performance.py # Performance benchmarks (TODO)
└── README.md                                # This file
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Run Specific Test File
```bash
pytest tests/unit/services/chart/test_prompt_builder.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app/services/chart --cov-report=html
```

## Test Coverage Targets

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| ChartPromptBuilder | >85% | ✅ Test file created |
| ChartValidationService | >90% | ✅ Test file created |
| ChartIntelligenceService | >80% | ⏳ TODO |
| ResponseFormatterService | >85% | ⏳ TODO |
| Integration Tests | >75% | ⏳ TODO |

## Test Files

### test_prompt_builder.py
**Tests**: 20+ test cases  
**Coverage**: Template loading, matching, similarity calculation, caching

**Key Test Categories**:
- System prompt loading and caching
- YAML example loading
- Template selection algorithms
- Similarity calculation with keyword matching
- Prompt building and structure
- Cache management
- Error handling

### test_validation.py
**Tests**: 30+ test cases  
**Coverage**: All validation rules, R7-Office compatibility

**Key Test Categories**:
- ChartResultResponse validation
- ChartConfig validation
- SeriesConfig validation
- Position validation (coordinates, dimensions)
- Styling validation (fonts, colors, borders)
- R7-Office compatibility checks
- Chart data validation
- Validation summaries

## Running Specific Test Categories

### Test Template Matching
```bash
pytest tests/unit/services/chart/test_prompt_builder.py::TestTemplateMatching -v
```

### Test Validation Rules
```bash
pytest tests/unit/services/chart/test_validation.py::TestChartValidationService -v
```

### Test R7-Office Compatibility
```bash
pytest tests/unit/services/chart/test_validation.py -k "r7_office" -v
```

## Test Fixtures

Common fixtures available across tests:

- `prompt_builder`: ChartPromptBuilder instance
- `validator`: ChartValidationService instance
- `valid_chart_config`: Valid ChartConfig object
- `valid_response`: Valid ChartResultResponse object
- `sample_chart_data`: Sample chart data dictionary

## Mocking Strategy

Tests use mocking for:
- File I/O operations (YAML loading)
- GigaChat API calls
- Database operations
- External service dependencies

## Performance Testing

Performance tests validate:
- Response generation time < 2 seconds
- Memory usage < 100MB per request
- Throughput: 50 requests/second
- Template matching accuracy > 95%

## Integration Testing

Integration tests cover:
- End-to-end chart generation flow
- Kafka message processing
- Database persistence
- Error recovery scenarios
- Concurrent request handling

## Contributing Tests

When adding new tests:

1. Follow the existing test structure
2. Use descriptive test names (test_what_it_does_when_condition)
3. Include docstrings for complex tests
4. Use fixtures for common setup
5. Mock external dependencies
6. Test both success and failure cases
7. Aim for >85% code coverage

## Test Dependencies

Required packages (in requirements.txt):
```
pytest>=7.0
pytest-asyncio
pytest-cov
pytest-mock
```

## Continuous Integration

Tests are run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds

CI pipeline requires:
- All tests passing
- Coverage targets met
- No linting errors
