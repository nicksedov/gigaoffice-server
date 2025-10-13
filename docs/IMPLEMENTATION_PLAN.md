# Implementation Plan: Structured Response Generation for Chart Data Processing

## Executive Summary

This implementation plan translates the design document into actionable coding tasks for building the structured response generation system for chart data processing in the GigaOffice server. The system will transform user requests into standardized JSON responses aligned with the `ChartResultResponse` class structure.

## Implementation Phases

### Phase 1: YAML Template System (Foundation)
**Goal**: Create comprehensive YAML templates for AI training and template-driven response generation

### Phase 2: Core Services (Business Logic)
**Goal**: Implement the four core service components for chart processing

### Phase 3: Middleware & Validation (Quality Assurance)
**Goal**: Build validation and formatting layers for response integrity

### Phase 4: Integration & Testing (Verification)
**Goal**: Integrate components and validate through comprehensive testing

### Phase 5: Documentation & Optimization (Finalization)
**Goal**: Document APIs and optimize performance

---

## Detailed Task Checklist

## ✅ Phase 1: YAML Template System

### Task 1.1: Enhanced YAML Template Examples
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: None

**Objective**: Create comprehensive YAML example files for chart generation that align with `ChartResultResponse` structure

**Files to Create/Modify**:
- ✅ `/resources/prompts/data-chart/example_01.yaml` (already exists - needs enhancement)
- 📝 `/resources/prompts/data-chart/example_02.yaml` (already exists - needs enhancement)
- 📝 `/resources/prompts/data-chart/example_03.yaml` (already exists - needs enhancement)
- 📝 `/resources/prompts/data-chart/example_04.yaml` (already exists - needs enhancement)
- 📝 `/resources/prompts/data-chart/example_05.yaml` (NEW - multi-series chart)
- 📝 `/resources/prompts/data-chart/example_06.yaml` (NEW - statistical chart)

**Acceptance Criteria**:
- [ ] Each example contains `task`, `request_table`, and `response_table` fields
- [ ] Response tables follow `ChartResultResponse` structure with all fields:
  - [ ] `success` (boolean)
  - [ ] `status` (string matching RequestStatus enum)
  - [ ] `message` (human-readable string)
  - [ ] `chart_config` (complete ChartConfig object)
  - [ ] `tokens_used` (integer)
  - [ ] `processing_time` (float)
- [ ] Examples cover all major chart types: line, column, pie, scatter, area, histogram, box_plot
- [ ] Examples include diverse data patterns: time series, categorical, multi-series, statistical
- [ ] Each ChartConfig includes all sub-components: series_config, position, styling
- [ ] YAML is valid and parseable
- [ ] Formatting is consistent across all examples

**Implementation Details**:
```yaml
# Example structure template
task: "User instruction in natural language"
request_table: |
  {
    "data_range": "A1:B10",
    "chart_data": [
      {
        "name": "Series Name",
        "values": [...],
        "format": "format_string"
      }
    ],
    "chart_type": "line",
    "query_text": "Build line chart"
  }
response_table: |
  {
    "success": true,
    "status": "completed",
    "message": "Chart generated successfully",
    "chart_config": {
      "chart_type": "line",
      "title": "Chart Title",
      "subtitle": null,
      "series_config": {
        "x_axis_column": 0,
        "y_axis_columns": [1],
        "series_names": ["Series 1"],
        "show_data_labels": false,
        "smooth_lines": true
      },
      "position": {
        "x": 400,
        "y": 50,
        "width": 600,
        "height": 400,
        "anchor_cell": "D2"
      },
      "styling": {
        "color_scheme": "office",
        "font_family": "Arial",
        "font_size": 12,
        "background_color": null,
        "border_style": "none",
        "legend_position": "bottom"
      }
    },
    "tokens_used": 450,
    "processing_time": 1.23
  }
```

---

### Task 1.2: Update System Prompt for Structured Output
**Priority**: HIGH | **Effort**: Small | **Dependencies**: Task 1.1

**Objective**: Update system_prompt.txt to enforce structured `ChartResultResponse` output format

**Files to Modify**:
- 📝 `/resources/prompts/data-chart/system_prompt.txt`

**Acceptance Criteria**:
- [ ] Prompt explicitly instructs AI to output ChartResultResponse structure
- [ ] All required fields are documented in the prompt
- [ ] Response format requirements are clear and unambiguous
- [ ] Prompt includes validation requirements
- [ ] Prompt specifies error handling approach
- [ ] Token usage tracking is mentioned

**Implementation Details**:
```text
Ты — виртуальный ассистент для создания графиков и диаграмм в электронных таблицах Р7-Офис.

ВАЖНО: Твой ответ ДОЛЖЕН быть в формате JSON, соответствующем структуре ChartResultResponse:
{
  "success": boolean,        // true если обработка успешна
  "status": string,          // "completed", "processing", "failed", "pending"
  "message": string,         // Человекочитаемое сообщение
  "chart_config": object,    // Конфигурация графика (см. структуру ChartConfig)
  "tokens_used": integer,    // Количество использованных токенов
  "processing_time": float   // Время обработки в секундах
}

[Continue with ChartConfig structure details and validation rules...]
```

---

## ✅ Phase 2: Core Services Implementation

### Task 2.1: Create ChartPromptBuilder Service
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: Task 1.1, Task 1.2

**Objective**: Build service for loading YAML templates and matching them to user requests

**Files to Create**:
- 📝 `/app/services/chart/prompt_builder.py` (NEW)

**Acceptance Criteria**:
- [ ] Implements template loading from YAML files
- [ ] Provides template matching based on user query similarity
- [ ] Supports context injection for personalizing templates
- [ ] Caches loaded templates for performance
- [ ] Handles template parsing errors gracefully
- [ ] Implements semantic similarity scoring for template selection
- [ ] Provides method to build complete prompt with system instructions and examples
- [ ] Unit tests achieve >80% code coverage

**Key Methods to Implement**:
```python
class ChartPromptBuilder:
    def __init__(self, resources_dir: str)
    def load_system_prompt(self) -> str
    def load_examples(self) -> List[Dict[str, Any]]
    def select_best_template(self, user_query: str, data_pattern: str) -> Dict[str, Any]
    def build_prompt(self, user_request: ChartData, selected_template: Dict) -> str
    def inject_context(self, template: Dict, user_data: Dict) -> str
    def calculate_similarity(self, query1: str, query2: str) -> float
```

---

### Task 2.2: Create ChartIntelligenceService
**Priority**: HIGH | **Effort**: Large | **Dependencies**: Task 2.1

**Objective**: Implement AI-driven chart generation with structured response parsing

**Files to Create**:
- 📝 `/app/services/chart/intelligence.py` (NEW)

**Acceptance Criteria**:
- [ ] Integrates with GigaChat API for AI processing
- [ ] Uses ChartPromptBuilder for prompt construction
- [ ] Parses AI responses into ChartResultResponse objects
- [ ] Implements chart type recommendation logic
- [ ] Handles data pattern analysis (time series, categorical, multi-series, statistical)
- [ ] Implements retry logic for AI API failures
- [ ] Tracks token usage and processing time
- [ ] Validates AI responses before returning
- [ ] Handles edge cases: malformed responses, timeouts, invalid JSON
- [ ] Unit tests with mocked AI responses

**Key Methods to Implement**:
```python
class ChartIntelligenceService:
    def __init__(self, gigachat_client, prompt_builder: ChartPromptBuilder)
    
    async def generate_chart_response(
        self, 
        chart_data: ChartData, 
        preferences: Optional[Dict]
    ) -> ChartResultResponse
    
    async def recommend_chart_type(
        self,
        chart_data: ChartData,
        query_text: str
    ) -> ChartType
    
    def analyze_data_pattern(self, chart_data: ChartData) -> DataPattern
    
    def parse_ai_response(self, raw_response: str) -> ChartResultResponse
    
    def generate_chart_config(
        self,
        chart_data: ChartData,
        chart_type: ChartType,
        preferences: Optional[Dict]
    ) -> ChartConfig
    
    async def _call_ai_with_retry(self, prompt: str, max_retries: int = 3) -> str
```

---

### Task 2.3: Create ChartValidationService
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: None

**Objective**: Build comprehensive validation service for ChartResultResponse and ChartConfig

**Files to Create**:
- 📝 `/app/services/chart/validation.py` (NEW)

**Acceptance Criteria**:
- [ ] Validates ChartResultResponse structure completeness
- [ ] Validates ChartConfig against business rules
- [ ] Checks R7-Office compatibility requirements
- [ ] Validates data series mapping correctness
- [ ] Checks position calculations for overlap avoidance
- [ ] Validates color scheme and styling options
- [ ] Provides detailed error messages for validation failures
- [ ] Returns validation summary with is_valid and errors list
- [ ] Unit tests cover all validation rules

**Key Methods to Implement**:
```python
class ChartValidationService:
    def validate_response(self, response: ChartResultResponse) -> Tuple[bool, List[str]]
    
    def validate_chart_config(self, config: ChartConfig) -> Tuple[bool, List[str]]
    
    def validate_series_config(self, series: SeriesConfig, data: ChartData) -> Tuple[bool, List[str]]
    
    def validate_position(self, position: ChartPosition) -> Tuple[bool, List[str]]
    
    def validate_styling(self, styling: ChartStyling) -> Tuple[bool, List[str]]
    
    def validate_r7_office_compatibility(self, config: ChartConfig) -> Tuple[bool, List[str]]
    
    def get_validation_summary(self, response: ChartResultResponse) -> Dict[str, Any]
```

**Validation Rules to Implement**:
- Required fields presence check
- Data type validation
- Range validations (font_size: 8-72, position coordinates >= 0)
- Enum value validation (ChartType, ColorScheme, etc.)
- Cross-field consistency (x_axis_column < total columns)
- R7-Office specific constraints

---

### Task 2.4: Create ResponseFormatterService
**Priority**: MEDIUM | **Effort**: Small | **Dependencies**: Task 2.3

**Objective**: Ensure consistent JSON formatting and serialization

**Files to Create**:
- 📝 `/app/services/chart/formatter.py` (NEW)

**Acceptance Criteria**:
- [ ] Formats ChartResultResponse to standardized JSON
- [ ] Handles datetime serialization correctly
- [ ] Ensures proper null handling
- [ ] Validates JSON structure before returning
- [ ] Supports pretty-printing for debugging
- [ ] Handles enum serialization
- [ ] Unit tests verify formatting consistency

**Key Methods to Implement**:
```python
class ResponseFormatterService:
    def format_response(self, response: ChartResultResponse) -> Dict[str, Any]
    
    def serialize_to_json(self, response: ChartResultResponse, pretty: bool = False) -> str
    
    def format_chart_config(self, config: ChartConfig) -> Dict[str, Any]
    
    def format_error_response(self, error: Exception) -> ChartResultResponse
    
    def validate_json_structure(self, json_str: str) -> bool
```

---

## ✅ Phase 3: Middleware & Integration

### Task 3.1: Create Response Validation Middleware
**Priority**: MEDIUM | **Effort**: Small | **Dependencies**: Task 2.3

**Objective**: Implement middleware for automatic response validation in API layer

**Files to Create**:
- 📝 `/app/middleware/chart_response_validator.py` (NEW)

**Acceptance Criteria**:
- [ ] Intercepts chart generation responses
- [ ] Validates responses before returning to client
- [ ] Logs validation failures
- [ ] Returns appropriate error responses for invalid data
- [ ] Adds validation metadata to responses
- [ ] Unit tests with FastAPI TestClient

**Implementation Details**:
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class ChartResponseValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Validate chart responses
        if request.url.path.startswith("/api/v1/charts/"):
            # Validate response structure
            pass
            
        return response
```

---

### Task 3.2: Update ChartProcessingService Integration
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: Task 2.2, Task 2.3, Task 2.4

**Objective**: Integrate new services into existing ChartProcessingService

**Files to Modify**:
- 📝 `/app/services/chart/processor.py`

**Acceptance Criteria**:
- [ ] Uses ChartIntelligenceService for generation
- [ ] Applies ChartValidationService for validation
- [ ] Uses ResponseFormatterService for output formatting
- [ ] Updates database with structured responses
- [ ] Maintains backward compatibility
- [ ] Handles all error scenarios gracefully
- [ ] Logs processing steps for debugging
- [ ] Integration tests validate full flow

**Changes to Implement**:
```python
# Update imports
from app.services.chart.intelligence import chart_intelligence_service
from app.services.chart.validation import chart_validation_service
from app.services.chart.formatter import response_formatter_service

# Update _generate_chart method
async def _generate_chart(self, chart_request: ChartGenerationRequest, request_id: str) -> Dict[str, Any]:
    # Generate structured response
    chart_response = await chart_intelligence_service.generate_chart_response(
        chart_request.chart_data,
        chart_request.chart_preferences
    )
    
    # Validate response
    is_valid, errors = chart_validation_service.validate_response(chart_response)
    
    # Format for output
    formatted_response = response_formatter_service.format_response(chart_response)
    
    return formatted_response
```

---

### Task 3.3: Enhance ChartResultResponse Model
**Priority**: MEDIUM | **Effort**: Small | **Dependencies**: None

**Objective**: Add additional validation and helper methods to ChartResultResponse

**Files to Modify**:
- 📝 `/app/models/api/chart.py`

**Acceptance Criteria**:
- [ ] Add field-level validators for all fields
- [ ] Add custom validators for cross-field validation
- [ ] Add helper methods: is_successful(), has_errors(), get_summary()
- [ ] Add example JSON in docstring
- [ ] Ensure Pydantic v2 compatibility
- [ ] Unit tests for all validators

**Enhancements to Add**:
```python
class ChartResultResponse(BaseModel):
    """Response model for chart generation result"""
    success: bool = Field(..., description="Request success status")
    status: str = Field(..., description="Current processing status")
    message: str = Field(..., description="Human-readable status message")
    chart_config: Optional[ChartConfig] = Field(None, description="Generated chart configuration")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used", ge=0)
    processing_time: Optional[float] = Field(None, description="Processing time in seconds", ge=0.0)
    
    @field_validator('status')
    def validate_status(cls, v):
        """Validate status against RequestStatus enum"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v
    
    @model_validator(mode='after')
    def validate_success_consistency(self):
        """Validate that success flag matches status and chart_config presence"""
        if self.success and self.chart_config is None:
            raise ValueError('Successful response must include chart_config')
        if self.success and self.status == 'failed':
            raise ValueError('Success cannot be true when status is failed')
        return self
    
    def is_successful(self) -> bool:
        return self.success and self.chart_config is not None
    
    def has_errors(self) -> bool:
        return not self.success or self.status == 'failed'
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'status': self.status,
            'message': self.message,
            'has_chart': self.chart_config is not None
        }
```

---

## ✅ Phase 4: Testing & Validation

### Task 4.1: Unit Tests for Template Processing
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: Task 2.1

**Objective**: Create comprehensive unit tests for YAML template loading and processing

**Files to Create**:
- 📝 `/tests/unit/services/chart/test_prompt_builder.py` (NEW)

**Test Coverage Requirements**:
- [ ] Test YAML loading success and error cases
- [ ] Test template selection algorithm
- [ ] Test similarity scoring
- [ ] Test context injection
- [ ] Test caching mechanism
- [ ] Test error handling for malformed YAML
- [ ] Test edge cases: empty files, missing fields
- [ ] Achieve >85% code coverage

**Test Cases to Implement**:
```python
def test_load_system_prompt_success():
    """Test successful loading of system prompt"""
    pass

def test_load_examples_all_files():
    """Test loading all example YAML files"""
    pass

def test_select_best_template_time_series():
    """Test template selection for time series data"""
    pass

def test_inject_context_replaces_placeholders():
    """Test context injection replaces template variables"""
    pass

def test_template_caching_reduces_io():
    """Test that templates are cached after first load"""
    pass

def test_malformed_yaml_raises_error():
    """Test error handling for invalid YAML"""
    pass
```

---

### Task 4.2: Unit Tests for Response Validation
**Priority**: HIGH | **Effort**: Medium | **Dependencies**: Task 2.3

**Objective**: Create unit tests for ChartValidationService

**Files to Create**:
- 📝 `/tests/unit/services/chart/test_validation.py` (NEW)

**Test Coverage Requirements**:
- [ ] Test all validation rules
- [ ] Test valid and invalid inputs for each validator
- [ ] Test R7-Office compatibility checks
- [ ] Test validation error message generation
- [ ] Test edge cases for numeric ranges
- [ ] Achieve >90% code coverage

**Test Cases to Implement**:
```python
def test_validate_response_valid():
    """Test validation of valid ChartResultResponse"""
    pass

def test_validate_response_missing_required_field():
    """Test validation fails when required field missing"""
    pass

def test_validate_chart_config_invalid_position():
    """Test position validation with negative coordinates"""
    pass

def test_validate_series_config_column_out_of_range():
    """Test series config validation with invalid column index"""
    pass

def test_validate_r7_office_compatibility_unsupported_feature():
    """Test R7-Office compatibility check for unsupported features"""
    pass

def test_validation_summary_structure():
    """Test validation summary contains all expected fields"""
    pass
```

---

### Task 4.3: Integration Tests for Chart Generation Flow
**Priority**: HIGH | **Effort**: Large | **Dependencies**: Task 3.2

**Objective**: Create end-to-end integration tests for complete chart generation

**Files to Create**:
- 📝 `/tests/integration/test_chart_generation_flow.py` (NEW)

**Test Coverage Requirements**:
- [ ] Test complete flow from API request to database storage
- [ ] Test all chart types
- [ ] Test error scenarios
- [ ] Test concurrent request handling
- [ ] Test Kafka message processing
- [ ] Use test database and mock GigaChat API
- [ ] Achieve >75% integration coverage

**Test Scenarios**:
```python
@pytest.mark.asyncio
async def test_line_chart_generation_end_to_end():
    """Test complete line chart generation from API to database"""
    pass

@pytest.mark.asyncio
async def test_pie_chart_with_invalid_data():
    """Test error handling for invalid pie chart data"""
    pass

@pytest.mark.asyncio
async def test_concurrent_chart_requests():
    """Test system handles multiple concurrent requests"""
    pass

@pytest.mark.asyncio
async def test_kafka_message_processing():
    """Test Kafka consumer processes chart requests correctly"""
    pass

@pytest.mark.asyncio
async def test_database_persistence():
    """Test chart config is correctly persisted to database"""
    pass
```

---

### Task 4.4: Performance Tests
**Priority**: MEDIUM | **Effort**: Medium | **Dependencies**: Task 3.2

**Objective**: Create performance benchmarks and load tests

**Files to Create**:
- 📝 `/tests/performance/test_chart_generation_performance.py` (NEW)

**Performance Targets** (from design doc):
- [ ] Response generation time: < 2 seconds
- [ ] Memory usage: < 100MB per request
- [ ] Concurrent requests: 50 requests/second
- [ ] Template matching accuracy: > 95%

**Test Cases**:
```python
def test_response_generation_time():
    """Test response generation completes within 2 seconds"""
    pass

def test_memory_usage_per_request():
    """Test memory usage stays below 100MB per request"""
    pass

def test_concurrent_request_throughput():
    """Test system handles 50 concurrent requests per second"""
    pass

def test_template_matching_accuracy():
    """Test template matching achieves >95% accuracy"""
    pass
```

---

## ✅ Phase 5: Documentation & Finalization

### Task 5.1: Update API Documentation
**Priority**: MEDIUM | **Effort**: Small | **Dependencies**: All previous tasks

**Objective**: Document new structured response format in Swagger/OpenAPI

**Files to Modify**:
- 📝 `/docs/swagger.yaml`

**Acceptance Criteria**:
- [ ] Add complete ChartResultResponse schema
- [ ] Add complete ChartConfig schema with all sub-schemas
- [ ] Add example responses for all chart types
- [ ] Document validation rules
- [ ] Document error responses
- [ ] Add usage examples

**Schema to Add**:
```yaml
components:
  schemas:
    ChartResultResponse:
      type: object
      required:
        - success
        - status
        - message
      properties:
        success:
          type: boolean
          description: Request success status
        status:
          type: string
          enum: [pending, processing, completed, failed]
          description: Current processing status
        message:
          type: string
          description: Human-readable status message
        chart_config:
          $ref: '#/components/schemas/ChartConfig'
        tokens_used:
          type: integer
          minimum: 0
          description: Number of AI tokens used
        processing_time:
          type: number
          format: float
          minimum: 0
          description: Processing time in seconds
      example:
        success: true
        status: completed
        message: "Chart generated successfully"
        chart_config:
          chart_type: line
          title: "Sales Over Time"
          # ... full example
        tokens_used: 450
        processing_time: 1.23
```

---

### Task 5.2: Create Developer Documentation
**Priority**: MEDIUM | **Effort**: Small | **Dependencies**: All previous tasks

**Objective**: Create comprehensive developer guide for the system

**Files to Create**:
- 📝 `/docs/CHART_GENERATION_GUIDE.md` (NEW)

**Documentation Sections**:
- [ ] System architecture overview
- [ ] Component descriptions
- [ ] Data flow diagrams
- [ ] YAML template structure guide
- [ ] Adding new chart types guide
- [ ] Debugging guide
- [ ] Performance optimization tips
- [ ] Common issues and solutions

---

## Implementation Timeline

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| **Phase 1: Templates** | 1.1, 1.2 | 2-3 days | None |
| **Phase 2: Services** | 2.1, 2.2, 2.3, 2.4 | 7-10 days | Phase 1 |
| **Phase 3: Integration** | 3.1, 3.2, 3.3 | 3-4 days | Phase 2 |
| **Phase 4: Testing** | 4.1, 4.2, 4.3, 4.4 | 5-7 days | Phase 3 |
| **Phase 5: Documentation** | 5.1, 5.2 | 2-3 days | Phase 4 |
| **Total** | 15 tasks | **19-27 days** | - |

---

## Success Metrics

### Code Quality Metrics
- [ ] Unit test coverage: >85%
- [ ] Integration test coverage: >75%
- [ ] No critical Pylint warnings
- [ ] All type hints validated with mypy
- [ ] Code review approval from 2+ developers

### Performance Metrics
- [ ] Response generation: <2s (95th percentile)
- [ ] Memory usage: <100MB per request
- [ ] Throughput: 50 requests/second
- [ ] Template matching accuracy: >95%

### Functional Metrics
- [ ] All chart types supported: line, column, pie, scatter, area, histogram, box_plot
- [ ] R7-Office compatibility: 100%
- [ ] Schema validation: 100% compliance
- [ ] Zero production errors in first week

---

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| AI response quality variation | HIGH | Implement retry logic, template refinement, response validation |
| Performance degradation | MEDIUM | Caching, async processing, load testing before deployment |
| R7-Office API changes | MEDIUM | Abstraction layer, compatibility checks, version pinning |
| Template maintenance overhead | LOW | Clear documentation, versioning system, automated validation |

---

## Dependencies & Requirements

### External Dependencies
- GigaChat API access and credentials
- R7-Office API documentation
- Kafka message queue setup

### Python Packages
- pydantic >= 2.0 (data validation)
- PyYAML >= 6.0 (YAML parsing)
- pytest >= 7.0 (testing)
- pytest-asyncio (async testing)
- pytest-cov (coverage reporting)

### Infrastructure
- Database: PostgreSQL with chart_requests table
- Message Queue: Kafka for async processing
- Caching: Redis (optional for template caching)

---

## Rollout Strategy

### Phase 1: Development (Week 1-3)
- Implement all core components
- Complete unit and integration tests
- Code review and refinement

### Phase 2: Staging (Week 4)
- Deploy to staging environment
- Load testing and performance validation
- Bug fixes and optimization

### Phase 3: Production (Week 5)
- Gradual rollout: 10% → 50% → 100% traffic
- Monitor error rates and performance
- Immediate rollback capability

### Phase 4: Post-Launch (Week 6+)
- Monitor production metrics
- Gather user feedback
- Iterate on template quality
- Performance optimization

---

## Appendix: File Structure

```
gigaoffice-server/
├── app/
│   ├── models/
│   │   └── api/
│   │       └── chart.py                    [MODIFY - Task 3.3]
│   ├── services/
│   │   └── chart/
│   │       ├── __init__.py                 [MODIFY - exports]
│   │       ├── processor.py                [MODIFY - Task 3.2]
│   │       ├── prompt_builder.py           [CREATE - Task 2.1]
│   │       ├── intelligence.py             [CREATE - Task 2.2]
│   │       ├── validation.py               [CREATE - Task 2.3]
│   │       └── formatter.py                [CREATE - Task 2.4]
│   └── middleware/
│       └── chart_response_validator.py     [CREATE - Task 3.1]
├── resources/
│   └── prompts/
│       └── data-chart/
│           ├── system_prompt.txt           [MODIFY - Task 1.2]
│           ├── example_01.yaml             [MODIFY - Task 1.1]
│           ├── example_02.yaml             [MODIFY - Task 1.1]
│           ├── example_03.yaml             [MODIFY - Task 1.1]
│           ├── example_04.yaml             [MODIFY - Task 1.1]
│           ├── example_05.yaml             [CREATE - Task 1.1]
│           └── example_06.yaml             [CREATE - Task 1.1]
├── tests/
│   ├── unit/
│   │   └── services/
│   │       └── chart/
│   │           ├── test_prompt_builder.py  [CREATE - Task 4.1]
│   │           ├── test_intelligence.py    [CREATE - Task 4.1]
│   │           └── test_validation.py      [CREATE - Task 4.2]
│   ├── integration/
│   │   └── test_chart_generation_flow.py   [CREATE - Task 4.3]
│   └── performance/
│       └── test_chart_generation_performance.py [CREATE - Task 4.4]
└── docs/
    ├── swagger.yaml                         [MODIFY - Task 5.1]
    ├── CHART_GENERATION_GUIDE.md           [CREATE - Task 5.2]
    └── IMPLEMENTATION_PLAN.md              [CREATE - This document]
```

---

## Next Steps

1. **Review this plan** with the development team
2. **Set up task tracking** in project management tool
3. **Begin Phase 1** with YAML template creation
4. **Schedule daily standups** during implementation
5. **Plan code review sessions** for each phase completion

---

## Questions & Clarifications

Before starting implementation, clarify:

1. Which GigaChat API version and model to use?
2. Database schema for chart_requests table - is it already created?
3. Redis availability for template caching?
4. R7-Office API version and documentation access?
5. Staging environment setup timeline?

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-13  
**Author**: AI Implementation Team  
**Status**: Ready for Review
