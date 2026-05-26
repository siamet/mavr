"""Tests for the Performance Agent."""

from src.agents import AgentContext, PerformanceAgent
from src.models.issue import IssueType, Severity
from src.parsing.ast_nodes import ASTNode, NodeType
from src.pipeline.pipeline import PipelineResult


def _node(
    node_type: NodeType,
    name: str | None = None,
    line: int = 1,
    children: list[ASTNode] | None = None,
    attributes: dict | None = None,
    source_text: str = "",
) -> ASTNode:
    n = ASTNode(
        node_type=node_type,
        name=name,
        start_line=line,
        end_line=line,
        children=children or [],
        attributes=attributes or {},
        source_text=source_text,
    )
    return n


def _module_with(*statements: ASTNode) -> ASTNode:
    return _node(NodeType.MODULE, name="m", children=list(statements))


def _loop(*body: ASTNode, kind: NodeType = NodeType.FOR, line: int = 1) -> ASTNode:
    block = _node(NodeType.BLOCK, children=list(body), line=line)
    return _node(kind, name="loop", line=line, children=[block])


def _context_from(file_path: str, root: ASTNode) -> AgentContext:
    pr = PipelineResult()
    pr.file_asts = {file_path: root}
    pr.entities_found = 1
    return AgentContext(pipeline_result=pr)


def test_nested_loops_detected() -> None:
    inner = _loop(_node(NodeType.IDENTIFIER, name="x", line=3), line=2)
    outer = _loop(inner, line=1)
    root = _module_with(outer)

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    nested = [i for i in result.issues if i.type == IssueType.INEFFICIENT_ALGORITHM]
    assert len(nested) == 1
    assert nested[0].severity == Severity.MEDIUM
    assert nested[0].metrics["loop_depth"] == 2.0


def test_triple_nested_loops_are_high_severity() -> None:
    innermost = _loop(_node(NodeType.IDENTIFIER, name="x"), line=3)
    middle = _loop(innermost, line=2)
    outer = _loop(middle, line=1)
    root = _module_with(outer)

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    nested = [i for i in result.issues if i.type == IssueType.INEFFICIENT_ALGORITHM]
    assert any(
        i.severity == Severity.HIGH and i.metrics["loop_depth"] == 3.0 for i in nested
    )


def test_single_loop_is_not_flagged() -> None:
    root = _module_with(_loop(_node(NodeType.IDENTIFIER, name="x")))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert not any(i.type == IssueType.INEFFICIENT_ALGORITHM for i in result.issues)


def test_nested_function_does_not_count_as_nested_loop() -> None:
    inner_fn_body = _node(
        NodeType.BLOCK, children=[_loop(_node(NodeType.IDENTIFIER, name="z"))]
    )
    inner_fn = _node(NodeType.FUNCTION, name="inner", children=[inner_fn_body])
    outer = _loop(inner_fn, line=1)
    root = _module_with(outer)

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert not any(i.type == IssueType.INEFFICIENT_ALGORITHM for i in result.issues)


def test_db_call_in_loop_flagged_as_n_plus_one() -> None:
    call = _node(NodeType.CALL, name="User.query", line=2)
    root = _module_with(_loop(call, line=1))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    n_plus_one = [i for i in result.issues if i.type == IssueType.N_PLUS_ONE_QUERY]
    assert len(n_plus_one) == 1
    assert "query" in n_plus_one[0].title


def test_db_call_outside_loop_not_flagged() -> None:
    call = _node(NodeType.CALL, name="repo.find_all", line=1)
    root = _module_with(call)

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert not any(i.type == IssueType.N_PLUS_ONE_QUERY for i in result.issues)


def test_non_db_call_in_loop_not_flagged() -> None:
    call = _node(NodeType.CALL, name="math.sqrt", line=2)
    root = _module_with(_loop(call, line=1))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert not any(i.type == IssueType.N_PLUS_ONE_QUERY for i in result.issues)


def test_string_concat_in_loop_flagged() -> None:
    concat = _node(
        NodeType.BINARY_OP,
        name="+=",
        line=2,
        attributes={"operator": "+="},
    )
    root = _module_with(_loop(concat, line=1))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    concat_issues = [
        i for i in result.issues if i.type == IssueType.UNNECESSARY_COMPUTATION
    ]
    assert len(concat_issues) == 1
    assert concat_issues[0].severity == Severity.LOW


def test_string_concat_outside_loop_not_flagged() -> None:
    concat = _node(
        NodeType.BINARY_OP,
        name="+=",
        attributes={"operator": "+="},
    )
    root = _module_with(concat)

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert not any(i.type == IssueType.UNNECESSARY_COMPUTATION for i in result.issues)


def test_db_call_via_source_text_when_operator_missing() -> None:
    concat = _node(
        NodeType.BINARY_OP,
        source_text="s += chunk",
        line=2,
    )
    root = _module_with(_loop(concat, line=1))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert any(i.type == IssueType.UNNECESSARY_COMPUTATION for i in result.issues)


def test_capabilities_advertise_three_issue_types() -> None:
    agent = PerformanceAgent()
    caps = agent.capabilities

    assert caps.agent_id == "performance_agent"
    assert caps.issue_types == {
        IssueType.INEFFICIENT_ALGORITHM,
        IssueType.N_PLUS_ONE_QUERY,
        IssueType.UNNECESSARY_COMPUTATION,
    }
    assert "python" in caps.supported_languages


def test_issues_stamped_with_agent_id() -> None:
    root = _module_with(_loop(_loop(_node(NodeType.IDENTIFIER, name="x"))))

    agent = PerformanceAgent()
    result = agent.analyze(_context_from("a.py", root))

    assert result.issues
    assert all(i.agent_id == "performance_agent" for i in result.issues)
