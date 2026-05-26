"""Analysis pipeline orchestrating parse -> graph -> metrics -> features -> analysis."""

import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.config.parser_config import ParserConfig
from src.parsing.base_parser import BaseParser
from src.parsing.ast_nodes import ASTNode, NodeType
from src.graph.graph_builder import GraphBuilder
from src.graph.knowledge_graph import KnowledgeGraph
from src.metrics.metrics_calculator import MetricsCalculator
from src.metrics.entity_metrics import EntityMetrics
from src.metrics.structural_metrics import StructuralMetrics
from src.features.feature_extractor import FeatureExtractor
from src.features.feature_vector import FeatureVector
from src.analysis.cfg_builder import CFGBuilder
from src.analysis.cfg import ControlFlowGraph
from src.analysis.taint import TaintAnalyzer, TaintFlow
from src.pipeline.cache import CacheBackend
from src.pipeline.storage import StorageBackend
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of running the analysis pipeline.

    Attributes:
        graph: The constructed knowledge graph.
        entity_metrics: Per-entity AST-based metrics.
        structural_metrics: Per-entity graph-based metrics.
        feature_vectors: Per-entity 128-dim feature vectors.
        cfgs: Per-function control flow graphs.
        taint_flows: Detected taint flows (potential vulnerabilities).
        file_asts: Per-file root AST nodes, keyed by file path.
        processing_time_seconds: Total pipeline execution time.
        files_processed: Number of files processed.
        entities_found: Total number of entities extracted.
    """

    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    entity_metrics: Dict[str, EntityMetrics] = field(default_factory=dict)
    structural_metrics: Dict[str, StructuralMetrics] = field(default_factory=dict)
    feature_vectors: Dict[str, FeatureVector] = field(default_factory=dict)
    cfgs: Dict[str, ControlFlowGraph] = field(default_factory=dict)
    taint_flows: List[TaintFlow] = field(default_factory=list)
    file_asts: Dict[str, ASTNode] = field(default_factory=dict)
    processing_time_seconds: float = 0.0
    files_processed: int = 0
    entities_found: int = 0


class AnalysisPipeline:
    """Orchestrates the full analysis pipeline.

    parse -> graph -> metrics -> features -> CFG -> taint analysis
    """

    def __init__(
        self,
        cache: Optional[CacheBackend] = None,
        storage: Optional[StorageBackend] = None,
    ) -> None:
        self._parser_config = ParserConfig()
        self._graph_builder = GraphBuilder()
        self._metrics_calc = MetricsCalculator()
        self._feature_extractor = FeatureExtractor()
        self._cfg_builder = CFGBuilder()
        self._taint_analyzer = TaintAnalyzer()
        self._cache = cache
        self._storage = storage
        self._ast_map: Dict[str, ASTNode] = {}

    def analyze_file(self, file_path: str) -> PipelineResult:
        """Analyze a single file."""
        return self.analyze_files([file_path])

    def analyze_directory(self, dir_path: str) -> PipelineResult:
        """Analyze all supported files in a directory."""
        files = self._discover_files(dir_path)
        return self.analyze_files(files)

    def analyze_files(self, file_paths: List[str]) -> PipelineResult:
        """Analyze a list of files through the full pipeline."""
        start = time.time()
        result = PipelineResult()

        # Step 1: Parse all files
        for fp in file_paths:
            parser = self._select_parser(fp)
            if parser is None:
                continue
            ast = parser.parse_file(fp)
            if ast is not None:
                self._ast_map[fp] = ast
                self._graph_builder.add_file(ast, fp)
                result.files_processed += 1

        # Step 2: Resolve cross-file references
        self._graph_builder.resolve_cross_file_references()
        result.graph = self._graph_builder.build()
        result.entities_found = result.graph.entity_count
        result.file_asts = dict(self._ast_map)

        # Step 3: Compute metrics
        metrics_result = self._metrics_calc.compute_all(result.graph, self._ast_map)
        result.entity_metrics = metrics_result.entity_metrics
        result.structural_metrics = metrics_result.structural_metrics

        # Step 4: Generate feature vectors
        result.feature_vectors = self._feature_extractor.extract_all(metrics_result)

        # Step 5: Build CFGs and run taint analysis
        for entity in result.graph.entities.values():
            if entity.is_function_like():
                ast_node = self._find_ast_node(
                    entity.location.file_path,
                    entity.location.start_line,
                )
                if ast_node is not None:
                    cfg = self._cfg_builder.build(ast_node)
                    result.cfgs[entity.id] = cfg
                    flows = self._taint_analyzer.analyze(cfg)
                    result.taint_flows.extend(flows)

        result.processing_time_seconds = time.time() - start

        # Cache/store if backends provided
        if self._storage is not None:
            self._storage.save_result(result, "latest")

        return result

    def update_file(
        self,
        file_path: str,
        previous_result: PipelineResult,
    ) -> PipelineResult:
        """Incrementally update analysis for a changed file."""
        start = time.time()

        # Re-parse the changed file
        parser = self._select_parser(file_path)
        if parser is None:
            return previous_result

        ast = parser.parse_file(file_path)
        if ast is None:
            return previous_result

        # Update graph
        self._ast_map[file_path] = ast
        self._graph_builder = GraphBuilder(graph=previous_result.graph)
        self._graph_builder.update_file(ast, file_path)
        self._graph_builder.resolve_cross_file_references()

        # Recompute metrics
        metrics_result = self._metrics_calc.compute_all(
            previous_result.graph, self._ast_map
        )
        previous_result.entity_metrics = metrics_result.entity_metrics
        previous_result.structural_metrics = metrics_result.structural_metrics

        # Recompute feature vectors
        previous_result.feature_vectors = self._feature_extractor.extract_all(
            metrics_result
        )
        previous_result.entities_found = previous_result.graph.entity_count
        previous_result.file_asts = dict(self._ast_map)
        previous_result.processing_time_seconds = time.time() - start

        return previous_result

    def _select_parser(self, file_path: str) -> Optional[BaseParser]:
        """Select the appropriate parser for a file."""
        if self._parser_config.should_skip_file(file_path):
            return None

        lang = self._parser_config.get_language_for_file(file_path)
        return _get_parser(lang)

    def _discover_files(self, dir_path: str) -> List[str]:
        """Discover all supported source files in a directory."""
        files: List[str] = []
        for root, _, filenames in os.walk(dir_path):
            for fname in filenames:
                full_path = os.path.join(root, fname)
                if self._parser_config.should_skip_file(full_path):
                    continue
                lang = self._parser_config.get_language_for_file(full_path)
                if lang != "unknown":
                    files.append(full_path)
        return files

    def _find_ast_node(self, file_path: str, start_line: int) -> Optional[ASTNode]:
        """Find an AST node by file path and start line."""
        root = self._ast_map.get(file_path)
        if root is None:
            return None
        return self._search_by_line(root, start_line)

    def _search_by_line(self, node: ASTNode, target_line: int) -> Optional[ASTNode]:
        """Search for a function/method node at the given start line."""
        func_types = {
            NodeType.FUNCTION,
            NodeType.METHOD,
            NodeType.CONSTRUCTOR,
        }
        if node.node_type in func_types and node.start_line == target_line:
            return node
        for child in node.children:
            result = self._search_by_line(child, target_line)
            if result is not None:
                return result
        return None


def _get_parser(language: str) -> Optional[BaseParser]:
    """Get a parser instance for the given language."""
    try:
        if language == "python":
            from src.parsing.python_parser import PythonParser

            return PythonParser()
        elif language == "javascript":
            from src.parsing.javascript_parser import JavaScriptParser

            return JavaScriptParser()
        elif language == "typescript":
            from src.parsing.javascript_parser import TypeScriptParser

            return TypeScriptParser()
        elif language == "java":
            from src.parsing.java_parser import JavaParser

            return JavaParser()
    except ImportError:
        logger.warning(f"Parser for {language} not available")
    return None
