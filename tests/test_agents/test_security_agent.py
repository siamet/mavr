"""Tests for the Security Agent."""

from src.agents import AgentContext, SecurityAgent
from src.analysis.taint import TaintFlow, TaintSink, TaintSource
from src.graph.knowledge_graph import KnowledgeGraph
from src.models.code_entity import CodeEntity, EntityType
from src.models.issue import IssueType, Severity
from src.models.source_location import SourceLocation
from src.parsing.ast_nodes import ASTNode, NodeType
from src.pipeline.pipeline import PipelineResult


def _entity(eid: str, file_path: str, name: str = "handler") -> CodeEntity:
    return CodeEntity(
        id=eid,
        name=name,
        entity_type=EntityType.FUNCTION,
        location=SourceLocation(file_path=file_path, start_line=10, end_line=20),
        language="python",
    )


def _node(
    node_type: NodeType,
    name: str | None = None,
    line: int = 1,
    source_text: str = "",
    children: list[ASTNode] | None = None,
) -> ASTNode:
    return ASTNode(
        node_type=node_type,
        name=name,
        start_line=line,
        end_line=line,
        source_text=source_text,
        children=children or [],
    )


def _module(*statements: ASTNode) -> ASTNode:
    return _node(NodeType.MODULE, name="m", children=list(statements))


def _flow(vulnerability: str, sanitized: bool = False, entity_id: str = "e1") -> TaintFlow:
    return TaintFlow(
        source=TaintSource(name="user_input", pattern=".", category="user_input"),
        sink=TaintSink(name="sql_exec", pattern=".", vulnerability=vulnerability),
        path=["block_1", "block_2"],
        sanitized=sanitized,
        entity_id=entity_id,
    )


def _context(
    flows: list[TaintFlow] | None = None,
    file_asts: dict[str, ASTNode] | None = None,
    entities: dict[str, CodeEntity] | None = None,
) -> AgentContext:
    pr = PipelineResult()
    pr.taint_flows = list(flows or [])
    pr.file_asts = dict(file_asts or {})
    if entities:
        graph = KnowledgeGraph()
        for entity in entities.values():
            graph.add_entity(entity)
        pr.graph = graph
        pr.entities_found = len(entities)
    return AgentContext(pipeline_result=pr)


def test_unsanitized_sql_injection_flow_emits_issue() -> None:
    entity = _entity("e1", "app.py")
    ctx = _context(flows=[_flow("sql_injection")], entities={"e1": entity})

    result = SecurityAgent().analyze(ctx)

    sqli = [i for i in result.issues if i.type == IssueType.SQL_INJECTION]
    assert len(sqli) == 1
    assert sqli[0].severity == Severity.HIGH
    assert sqli[0].location.file_path == "app.py"
    assert sqli[0].metadata["sink"] == "sql_exec"


def test_xss_command_and_code_injection_flows_each_map_to_their_type() -> None:
    entity = _entity("e1", "app.py")
    flows = [
        _flow("xss"),
        _flow("command_injection"),
        _flow("code_injection"),
    ]
    ctx = _context(flows=flows, entities={"e1": entity})

    result = SecurityAgent().analyze(ctx)

    types = {i.type for i in result.issues}
    assert IssueType.XSS_VULNERABILITY in types
    assert IssueType.COMMAND_INJECTION in types
    assert IssueType.CODE_INJECTION in types


def test_sanitized_flow_does_not_emit_issue() -> None:
    entity = _entity("e1", "app.py")
    ctx = _context(flows=[_flow("sql_injection", sanitized=True)], entities={"e1": entity})

    result = SecurityAgent().analyze(ctx)

    assert not any(i.type == IssueType.SQL_INJECTION for i in result.issues)


def test_flow_with_unknown_entity_is_skipped() -> None:
    ctx = _context(flows=[_flow("sql_injection", entity_id="missing")], entities={})

    result = SecurityAgent().analyze(ctx)

    assert result.issues == []


def test_hardcoded_password_assignment_flagged() -> None:
    literal = _node(NodeType.LITERAL, source_text='"hunter2"', line=2)
    assignment = _node(NodeType.ASSIGNMENT, name="password", line=2, children=[literal])
    ctx = _context(file_asts={"app.py": _module(assignment)})

    result = SecurityAgent().analyze(ctx)

    secrets = [i for i in result.issues if i.type == IssueType.SENSITIVE_DATA_EXPOSURE]
    assert len(secrets) == 1
    assert "password" in secrets[0].title


def test_hardcoded_api_key_assignment_flagged() -> None:
    literal = _node(NodeType.LITERAL, source_text="'sk-abc123'", line=3)
    assignment = _node(NodeType.ASSIGNMENT, name="API_KEY", line=3, children=[literal])
    ctx = _context(file_asts={"app.py": _module(assignment)})

    result = SecurityAgent().analyze(ctx)

    assert any(i.type == IssueType.SENSITIVE_DATA_EXPOSURE for i in result.issues)


def test_non_string_assignment_to_secret_name_not_flagged() -> None:
    # `token = compute_token()` — RHS is a call, not a string literal.
    call = _node(NodeType.CALL, name="compute_token", line=2)
    assignment = _node(NodeType.ASSIGNMENT, name="token", line=2, children=[call])
    ctx = _context(file_asts={"app.py": _module(assignment)})

    result = SecurityAgent().analyze(ctx)

    assert not any(i.type == IssueType.SENSITIVE_DATA_EXPOSURE for i in result.issues)


def test_non_secret_name_with_string_literal_not_flagged() -> None:
    literal = _node(NodeType.LITERAL, source_text='"hello"', line=2)
    assignment = _node(NodeType.ASSIGNMENT, name="greeting", line=2, children=[literal])
    ctx = _context(file_asts={"app.py": _module(assignment)})

    result = SecurityAgent().analyze(ctx)

    assert not any(i.type == IssueType.SENSITIVE_DATA_EXPOSURE for i in result.issues)


def test_md5_call_flagged_as_weak_crypto() -> None:
    call = _node(NodeType.CALL, name="hashlib.md5", line=5)
    ctx = _context(file_asts={"app.py": _module(call)})

    result = SecurityAgent().analyze(ctx)

    weak = [i for i in result.issues if i.type == IssueType.CRYPTO_MISUSE]
    assert len(weak) == 1
    assert "md5" in weak[0].title.lower()


def test_sha1_call_flagged() -> None:
    call = _node(NodeType.CALL, name="hashlib.sha1", line=5)
    ctx = _context(file_asts={"app.py": _module(call)})

    result = SecurityAgent().analyze(ctx)

    assert any(i.type == IssueType.CRYPTO_MISUSE for i in result.issues)


def test_strong_crypto_not_flagged() -> None:
    call = _node(NodeType.CALL, name="hashlib.sha256", line=5)
    ctx = _context(file_asts={"app.py": _module(call)})

    result = SecurityAgent().analyze(ctx)

    assert not any(i.type == IssueType.CRYPTO_MISUSE for i in result.issues)


def test_word_describe_does_not_match_des() -> None:
    # `describe()` contains "des" but should not be flagged.
    call = _node(NodeType.CALL, name="model.describe", line=3)
    ctx = _context(file_asts={"app.py": _module(call)})

    result = SecurityAgent().analyze(ctx)

    assert not any(i.type == IssueType.CRYPTO_MISUSE for i in result.issues)


def test_capabilities_advertise_security_issue_types() -> None:
    caps = SecurityAgent().capabilities

    assert caps.agent_id == "security_agent"
    assert IssueType.SQL_INJECTION in caps.issue_types
    assert IssueType.COMMAND_INJECTION in caps.issue_types
    assert IssueType.CRYPTO_MISUSE in caps.issue_types
    assert IssueType.SENSITIVE_DATA_EXPOSURE in caps.issue_types


def test_issues_stamped_with_agent_id() -> None:
    entity = _entity("e1", "app.py")
    literal = _node(NodeType.LITERAL, source_text='"x"', line=2)
    assignment = _node(NodeType.ASSIGNMENT, name="password", line=2, children=[literal])
    ctx = _context(
        flows=[_flow("sql_injection")],
        file_asts={"app.py": _module(assignment)},
        entities={"e1": entity},
    )

    result = SecurityAgent().analyze(ctx)

    assert result.issues
    assert all(i.agent_id == "security_agent" for i in result.issues)
