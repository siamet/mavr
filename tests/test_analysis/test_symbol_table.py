"""Tests for SymbolTable."""

import pytest

from src.analysis.symbol_table import Symbol, Scope, SymbolTable
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


class TestScope:
    def test_define_and_lookup(self) -> None:
        s = Scope("test")
        sym = Symbol(name="x", symbol_type="variable", scope_id="test")
        s.define(sym)
        assert s.lookup("x") is sym

    def test_lookup_not_found(self) -> None:
        s = Scope("test")
        assert s.lookup("missing") is None

    def test_lookup_parent_chain(self) -> None:
        parent = Scope("parent")
        child = Scope("child", parent=parent)
        sym = Symbol(name="x", symbol_type="variable", scope_id="parent")
        parent.define(sym)
        # Should find x through parent chain
        assert child.lookup("x") is sym

    def test_lookup_local_only(self) -> None:
        parent = Scope("parent")
        child = Scope("child", parent=parent)
        sym = Symbol(name="x", symbol_type="variable", scope_id="parent")
        parent.define(sym)
        # Local lookup should not find parent's symbol
        assert child.lookup_local("x") is None

    def test_shadowing(self) -> None:
        parent = Scope("parent")
        child = Scope("child", parent=parent)
        parent_sym = Symbol(name="x", symbol_type="variable", scope_id="parent")
        child_sym = Symbol(name="x", symbol_type="variable", scope_id="child")
        parent.define(parent_sym)
        child.define(child_sym)
        # Child's x should shadow parent's
        assert child.lookup("x") is child_sym
        assert parent.lookup("x") is parent_sym


class TestSymbolTable:
    @pytest.fixture
    def table(self) -> SymbolTable:
        return SymbolTable()

    def test_build_from_simple_module(self, table: SymbolTable) -> None:
        func = _make_node(NodeType.FUNCTION, name="foo")
        root = _make_node(NodeType.MODULE, children=[func])
        table.build_from_ast(root)
        assert table.global_scope is not None
        assert table.scope_count >= 2  # global + foo

    def test_resolve_function_in_global(self, table: SymbolTable) -> None:
        func = _make_node(NodeType.FUNCTION, name="foo")
        root = _make_node(NodeType.MODULE, children=[func])
        table.build_from_ast(root)
        sym = table.resolve("foo", "global")
        assert sym is not None
        assert sym.name == "foo"
        assert sym.symbol_type == "function"

    def test_resolve_class_in_global(self, table: SymbolTable) -> None:
        cls = _make_node(NodeType.CLASS, name="MyClass")
        root = _make_node(NodeType.MODULE, children=[cls])
        table.build_from_ast(root)
        sym = table.resolve("MyClass", "global")
        assert sym is not None
        assert sym.symbol_type == "class"

    def test_resolve_method_in_class_scope(self, table: SymbolTable) -> None:
        method = _make_node(NodeType.METHOD, name="bar")
        cls = _make_node(NodeType.CLASS, name="Foo", children=[method])
        root = _make_node(NodeType.MODULE, children=[cls])
        table.build_from_ast(root)

        # bar should be in the Foo scope
        sym = table.resolve("bar", "global.Foo")
        assert sym is not None
        assert sym.symbol_type == "method"

    def test_resolve_parameter(self, table: SymbolTable) -> None:
        param = _make_node(NodeType.PARAMETER, name="x")
        func = _make_node(NodeType.FUNCTION, name="foo", children=[param])
        root = _make_node(NodeType.MODULE, children=[func])
        table.build_from_ast(root)

        sym = table.resolve("x", "global.foo")
        assert sym is not None
        assert sym.symbol_type == "parameter"

    def test_get_definitions(self, table: SymbolTable) -> None:
        func1 = _make_node(NodeType.FUNCTION, name="process")
        func2 = _make_node(NodeType.FUNCTION, name="process")
        cls = _make_node(NodeType.CLASS, name="A", children=[func2])
        root = _make_node(NodeType.MODULE, children=[func1, cls])
        table.build_from_ast(root)
        defs = table.get_definitions("process")
        assert len(defs) == 2

    def test_assignment_creates_symbol(self, table: SymbolTable) -> None:
        ident = _make_node(NodeType.IDENTIFIER, name="x")
        assignment = _make_node(
            NodeType.ASSIGNMENT,
            children=[ident],
            source_text="x = 42",
        )
        func = _make_node(
            NodeType.FUNCTION,
            name="foo",
            children=[assignment],
        )
        root = _make_node(NodeType.MODULE, children=[func])
        table.build_from_ast(root)

        sym = table.resolve("x", "global.foo")
        assert sym is not None
        assert sym.symbol_type == "variable"
