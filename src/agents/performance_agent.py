"""Performance agent: static analysis for common performance smells.

This agent walks the per-file ASTs in the pipeline result and emits
Issues for three v1 patterns:

- Nested loops (potential O(n^k)) -> INEFFICIENT_ALGORITHM
- Database-style calls inside a loop (N+1) -> N_PLUS_ONE_QUERY
- String accumulation via += inside a loop -> UNNECESSARY_COMPUTATION
"""

from typing import List, Optional, Set
from uuid import uuid4

from src.agents.base_agent import AgentCapabilities, AgentContext, BaseAgent
from src.models.issue import Issue, IssueType, Severity
from src.models.source_location import SourceLocation
from src.parsing.ast_nodes import ASTNode, NodeType

_LOOP_TYPES = {NodeType.FOR, NodeType.WHILE}
_FUNCTION_TYPES = {NodeType.FUNCTION, NodeType.METHOD, NodeType.CONSTRUCTOR}

# Heuristic: substrings that, when they appear in a call name, suggest a
# database / remote query. Intentionally conservative — false positives here
# are noisier than misses.
_DB_CALL_HINTS: Set[str] = {
    "query",
    "execute",
    "fetch",
    "fetchone",
    "fetchall",
    "find",
    "find_one",
    "find_all",
    "filter",
    "get",
    "get_one",
    "select",
    "all",
}


class PerformanceAgent(BaseAgent):
    """Detects performance smells via AST pattern matching."""

    AGENT_ID = "performance_agent"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_id=self.AGENT_ID,
            name="Performance Agent",
            description="Static analysis for performance smells (nested loops, N+1, repeated work).",
            issue_types={
                IssueType.INEFFICIENT_ALGORITHM,
                IssueType.N_PLUS_ONE_QUERY,
                IssueType.UNNECESSARY_COMPUTATION,
            },
            supported_languages={"python", "javascript", "typescript", "java"},
        )

    def _analyze(self, context: AgentContext) -> List[Issue]:
        issues: List[Issue] = []
        targets = self._resolve_target_files(context)

        for file_path, root in context.pipeline_result.file_asts.items():
            if targets is not None and file_path not in targets:
                continue
            issues.extend(self._scan_node(root, file_path, loop_depth=0))

        return issues

    def _resolve_target_files(self, context: AgentContext) -> Optional[Set[str]]:
        """Map target entity IDs to the set of files they live in."""
        if context.target_entity_ids is None:
            return None
        entities = context.pipeline_result.graph.entities
        return {
            entities[eid].location.file_path
            for eid in context.target_entity_ids
            if eid in entities
        }

    def _scan_node(self, node: ASTNode, file_path: str, loop_depth: int) -> List[Issue]:
        """Recursively walk the AST, emitting issues as patterns match.

        `loop_depth` is the number of enclosing loops at this point. Function
        definitions reset it to zero — their bodies aren't executed per iteration.
        """
        issues: List[Issue] = []

        if node.node_type in _LOOP_TYPES:
            new_depth = loop_depth + 1
            if new_depth >= 2:
                issues.append(self._nested_loop_issue(node, file_path, new_depth))
            for child in node.children:
                issues.extend(self._scan_node(child, file_path, new_depth))
            return issues

        if node.node_type in _FUNCTION_TYPES:
            for child in node.children:
                issues.extend(self._scan_node(child, file_path, loop_depth=0))
            return issues

        if loop_depth > 0:
            if node.node_type == NodeType.CALL and _is_db_call(node.name):
                issues.append(self._n_plus_one_issue(node, file_path))
            elif node.node_type == NodeType.BINARY_OP and _is_string_concat_accumulator(
                node
            ):
                issues.append(self._string_concat_issue(node, file_path))

        for child in node.children:
            issues.extend(self._scan_node(child, file_path, loop_depth))
        return issues

    def _nested_loop_issue(self, node: ASTNode, file_path: str, depth: int) -> Issue:
        severity = Severity.HIGH if depth >= 3 else Severity.MEDIUM
        return Issue(
            id=f"perf_nested_loop_{uuid4().hex[:8]}",
            type=IssueType.INEFFICIENT_ALGORITHM,
            severity=severity,
            location=_location_of(node, file_path),
            title=f"Nested loop (depth {depth})",
            description=f"Loop nested at depth {depth} can produce O(n^{depth}) complexity.",
            explanation=(
                "Deeply nested loops multiply iteration counts and can degrade "
                "performance sharply on large inputs."
            ),
            recommendation=(
                "Consider whether one of the loops can be hoisted, replaced by "
                "a hash-based lookup, or vectorized."
            ),
            confidence=0.75 if depth >= 3 else 0.6,
            agent_id=self.AGENT_ID,
            metrics={"loop_depth": float(depth)},
        )

    def _n_plus_one_issue(self, call_node: ASTNode, file_path: str) -> Issue:
        return Issue(
            id=f"perf_n_plus_one_{uuid4().hex[:8]}",
            type=IssueType.N_PLUS_ONE_QUERY,
            severity=Severity.HIGH,
            location=_location_of(call_node, file_path),
            title=f"Likely N+1 query: '{call_node.name}' inside loop",
            description=(
                f"Call to '{call_node.name}' appears inside a loop, suggesting "
                "one database round-trip per iteration."
            ),
            explanation=(
                "Repeated queries inside a loop typically scale linearly with the "
                "iteration count and dominate request latency."
            ),
            recommendation=(
                "Batch the query (e.g., a single IN/JOIN fetching all rows) or "
                "preload data outside the loop."
            ),
            confidence=0.55,
            agent_id=self.AGENT_ID,
        )

    def _string_concat_issue(self, op_node: ASTNode, file_path: str) -> Issue:
        return Issue(
            id=f"perf_str_concat_{uuid4().hex[:8]}",
            type=IssueType.UNNECESSARY_COMPUTATION,
            severity=Severity.LOW,
            location=_location_of(op_node, file_path),
            title="String concatenation in loop",
            description="String accumulation with += inside a loop creates a new string each iteration.",
            explanation=(
                "In languages with immutable strings (Python, Java), repeated "
                "concatenation is O(n^2) in the final length."
            ),
            recommendation=(
                "Collect parts in a list and join once after the loop, or use a "
                "language-native string builder."
            ),
            confidence=0.7,
            agent_id=self.AGENT_ID,
        )


def _is_db_call(call_name: Optional[str]) -> bool:
    """True if the (possibly dotted) call name ends in a DB-style hint."""
    if not call_name:
        return False
    tail = call_name.split(".")[-1].lower()
    return tail in _DB_CALL_HINTS


def _is_string_concat_accumulator(op_node: ASTNode) -> bool:
    """Match `x += y` or `x = x + y` style accumulation.

    We rely on the parsers tagging BINARY_OP nodes with an 'operator' attribute
    when available; otherwise fall back to scanning source_text.
    """
    op = op_node.attributes.get("operator") if op_node.attributes else None
    if op == "+=":
        return True
    src = (op_node.source_text or "").strip()
    return "+=" in src and not src.startswith("//")


def _location_of(node: ASTNode, file_path: str) -> SourceLocation:
    start = max(node.start_line, 1)
    end = max(node.end_line, start)
    return SourceLocation(
        file_path=file_path,
        start_line=start,
        end_line=end,
        start_column=node.start_column,
        end_column=max(node.end_column, node.start_column),
        symbol_name=node.name,
    )
