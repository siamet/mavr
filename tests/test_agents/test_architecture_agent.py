"""Tests for the Architecture Agent."""

from src.agents import AgentContext, ArchitectureAgent
from src.graph.knowledge_graph import KnowledgeGraph
from src.graph.relationship import RelationshipType
from src.metrics.entity_metrics import EntityMetrics
from src.metrics.structural_metrics import StructuralMetrics
from src.models.code_entity import CodeEntity, EntityType
from src.models.issue import IssueType, Severity
from src.models.source_location import SourceLocation
from src.pipeline.pipeline import PipelineResult


def _entity(
    eid: str,
    name: str,
    entity_type: EntityType,
    file_path: str = "app.py",
    parent_id: str | None = None,
    start_line: int = 1,
    end_line: int = 10,
) -> CodeEntity:
    return CodeEntity(
        id=eid,
        name=name,
        entity_type=entity_type,
        location=SourceLocation(file_path=file_path, start_line=start_line, end_line=end_line),
        language="python",
        parent_id=parent_id,
    )


def _build_class(
    graph: KnowledgeGraph,
    class_id: str,
    method_count: int,
    name: str | None = None,
) -> CodeEntity:
    class_name = name or f"Class_{class_id}"
    cls = _entity(class_id, class_name, EntityType.CLASS)
    graph.add_entity(cls)
    for i in range(method_count):
        method = _entity(
            f"{class_id}_m{i}",
            f"method_{i}",
            EntityType.METHOD,
            parent_id=class_id,
        )
        graph.add_entity(method)
        graph.add_relationship(class_id, method.id, RelationshipType.HAS_METHOD)
    return cls


def _context(
    graph: KnowledgeGraph,
    entity_metrics: dict | None = None,
    structural_metrics: dict | None = None,
    config: dict | None = None,
    target_entity_ids: list[str] | None = None,
) -> AgentContext:
    pr = PipelineResult()
    pr.graph = graph
    pr.entity_metrics = dict(entity_metrics or {})
    pr.structural_metrics = dict(structural_metrics or {})
    pr.entities_found = graph.entity_count
    return AgentContext(
        pipeline_result=pr,
        config=dict(config or {}),
        target_entity_ids=target_entity_ids,
    )


# ----- God Class -----


def test_god_class_flagged_when_method_count_exceeds_threshold() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C", method_count=25, name="UserManager")

    issues = ArchitectureAgent().analyze(_context(g)).issues
    god = [i for i in issues if i.type == IssueType.GOD_CLASS]

    assert len(god) == 1
    assert "UserManager" in god[0].title
    assert god[0].metrics["method_count"] == 25.0


def test_god_class_severity_high_when_multiple_thresholds_exceeded() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C", method_count=25, name="Mega")

    entity_metrics = {"C": EntityMetrics(entity_id="C", lines_of_code=600)}
    structural = {"C": StructuralMetrics(entity_id="C", lack_of_cohesion=0.8)}

    issues = ArchitectureAgent().analyze(_context(g, entity_metrics, structural)).issues
    god = [i for i in issues if i.type == IssueType.GOD_CLASS][0]

    assert god.severity == Severity.HIGH
    assert god.metrics["thresholds_exceeded"] == 3.0


def test_small_class_not_flagged_as_god_class() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C", method_count=5)

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.GOD_CLASS for i in issues)


def test_god_class_thresholds_overridable_via_config() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C", method_count=10, name="Mid")

    # Default threshold is 20 — wouldn't fire. Lower it to 5.
    config = {"architecture": {"god_class_method_count": 5}}
    issues = ArchitectureAgent().analyze(_context(g, config=config)).issues

    assert any(i.type == IssueType.GOD_CLASS for i in issues)


def test_non_class_entities_skipped_for_god_class() -> None:
    g = KnowledgeGraph()
    func = _entity("F", "huge_function", EntityType.FUNCTION)
    g.add_entity(func)
    entity_metrics = {"F": EntityMetrics(entity_id="F", lines_of_code=1000)}

    issues = ArchitectureAgent().analyze(_context(g, entity_metrics)).issues

    assert not any(i.type == IssueType.GOD_CLASS for i in issues)


# ----- Circular Dependency -----


def test_circular_dependency_via_calls() -> None:
    g = KnowledgeGraph()
    a = _entity("A", "A", EntityType.CLASS)
    b = _entity("B", "B", EntityType.CLASS)
    c = _entity("C", "C", EntityType.CLASS)
    for e in (a, b, c):
        g.add_entity(e)
    g.add_relationship("A", "B", RelationshipType.CALLS)
    g.add_relationship("B", "C", RelationshipType.CALLS)
    g.add_relationship("C", "A", RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues
    cycles = [i for i in issues if i.type == IssueType.CIRCULAR_DEPENDENCY]

    assert len(cycles) == 1
    assert cycles[0].metrics["cycle_length"] == 3.0
    assert set(cycles[0].affected_entities) == {"A", "B", "C"}


def test_acyclic_graph_emits_no_cycle_issues() -> None:
    g = KnowledgeGraph()
    a = _entity("A", "A", EntityType.CLASS)
    b = _entity("B", "B", EntityType.CLASS)
    g.add_entity(a)
    g.add_entity(b)
    g.add_relationship("A", "B", RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.CIRCULAR_DEPENDENCY for i in issues)


def test_has_method_edges_do_not_create_spurious_cycles() -> None:
    # HAS_METHOD edges form a tree (class -> method); they should not be
    # interpreted as dependency cycles even if other edges exist.
    g = KnowledgeGraph()
    cls = _build_class(g, "C", method_count=2)
    # No CALLS edges at all — graph is acyclic in the dependency subgraph.

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.CIRCULAR_DEPENDENCY for i in issues)
    assert cls.id == "C"  # silence unused-var


# ----- Feature Envy -----


def test_feature_envy_flagged_when_external_calls_dominate() -> None:
    g = KnowledgeGraph()
    own = _entity("Own", "OwnerClass", EntityType.CLASS)
    envied = _entity("Envied", "DataBag", EntityType.CLASS)
    method = _entity("M", "do_work", EntityType.METHOD, parent_id="Own")
    g.add_entity(own)
    g.add_entity(envied)
    g.add_entity(method)
    g.add_relationship("Own", "M", RelationshipType.HAS_METHOD)

    # Four methods on DataBag, one on OwnerClass.
    for i, parent in enumerate(["Envied", "Envied", "Envied", "Envied", "Own"]):
        callee_id = f"callee_{i}"
        callee = _entity(callee_id, f"f{i}", EntityType.METHOD, parent_id=parent)
        g.add_entity(callee)
        g.add_relationship("M", callee_id, RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues
    envy = [i for i in issues if i.type == IssueType.FEATURE_ENVY]

    assert len(envy) == 1
    assert "DataBag" in envy[0].title
    assert envy[0].metrics["external_calls"] == 4.0
    assert envy[0].metrics["internal_calls"] == 1.0


def test_balanced_method_not_flagged_as_feature_envy() -> None:
    g = KnowledgeGraph()
    own = _entity("Own", "Own", EntityType.CLASS)
    other = _entity("Other", "Other", EntityType.CLASS)
    method = _entity("M", "balanced", EntityType.METHOD, parent_id="Own")
    g.add_entity(own)
    g.add_entity(other)
    g.add_entity(method)

    # 2 external, 3 internal — well within ratio.
    for i, parent in enumerate(["Other", "Other", "Own", "Own", "Own"]):
        callee = _entity(f"c{i}", f"f{i}", EntityType.METHOD, parent_id=parent)
        g.add_entity(callee)
        g.add_relationship("M", callee.id, RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.FEATURE_ENVY for i in issues)


def test_top_level_function_not_flagged_as_feature_envy() -> None:
    g = KnowledgeGraph()
    other = _entity("Other", "Other", EntityType.CLASS)
    fn = _entity("F", "top_level", EntityType.FUNCTION, parent_id=None)
    g.add_entity(other)
    g.add_entity(fn)
    for i in range(5):
        callee = _entity(f"c{i}", f"f{i}", EntityType.METHOD, parent_id="Other")
        g.add_entity(callee)
        g.add_relationship("F", callee.id, RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.FEATURE_ENVY for i in issues)


def test_feature_envy_below_min_calls_not_flagged() -> None:
    g = KnowledgeGraph()
    own = _entity("Own", "Own", EntityType.CLASS)
    other = _entity("Other", "Other", EntityType.CLASS)
    method = _entity("M", "small", EntityType.METHOD, parent_id="Own")
    g.add_entity(own)
    g.add_entity(other)
    g.add_entity(method)

    # Only 2 external calls — below default min of 3.
    for i in range(2):
        callee = _entity(f"c{i}", f"f{i}", EntityType.METHOD, parent_id="Other")
        g.add_entity(callee)
        g.add_relationship("M", callee.id, RelationshipType.CALLS)

    issues = ArchitectureAgent().analyze(_context(g)).issues

    assert not any(i.type == IssueType.FEATURE_ENVY for i in issues)


# ----- Agent contract -----


def test_capabilities_advertise_three_architecture_types() -> None:
    caps = ArchitectureAgent().capabilities

    assert caps.agent_id == "architecture_agent"
    assert caps.issue_types == {
        IssueType.GOD_CLASS,
        IssueType.CIRCULAR_DEPENDENCY,
        IssueType.FEATURE_ENVY,
    }


def test_issues_stamped_with_agent_id() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C", method_count=25, name="Big")

    result = ArchitectureAgent().analyze(_context(g))

    assert result.issues
    assert all(i.agent_id == "architecture_agent" for i in result.issues)


def test_target_entity_ids_filters_god_class_scan() -> None:
    g = KnowledgeGraph()
    _build_class(g, "C1", method_count=25, name="First")
    _build_class(g, "C2", method_count=25, name="Second")

    result = ArchitectureAgent().analyze(_context(g, target_entity_ids=["C1"]))
    god_names = [i.title for i in result.issues if i.type == IssueType.GOD_CLASS]

    assert any("First" in t for t in god_names)
    assert not any("Second" in t for t in god_names)
