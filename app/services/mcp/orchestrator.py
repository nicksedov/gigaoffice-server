"""
LangGraph Multi-Agent Orchestrator
Coordinates workflow execution through state graph
"""

import os
from typing import Dict, Any, Literal
from loguru import logger

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .multi_agent_models import GraphState, PhaseEnum
from .agents import AnalyzerAgent, PlannerAgent, ExecutorAgent, VerifierAgent
from .mcp_client import create_mcp_client, MCPExcelClient


# Configuration from environment
LLM_API_URL = os.getenv("GIGACHAT_BASE_URL", "https://ollama.ai-gateway.ru/v1")
LLM_API_KEY = os.getenv("GIGACHAT_API_KEY", "none")
LLM_MODEL_NAME = os.getenv("GIGACHAT_MODEL_NAME", "gpt-oss")
LLM_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", "0.7"))
MCP_SERVER_URL = os.getenv("MCP_EXCEL_SERVER_URL", "")


class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator using LangGraph
    
    Coordinates Analyzer, Planner, Executor, and Verifier agents
    through a state machine workflow
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self.llm = None
        self.graph = None
        self.mcp_client: MCPExcelClient = None
        
        logger.info("MultiAgentOrchestrator initialized")
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create LLM client"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=LLM_MODEL_NAME,
                temperature=LLM_TEMPERATURE,
                api_key=LLM_API_KEY,
                base_url=LLM_API_URL
            )
            logger.info(f"LLM client created: {LLM_MODEL_NAME}")
        return self.llm
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph state machine
        
        Returns:
            Configured StateGraph
        """
        # Create graph
        workflow = StateGraph(GraphState)
        
        # Get LLM for agents
        llm = self._get_llm()
        
        # Initialize agents (Executor will be initialized per-task with MCP client)
        analyzer = AnalyzerAgent(llm)
        planner = PlannerAgent(llm)
        verifier = VerifierAgent(llm)
        
        # Define nodes
        async def analyzer_node(state: GraphState) -> GraphState:
            """Analyzer agent node"""
            logger.info(f"Graph node: analyzer for task {state.task_id}")
            return await analyzer.analyze(state)
        
        async def planner_node(state: GraphState) -> GraphState:
            """Planner agent node"""
            logger.info(f"Graph node: planner for task {state.task_id}")
            return await planner.plan(state)
        
        async def executor_node(state: GraphState) -> GraphState:
            """Executor agent node"""
            logger.info(f"Graph node: executor for task {state.task_id}")
            
            # Executor needs MCP client
            if not self.mcp_client:
                raise RuntimeError("MCP client not initialized for executor")
            
            executor = ExecutorAgent(self.mcp_client)
            return await executor.execute(state)
        
        async def verifier_node(state: GraphState) -> GraphState:
            """Verifier agent node"""
            logger.info(f"Graph node: verifier for task {state.task_id}")
            return await verifier.verify(state)
        
        async def clarification_wait_node(state: GraphState) -> GraphState:
            """Clarification wait node - suspends for client input"""
            logger.info(f"Graph node: awaiting clarification for task {state.task_id}")
            # This node just passes through - actual waiting happens via task tracker
            return state
        
        async def completion_node(state: GraphState) -> GraphState:
            """Completion node"""
            logger.info(f"Graph node: completion for task {state.task_id}")
            state.transition_phase(PhaseEnum.COMPLETED, "Task completed successfully")
            return state
        
        async def error_node(state: GraphState) -> GraphState:
            """Error handling node"""
            logger.error(f"Graph node: error for task {state.task_id}")
            state.transition_phase(PhaseEnum.FAILED, f"Task failed: {state.error_context}")
            return state
        
        # Add nodes to graph
        workflow.add_node("analyzer", analyzer_node)
        workflow.add_node("planner", planner_node)
        workflow.add_node("executor", executor_node)
        workflow.add_node("verifier", verifier_node)
        workflow.add_node("clarification_wait", clarification_wait_node)
        workflow.add_node("completion", completion_node)
        workflow.add_node("error", error_node)
        
        # Define conditional edge routing functions
        def route_from_analyzer(
            state: GraphState
        ) -> Literal["clarification_wait", "planner", "error"]:
            """Route from analyzer based on next_action"""
            if state.next_action == "await_clarification":
                return "clarification_wait"
            elif state.next_action == "plan":
                return "planner"
            else:
                return "error"
        
        def route_from_clarification(
            state: GraphState
        ) -> Literal["analyzer", "error"]:
            """Route from clarification wait"""
            # Check if clarifications were received
            if state.clarification_queue and len(state.clarification_queue.responses) > 0:
                state.next_action = "analyze"
                return "analyzer"
            else:
                # Timeout or cancellation
                return "error"
        
        def route_from_planner(
            state: GraphState
        ) -> Literal["executor", "error"]:
            """Route from planner"""
            if state.next_action == "execute":
                return "executor"
            else:
                return "error"
        
        def route_from_executor(
            state: GraphState
        ) -> Literal["verifier", "error"]:
            """Route from executor"""
            if state.next_action == "verify":
                return "verifier"
            else:
                return "error"
        
        def route_from_verifier(
            state: GraphState
        ) -> Literal["completion", "executor", "error"]:
            """Route from verifier"""
            if state.next_action == "complete":
                return "completion"
            elif state.next_action == "execute":
                # Revision needed
                return "executor"
            else:
                return "error"
        
        # Set entry point
        workflow.set_entry_point("analyzer")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyzer",
            route_from_analyzer,
            {
                "clarification_wait": "clarification_wait",
                "planner": "planner",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "clarification_wait",
            route_from_clarification,
            {
                "analyzer": "analyzer",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "planner",
            route_from_planner,
            {
                "executor": "executor",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "executor",
            route_from_executor,
            {
                "verifier": "verifier",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "verifier",
            route_from_verifier,
            {
                "completion": "completion",
                "executor": "executor",
                "error": "error"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("completion", END)
        workflow.add_edge("error", END)
        
        return workflow
    
    async def execute_workflow(
        self,
        task_id: str,
        user_id: int,
        prompt: str,
        file_id: str,
        resolved_filepath: str,
        source_range: Dict[str, Any] = None,
        priority: int = 0
    ) -> GraphState:
        """
        Execute multi-agent workflow
        
        Args:
            task_id: Task identifier
            user_id: User identifier
            prompt: Task description
            file_id: File UUID
            resolved_filepath: Resolved file path
            source_range: Optional source range
            priority: Task priority
            
        Returns:
            Final graph state
        """
        try:
            logger.info(f"Orchestrator: Starting workflow for task {task_id}")
            
            # Initialize MCP client for this task
            self.mcp_client = create_mcp_client(
                filepath=resolved_filepath,
                base_url=MCP_SERVER_URL,
                debug=True
            )
            
            # Create initial state
            initial_state = GraphState(
                task_id=task_id,
                user_id=user_id,
                original_prompt=prompt,
                file_id=file_id,
                resolved_filepath=resolved_filepath,
                source_range=source_range,
                current_phase=PhaseEnum.RECEIVED,
                priority=priority
            )
            
            # Build and compile graph
            if self.graph is None:
                workflow = self._build_graph()
                self.graph = workflow.compile()
                logger.info("Orchestrator: Graph compiled")
            
            # Execute graph
            logger.info(f"Orchestrator: Invoking graph for task {task_id}")
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(
                f"Orchestrator: Workflow completed for task {task_id}, "
                f"final phase: {final_state.current_phase.value}"
            )
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator error for task {task_id}: {e}")
            raise
        finally:
            # Cleanup MCP client
            if self.mcp_client:
                await self.mcp_client.cleanup()
                self.mcp_client = None
    
    async def resume_workflow(
        self,
        state: GraphState,
        clarification_responses: list
    ) -> GraphState:
        """
        Resume workflow after clarifications received
        
        Args:
            state: Current graph state
            clarification_responses: User's clarification answers
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Orchestrator: Resuming workflow for task {state.task_id}")
            
            # Add responses to state
            if state.clarification_queue:
                for response in clarification_responses:
                    state.clarification_queue.responses.append(response)
            
            # Re-initialize MCP client
            if state.resolved_filepath:
                self.mcp_client = create_mcp_client(
                    filepath=state.resolved_filepath,
                    base_url=MCP_SERVER_URL,
                    debug=True
                )
            
            # Resume from clarification_wait node
            if self.graph is None:
                workflow = self._build_graph()
                self.graph = workflow.compile()
            
            # Continue execution
            final_state = await self.graph.ainvoke(state)
            
            logger.info(f"Orchestrator: Resumed workflow completed for task {state.task_id}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator resume error for task {state.task_id}: {e}")
            raise
        finally:
            if self.mcp_client:
                await self.mcp_client.cleanup()
                self.mcp_client = None


# Global orchestrator instance
multi_agent_orchestrator = MultiAgentOrchestrator()
"""
LangGraph Multi-Agent Orchestrator
Coordinates workflow execution through state graph
"""

import os
from typing import Dict, Any, Literal
from loguru import logger

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from .multi_agent_models import GraphState, PhaseEnum
from .agents import AnalyzerAgent, PlannerAgent, ExecutorAgent, VerifierAgent
from .mcp_client import create_mcp_client, MCPExcelClient


# Configuration from environment
LLM_API_URL = os.getenv("GIGACHAT_BASE_URL", "https://ollama.ai-gateway.ru/v1")
LLM_API_KEY = os.getenv("GIGACHAT_API_KEY", "none")
LLM_MODEL_NAME = os.getenv("GIGACHAT_MODEL_NAME", "gpt-oss")
LLM_TEMPERATURE = float(os.getenv("GIGACHAT_TEMPERATURE", "0.7"))
MCP_SERVER_URL = os.getenv("MCP_EXCEL_SERVER_URL", "")


class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator using LangGraph
    
    Coordinates Analyzer, Planner, Executor, and Verifier agents
    through a state machine workflow
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self.llm = None
        self.graph = None
        self.mcp_client: MCPExcelClient = None
        
        logger.info("MultiAgentOrchestrator initialized")
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create LLM client"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=LLM_MODEL_NAME,
                temperature=LLM_TEMPERATURE,
                api_key=LLM_API_KEY,
                base_url=LLM_API_URL
            )
            logger.info(f"LLM client created: {LLM_MODEL_NAME}")
        return self.llm
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph state machine
        
        Returns:
            Configured StateGraph
        """
        # Create graph
        workflow = StateGraph(GraphState)
        
        # Get LLM for agents
        llm = self._get_llm()
        
        # Initialize agents (Executor will be initialized per-task with MCP client)
        analyzer = AnalyzerAgent(llm)
        planner = PlannerAgent(llm)
        verifier = VerifierAgent(llm)
        
        # Define nodes
        async def analyzer_node(state: GraphState) -> GraphState:
            """Analyzer agent node"""
            logger.info(f"Graph node: analyzer for task {state.task_id}")
            return await analyzer.analyze(state)
        
        async def planner_node(state: GraphState) -> GraphState:
            """Planner agent node"""
            logger.info(f"Graph node: planner for task {state.task_id}")
            return await planner.plan(state)
        
        async def executor_node(state: GraphState) -> GraphState:
            """Executor agent node"""
            logger.info(f"Graph node: executor for task {state.task_id}")
            
            # Executor needs MCP client
            if not self.mcp_client:
                raise RuntimeError("MCP client not initialized for executor")
            
            executor = ExecutorAgent(self.mcp_client)
            return await executor.execute(state)
        
        async def verifier_node(state: GraphState) -> GraphState:
            """Verifier agent node"""
            logger.info(f"Graph node: verifier for task {state.task_id}")
            return await verifier.verify(state)
        
        async def clarification_wait_node(state: GraphState) -> GraphState:
            """Clarification wait node - suspends for client input"""
            logger.info(f"Graph node: awaiting clarification for task {state.task_id}")
            # This node just passes through - actual waiting happens via task tracker
            return state
        
        async def completion_node(state: GraphState) -> GraphState:
            """Completion node"""
            logger.info(f"Graph node: completion for task {state.task_id}")
            state.transition_phase(PhaseEnum.COMPLETED, "Task completed successfully")
            return state
        
        async def error_node(state: GraphState) -> GraphState:
            """Error handling node"""
            logger.error(f"Graph node: error for task {state.task_id}")
            state.transition_phase(PhaseEnum.FAILED, f"Task failed: {state.error_context}")
            return state
        
        # Add nodes to graph
        workflow.add_node("analyzer", analyzer_node)
        workflow.add_node("planner", planner_node)
        workflow.add_node("executor", executor_node)
        workflow.add_node("verifier", verifier_node)
        workflow.add_node("clarification_wait", clarification_wait_node)
        workflow.add_node("completion", completion_node)
        workflow.add_node("error", error_node)
        
        # Define conditional edge routing functions
        def route_from_analyzer(
            state: GraphState
        ) -> Literal["clarification_wait", "planner", "error"]:
            """Route from analyzer based on next_action"""
            if state.next_action == "await_clarification":
                return "clarification_wait"
            elif state.next_action == "plan":
                return "planner"
            else:
                return "error"
        
        def route_from_clarification(
            state: GraphState
        ) -> Literal["analyzer", "error"]:
            """Route from clarification wait"""
            # Check if clarifications were received
            if state.clarification_queue and len(state.clarification_queue.responses) > 0:
                state.next_action = "analyze"
                return "analyzer"
            else:
                # Timeout or cancellation
                return "error"
        
        def route_from_planner(
            state: GraphState
        ) -> Literal["executor", "error"]:
            """Route from planner"""
            if state.next_action == "execute":
                return "executor"
            else:
                return "error"
        
        def route_from_executor(
            state: GraphState
        ) -> Literal["verifier", "error"]:
            """Route from executor"""
            if state.next_action == "verify":
                return "verifier"
            else:
                return "error"
        
        def route_from_verifier(
            state: GraphState
        ) -> Literal["completion", "executor", "error"]:
            """Route from verifier"""
            if state.next_action == "complete":
                return "completion"
            elif state.next_action == "execute":
                # Revision needed
                return "executor"
            else:
                return "error"
        
        # Set entry point
        workflow.set_entry_point("analyzer")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "analyzer",
            route_from_analyzer,
            {
                "clarification_wait": "clarification_wait",
                "planner": "planner",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "clarification_wait",
            route_from_clarification,
            {
                "analyzer": "analyzer",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "planner",
            route_from_planner,
            {
                "executor": "executor",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "executor",
            route_from_executor,
            {
                "verifier": "verifier",
                "error": "error"
            }
        )
        
        workflow.add_conditional_edges(
            "verifier",
            route_from_verifier,
            {
                "completion": "completion",
                "executor": "executor",
                "error": "error"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("completion", END)
        workflow.add_edge("error", END)
        
        return workflow
    
    async def execute_workflow(
        self,
        task_id: str,
        user_id: int,
        prompt: str,
        file_id: str,
        resolved_filepath: str,
        source_range: Dict[str, Any] = None,
        priority: int = 0
    ) -> GraphState:
        """
        Execute multi-agent workflow
        
        Args:
            task_id: Task identifier
            user_id: User identifier
            prompt: Task description
            file_id: File UUID
            resolved_filepath: Resolved file path
            source_range: Optional source range
            priority: Task priority
            
        Returns:
            Final graph state
        """
        try:
            logger.info(f"Orchestrator: Starting workflow for task {task_id}")
            
            # Initialize MCP client for this task
            self.mcp_client = create_mcp_client(
                filepath=resolved_filepath,
                base_url=MCP_SERVER_URL,
                debug=True
            )
            
            # Create initial state
            initial_state = GraphState(
                task_id=task_id,
                user_id=user_id,
                original_prompt=prompt,
                file_id=file_id,
                resolved_filepath=resolved_filepath,
                source_range=source_range,
                current_phase=PhaseEnum.RECEIVED,
                priority=priority
            )
            
            # Build and compile graph
            if self.graph is None:
                workflow = self._build_graph()
                self.graph = workflow.compile()
                logger.info("Orchestrator: Graph compiled")
            
            # Execute graph
            logger.info(f"Orchestrator: Invoking graph for task {task_id}")
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(
                f"Orchestrator: Workflow completed for task {task_id}, "
                f"final phase: {final_state.current_phase.value}"
            )
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator error for task {task_id}: {e}")
            raise
        finally:
            # Cleanup MCP client
            if self.mcp_client:
                await self.mcp_client.cleanup()
                self.mcp_client = None
    
    async def resume_workflow(
        self,
        state: GraphState,
        clarification_responses: list
    ) -> GraphState:
        """
        Resume workflow after clarifications received
        
        Args:
            state: Current graph state
            clarification_responses: User's clarification answers
            
        Returns:
            Updated graph state
        """
        try:
            logger.info(f"Orchestrator: Resuming workflow for task {state.task_id}")
            
            # Add responses to state
            if state.clarification_queue:
                for response in clarification_responses:
                    state.clarification_queue.responses.append(response)
            
            # Re-initialize MCP client
            if state.resolved_filepath:
                self.mcp_client = create_mcp_client(
                    filepath=state.resolved_filepath,
                    base_url=MCP_SERVER_URL,
                    debug=True
                )
            
            # Resume from clarification_wait node
            if self.graph is None:
                workflow = self._build_graph()
                self.graph = workflow.compile()
            
            # Continue execution
            final_state = await self.graph.ainvoke(state)
            
            logger.info(f"Orchestrator: Resumed workflow completed for task {state.task_id}")
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator resume error for task {state.task_id}: {e}")
            raise
        finally:
            if self.mcp_client:
                await self.mcp_client.cleanup()
                self.mcp_client = None


# Global orchestrator instance
multi_agent_orchestrator = MultiAgentOrchestrator()
