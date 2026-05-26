"""Tests for CFG construction."""

import pytest

from src.analysis.cfg import BasicBlock, ControlFlowGraph
from src.analysis.cfg_builder import CFGBuilder
from src.parsing.ast_nodes import ASTNode, NodeType


def _make_node(
    node_type: NodeType,
    name: str = None,
    children: list = None,
    start_line: int = 1,
    end_line: int = 5,
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


class TestBasicBlock:
    def test_empty_block(self) -> None:
        b = BasicBlock(id="b1")
        assert b.is_empty

    def test_non_empty_block(self) -> None:
        stmt = _make_node(NodeType.RETURN)
        b = BasicBlock(id="b1", statements=[stmt])
        assert not b.is_empty


class TestControlFlowGraph:
    def test_create_cfg(self) -> None:
        cfg = ControlFlowGraph("my_func")
        assert cfg.function_name == "my_func"
        assert cfg.block_count == 0

    def test_add_block_and_edge(self) -> None:
        cfg = ControlFlowGraph("f")
        b1 = BasicBlock(id="b1")
        b2 = BasicBlock(id="b2")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_edge("b1", "b2", label="next")
        assert cfg.block_count == 2
        assert cfg.edge_count == 1
        assert cfg.get_edge_label("b1", "b2") == "next"

    def test_successors_predecessors(self) -> None:
        cfg = ControlFlowGraph("f")
        b1 = BasicBlock(id="b1")
        b2 = BasicBlock(id="b2")
        b3 = BasicBlock(id="b3")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(b3)
        cfg.add_edge("b1", "b2")
        cfg.add_edge("b1", "b3")
        succs = cfg.get_successors("b1")
        assert len(succs) == 2
        preds = cfg.get_predecessors("b2")
        assert len(preds) == 1
        assert preds[0].id == "b1"


class TestCFGBuilder:
    @pytest.fixture
    def builder(self) -> CFGBuilder:
        return CFGBuilder()

    def test_linear_function(self, builder: CFGBuilder) -> None:
        """Function with no branches: entry -> stmts -> exit."""
        body_block = _make_node(
            NodeType.BLOCK,
            children=[
                _make_node(NodeType.ASSIGNMENT, source_text="x = 1"),
                _make_node(NodeType.RETURN, source_text="return x"),
            ],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[body_block],
        )
        cfg = builder.build(func)
        assert cfg.function_name == "foo"
        assert cfg.entry_block is not None
        assert cfg.exit_block is not None
        assert cfg.block_count >= 2

    def test_if_branch(self, builder: CFGBuilder) -> None:
        """Function with if creates true/false/merge blocks."""
        if_node = _make_node(NodeType.IF)
        body_block = _make_node(
            NodeType.BLOCK,
            children=[if_node],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="branchy",
            children=[body_block],
        )
        cfg = builder.build(func)
        # Should have entry, true, false, merge, exit = 5+ blocks
        assert cfg.block_count >= 5

        # Check for true/false edge labels
        labels = set()
        for _, _, data in cfg.networkx_graph.edges(data=True):
            labels.add(data.get("label"))
        assert "true" in labels
        assert "false" in labels

    def test_for_loop(self, builder: CFGBuilder) -> None:
        """Function with for loop creates header/body/after blocks."""
        for_node = _make_node(NodeType.FOR)
        body_block = _make_node(
            NodeType.BLOCK,
            children=[for_node],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="loopy",
            children=[body_block],
        )
        cfg = builder.build(func)
        # Should have back edge
        labels = set()
        for _, _, data in cfg.networkx_graph.edges(data=True):
            labels.add(data.get("label"))
        assert "back" in labels

    def test_while_loop(self, builder: CFGBuilder) -> None:
        for_node = _make_node(NodeType.WHILE)
        body_block = _make_node(
            NodeType.BLOCK,
            children=[for_node],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="while_func",
            children=[body_block],
        )
        cfg = builder.build(func)
        assert cfg.block_count >= 4

    def test_try_except(self, builder: CFGBuilder) -> None:
        try_node = _make_node(NodeType.TRY)
        body_block = _make_node(
            NodeType.BLOCK,
            children=[try_node],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="try_func",
            children=[body_block],
        )
        cfg = builder.build(func)
        labels = set()
        for _, _, data in cfg.networkx_graph.edges(data=True):
            labels.add(data.get("label"))
        assert "exception" in labels

    def test_return_connects_to_exit(self, builder: CFGBuilder) -> None:
        body_block = _make_node(
            NodeType.BLOCK,
            children=[
                _make_node(NodeType.RETURN, source_text="return 42"),
            ],
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="ret_func",
            children=[body_block],
        )
        cfg = builder.build(func)
        # Should have a 'return' edge to exit
        labels = set()
        for _, _, data in cfg.networkx_graph.edges(data=True):
            labels.add(data.get("label"))
        assert "return" in labels
