"""Multi-agent analysis system.

This package contains the base agent contract and the four specialized
agents (Architecture, Performance, Security, Maintainability).
"""

from src.agents.architecture_agent import ArchitectureAgent
from src.agents.base_agent import (
    AgentCapabilities,
    AgentContext,
    AgentResult,
    BaseAgent,
)
from src.agents.performance_agent import PerformanceAgent
from src.agents.security_agent import SecurityAgent

__all__ = [
    "AgentCapabilities",
    "AgentContext",
    "AgentResult",
    "ArchitectureAgent",
    "BaseAgent",
    "PerformanceAgent",
    "SecurityAgent",
]
