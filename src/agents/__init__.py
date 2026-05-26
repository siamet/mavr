"""Multi-agent analysis system.

This package contains the base agent contract and the four specialized
agents (Architecture, Performance, Security, Maintainability).
"""

from src.agents.base_agent import (
    AgentCapabilities,
    AgentContext,
    AgentResult,
    BaseAgent,
)

__all__ = [
    "AgentCapabilities",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
]
