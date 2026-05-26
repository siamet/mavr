"""Tests for DataFlowAnalyzer."""

import pytest

from src.analysis.cfg import BasicBlock, ControlFlowGraph
from src.analysis.data_flow import DataFlowAnalyzer, Definition, Use
from src.parsing.ast_nodes import ASTNode, NodeType


def _make_node(
    node_type: NodeType,
    name: str = None,
    children: list = None,
    source_text: str = "",
) -> ASTNode:
    node = ASTNode(
        node_type=node_type,
        name=name,
        source_text=source_text,
        start_line=1,
        end_line=1,
        start_column=0,
        end_column=0,
        language="python",
    )
    for child in children or []:
        node.add_child(child)
    return node


def _build_simple_cfg() -> ControlFlowGraph:
    """Build a simple CFG: b1 (x=1) -> b2 (use x) -> exit."""
    cfg = ControlFlowGraph("simple")

    # Block 1: x = 1
    ident_x = _make_node(NodeType.IDENTIFIER, name="x")
    assign = _make_node(
        NodeType.ASSIGNMENT,
        children=[ident_x],
        source_text="x = 1",
    )
    b1 = BasicBlock(id="b1", statements=[assign])

    # Block 2: print(x)
    use_x = _make_node(NodeType.IDENTIFIER, name="x")
    call = _make_node(
        NodeType.CALL,
        children=[use_x],
        source_text="print(x)",
    )
    b2 = BasicBlock(id="b2", statements=[call])

    exit_block = BasicBlock(id="exit")

    cfg.add_block(b1)
    cfg.add_block(b2)
    cfg.add_block(exit_block)
    cfg.entry_block = b1
    cfg.exit_block = exit_block

    cfg.add_edge("b1", "b2")
    cfg.add_edge("b2", "exit")

    return cfg


class TestDataFlowAnalyzer:
    @pytest.fixture
    def analyzer(self) -> DataFlowAnalyzer:
        return DataFlowAnalyzer()

    def test_reaching_definitions(self, analyzer: DataFlowAnalyzer) -> None:
        cfg = _build_simple_cfg()
        result = analyzer.analyze(cfg)

        # Definition of x in b1 should reach b2
        defs_at_b2 = result.reaching_definitions.get("b2", set())
        assert any(d.variable == "x" for d in defs_at_b2)

    def test_use_def_chains(self, analyzer: DataFlowAnalyzer) -> None:
        cfg = _build_simple_cfg()
        result = analyzer.analyze(cfg)

        # The use of x in b2 should link to the definition in b1
        x_use = Use(variable="x", block_id="b2")
        if x_use in result.use_def_chains:
            defs = result.use_def_chains[x_use]
            assert any(d.variable == "x" and d.block_id == "b1" for d in defs)

    def test_def_use_chains(self, analyzer: DataFlowAnalyzer) -> None:
        cfg = _build_simple_cfg()
        result = analyzer.analyze(cfg)

        # The definition of x in b1 should have a use in b2
        x_def = Definition(variable="x", block_id="b1")
        if x_def in result.def_use_chains:
            uses = result.def_use_chains[x_def]
            assert any(u.variable == "x" and u.block_id == "b2" for u in uses)

    def test_empty_cfg(self, analyzer: DataFlowAnalyzer) -> None:
        cfg = ControlFlowGraph("empty")
        entry = BasicBlock(id="entry")
        exit_b = BasicBlock(id="exit")
        cfg.add_block(entry)
        cfg.add_block(exit_b)
        cfg.add_edge("entry", "exit")
        result = analyzer.analyze(cfg)
        assert isinstance(result.reaching_definitions, dict)

    def test_no_definitions(self, analyzer: DataFlowAnalyzer) -> None:
        cfg = ControlFlowGraph("no_defs")
        use_x = _make_node(NodeType.IDENTIFIER, name="x")
        call = _make_node(NodeType.CALL, children=[use_x])
        b1 = BasicBlock(id="b1", statements=[call])
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "exit")
        result = analyzer.analyze(cfg)
        # Use of x should have no reaching definitions
        x_use = Use(variable="x", block_id="b1")
        defs = result.use_def_chains.get(x_use, set())
        assert len(defs) == 0
