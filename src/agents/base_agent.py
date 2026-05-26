"""Base agent interface for the multi-agent analysis system.

This module defines the shared contract that every analysis agent
(Architecture, Performance, Security, Maintainability) implements.
The Phase 3 orchestrator depends on this contract being uniform.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field

from src.models.issue import Issue, IssueType
from src.pipeline.pipeline import PipelineResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentCapabilities(BaseModel):
    """Static metadata describing what an agent can do.

    Used by the orchestrator to route work and plan resources.

    Attributes:
        agent_id: Stable identifier used in Issue.agent_id and logging.
        name: Human-readable name.
        description: One-line description of the agent's purpose.
        issue_types: Issue types this agent is capable of detecting.
        supported_languages: Languages the agent can analyze.
        requires_gpu: Resource hint for the orchestrator.
    """

    agent_id: str = Field(..., description="Stable agent identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="One-line description")
    issue_types: Set[IssueType] = Field(..., description="Detectable issue types")
    supported_languages: Set[str] = Field(..., description="Supported languages")
    requires_gpu: bool = Field(default=False, description="True if GPU is needed")


class AgentContext(BaseModel):
    """Input bundle passed to an agent's analyze() call.

    Attributes:
        pipeline_result: Full output from the analysis pipeline.
        target_entity_ids: If set, restrict analysis to these entity IDs.
        config: Agent-specific overrides (thresholds, model paths, etc.).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    pipeline_result: PipelineResult
    target_entity_ids: Optional[List[str]] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Structured output produced by an agent.

    Attributes:
        agent_id: Identifier of the agent that produced this result.
        issues: Detected issues.
        processing_time_seconds: Wall-clock time spent in _analyze().
        entities_analyzed: Number of entities the agent actually inspected.
        metadata: Agent-specific telemetry (e.g., rules fired, model stats).
    """

    agent_id: str
    issues: List[Issue] = Field(default_factory=list)
    processing_time_seconds: float = Field(default=0.0, ge=0.0)
    entities_analyzed: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all analysis agents.

    Subclasses implement `capabilities` and `_analyze`. The base class
    wraps `_analyze` with timing, logging, and result packaging so that
    every agent emits a consistent `AgentResult`.
    """

    def __init__(self, agent_id: Optional[str] = None) -> None:
        """Initialize the agent.

        Args:
            agent_id: Optional override for the agent ID. Defaults to
                `self.capabilities.agent_id`.
        """
        self._agent_id_override = agent_id

    @property
    @abstractmethod
    def capabilities(self) -> AgentCapabilities:
        """Return this agent's capabilities."""

    @abstractmethod
    def _analyze(self, context: AgentContext) -> List[Issue]:
        """Subclass-defined analysis logic.

        Args:
            context: The analysis context.

        Returns:
            Detected issues. The base class will stamp `agent_id` onto
            each issue automatically.
        """

    @property
    def agent_id(self) -> str:
        """Resolved agent ID (override or capability default)."""
        return self._agent_id_override or self.capabilities.agent_id

    def supports_language(self, language: str) -> bool:
        """Check whether this agent supports the given language."""
        return language in self.capabilities.supported_languages

    def analyze(self, context: AgentContext) -> AgentResult:
        """Run the agent and produce a structured result.

        This is the template method: subclasses override `_analyze` and
        inherit timing/logging/packaging from here.
        """
        agent_id = self.agent_id
        logger.info("Agent %s starting analysis", agent_id)
        start = time.time()

        issues = self._analyze(context)
        for issue in issues:
            issue.agent_id = agent_id

        elapsed = time.time() - start
        entities_analyzed = self._count_entities_analyzed(context)

        logger.info(
            "Agent %s finished: %d issues, %d entities, %.3fs",
            agent_id,
            len(issues),
            entities_analyzed,
            elapsed,
        )

        return AgentResult(
            agent_id=agent_id,
            issues=issues,
            processing_time_seconds=elapsed,
            entities_analyzed=entities_analyzed,
        )

    @staticmethod
    def _count_entities_analyzed(context: AgentContext) -> int:
        """How many entities the agent had access to in this run."""
        if context.target_entity_ids is not None:
            return len(context.target_entity_ids)
        return context.pipeline_result.entities_found
