"""
Multi-Agent System Agent Implementations
Includes Analyzer, Planner, Executor, and Verifier agents
"""

import os
import json
from typing import Optional
from loguru import logger
from langchain_openai import ChatOpenAI

from .multi_agent_models import (
    GraphState,
    PhaseEnum,
    AnalysisResult,
    ExecutionPlan,
    PlanStep,
    Dependency,
    VerificationResult,
    FeasibilityEnum,
    VerificationEnum
)
from .mcp_client import MCPExcelClient


# Configuration for logging
PLANNER_LOG_LEVEL = os.getenv("MCP_PLANNER_LOG_LEVEL", "DEBUG")
PLANNER_MAX_PROMPT_LENGTH = int(os.getenv("MCP_PLANNER_LOG_MAX_PROMPT_LENGTH", "10000"))
PLANNER_SANITIZE_PARAMS = os.getenv("MCP_PLANNER_LOG_SANITIZE_PARAMS", "true").lower() == "true"


class AnalyzerAgent:
    """
    Analyzer Agent - Analyzes user requests and determines feasibility
    """
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize Analyzer Agent with LLM"""
        self.llm = llm
        logger.info("AnalyzerAgent initialized")
    
    async def analyze(self, state: GraphState) -> GraphState:
        """
        Analyze user request and assess feasibility
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state with analysis result
        """
        logger.info(f"AnalyzerAgent analyzing task {state.task_id}")
        
        try:
            # TODO: Implement actual analysis logic with LLM
            # For now, create a basic analysis result
            state.analysis_result = AnalysisResult(
                feasibility=FeasibilityEnum.FEASIBLE,
                confidence_score=0.9,
                analysis_notes="Task is feasible and ready for planning"
            )
            
            state.transition_phase(PhaseEnum.PLANNING, "Analysis complete, proceeding to planning")
            state.next_action = "plan"
            
            logger.info(f"AnalyzerAgent completed analysis for task {state.task_id}")
            return state
            
        except Exception as e:
            logger.error(f"AnalyzerAgent error for task {state.task_id}: {e}")
            state.error_context = {"error": str(e), "agent": "analyzer"}
            state.next_action = "error"
            return state


class PlannerAgent:
    """
    Planner Agent - Creates detailed execution plans with extended logging
    """
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize Planner Agent with LLM"""
        self.llm = llm
        logger.info("PlannerAgent initialized")
    
    def _sanitize_parameters(self, parameters: dict) -> dict:
        """
        Sanitize parameters to remove sensitive data from logs
        
        Args:
            parameters: Original parameters dict
            
        Returns:
            Sanitized parameters dict
        """
        if not PLANNER_SANITIZE_PARAMS:
            return parameters
        
        sanitized = {}
        sensitive_keys = ["password", "token", "secret", "api_key", "auth"]
        
        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _log_execution_plan(self, task_id: str, plan: ExecutionPlan):
        """
        Log detailed execution plan at DEBUG level
        
        Args:
            task_id: Task identifier for correlation
            plan: ExecutionPlan object to log
        """
        try:
            # Count dependency types
            sequential_deps = sum(1 for d in plan.dependencies if d.dependency_type == "sequential")
            conditional_deps = sum(1 for d in plan.dependencies if d.dependency_type == "conditional")
            data_deps = sum(1 for d in plan.dependencies if d.dependency_type == "data")
            
            # Build log message
            log_lines = [
                f"task_id={task_id} | Planner Agent generated execution plan:",
                f"  - Steps: {len(plan.steps)}",
                f"  - Complexity Score: {plan.complexity_score}/10",
                f"  - Estimated Duration: {plan.estimated_duration}s",
                "  - Plan Steps:"
            ]
            
            # Add each step with details
            for step in plan.steps:
                sanitized_params = self._sanitize_parameters(step.parameters)
                deps_str = f" (depends on: {', '.join(step.dependencies)})" if step.dependencies else ""
                log_lines.append(
                    f"    [{step.step_id}] {step.tool_name}: {step.expected_outcome}{deps_str}"
                )
                log_lines.append(f"      Parameters: {json.dumps(sanitized_params, indent=8)}")
                if step.rollback_action:
                    log_lines.append(f"      Rollback: {step.rollback_action}")
            
            # Add dependency summary
            log_lines.append(
                f"  - Dependencies: {sequential_deps} sequential, "
                f"{conditional_deps} conditional, {data_deps} data"
            )
            
            # Add plan notes
            if plan.plan_notes:
                log_lines.append(f"  - Plan Notes: {plan.plan_notes}")
            
            # Log at DEBUG level
            logger.debug("\n".join(log_lines))
            
        except Exception as e:
            logger.warning(f"Failed to log execution plan for task {task_id}: {e}")
    
    def _build_executor_prompt(self, state: GraphState) -> str:
        """
        Build detailed prompt for the Executor Agent
        
        Args:
            state: Current graph state with execution plan
            
        Returns:
            Formatted prompt string for executor
        """
        plan = state.execution_plan
        if not plan:
            return ""
        
        prompt_parts = [
            "# Execution Instructions",
            "",
            f"## Task: {state.original_prompt}",
            "",
            f"## File Context",
            f"- File ID: {state.file_id}",
            f"- File Path: {state.resolved_filepath}",
        ]
        
        if state.source_range:
            prompt_parts.append(f"- Source Range: {state.source_range}")
        
        prompt_parts.extend([
            "",
            f"## Execution Plan ({len(plan.steps)} steps)",
            f"Complexity: {plan.complexity_score}/10 | Estimated Duration: {plan.estimated_duration}s",
            ""
        ])
        
        if plan.plan_notes:
            prompt_parts.extend([
                f"### Strategic Notes",
                plan.plan_notes,
                ""
            ])
        
        prompt_parts.append("### Steps to Execute")
        
        for i, step in enumerate(plan.steps, 1):
            prompt_parts.extend([
                f"",
                f"**Step {i}: {step.step_id}**",
                f"- Tool: `{step.tool_name}`",
                f"- Expected Outcome: {step.expected_outcome}",
                f"- Parameters:",
            ])
            
            for key, value in step.parameters.items():
                prompt_parts.append(f"  - {key}: {json.dumps(value)}")
            
            if step.dependencies:
                prompt_parts.append(f"- Dependencies: {', '.join(step.dependencies)}")
            
            if step.rollback_action:
                prompt_parts.append(f"- Rollback Action: {step.rollback_action}")
            
            prompt_parts.append(f"- Retry Policy: {step.retry_policy}")
        
        if plan.dependencies:
            prompt_parts.extend([
                "",
                "### Dependency Graph",
            ])
            for dep in plan.dependencies:
                prompt_parts.append(
                    f"- {dep.from_step} → {dep.to_step} ({dep.dependency_type})"
                )
        
        prompt_parts.extend([
            "",
            "## Execution Guidelines",
            "1. Execute steps in dependency order",
            "2. Validate tool parameters before invocation",
            "3. Handle errors according to retry policy",
            "4. Execute rollback actions on critical failures",
            "5. Record detailed results for each step",
            ""
        ])
        
        return "\n".join(prompt_parts)
    
    def _log_executor_prompt(self, task_id: str, prompt: str):
        """
        Log the executor prompt at DEBUG level
        
        Args:
            task_id: Task identifier for correlation
            prompt: Formatted prompt text
        """
        try:
            # Truncate if needed
            if len(prompt) > PLANNER_MAX_PROMPT_LENGTH:
                truncated_prompt = prompt[:PLANNER_MAX_PROMPT_LENGTH]
                truncated_prompt += f"\n... [TRUNCATED - {len(prompt) - PLANNER_MAX_PROMPT_LENGTH} chars omitted]"
                prompt_to_log = truncated_prompt
            else:
                prompt_to_log = prompt
            
            log_message = (
                f"task_id={task_id} | Executor prompt generated:\n"
                f"---BEGIN PROMPT---\n"
                f"{prompt_to_log}\n"
                f"---END PROMPT---"
            )
            
            logger.debug(log_message)
            
        except Exception as e:
            logger.warning(f"Failed to log executor prompt for task {task_id}: {e}")
    
    async def plan(self, state: GraphState) -> GraphState:
        """
        Create detailed execution plan with comprehensive logging
        
        Args:
            state: Current graph state
            
        Returns:
            Updated graph state with execution plan
        """
        logger.info(f"PlannerAgent creating plan for task {state.task_id}")
        
        try:
            # TODO: Implement actual planning logic with LLM
            # For now, create a basic execution plan
            
            # Create sample plan steps
            steps = [
                PlanStep(
                    step_id="step_1",
                    tool_name="read_excel_range",
                    parameters={"range": "A1:B10"},
                    expected_outcome="Read data from specified range",
                    dependencies=[],
                    retry_policy={"max_attempts": 3, "backoff": "exponential"}
                ),
                PlanStep(
                    step_id="step_2",
                    tool_name="process_data",
                    parameters={"operation": "sum"},
                    expected_outcome="Calculate sum of values",
                    dependencies=["step_1"],
                    retry_policy={"max_attempts": 2, "backoff": "linear"}
                ),
                PlanStep(
                    step_id="step_3",
                    tool_name="write_excel_range",
                    parameters={"range": "C1", "value": "result"},
                    expected_outcome="Write result to cell",
                    dependencies=["step_2"],
                    rollback_action="Clear cell C1",
                    retry_policy={"max_attempts": 3, "backoff": "exponential"}
                )
            ]
            
            # Create dependencies
            dependencies = [
                Dependency(from_step="step_1", to_step="step_2", dependency_type="sequential"),
                Dependency(from_step="step_2", to_step="step_3", dependency_type="data")
            ]
            
            # Create execution plan
            execution_plan = ExecutionPlan(
                steps=steps,
                estimated_duration=45,
                complexity_score=7,
                dependencies=dependencies,
                plan_notes="Multi-step calculation with error handling and rollback support"
            )
            
            # Attach plan to state
            state.execution_plan = execution_plan
            
            # Log execution plan details (FR-1, FR-3, FR-4, FR-5)
            self._log_execution_plan(state.task_id, execution_plan)
            
            # Build and log executor prompt (FR-2, FR-3, FR-4)
            executor_prompt = self._build_executor_prompt(state)
            self._log_executor_prompt(state.task_id, executor_prompt)
            
            # Update state
            state.transition_phase(PhaseEnum.EXECUTING, "Plan created, ready for execution")
            state.next_action = "execute"
            
            logger.info(f"PlannerAgent completed planning for task {state.task_id}")
            return state
            
        except Exception as e:
            logger.error(f"PlannerAgent error for task {state.task_id}: {e}", exc_info=True)
            state.error_context = {"error": str(e), "agent": "planner"}
            state.next_action = "error"
            return state


class ExecutorAgent:
    """
    Executor Agent - Executes the planned steps using MCP tools
    """
    
    def __init__(self, mcp_client: MCPExcelClient):
        """Initialize Executor Agent with MCP client"""
        self.mcp_client = mcp_client
        logger.info("ExecutorAgent initialized")
    
    async def execute(self, state: GraphState) -> GraphState:
        """
        Execute the plan steps
        
        Args:
            state: Current graph state with execution plan
            
        Returns:
            Updated graph state with execution results
        """
        logger.info(f"ExecutorAgent executing plan for task {state.task_id}")
        
        try:
            # TODO: Implement actual execution logic with MCP client
            # For now, just transition to verification
            
            state.transition_phase(PhaseEnum.VERIFYING, "Execution complete, ready for verification")
            state.next_action = "verify"
            
            logger.info(f"ExecutorAgent completed execution for task {state.task_id}")
            return state
            
        except Exception as e:
            logger.error(f"ExecutorAgent error for task {state.task_id}: {e}")
            state.error_context = {"error": str(e), "agent": "executor"}
            state.next_action = "error"
            return state


class VerifierAgent:
    """
    Verifier Agent - Verifies execution results against requirements
    """
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize Verifier Agent with LLM"""
        self.llm = llm
        logger.info("VerifierAgent initialized")
    
    async def verify(self, state: GraphState) -> GraphState:
        """
        Verify execution results
        
        Args:
            state: Current graph state with execution results
            
        Returns:
            Updated graph state with verification result
        """
        logger.info(f"VerifierAgent verifying results for task {state.task_id}")
        
        try:
            # TODO: Implement actual verification logic with LLM
            # For now, create a basic verification result
            
            state.verification_result = VerificationResult(
                status=VerificationEnum.PASSED,
                quality_score=0.95,
                verification_notes="All steps executed successfully"
            )
            
            state.next_action = "complete"
            
            logger.info(f"VerifierAgent completed verification for task {state.task_id}")
            return state
            
        except Exception as e:
            logger.error(f"VerifierAgent error for task {state.task_id}: {e}")
            state.error_context = {"error": str(e), "agent": "verifier"}
            state.next_action = "error"
            return state
