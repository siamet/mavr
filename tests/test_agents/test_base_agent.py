"""Tests for the base agent interface."""

import time
from typing import List

import pytest

from src.agents import AgentCapabilities, AgentContext, AgentResult, BaseAgent
from src.models.issue import Issue, IssueType, Severity
from src.models.source_location import SourceLocation
from src.pipeline.pipeline import PipelineResult


def _make_issue(issue_id: str, agent_id: str = "stub") -> Issue:
    """Build a minimal valid Issue for tests."""
    return Issue(
        id=issue_id,
        type=IssueType.GOD_CLASS,
        severity=Severity.MEDIUM,
        location=SourceLocation(file_path="x.py", start_line=1, end_line=2),
        title="t",
        description="d",
        explanation="e",
        recommendation="r",
        confidence=0.9,
        agent_id=agent_id,
    )


class FakeAgent(BaseAgent):
    """Minimal agent used to exercise the BaseAgent template method."""

    def __init__(self, issues: List[Issue], sleep_seconds: float = 0.0) -> None:
        super().__init__()
        self._issues = issues
        self._sleep = sleep_seconds
        self._received_context: AgentContext | None = None

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_id="fake_agent",
            name="Fake",
            description="Test double",
            issue_types={IssueType.GOD_CLASS},
            supported_languages={"python"},
        )

    def _analyze(self, context: AgentContext) -> List[Issue]:
        self._received_context = context
        if self._sleep:
            time.sleep(self._sleep)
        return list(self._issues)


def _empty_context(target_ids: list[str] | None = None) -> AgentContext:
    result = PipelineResult()
    result.entities_found = 5
    return AgentContext(pipeline_result=result, target_entity_ids=target_ids)


def test_analyze_returns_agent_result_with_timing() -> None:
    agent = FakeAgent(issues=[_make_issue("i1", agent_id="other")], sleep_seconds=0.01)

    result = agent.analyze(_empty_context())

    assert isinstance(result, AgentResult)
    assert result.agent_id == "fake_agent"
    assert len(result.issues) == 1
    assert result.processing_time_seconds > 0
    assert result.entities_analyzed == 5


def test_analyze_stamps_agent_id_onto_every_issue() -> None:
    issues = [
        _make_issue("i1", agent_id="other"),
        _make_issue("i2", agent_id="another"),
    ]
    agent = FakeAgent(issues=issues)

    result = agent.analyze(_empty_context())

    assert {i.agent_id for i in result.issues} == {"fake_agent"}


def test_analyze_passes_target_entity_ids_through_context() -> None:
    agent = FakeAgent(issues=[])

    context = _empty_context(target_ids=["e1", "e2", "e3"])
    result = agent.analyze(context)

    assert agent._received_context is context
    assert result.entities_analyzed == 3


def test_entities_analyzed_falls_back_to_pipeline_count() -> None:
    agent = FakeAgent(issues=[])

    result = agent.analyze(_empty_context())

    assert result.entities_analyzed == 5


def test_supports_language_uses_capabilities() -> None:
    agent = FakeAgent(issues=[])

    assert agent.supports_language("python")
    assert not agent.supports_language("rust")


def test_agent_id_override() -> None:
    class Override(FakeAgent):
        def __init__(self) -> None:
            super().__init__(issues=[])
            self._agent_id_override = "custom_id"

    agent = Override()
    result = agent.analyze(_empty_context())

    assert agent.agent_id == "custom_id"
    assert result.agent_id == "custom_id"


def test_base_agent_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore[abstract]


def test_subclass_without_capabilities_cannot_instantiate() -> None:
    class Incomplete(BaseAgent):
        def _analyze(self, context: AgentContext) -> List[Issue]:
            return []

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_subclass_without_analyze_cannot_instantiate() -> None:
    class Incomplete(BaseAgent):
        @property
        def capabilities(self) -> AgentCapabilities:
            return AgentCapabilities(
                agent_id="x",
                name="x",
                description="x",
                issue_types=set(),
                supported_languages=set(),
            )

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_agent_result_serializes_to_dict() -> None:
    agent = FakeAgent(issues=[_make_issue("i1")])
    result = agent.analyze(_empty_context())

    dumped = result.model_dump()

    assert dumped["agent_id"] == "fake_agent"
    assert dumped["entities_analyzed"] == 5
    assert len(dumped["issues"]) == 1


def test_agent_context_is_frozen() -> None:
    context = _empty_context()

    with pytest.raises(Exception):
        context.target_entity_ids = ["e1"]  # type: ignore[misc]


def test_capabilities_required_fields() -> None:
    caps = AgentCapabilities(
        agent_id="x",
        name="X",
        description="x",
        issue_types={IssueType.SQL_INJECTION},
        supported_languages={"python", "java"},
    )

    assert caps.requires_gpu is False
    assert "python" in caps.supported_languages
