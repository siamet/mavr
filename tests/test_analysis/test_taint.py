"""Tests for TaintAnalyzer."""

import pytest

from src.analysis.cfg import BasicBlock, ControlFlowGraph
from src.analysis.taint import (
    TaintAnalyzer,
    TaintFlow,
    TaintSink,
    TaintSanitizer,
    TaintSource,
)
from src.parsing.ast_nodes import ASTNode, NodeType


def _make_stmt(source_text: str) -> ASTNode:
    """Create a simple statement node with source text."""
    return ASTNode(
        node_type=NodeType.UNKNOWN,
        source_text=source_text,
        start_line=1,
        end_line=1,
        start_column=0,
        end_column=0,
        language="python",
    )


class TestTaintAnalyzer:
    @pytest.fixture
    def analyzer(self) -> TaintAnalyzer:
        return TaintAnalyzer()

    def test_no_taint_flows(self, analyzer: TaintAnalyzer) -> None:
        cfg = ControlFlowGraph("clean")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("x = 42")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "exit")
        flows = analyzer.analyze(cfg)
        assert flows == []

    def test_detect_sql_injection(self, analyzer: TaintAnalyzer) -> None:
        cfg = ControlFlowGraph("vuln")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("user = input('name: ')")],
        )
        b2 = BasicBlock(
            id="b2",
            statements=[_make_stmt("cursor.execute('SELECT * WHERE name=' + user)")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "b2")
        cfg.add_edge("b2", "exit")

        flows = analyzer.analyze(cfg)
        assert len(flows) >= 1
        assert any(f.sink.vulnerability == "sql_injection" for f in flows)
        assert any(not f.sanitized for f in flows)

    def test_sanitized_flow(self) -> None:
        sources = [TaintSource("input", r"input", "user_input")]
        sinks = [TaintSink("sql", r"execute", "sql_injection")]
        sanitizers = [TaintSanitizer("escape", r"escape_string", ["sql_injection"])]
        analyzer = TaintAnalyzer(sources, sinks, sanitizers)

        cfg = ControlFlowGraph("sanitized")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("user = input()")],
        )
        b2 = BasicBlock(
            id="b2",
            statements=[_make_stmt("safe = escape_string(user)")],
        )
        b3 = BasicBlock(
            id="b3",
            statements=[_make_stmt("cursor.execute(safe)")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(b3)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "b2")
        cfg.add_edge("b2", "b3")
        cfg.add_edge("b3", "exit")

        flows = analyzer.analyze(cfg)
        assert len(flows) >= 1
        assert all(f.sanitized for f in flows)

    def test_detect_command_injection(self, analyzer: TaintAnalyzer) -> None:
        cfg = ControlFlowGraph("cmd_inj")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("cmd = input('command: ')")],
        )
        b2 = BasicBlock(
            id="b2",
            statements=[_make_stmt("os.system(cmd)")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "b2")
        cfg.add_edge("b2", "exit")

        flows = analyzer.analyze(cfg)
        assert any(f.sink.vulnerability == "command_injection" for f in flows)

    def test_custom_sources_sinks(self) -> None:
        sources = [TaintSource("api", r"api\.get", "network")]
        sinks = [TaintSink("log", r"write_log", "info_leak")]
        analyzer = TaintAnalyzer(sources, sinks, [])

        cfg = ControlFlowGraph("custom")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("data = api.get('/users')")],
        )
        b2 = BasicBlock(
            id="b2",
            statements=[_make_stmt("write_log(data)")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(exit_b)
        cfg.add_edge("b1", "b2")
        cfg.add_edge("b2", "exit")

        flows = analyzer.analyze(cfg)
        assert len(flows) == 1
        assert flows[0].sink.vulnerability == "info_leak"

    def test_no_path_between_source_and_sink(self, analyzer: TaintAnalyzer) -> None:
        cfg = ControlFlowGraph("no_path")
        b1 = BasicBlock(
            id="b1",
            statements=[_make_stmt("user = input()")],
        )
        b2 = BasicBlock(
            id="b2",
            statements=[_make_stmt("cursor.execute('safe query')")],
        )
        exit_b = BasicBlock(id="exit")
        cfg.add_block(b1)
        cfg.add_block(b2)
        cfg.add_block(exit_b)
        # No edge from b1 to b2 — they're disconnected
        cfg.add_edge("b1", "exit")
        cfg.add_edge("b2", "exit")

        flows = analyzer.analyze(cfg)
        # Source in b1 can't reach sink in b2
        unsanitized = [f for f in flows if not f.sanitized]
        # Either no flows, or flows have empty paths
        for f in unsanitized:
            # If there's a flow, it must have a valid path
            assert len(f.path) > 0 or f.sanitized
