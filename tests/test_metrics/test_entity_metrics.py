"""Tests for EntityMetricsCalculator."""

import pytest

from src.metrics.entity_metrics import EntityMetrics, EntityMetricsCalculator
from src.parsing.ast_nodes import ASTNode, NodeType


def _make_node(
    node_type: NodeType,
    name: str = None,
    children: list = None,
    start_line: int = 1,
    end_line: int = 1,
    source_text: str = "",
    language: str = "python",
    attributes: dict = None,
) -> ASTNode:
    node = ASTNode(
        node_type=node_type,
        name=name,
        source_text=source_text,
        start_line=start_line,
        end_line=end_line,
        start_column=0,
        end_column=0,
        language=language,
        attributes=attributes or {},
    )
    for child in children or []:
        node.add_child(child)
    return node


class TestEntityMetricsCalculator:
    @pytest.fixture
    def calc(self) -> EntityMetricsCalculator:
        return EntityMetricsCalculator()

    def test_lines_of_code(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            start_line=1,
            end_line=10,
        )
        m = calc.compute(node, "f1")
        assert m.lines_of_code == 10

    def test_cyclomatic_complexity_simple(self, calc: EntityMetricsCalculator) -> None:
        # Simple function with no branches = complexity 1
        node = _make_node(
            NodeType.FUNCTION,
            name="simple",
            children=[
                _make_node(NodeType.RETURN, start_line=2, end_line=2),
            ],
            start_line=1,
            end_line=3,
        )
        m = calc.compute(node, "f1")
        assert m.cyclomatic_complexity == 1

    def test_cyclomatic_complexity_with_branches(self, calc: EntityMetricsCalculator) -> None:
        # Function with if + for + while = complexity 4
        node = _make_node(
            NodeType.FUNCTION,
            name="complex",
            children=[
                _make_node(NodeType.IF, start_line=2, end_line=3),
                _make_node(NodeType.FOR, start_line=4, end_line=5),
                _make_node(NodeType.WHILE, start_line=6, end_line=7),
            ],
            start_line=1,
            end_line=8,
        )
        m = calc.compute(node, "f1")
        assert m.cyclomatic_complexity == 4

    def test_nesting_depth(self, calc: EntityMetricsCalculator) -> None:
        # if -> for (nested)
        inner_for = _make_node(NodeType.FOR, start_line=3, end_line=4)
        outer_if = _make_node(
            NodeType.IF,
            children=[inner_for],
            start_line=2,
            end_line=5,
        )
        node = _make_node(
            NodeType.FUNCTION,
            name="nested",
            children=[outer_if],
            start_line=1,
            end_line=6,
        )
        m = calc.compute(node, "f1")
        assert m.nesting_depth_max == 2

    def test_parameter_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(NodeType.PARAMETER, name="x"),
                _make_node(NodeType.PARAMETER, name="y"),
            ],
            start_line=1,
            end_line=3,
        )
        m = calc.compute(node, "f1")
        assert m.parameter_count == 2

    def test_return_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(
                    NodeType.IF,
                    children=[
                        _make_node(NodeType.RETURN),
                    ],
                ),
                _make_node(NodeType.RETURN),
            ],
            start_line=1,
            end_line=5,
        )
        m = calc.compute(node, "f1")
        assert m.return_count == 2

    def test_branch_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(NodeType.IF),
                _make_node(NodeType.FOR),
                _make_node(NodeType.TRY),
            ],
            start_line=1,
            end_line=10,
        )
        m = calc.compute(node, "f1")
        assert m.branch_count == 3

    def test_loop_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(NodeType.FOR),
                _make_node(NodeType.WHILE),
                _make_node(NodeType.IF),
            ],
            start_line=1,
            end_line=10,
        )
        m = calc.compute(node, "f1")
        assert m.loop_count == 2

    def test_call_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(NodeType.CALL),
                _make_node(NodeType.CALL),
            ],
            start_line=1,
            end_line=5,
        )
        m = calc.compute(node, "f1")
        assert m.call_count == 2

    def test_comment_count(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[
                _make_node(NodeType.COMMENT, source_text="# a comment"),
            ],
            start_line=1,
            end_line=3,
        )
        m = calc.compute(node, "f1")
        assert m.comment_count == 1

    def test_zero_lines(self, calc: EntityMetricsCalculator) -> None:
        node = _make_node(
            NodeType.FUNCTION,
            name="foo",
            start_line=0,
            end_line=0,
        )
        m = calc.compute(node, "f1")
        assert m.lines_of_code == 0


class TestEntityMetricsWithParser:
    """Integration test using real parser output."""

    def test_compute_from_parsed_python(self, sample_python_file) -> None:
        from src.parsing.python_parser import PythonParser

        parser = PythonParser()
        ast = parser.parse_file(str(sample_python_file))
        assert ast is not None

        calc = EntityMetricsCalculator()
        m = calc.compute(ast, "module1")

        # The sample.py file has content
        assert m.lines_of_code > 0
        # Should have some branches (if in divide method)
        assert m.branch_count >= 1
