"""
Test script for Planner Agent extended logging functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from langchain_openai import ChatOpenAI

from app.services.mcp.agents import PlannerAgent
from app.services.mcp.multi_agent_models import (
    GraphState,
    PhaseEnum,
    AnalysisResult,
    FeasibilityEnum
)


# Configure logger to show DEBUG messages
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG"
)


async def test_planner_logging():
    """Test the planner agent logging functionality"""
    
    print("\n" + "="*80)
    print("Testing Planner Agent Extended Logging")
    print("="*80 + "\n")
    
    # Create a mock LLM (won't actually be used in this test)
    llm = ChatOpenAI(
        model="gpt-oss",
        temperature=0.7,
        api_key="test-key",
        base_url="http://localhost:11434/v1"
    )
    
    # Initialize Planner Agent
    planner = PlannerAgent(llm)
    
    # Create a test state
    state = GraphState(
        task_id="test-task-123",
        user_id=1,
        original_prompt="Calculate the sum of column A and write to column B",
        file_id="file-uuid-456",
        resolved_filepath="/path/to/test.xlsx",
        source_range={"start": "A1", "end": "A10"},
        current_phase=PhaseEnum.ANALYZING
    )
    
    # Add analysis result
    state.analysis_result = AnalysisResult(
        feasibility=FeasibilityEnum.FEASIBLE,
        confidence_score=0.9,
        analysis_notes="Task is feasible and ready for planning"
    )
    
    print("\n--- STARTING PLAN GENERATION ---\n")
    
    # Execute planner
    result_state = await planner.plan(state)
    
    print("\n--- PLAN GENERATION COMPLETED ---\n")
    
    # Verify results
    if result_state.execution_plan:
        print(f"✓ Execution plan created successfully")
        print(f"✓ Plan has {len(result_state.execution_plan.steps)} steps")
        print(f"✓ Complexity score: {result_state.execution_plan.complexity_score}/10")
        print(f"✓ Estimated duration: {result_state.execution_plan.estimated_duration}s")
        print(f"✓ Next action: {result_state.next_action}")
    else:
        print("✗ No execution plan created")
    
    print("\n" + "="*80)
    print("Test completed - Check DEBUG logs above for detailed plan and prompt")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_planner_logging())
"""
Test script for Planner Agent extended logging functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from langchain_openai import ChatOpenAI

from app.services.mcp.agents import PlannerAgent
from app.services.mcp.multi_agent_models import (
    GraphState,
    PhaseEnum,
    AnalysisResult,
    FeasibilityEnum
)


# Configure logger to show DEBUG messages
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG"
)


async def test_planner_logging():
    """Test the planner agent logging functionality"""
    
    print("\n" + "="*80)
    print("Testing Planner Agent Extended Logging")
    print("="*80 + "\n")
    
    # Create a mock LLM (won't actually be used in this test)
    llm = ChatOpenAI(
        model="gpt-oss",
        temperature=0.7,
        api_key="test-key",
        base_url="http://localhost:11434/v1"
    )
    
    # Initialize Planner Agent
    planner = PlannerAgent(llm)
    
    # Create a test state
    state = GraphState(
        task_id="test-task-123",
        user_id=1,
        original_prompt="Calculate the sum of column A and write to column B",
        file_id="file-uuid-456",
        resolved_filepath="/path/to/test.xlsx",
        source_range={"start": "A1", "end": "A10"},
        current_phase=PhaseEnum.ANALYZING
    )
    
    # Add analysis result
    state.analysis_result = AnalysisResult(
        feasibility=FeasibilityEnum.FEASIBLE,
        confidence_score=0.9,
        analysis_notes="Task is feasible and ready for planning"
    )
    
    print("\n--- STARTING PLAN GENERATION ---\n")
    
    # Execute planner
    result_state = await planner.plan(state)
    
    print("\n--- PLAN GENERATION COMPLETED ---\n")
    
    # Verify results
    if result_state.execution_plan:
        print(f"✓ Execution plan created successfully")
        print(f"✓ Plan has {len(result_state.execution_plan.steps)} steps")
        print(f"✓ Complexity score: {result_state.execution_plan.complexity_score}/10")
        print(f"✓ Estimated duration: {result_state.execution_plan.estimated_duration}s")
        print(f"✓ Next action: {result_state.next_action}")
    else:
        print("✗ No execution plan created")
    
    print("\n" + "="*80)
    print("Test completed - Check DEBUG logs above for detailed plan and prompt")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_planner_logging())
