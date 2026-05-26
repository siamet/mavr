"""Tests for StructuralMetricsCalculator."""

import pytest

from src.graph.knowledge_graph import KnowledgeGraph
from src.graph.relationship import RelationshipType
from src.metrics.structural_metrics import (
    StructuralMetrics,
    StructuralMetricsCalculator,
)
from src.models.code_entity import CodeEntity, EntityType
from src.models.source_location import SourceLocation


def _make_entity(
    entity_id: str,
    name: str,
    entity_type: EntityType,
    file_path: str = "test.py",
) -> CodeEntity:
    return CodeEntity(
        id=entity_id,
        name=name,
        entity_type=entity_type,
        location=SourceLocation(file_path=file_path, start_line=1, end_line=10),
        language="python",
    )


class TestStructuralMetricsCalculator:
    @pytest.fixture
    def calc(self) -> StructuralMetricsCalculator:
        return StructuralMetricsCalculator()

    def test_fan_in_out(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("f1", "foo", EntityType.FUNCTION))
        g.add_entity(_make_entity("f2", "bar", EntityType.FUNCTION))
        g.add_entity(_make_entity("f3", "baz", EntityType.FUNCTION))
        g.add_relationship("f2", "f1", RelationshipType.CALLS)
        g.add_relationship("f3", "f1", RelationshipType.CALLS)
        g.add_relationship("f1", "f2", RelationshipType.CALLS)

        m = calc.compute(g, "f1")
        assert m.fan_in == 2
        assert m.fan_out == 1

    def test_coupling(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "B", EntityType.CLASS))
        g.add_entity(_make_entity("c3", "C", EntityType.CLASS))
        # B depends on A, C depends on A
        g.add_relationship("c2", "c1", RelationshipType.DEPENDS_ON)
        g.add_relationship("c3", "c1", RelationshipType.DEPENDS_ON)
        # A depends on B
        g.add_relationship("c1", "c2", RelationshipType.DEPENDS_ON)

        m = calc.compute(g, "c1")
        assert m.afferent_coupling == 2  # B and C depend on A
        assert m.efferent_coupling == 1  # A depends on B
        assert m.coupling_between_objects == 3

    def test_instability(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "B", EntityType.CLASS))
        g.add_relationship("c1", "c2", RelationshipType.DEPENDS_ON)
        # Ca=0, Ce=1 => instability = 1.0
        m = calc.compute(g, "c1")
        assert m.instability == 1.0

    def test_instability_stable(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "B", EntityType.CLASS))
        g.add_relationship("c2", "c1", RelationshipType.DEPENDS_ON)
        # Ca=1, Ce=0 => instability = 0.0
        m = calc.compute(g, "c1")
        assert m.instability == 0.0

    def test_dit(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "Base", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "Mid", EntityType.CLASS))
        g.add_entity(_make_entity("c3", "Child", EntityType.CLASS))
        g.add_relationship("c3", "c2", RelationshipType.INHERITS)
        g.add_relationship("c2", "c1", RelationshipType.INHERITS)

        m = calc.compute(g, "c3")
        assert m.depth_of_inheritance == 2

    def test_noc(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "Base", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "Sub1", EntityType.CLASS))
        g.add_entity(_make_entity("c3", "Sub2", EntityType.CLASS))
        g.add_relationship("c2", "c1", RelationshipType.INHERITS)
        g.add_relationship("c3", "c1", RelationshipType.INHERITS)

        m = calc.compute(g, "c1")
        assert m.number_of_children == 2

    def test_lcom_cohesive(self, calc: StructuralMetricsCalculator) -> None:
        """Two methods both using the same field = high cohesion."""
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("m1", "get_x", EntityType.METHOD))
        g.add_entity(_make_entity("m2", "set_x", EntityType.METHOD))
        g.add_entity(_make_entity("f1", "x", EntityType.FIELD))
        g.add_relationship("c1", "m1", RelationshipType.HAS_METHOD)
        g.add_relationship("c1", "m2", RelationshipType.HAS_METHOD)
        g.add_relationship("c1", "f1", RelationshipType.HAS_FIELD)
        g.add_relationship("m1", "f1", RelationshipType.USES)
        g.add_relationship("m2", "f1", RelationshipType.USES)

        m = calc.compute(g, "c1")
        assert m.lack_of_cohesion == 0.0

    def test_lcom_not_cohesive(self, calc: StructuralMetricsCalculator) -> None:
        """Two methods using different fields = low cohesion."""
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("m1", "get_x", EntityType.METHOD))
        g.add_entity(_make_entity("m2", "get_y", EntityType.METHOD))
        g.add_entity(_make_entity("f1", "x", EntityType.FIELD))
        g.add_entity(_make_entity("f2", "y", EntityType.FIELD))
        g.add_relationship("c1", "m1", RelationshipType.HAS_METHOD)
        g.add_relationship("c1", "m2", RelationshipType.HAS_METHOD)
        g.add_relationship("c1", "f1", RelationshipType.HAS_FIELD)
        g.add_relationship("c1", "f2", RelationshipType.HAS_FIELD)
        g.add_relationship("m1", "f1", RelationshipType.USES)
        g.add_relationship("m2", "f2", RelationshipType.USES)

        m = calc.compute(g, "c1")
        assert m.lack_of_cohesion == 1.0

    def test_compute_all(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "A", EntityType.CLASS))
        g.add_entity(_make_entity("c2", "B", EntityType.CLASS))
        all_metrics = calc.compute_all(g)
        assert "c1" in all_metrics
        assert "c2" in all_metrics

    def test_no_coupling(self, calc: StructuralMetricsCalculator) -> None:
        g = KnowledgeGraph()
        g.add_entity(_make_entity("c1", "Isolated", EntityType.CLASS))
        m = calc.compute(g, "c1")
        assert m.afferent_coupling == 0
        assert m.efferent_coupling == 0
        assert m.instability == 0.0
