# Planner Agent Extended Logging Implementation

## Overview

This document describes the extended logging implementation for the Planner Agent in the multi-agent orchestration system.

## Implementation Details

### Location
- **File**: `app/services/mcp/agents.py`
- **Class**: `PlannerAgent`

### Features Implemented

#### 1. Execution Plan Logging (FR-1, FR-5)

The `_log_execution_plan()` method logs comprehensive plan details at DEBUG level:

```python
def _log_execution_plan(self, task_id: str, plan: ExecutionPlan):
    """Log detailed execution plan at DEBUG level"""
```

**Logged Information**:
- Task ID (for traceability)
- Total number of steps
- Complexity score (1-10)
- Estimated duration (seconds)
- Detailed step information:
  - Step ID
  - Tool name
  - Expected outcome
  - Parameters (sanitized)
  - Dependencies
  - Rollback actions
  - Retry policy
- Dependency graph summary (sequential, conditional, data dependencies)
- Plan notes and strategic rationale

**Example Log Output**:
```
DEBUG | task_id=test-task-123 | Planner Agent generated execution plan:
  - Steps: 3
  - Complexity Score: 7/10
  - Estimated Duration: 45s
  - Plan Steps:
    [step_1] read_excel_range: Read data from specified range
      Parameters: {"range": "A1:B10"}
    [step_2] process_data: Calculate sum of values (depends on: step_1)
      Parameters: {"operation": "sum"}
    [step_3] write_excel_range: Write result to cell (depends on: step_2)
      Parameters: {"range": "C1", "value": "result"}
      Rollback: Clear cell C1
  - Dependencies: 1 sequential, 0 conditional, 1 data
  - Plan Notes: Multi-step calculation with error handling and rollback support
```

#### 2. Executor Prompt Logging (FR-2)

The `_log_executor_prompt()` method logs the complete prompt text that will be sent to the Executor Agent:

```python
def _log_executor_prompt(self, task_id: str, prompt: str):
    """Log the executor prompt at DEBUG level"""
```

**Logged Information**:
- Task ID (for correlation)
- Complete formatted prompt with:
  - Task description
  - File context (ID, path, range)
  - Execution plan summary
  - Step-by-step instructions
  - Tool parameters
  - Dependency information
  - Execution guidelines

**Example Log Output**:
```
DEBUG | task_id=test-task-123 | Executor prompt generated:
---BEGIN PROMPT---
# Execution Instructions

## Task: Calculate the sum of column A and write to column B

## File Context
- File ID: file-uuid-456
- File Path: /path/to/test.xlsx
- Source Range: {'start': 'A1', 'end': 'A10'}

## Execution Plan (3 steps)
Complexity: 7/10 | Estimated Duration: 45s

### Strategic Notes
Multi-step calculation with error handling and rollback support

### Steps to Execute
[Full step details...]

### Dependency Graph
[Dependency relationships...]

## Execution Guidelines
1. Execute steps in dependency order
2. Validate tool parameters before invocation
3. Handle errors according to retry policy
4. Execute rollback actions on critical failures
5. Record detailed results for each step
---END PROMPT---
```

#### 3. Parameter Sanitization (NFR: Safety)

The `_sanitize_parameters()` method removes sensitive data from logs:

```python
def _sanitize_parameters(self, parameters: dict) -> dict:
    """Sanitize parameters to remove sensitive data from logs"""
```

Sensitive keys that get redacted:
- password
- token
- secret
- api_key
- auth

Can be disabled via: `MCP_PLANNER_LOG_SANITIZE_PARAMS=false`

#### 4. Prompt Truncation (FR-6)

Large prompts are automatically truncated to prevent log overflow:

```python
if len(prompt) > PLANNER_MAX_PROMPT_LENGTH:
    truncated_prompt = prompt[:PLANNER_MAX_PROMPT_LENGTH]
    truncated_prompt += f"\n... [TRUNCATED - {len(prompt) - PLANNER_MAX_PROMPT_LENGTH} chars omitted]"
```

Default max length: 10,000 characters (configurable)

#### 5. Error Handling (FR-6)

All logging operations are wrapped in try-except blocks to ensure:
- Logging failures don't crash the agent
- Warnings are logged if logging fails
- Normal execution continues even if logging fails

```python
try:
    # Logging logic
except Exception as e:
    logger.warning(f"Failed to log execution plan for task {task_id}: {e}")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_PLANNER_LOG_LEVEL` | `DEBUG` | Minimum log level for planner logging |
| `MCP_PLANNER_LOG_MAX_PROMPT_LENGTH` | `10000` | Maximum characters to log for prompts |
| `MCP_PLANNER_LOG_SANITIZE_PARAMS` | `true` | Whether to sanitize sensitive parameters |

### Usage Example

```python
# Set in environment or .env file
MCP_PLANNER_LOG_LEVEL=DEBUG
MCP_PLANNER_LOG_MAX_PROMPT_LENGTH=20000
MCP_PLANNER_LOG_SANITIZE_PARAMS=true
```

## Integration with Orchestrator

The PlannerAgent is used in the orchestrator's `planner_node`:

```python
async def planner_node(state: GraphState) -> GraphState:
    """Planner agent node"""
    logger.info(f"Graph node: planner for task {state.task_id}")
    return await planner.plan(state)
```

The `plan()` method automatically:
1. Creates the execution plan
2. Logs plan details at DEBUG level
3. Builds the executor prompt
4. Logs the executor prompt at DEBUG level
5. Updates the graph state
6. Returns the updated state

## Testing

To test the logging functionality:

1. **Enable DEBUG logging** in your application configuration
2. **Run a workflow** that triggers the planner agent
3. **Check logs** for entries containing:
   - `"Planner Agent generated execution plan:"`
   - `"Executor prompt generated:"`

### Test Script

A test script is provided at `tests/test_planner_logging.py`:

```bash
# Run the test (requires dependencies installed)
python tests/test_planner_logging.py
```

## Requirements Met

| Requirement ID | Status | Description |
|---|---|---|
| FR-1 | ✅ Complete | Log the complete execution plan after plan generation |
| FR-2 | ✅ Complete | Log the formatted prompt text prepared for the Executor Agent |
| FR-3 | ✅ Complete | Use DEBUG log level for all plan-related logging |
| FR-4 | ✅ Complete | Include task_id in all log entries for traceability |
| FR-5 | ✅ Complete | Log plan complexity metrics (step count, complexity score, estimated duration) |
| FR-6 | ✅ Complete | Ensure logging does not impact performance or fail silently on errors |

## Log Filtering

To view only planner-related logs:

```bash
# Filter by component
grep "PlannerAgent" app.log

# Filter by task ID
grep "task_id=abc-123" app.log

# Filter for execution plans
grep "generated execution plan" app.log

# Filter for executor prompts
grep "Executor prompt generated" app.log
```

## Performance Considerations

- Logging is performed at DEBUG level (disabled by default in production)
- All logging operations are wrapped in try-except to prevent crashes
- Large prompts are truncated to prevent memory issues
- Parameter sanitization has minimal overhead (dictionary iteration)

## Future Enhancements

As noted in the design document:
- Structured JSON logging for machine parsing
- Log aggregation and analysis dashboard
- Plan visualization from logs
- Diff comparison between plan versions for retry scenarios
- Metrics extraction from logged plan complexity scores
# Planner Agent Extended Logging Implementation

## Overview

This document describes the extended logging implementation for the Planner Agent in the multi-agent orchestration system.

## Implementation Details

### Location
- **File**: `app/services/mcp/agents.py`
- **Class**: `PlannerAgent`

### Features Implemented

#### 1. Execution Plan Logging (FR-1, FR-5)

The `_log_execution_plan()` method logs comprehensive plan details at DEBUG level:

```python
def _log_execution_plan(self, task_id: str, plan: ExecutionPlan):
    """Log detailed execution plan at DEBUG level"""
```

**Logged Information**:
- Task ID (for traceability)
- Total number of steps
- Complexity score (1-10)
- Estimated duration (seconds)
- Detailed step information:
  - Step ID
  - Tool name
  - Expected outcome
  - Parameters (sanitized)
  - Dependencies
  - Rollback actions
  - Retry policy
- Dependency graph summary (sequential, conditional, data dependencies)
- Plan notes and strategic rationale

**Example Log Output**:
```
DEBUG | task_id=test-task-123 | Planner Agent generated execution plan:
  - Steps: 3
  - Complexity Score: 7/10
  - Estimated Duration: 45s
  - Plan Steps:
    [step_1] read_excel_range: Read data from specified range
      Parameters: {"range": "A1:B10"}
    [step_2] process_data: Calculate sum of values (depends on: step_1)
      Parameters: {"operation": "sum"}
    [step_3] write_excel_range: Write result to cell (depends on: step_2)
      Parameters: {"range": "C1", "value": "result"}
      Rollback: Clear cell C1
  - Dependencies: 1 sequential, 0 conditional, 1 data
  - Plan Notes: Multi-step calculation with error handling and rollback support
```

#### 2. Executor Prompt Logging (FR-2)

The `_log_executor_prompt()` method logs the complete prompt text that will be sent to the Executor Agent:

```python
def _log_executor_prompt(self, task_id: str, prompt: str):
    """Log the executor prompt at DEBUG level"""
```

**Logged Information**:
- Task ID (for correlation)
- Complete formatted prompt with:
  - Task description
  - File context (ID, path, range)
  - Execution plan summary
  - Step-by-step instructions
  - Tool parameters
  - Dependency information
  - Execution guidelines

**Example Log Output**:
```
DEBUG | task_id=test-task-123 | Executor prompt generated:
---BEGIN PROMPT---
# Execution Instructions

## Task: Calculate the sum of column A and write to column B

## File Context
- File ID: file-uuid-456
- File Path: /path/to/test.xlsx
- Source Range: {'start': 'A1', 'end': 'A10'}

## Execution Plan (3 steps)
Complexity: 7/10 | Estimated Duration: 45s

### Strategic Notes
Multi-step calculation with error handling and rollback support

### Steps to Execute
[Full step details...]

### Dependency Graph
[Dependency relationships...]

## Execution Guidelines
1. Execute steps in dependency order
2. Validate tool parameters before invocation
3. Handle errors according to retry policy
4. Execute rollback actions on critical failures
5. Record detailed results for each step
---END PROMPT---
```

#### 3. Parameter Sanitization (NFR: Safety)

The `_sanitize_parameters()` method removes sensitive data from logs:

```python
def _sanitize_parameters(self, parameters: dict) -> dict:
    """Sanitize parameters to remove sensitive data from logs"""
```

Sensitive keys that get redacted:
- password
- token
- secret
- api_key
- auth

Can be disabled via: `MCP_PLANNER_LOG_SANITIZE_PARAMS=false`

#### 4. Prompt Truncation (FR-6)

Large prompts are automatically truncated to prevent log overflow:

```python
if len(prompt) > PLANNER_MAX_PROMPT_LENGTH:
    truncated_prompt = prompt[:PLANNER_MAX_PROMPT_LENGTH]
    truncated_prompt += f"\n... [TRUNCATED - {len(prompt) - PLANNER_MAX_PROMPT_LENGTH} chars omitted]"
```

Default max length: 10,000 characters (configurable)

#### 5. Error Handling (FR-6)

All logging operations are wrapped in try-except blocks to ensure:
- Logging failures don't crash the agent
- Warnings are logged if logging fails
- Normal execution continues even if logging fails

```python
try:
    # Logging logic
except Exception as e:
    logger.warning(f"Failed to log execution plan for task {task_id}: {e}")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_PLANNER_LOG_LEVEL` | `DEBUG` | Minimum log level for planner logging |
| `MCP_PLANNER_LOG_MAX_PROMPT_LENGTH` | `10000` | Maximum characters to log for prompts |
| `MCP_PLANNER_LOG_SANITIZE_PARAMS` | `true` | Whether to sanitize sensitive parameters |

### Usage Example

```python
# Set in environment or .env file
MCP_PLANNER_LOG_LEVEL=DEBUG
MCP_PLANNER_LOG_MAX_PROMPT_LENGTH=20000
MCP_PLANNER_LOG_SANITIZE_PARAMS=true
```

## Integration with Orchestrator

The PlannerAgent is used in the orchestrator's `planner_node`:

```python
async def planner_node(state: GraphState) -> GraphState:
    """Planner agent node"""
    logger.info(f"Graph node: planner for task {state.task_id}")
    return await planner.plan(state)
```

The `plan()` method automatically:
1. Creates the execution plan
2. Logs plan details at DEBUG level
3. Builds the executor prompt
4. Logs the executor prompt at DEBUG level
5. Updates the graph state
6. Returns the updated state

## Testing

To test the logging functionality:

1. **Enable DEBUG logging** in your application configuration
2. **Run a workflow** that triggers the planner agent
3. **Check logs** for entries containing:
   - `"Planner Agent generated execution plan:"`
   - `"Executor prompt generated:"`

### Test Script

A test script is provided at `tests/test_planner_logging.py`:

```bash
# Run the test (requires dependencies installed)
python tests/test_planner_logging.py
```

## Requirements Met

| Requirement ID | Status | Description |
|---|---|---|
| FR-1 | ✅ Complete | Log the complete execution plan after plan generation |
| FR-2 | ✅ Complete | Log the formatted prompt text prepared for the Executor Agent |
| FR-3 | ✅ Complete | Use DEBUG log level for all plan-related logging |
| FR-4 | ✅ Complete | Include task_id in all log entries for traceability |
| FR-5 | ✅ Complete | Log plan complexity metrics (step count, complexity score, estimated duration) |
| FR-6 | ✅ Complete | Ensure logging does not impact performance or fail silently on errors |

## Log Filtering

To view only planner-related logs:

```bash
# Filter by component
grep "PlannerAgent" app.log

# Filter by task ID
grep "task_id=abc-123" app.log

# Filter for execution plans
grep "generated execution plan" app.log

# Filter for executor prompts
grep "Executor prompt generated" app.log
```

## Performance Considerations

- Logging is performed at DEBUG level (disabled by default in production)
- All logging operations are wrapped in try-except to prevent crashes
- Large prompts are truncated to prevent memory issues
- Parameter sanitization has minimal overhead (dictionary iteration)

## Future Enhancements

As noted in the design document:
- Structured JSON logging for machine parsing
- Log aggregation and analysis dashboard
- Plan visualization from logs
- Diff comparison between plan versions for retry scenarios
- Metrics extraction from logged plan complexity scores
