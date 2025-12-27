"""
Multi-Agent System Data Models
Enhanced data structures for LangGraph-based multi-agent workflow
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


class PhaseEnum(str, Enum):
    """Workflow phase enumeration"""
    RECEIVED = "received"
    ANALYZING = "analyzing"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FeasibilityEnum(str, Enum):
    """Task feasibility assessment"""
    FEASIBLE = "feasible"
    NEEDS_CLARIFICATION = "needs_clarification"
    INFEASIBLE = "infeasible"
    UNCERTAIN = "uncertain"


class VerificationEnum(str, Enum):
    """Verification result status"""
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


class QuestionType(str, Enum):
    """Clarification question types"""
    BINARY = "binary"  # Yes/No questions
    CHOICE = "choice"  # Multiple choice
    TEXT = "text"  # Free-form text input


@dataclass
class Requirement:
    """Single parsed requirement"""
    id: str
    description: str
    priority: int = 0  # 0-10, higher is more important
    is_explicit: bool = True  # False if inferred


@dataclass
class Clarification:
    """Single clarification question"""
    clarification_id: str
    question: str
    question_type: QuestionType
    options: Optional[List[str]] = None  # For choice type
    required: bool = True
    context: str = ""  # Why this information is needed


@dataclass
class ClarificationResponse:
    """User response to a clarification question"""
    clarification_id: str
    answer: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AnalysisResult:
    """Output from Analyzer agent"""
    requirements: List[Requirement] = field(default_factory=list)
    feasibility: FeasibilityEnum = FeasibilityEnum.UNCERTAIN
    risk_factors: List[str] = field(default_factory=list)
    clarifications_needed: bool = False
    confidence_score: float = 0.0  # 0-1
    analysis_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "requirements": [
                {
                    "id": req.id,
                    "description": req.description,
                    "priority": req.priority,
                    "is_explicit": req.is_explicit
                }
                for req in self.requirements
            ],
            "feasibility": self.feasibility.value,
            "risk_factors": self.risk_factors,
            "clarifications_needed": self.clarifications_needed,
            "confidence_score": self.confidence_score,
            "analysis_notes": self.analysis_notes
        }


@dataclass
class ClarificationQueue:
    """Pending clarification questions and responses"""
    questions: List[Clarification] = field(default_factory=list)
    responses: List[ClarificationResponse] = field(default_factory=list)
    deadline: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "questions": [
                {
                    "clarification_id": q.clarification_id,
                    "question": q.question,
                    "question_type": q.question_type.value,
                    "options": q.options,
                    "required": q.required,
                    "context": q.context
                }
                for q in self.questions
            ],
            "responses": [
                {
                    "clarification_id": r.clarification_id,
                    "answer": r.answer,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.responses
            ],
            "deadline": self.deadline.isoformat() if self.deadline else None
        }


@dataclass
class PlanStep:
    """Single step in execution plan"""
    step_id: str
    tool_name: str
    parameters: Dict[str, Any]
    expected_outcome: str
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    rollback_action: Optional[str] = None
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {
        "max_attempts": 3,
        "backoff": "linear"
    })


@dataclass
class Dependency:
    """Dependency between plan steps"""
    from_step: str
    to_step: str
    dependency_type: str = "sequential"  # sequential, data, conditional


@dataclass
class ExecutionPlan:
    """Complete execution plan from Planner agent"""
    steps: List[PlanStep] = field(default_factory=list)
    estimated_duration: int = 0  # Seconds
    complexity_score: int = 0  # 1-10
    dependencies: List[Dependency] = field(default_factory=list)
    plan_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "steps": [
                {
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "parameters": step.parameters,
                    "expected_outcome": step.expected_outcome,
                    "dependencies": step.dependencies,
                    "rollback_action": step.rollback_action,
                    "retry_policy": step.retry_policy
                }
                for step in self.steps
            ],
            "estimated_duration": self.estimated_duration,
            "complexity_score": self.complexity_score,
            "dependencies": [
                {
                    "from_step": dep.from_step,
                    "to_step": dep.to_step,
                    "dependency_type": dep.dependency_type
                }
                for dep in self.dependencies
            ],
            "plan_notes": self.plan_notes
        }


@dataclass
class StepResult:
    """Result of a single execution step"""
    step_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VerificationIssue:
    """Single issue detected during verification"""
    issue_id: str
    severity: str  # "critical", "major", "minor", "info"
    description: str
    affected_requirement: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class VerificationResult:
    """Output from Verifier agent"""
    status: VerificationEnum = VerificationEnum.PASSED
    issues: List[VerificationIssue] = field(default_factory=list)
    quality_score: float = 0.0  # 0-1
    recommendations: List[str] = field(default_factory=list)
    verification_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "severity": issue.severity,
                    "description": issue.description,
                    "affected_requirement": issue.affected_requirement,
                    "suggestion": issue.suggestion
                }
                for issue in self.issues
            ],
            "quality_score": self.quality_score,
            "recommendations": self.recommendations,
            "verification_notes": self.verification_notes
        }


@dataclass
class PhaseTransition:
    """Record of a phase transition"""
    from_phase: PhaseEnum
    to_phase: PhaseEnum
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason
        }


@dataclass
class GraphState:
    """
    Complete LangGraph state for multi-agent workflow
    This represents the shared state passed between agent nodes
    """
    # Core task information
    task_id: str
    user_id: int
    original_prompt: str
    file_id: str
    resolved_filepath: Optional[str] = None
    source_range: Optional[Dict[str, Any]] = None
    
    # Workflow control
    current_phase: PhaseEnum = PhaseEnum.RECEIVED
    next_action: str = "analyze"  # Routing signal for conditional edges
    
    # Agent outputs
    analysis_result: Optional[AnalysisResult] = None
    clarification_queue: Optional[ClarificationQueue] = None
    execution_plan: Optional[ExecutionPlan] = None
    execution_results: List[StepResult] = field(default_factory=list)
    verification_result: Optional[VerificationResult] = None
    
    # Error handling
    error_context: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    phase_history: List[PhaseTransition] = field(default_factory=list)
    priority: int = 0
    
    def transition_phase(self, to_phase: PhaseEnum, reason: str = ""):
        """Record a phase transition"""
        transition = PhaseTransition(
            from_phase=self.current_phase,
            to_phase=to_phase,
            reason=reason
        )
        self.phase_history.append(transition)
        self.current_phase = to_phase
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "original_prompt": self.original_prompt,
            "file_id": self.file_id,
            "resolved_filepath": self.resolved_filepath,
            "source_range": self.source_range,
            "current_phase": self.current_phase.value,
            "next_action": self.next_action,
            "analysis_result": self.analysis_result.to_dict() if self.analysis_result else None,
            "clarification_queue": self.clarification_queue.to_dict() if self.clarification_queue else None,
            "execution_plan": self.execution_plan.to_dict() if self.execution_plan else None,
            "execution_results": [
                {
                    "step_id": r.step_id,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "duration_seconds": r.duration_seconds,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.execution_results
            ],
            "verification_result": self.verification_result.to_dict() if self.verification_result else None,
            "error_context": self.error_context,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "phase_history": [t.to_dict() for t in self.phase_history],
            "priority": self.priority
        }
