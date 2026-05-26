"""Basic taint analysis framework.

Tracks data flow from taint sources to taint sinks through a CFG,
checking for sanitizers along the path. Extensible with custom
source/sink/sanitizer definitions for Phase 2 Security Agent.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set
from src.analysis.cfg import ControlFlowGraph


@dataclass
class TaintSource:
    """A source of tainted (user-controlled) data.

    Attributes:
        name: Human-readable name.
        pattern: Regex pattern matching function/method names.
        category: Category (e.g., 'user_input', 'file_read', 'network').
    """

    name: str
    pattern: str
    category: str


@dataclass
class TaintSink:
    """A dangerous sink where tainted data should not flow unvalidated.

    Attributes:
        name: Human-readable name.
        pattern: Regex pattern matching function/method names.
        vulnerability: Type of vulnerability (e.g., 'sql_injection', 'xss').
    """

    name: str
    pattern: str
    vulnerability: str


@dataclass
class TaintSanitizer:
    """A function that sanitizes tainted data.

    Attributes:
        name: Human-readable name.
        pattern: Regex pattern matching function/method names.
        sanitizes: List of vulnerability types this sanitizer covers.
    """

    name: str
    pattern: str
    sanitizes: List[str] = field(default_factory=list)


@dataclass
class TaintFlow:
    """A detected flow of tainted data from source to sink.

    Attributes:
        source: The taint source.
        sink: The taint sink.
        path: List of block IDs from source to sink.
        sanitized: Whether a sanitizer was found along the path.
        entity_id: ID of the containing function entity (populated by pipeline).
    """

    source: TaintSource
    sink: TaintSink
    path: List[str] = field(default_factory=list)
    sanitized: bool = False
    entity_id: Optional[str] = None


# Default sources, sinks, and sanitizers for common patterns
DEFAULT_SOURCES = [
    TaintSource("user_input", r"input|raw_input|readline", "user_input"),
    TaintSource("http_param", r"request\.(get|post|params|args|form)", "network"),
    TaintSource("env_var", r"os\.environ|getenv", "environment"),
]

DEFAULT_SINKS = [
    TaintSink("sql_exec", r"execute|executemany|cursor\.execute", "sql_injection"),
    TaintSink(
        "os_command", r"os\.system|subprocess\.(run|call|Popen)", "command_injection"
    ),
    TaintSink("eval", r"eval|exec", "code_injection"),
    TaintSink("html_render", r"render|write.*html|innerHTML", "xss"),
]

DEFAULT_SANITIZERS = [
    TaintSanitizer(
        "parameterize", r"parameterize|quote|escape_string", ["sql_injection"]
    ),
    TaintSanitizer("html_escape", r"escape|html\.escape|bleach\.clean", ["xss"]),
    TaintSanitizer("shlex_quote", r"shlex\.quote|pipes\.quote", ["command_injection"]),
]


class TaintAnalyzer:
    """Basic forward taint analysis through a CFG.

    Identifies flows where tainted data (from sources) reaches
    dangerous sinks without passing through a sanitizer.
    """

    def __init__(
        self,
        sources: Optional[List[TaintSource]] = None,
        sinks: Optional[List[TaintSink]] = None,
        sanitizers: Optional[List[TaintSanitizer]] = None,
    ) -> None:
        self._sources = sources or list(DEFAULT_SOURCES)
        self._sinks = sinks or list(DEFAULT_SINKS)
        self._sanitizers = sanitizers or list(DEFAULT_SANITIZERS)

    def analyze(self, cfg: ControlFlowGraph) -> List[TaintFlow]:
        """Run taint analysis on a CFG.

        Args:
            cfg: Control flow graph of a function.

        Returns:
            List of detected taint flows (unsanitized = potential vulns).
        """
        flows: List[TaintFlow] = []

        # Find blocks containing sources and sinks
        source_blocks = self._find_source_blocks(cfg)
        sink_blocks = self._find_sink_blocks(cfg)

        if not source_blocks or not sink_blocks:
            return flows

        # For each source-sink pair, check if a path exists
        for source, s_block_id in source_blocks:
            for sink, t_block_id in sink_blocks:
                path = self._find_path(cfg, s_block_id, t_block_id)
                if path:
                    sanitized = self._is_sanitized(cfg, path, sink.vulnerability)
                    flows.append(
                        TaintFlow(
                            source=source,
                            sink=sink,
                            path=path,
                            sanitized=sanitized,
                        )
                    )

        return flows

    def _find_source_blocks(self, cfg: ControlFlowGraph) -> List[tuple]:
        """Find (source, block_id) pairs in the CFG."""
        results = []
        for block_id, block in cfg.blocks.items():
            for stmt in block.statements:
                text = stmt.source_text
                for source in self._sources:
                    if re.search(source.pattern, text):
                        results.append((source, block_id))
        return results

    def _find_sink_blocks(self, cfg: ControlFlowGraph) -> List[tuple]:
        """Find (sink, block_id) pairs in the CFG."""
        results = []
        for block_id, block in cfg.blocks.items():
            for stmt in block.statements:
                text = stmt.source_text
                for sink in self._sinks:
                    if re.search(sink.pattern, text):
                        results.append((sink, block_id))
        return results

    def _find_path(
        self,
        cfg: ControlFlowGraph,
        from_id: str,
        to_id: str,
    ) -> List[str]:
        """Find a path from source block to sink block (BFS)."""
        if from_id == to_id:
            return [from_id]

        visited: Set[str] = set()
        queue: List[List[str]] = [[from_id]]

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if current in visited:
                continue
            visited.add(current)

            for succ in cfg.get_successors(current):
                new_path = path + [succ.id]
                if succ.id == to_id:
                    return new_path
                queue.append(new_path)

        return []

    def _is_sanitized(
        self,
        cfg: ControlFlowGraph,
        path: List[str],
        vulnerability: str,
    ) -> bool:
        """Check if any block in the path contains a sanitizer."""
        for block_id in path:
            block = cfg.get_block(block_id)
            if block is None:
                continue
            for stmt in block.statements:
                text = stmt.source_text
                for sanitizer in self._sanitizers:
                    if vulnerability in sanitizer.sanitizes:
                        if re.search(sanitizer.pattern, text):
                            return True
        return False
