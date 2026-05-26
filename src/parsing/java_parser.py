"""Java code parser using tree-sitter."""

from typing import Optional, Any

try:
    from tree_sitter import Language, Parser
    import tree_sitter_java

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from src.parsing.base_parser import BaseParser
from src.parsing.ast_nodes import ASTNode, NodeType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JavaParser(BaseParser):
    """Parser for Java source code using tree-sitter.

    This parser uses tree-sitter to parse Java code and converts
    the tree-sitter AST to our unified AST representation.
    """

    def __init__(self):
        """Initialize the Java parser."""
        super().__init__("java")

        if not TREE_SITTER_AVAILABLE:
            raise ImportError(
                "tree-sitter not available. Install with: pip install tree-sitter tree-sitter-java"
            )

        try:
            # Create parser with Java language
            java_language = Language(tree_sitter_java.language())
            self.parser = Parser(java_language)
            logger.info("Java parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Java parser: {e}")
            raise

    def parse_file(self, file_path: str) -> Optional[ASTNode]:
        """Parse a Java file.

        Args:
            file_path: Path to Java file

        Returns:
            Root AST node or None if parsing fails
        """
        try:
            self.validate_file(file_path)
            source_code = self.read_file(file_path)
            return self.parse_string(source_code, file_path)
        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return None

    def parse_string(self, source_code: str, file_path: str = "<string>") -> Optional[ASTNode]:
        """Parse Java source code from string.

        Args:
            source_code: Java source code
            file_path: Optional file path for context

        Returns:
            Root AST node or None if parsing fails
        """
        try:
            # Parse with tree-sitter
            tree = self.parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node

            # Convert to our unified AST
            ast_root = self._convert_node(root_node, source_code, file_path)
            return ast_root

        except Exception as e:
            logger.error(f"Failed to parse Java code: {e}")
            return None

    def _convert_node(self, ts_node: Any, source_code: str, file_path: str) -> ASTNode:
        """Convert tree-sitter node to unified ASTNode.

        Args:
            ts_node: Tree-sitter node
            source_code: Original source code
            file_path: Source file path

        Returns:
            Unified ASTNode
        """
        # Map tree-sitter node types to our NodeType
        node_type = self._map_node_type(ts_node.type)

        # Extract source text for this node
        start_byte = ts_node.start_byte
        end_byte = ts_node.end_byte
        source_text = source_code[start_byte:end_byte]

        # Get position information
        start_line = ts_node.start_point[0] + 1  # Convert to 1-indexed
        start_column = ts_node.start_point[1]
        end_line = ts_node.end_point[0] + 1
        end_column = ts_node.end_point[1]

        # Extract name if applicable
        name = self._extract_name(ts_node, source_code)

        # Create ASTNode
        ast_node = ASTNode(
            node_type=node_type,
            name=name,
            source_text=source_text,
            start_line=start_line,
            end_line=end_line,
            start_column=start_column,
            end_column=end_column,
            language="java",
            attributes={"ts_type": ts_node.type},
        )

        # Recursively convert children
        for child in ts_node.children:
            child_node = self._convert_node(child, source_code, file_path)
            ast_node.add_child(child_node)

        return ast_node

    def _map_node_type(self, ts_type: str) -> NodeType:
        """Map tree-sitter node type to unified NodeType.

        Args:
            ts_type: Tree-sitter node type string

        Returns:
            Unified NodeType
        """
        type_mapping = {
            # Structural
            "program": NodeType.MODULE,
            "class_declaration": NodeType.CLASS,
            "interface_declaration": NodeType.CLASS,
            "enum_declaration": NodeType.CLASS,
            "method_declaration": NodeType.METHOD,
            "constructor_declaration": NodeType.CONSTRUCTOR,
            # Statements
            "import_declaration": NodeType.IMPORT,
            "package_declaration": NodeType.IMPORT,
            "local_variable_declaration": NodeType.ASSIGNMENT,
            "field_declaration": NodeType.FIELD,
            "assignment_expression": NodeType.ASSIGNMENT,
            "return_statement": NodeType.RETURN,
            "if_statement": NodeType.IF,
            "for_statement": NodeType.FOR,
            "enhanced_for_statement": NodeType.FOR,
            "while_statement": NodeType.WHILE,
            "do_statement": NodeType.WHILE,
            "try_statement": NodeType.TRY,
            "try_with_resources_statement": NodeType.TRY,
            "throw_statement": NodeType.THROW,
            # Expressions
            "method_invocation": NodeType.CALL,
            "object_creation_expression": NodeType.CALL,
            "binary_expression": NodeType.BINARY_OP,
            "unary_expression": NodeType.UNARY_OP,
            "update_expression": NodeType.UNARY_OP,
            "identifier": NodeType.IDENTIFIER,
            "decimal_integer_literal": NodeType.LITERAL,
            "hex_integer_literal": NodeType.LITERAL,
            "octal_integer_literal": NodeType.LITERAL,
            "binary_integer_literal": NodeType.LITERAL,
            "decimal_floating_point_literal": NodeType.LITERAL,
            "hex_floating_point_literal": NodeType.LITERAL,
            "string_literal": NodeType.LITERAL,
            "character_literal": NodeType.LITERAL,
            "true": NodeType.LITERAL,
            "false": NodeType.LITERAL,
            "null_literal": NodeType.LITERAL,
            # Declarations
            "variable_declarator": NodeType.VARIABLE,
            "formal_parameter": NodeType.PARAMETER,
            "spread_parameter": NodeType.PARAMETER,
            # Other
            "line_comment": NodeType.COMMENT,
            "block_comment": NodeType.COMMENT,
            "block": NodeType.BLOCK,
        }

        return type_mapping.get(ts_type, NodeType.UNKNOWN)

    def _extract_name(self, ts_node: Any, source_code: str) -> Optional[str]:
        """Extract the name identifier from a node if applicable.

        Args:
            ts_node: Tree-sitter node
            source_code: Original source code

        Returns:
            Name string or None
        """
        # For class, interface, enum, and method declarations, find the name child
        if ts_node.type in [
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "method_declaration",
            "constructor_declaration",
        ]:
            for child in ts_node.children:
                if child.type == "identifier":
                    start = child.start_byte
                    end = child.end_byte
                    return source_code[start:end]

        # For variable declarators, get the identifier
        if ts_node.type in ["variable_declarator", "formal_parameter"]:
            for child in ts_node.children:
                if child.type == "identifier":
                    start = child.start_byte
                    end = child.end_byte
                    return source_code[start:end]

        # For field declarations, find the variable_declarator
        if ts_node.type == "field_declaration":
            for child in ts_node.children:
                if child.type == "variable_declarator":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            start = subchild.start_byte
                            end = subchild.end_byte
                            return source_code[start:end]

        # For identifiers, return the text directly
        if ts_node.type == "identifier":
            start = ts_node.start_byte
            end = ts_node.end_byte
            return source_code[start:end]

        return None
