"""Architecture agent: detects architectural smells from metrics + graph.

This is a v1 metric-based implementation. The GNN approach described in
the roadmap is reserved for future work — feature vectors are already
computed by the pipeline and will plug in behind this same contract.

v1 rules:

- God Class -> classes that exceed any of: method count, LOC, or LCOM
  thresholds. Severity scales with how many thresholds are exceeded.
- Circular Dependency -> cycles in a subgraph restricted to dependency
  edges (CALLS / DEPENDS_ON / IMPORTS), filtering out structural edges
  like HAS_METHOD that don't represent real dependencies.
- Feature Envy -> methods whose outgoing calls hit other classes far
  more often than their own.
"""

from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import networkx as nx

from src.agents.base_agent import AgentCapabilities, AgentContext, BaseAgent
from src.graph.knowledge_graph import KnowledgeGraph
from src.graph.relationship import RelationshipType
from src.models.code_entity import CodeEntity
from src.models.issue import Issue, IssueType, Severity
from src.models.source_location import SourceLocation
from src.pipeline.pipeline import PipelineResult

# Default thresholds. Overridable via context.config["architecture"].
DEFAULT_GOD_CLASS_METHOD_COUNT = 20
DEFAULT_GOD_CLASS_LOC = 500
DEFAULT_GOD_CLASS_LCOM = 0.7

DEFAULT_FEATURE_ENVY_MIN_EXTERNAL_CALLS = 3
DEFAULT_FEATURE_ENVY_EXTERNAL_RATIO = 2.0  # external must be > internal * this

_DEPENDENCY_EDGES = {
    RelationshipType.CALLS,
    RelationshipType.DEPENDS_ON,
    RelationshipType.IMPORTS,
}


class ArchitectureAgent(BaseAgent):
    """Detects architectural smells using existing metrics and the knowledge graph."""

    AGENT_ID = "architecture_agent"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_id=self.AGENT_ID,
            name="Architecture Agent",
            description="Metric- and graph-based detection of architectural smells.",
            issue_types={
                IssueType.GOD_CLASS,
                IssueType.CIRCULAR_DEPENDENCY,
                IssueType.FEATURE_ENVY,
            },
            supported_languages={"python", "javascript", "typescript", "java"},
        )

    def _analyze(self, context: AgentContext) -> List[Issue]:
        result = context.pipeline_result
        targets = self._target_entities(context)
        config = context.config.get("architecture", {}) if context.config else {}

        issues: List[Issue] = []
        issues.extend(self._detect_god_classes(result, targets, config))
        issues.extend(self._detect_circular_dependencies(result, targets))
        issues.extend(self._detect_feature_envy(result, targets, config))
        return issues

    def _target_entities(self, context: AgentContext) -> Optional[Set[str]]:
        if context.target_entity_ids is None:
            return None
        return set(context.target_entity_ids)

    # ----- God Class -----

    def _detect_god_classes(
        self,
        result: PipelineResult,
        targets: Optional[Set[str]],
        config: Dict[str, Any],
    ) -> List[Issue]:
        max_methods = int(config.get("god_class_method_count", DEFAULT_GOD_CLASS_METHOD_COUNT))
        max_loc = int(config.get("god_class_loc", DEFAULT_GOD_CLASS_LOC))
        max_lcom = float(config.get("god_class_lcom", DEFAULT_GOD_CLASS_LCOM))

        issues: List[Issue] = []
        for entity in result.graph.entities.values():
            if not entity.is_class_like():
                continue
            if targets is not None and entity.id not in targets:
                continue

            method_count = len(result.graph.get_class_methods(entity.id))
            loc = result.entity_metrics.get(entity.id)
            loc_value = loc.lines_of_code if loc is not None else 0
            structural = result.structural_metrics.get(entity.id)
            lcom = structural.lack_of_cohesion if structural is not None else 0.0

            exceeded = [
                ("method_count", method_count, max_methods, method_count > max_methods),
                ("lines_of_code", loc_value, max_loc, loc_value > max_loc),
                ("lcom", lcom, max_lcom, lcom > max_lcom),
            ]
            triggered = [t for t in exceeded if t[3]]
            if not triggered:
                continue

            issues.append(self._god_class_issue(entity, method_count, loc_value, lcom, triggered))
        return issues

    def _god_class_issue(
        self,
        entity: CodeEntity,
        method_count: int,
        loc: int,
        lcom: float,
        triggered: List[tuple],
    ) -> Issue:
        severity = Severity.HIGH if len(triggered) >= 2 else Severity.MEDIUM
        reasons = ", ".join(f"{name}={value}" for name, value, _, _ in triggered)
        return Issue(
            id=f"arch_god_class_{uuid4().hex[:8]}",
            type=IssueType.GOD_CLASS,
            severity=severity,
            location=_location_of_entity(entity),
            title=f"God Class: {entity.name}",
            description=f"Class {entity.name} exceeds thresholds: {reasons}.",
            explanation=(
                "Classes that combine too many methods, lines, or weakly-related "
                "responsibilities become hard to understand, test, and modify safely."
            ),
            recommendation=(
                "Split the class along responsibility lines (Extract Class), "
                "moving related methods and fields into smaller cohesive units."
            ),
            confidence=0.7,
            agent_id=self.AGENT_ID,
            entity_id=entity.id,
            metrics={
                "method_count": float(method_count),
                "lines_of_code": float(loc),
                "lcom": float(lcom),
                "thresholds_exceeded": float(len(triggered)),
            },
        )

    # ----- Circular Dependency -----

    def _detect_circular_dependencies(
        self,
        result: PipelineResult,
        targets: Optional[Set[str]],
    ) -> List[Issue]:
        dep_graph = _dependency_subgraph(result.graph)
        if dep_graph.number_of_edges() == 0:
            return []

        issues: List[Issue] = []
        for cycle in nx.simple_cycles(dep_graph):
            if len(cycle) < 2:
                # Self-loop — usually a graph artifact, not a real cycle.
                continue
            if targets is not None and not any(eid in targets for eid in cycle):
                continue
            issue = self._cycle_issue(cycle, result.graph)
            if issue is not None:
                issues.append(issue)
        return issues

    def _cycle_issue(self, cycle: List[str], graph: KnowledgeGraph) -> Optional[Issue]:
        entities = [graph.get_entity(eid) for eid in cycle]
        first_known = next((e for e in entities if e is not None), None)
        if first_known is None:
            return None

        names = [(e.name if e is not None else "?") for e in entities]
        chain = " -> ".join(names + [names[0]])

        return Issue(
            id=f"arch_cycle_{uuid4().hex[:8]}",
            type=IssueType.CIRCULAR_DEPENDENCY,
            severity=Severity.HIGH,
            location=_location_of_entity(first_known),
            title=f"Circular dependency ({len(cycle)} entities)",
            description=f"Dependency cycle detected: {chain}.",
            explanation=(
                "Cycles in the dependency graph couple modules tightly, prevent "
                "independent testing, and make builds order-sensitive."
            ),
            recommendation=(
                "Break the cycle by introducing an interface, moving shared code "
                "to a lower-level module, or applying dependency inversion."
            ),
            confidence=0.85,
            agent_id=self.AGENT_ID,
            entity_id=first_known.id,
            affected_entities=cycle,
            metrics={"cycle_length": float(len(cycle))},
        )

    # ----- Feature Envy -----

    def _detect_feature_envy(
        self,
        result: PipelineResult,
        targets: Optional[Set[str]],
        config: Dict[str, Any],
    ) -> List[Issue]:
        min_external = int(
            config.get("feature_envy_min_external", DEFAULT_FEATURE_ENVY_MIN_EXTERNAL_CALLS)
        )
        ratio = float(config.get("feature_envy_ratio", DEFAULT_FEATURE_ENVY_EXTERNAL_RATIO))

        issues: List[Issue] = []
        for entity in result.graph.entities.values():
            if not entity.is_function_like():
                continue
            if entity.parent_id is None:
                continue  # Top-level functions can't envy a class they don't have.
            if targets is not None and entity.id not in targets:
                continue

            counts = self._count_envy(result.graph, entity)
            if counts is None:
                continue

            external, internal, top_class_id, top_class_count = counts
            if external < min_external:
                continue
            if external <= internal * ratio:
                continue

            issues.append(
                self._feature_envy_issue(
                    entity, external, internal, top_class_id, top_class_count, result.graph
                )
            )
        return issues

    def _count_envy(
        self,
        graph: KnowledgeGraph,
        method: CodeEntity,
    ) -> Optional[tuple]:
        """Return (external_calls, internal_calls, top_class_id, top_class_count)."""
        callees = graph.get_callees(method.id)
        if not callees:
            return None

        external = 0
        internal = 0
        per_class: Dict[str, int] = {}

        for callee in callees:
            owner = callee.parent_id
            if owner is None:
                continue
            if owner == method.parent_id:
                internal += 1
            else:
                external += 1
                per_class[owner] = per_class.get(owner, 0) + 1

        if external == 0:
            return None

        top_class_id, top_class_count = max(per_class.items(), key=lambda kv: kv[1])
        return external, internal, top_class_id, top_class_count

    def _feature_envy_issue(
        self,
        method: CodeEntity,
        external: int,
        internal: int,
        top_class_id: str,
        top_class_count: int,
        graph: KnowledgeGraph,
    ) -> Issue:
        envied = graph.get_entity(top_class_id)
        envied_name = envied.name if envied is not None else top_class_id
        return Issue(
            id=f"arch_feature_envy_{uuid4().hex[:8]}",
            type=IssueType.FEATURE_ENVY,
            severity=Severity.MEDIUM,
            location=_location_of_entity(method),
            title=f"Feature Envy: {method.name} prefers {envied_name}",
            description=(
                f"{method.name} makes {external} external calls vs {internal} "
                f"internal; most ({top_class_count}) target {envied_name}."
            ),
            explanation=(
                "Methods that mostly operate on another class's data probably "
                "belong on that class — moving them improves cohesion and locality."
            ),
            recommendation=(
                f"Consider Move Method: relocate {method.name} onto {envied_name} "
                "(or extract a helper that lives there)."
            ),
            confidence=0.55,
            agent_id=self.AGENT_ID,
            entity_id=method.id,
            affected_entities=[top_class_id],
            metrics={
                "external_calls": float(external),
                "internal_calls": float(internal),
                "top_target_calls": float(top_class_count),
            },
        )


def _dependency_subgraph(graph: KnowledgeGraph) -> nx.DiGraph:
    """Return a DiGraph containing only dependency-style edges.

    Structural edges (HAS_METHOD, HAS_FIELD, CONTAINS, etc.) would create
    spurious cycles between containers and their members. We exclude them.
    """
    nx_graph = graph.networkx_graph
    sub = nx.DiGraph()
    for src, tgt, data in nx_graph.edges(data=True):
        if data.get("type") in _DEPENDENCY_EDGES:
            sub.add_edge(src, tgt)
    return sub


def _location_of_entity(entity: CodeEntity) -> SourceLocation:
    loc = entity.location
    return SourceLocation(
        file_path=loc.file_path,
        start_line=loc.start_line,
        end_line=loc.end_line,
        start_column=loc.start_column,
        end_column=loc.end_column,
        symbol_name=entity.name,
    )
