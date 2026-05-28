"""Security agent: detects common application-security vulnerabilities.

This agent emits Issues for three v1 patterns:

- Unsanitized taint flows from PipelineResult.taint_flows -> SQL_INJECTION,
  XSS_VULNERABILITY, COMMAND_INJECTION, or CODE_INJECTION depending on the
  taint sink's vulnerability category.
- Hardcoded secrets: assignments to identifiers like password / api_key /
  secret / token bound to a string literal -> SENSITIVE_DATA_EXPOSURE.
- Weak cryptography: calls to broken algorithms (MD5, SHA1, DES, RC4)
  -> CRYPTO_MISUSE.
"""

import re
from typing import List, Optional, Set
from uuid import uuid4

from src.agents.base_agent import AgentCapabilities, AgentContext, BaseAgent
from src.analysis.taint import TaintFlow
from src.models.code_entity import CodeEntity
from src.models.issue import Issue, IssueType, Severity
from src.models.source_location import SourceLocation
from src.parsing.ast_nodes import ASTNode, NodeType

_VULN_TO_ISSUE_TYPE = {
    "sql_injection": IssueType.SQL_INJECTION,
    "xss": IssueType.XSS_VULNERABILITY,
    "command_injection": IssueType.COMMAND_INJECTION,
    "code_injection": IssueType.CODE_INJECTION,
}

# Identifiers whose value being a string literal almost always indicates
# a secret has been hardcoded. Case-insensitive substring match.
_SECRET_NAME_HINTS = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "private_key",
    "access_key",
)

# Cryptographic primitives considered broken or weak for the modern web.
_WEAK_CRYPTO_PATTERNS = (
    re.compile(r"\bmd5\b", re.IGNORECASE),
    re.compile(r"\bsha1\b", re.IGNORECASE),
    re.compile(r"\bdes\b(?!c)", re.IGNORECASE),  # DES, not "describe"
    re.compile(r"\brc4\b", re.IGNORECASE),
)


class SecurityAgent(BaseAgent):
    """Detects security vulnerabilities via taint flows and AST patterns."""

    AGENT_ID = "security_agent"

    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_id=self.AGENT_ID,
            name="Security Agent",
            description="Taint-based and pattern-based detection of security vulnerabilities.",
            issue_types={
                IssueType.SQL_INJECTION,
                IssueType.XSS_VULNERABILITY,
                IssueType.COMMAND_INJECTION,
                IssueType.CODE_INJECTION,
                IssueType.SENSITIVE_DATA_EXPOSURE,
                IssueType.CRYPTO_MISUSE,
            },
            supported_languages={"python", "javascript", "typescript", "java"},
        )

    def _analyze(self, context: AgentContext) -> List[Issue]:
        issues: List[Issue] = []
        target_entities = self._target_entity_set(context)
        target_files = self._target_file_set(context, target_entities)

        for flow in context.pipeline_result.taint_flows:
            if target_entities is not None and flow.entity_id not in target_entities:
                continue
            issue = self._taint_flow_issue(flow, context)
            if issue is not None:
                issues.append(issue)

        for file_path, root in context.pipeline_result.file_asts.items():
            if target_files is not None and file_path not in target_files:
                continue
            issues.extend(self._scan_ast(root, file_path))

        return issues

    def _target_entity_set(self, context: AgentContext) -> Optional[Set[str]]:
        if context.target_entity_ids is None:
            return None
        return set(context.target_entity_ids)

    def _target_file_set(
        self,
        context: AgentContext,
        target_entities: Optional[Set[str]],
    ) -> Optional[Set[str]]:
        if target_entities is None:
            return None
        entities = context.pipeline_result.graph.entities
        return {entities[eid].location.file_path for eid in target_entities if eid in entities}

    def _taint_flow_issue(self, flow: TaintFlow, context: AgentContext) -> Optional[Issue]:
        if flow.sanitized:
            return None

        issue_type = _VULN_TO_ISSUE_TYPE.get(flow.sink.vulnerability)
        if issue_type is None:
            return None

        entity = self._lookup_entity(flow.entity_id, context)
        location = self._location_from_entity(entity)
        if location is None:
            return None

        return Issue(
            id=f"sec_taint_{uuid4().hex[:8]}",
            type=issue_type,
            severity=Severity.HIGH,
            location=location,
            title=f"Unsanitized {flow.sink.vulnerability.replace('_', ' ')} flow",
            description=(
                f"Tainted data from {flow.source.name} ({flow.source.category}) reaches "
                f"{flow.sink.name} without passing through a sanitizer."
            ),
            explanation=(
                "User-controlled input flowing into a dangerous sink can be exploited "
                "to alter the meaning of the operation the sink performs."
            ),
            recommendation=(
                "Validate and sanitize the input before it reaches the sink, or use a "
                "parameterized API (e.g., prepared statements, safe templating)."
            ),
            confidence=0.7,
            agent_id=self.AGENT_ID,
            metadata={
                "source": flow.source.name,
                "sink": flow.sink.name,
                "vulnerability": flow.sink.vulnerability,
            },
        )

    def _lookup_entity(
        self,
        entity_id: Optional[str],
        context: AgentContext,
    ) -> Optional[CodeEntity]:
        if entity_id is None:
            return None
        return context.pipeline_result.graph.entities.get(entity_id)

    def _location_from_entity(self, entity: Optional[CodeEntity]) -> Optional[SourceLocation]:
        if entity is None:
            return None
        loc = entity.location
        return SourceLocation(
            file_path=loc.file_path,
            start_line=loc.start_line,
            end_line=loc.end_line,
            start_column=loc.start_column,
            end_column=loc.end_column,
            symbol_name=entity.name,
        )

    def _scan_ast(self, node: ASTNode, file_path: str) -> List[Issue]:
        """Walk an AST emitting Issues for hardcoded secrets and weak crypto."""
        issues: List[Issue] = []

        if node.node_type == NodeType.ASSIGNMENT and _is_hardcoded_secret(node):
            issues.append(self._secret_issue(node, file_path))

        if node.node_type == NodeType.CALL and _is_weak_crypto_call(node):
            issues.append(self._weak_crypto_issue(node, file_path))

        for child in node.children:
            issues.extend(self._scan_ast(child, file_path))

        return issues

    def _secret_issue(self, node: ASTNode, file_path: str) -> Issue:
        identifier = node.name or "<unknown>"
        return Issue(
            id=f"sec_secret_{uuid4().hex[:8]}",
            type=IssueType.SENSITIVE_DATA_EXPOSURE,
            severity=Severity.HIGH,
            location=_location_of(node, file_path),
            title=f"Hardcoded secret in '{identifier}'",
            description=(
                f"Identifier '{identifier}' is assigned a string literal — likely a "
                "credential committed to the codebase."
            ),
            explanation=(
                "Secrets in source control leak into backups, logs, and forks; rotation "
                "becomes painful and breach blast-radius grows."
            ),
            recommendation=(
                "Load the value from an environment variable, a secrets manager "
                "(Vault, AWS Secrets Manager), or a non-committed config file."
            ),
            confidence=0.6,
            agent_id=self.AGENT_ID,
        )

    def _weak_crypto_issue(self, node: ASTNode, file_path: str) -> Issue:
        call_name = node.name or "<unknown>"
        return Issue(
            id=f"sec_weak_crypto_{uuid4().hex[:8]}",
            type=IssueType.CRYPTO_MISUSE,
            severity=Severity.MEDIUM,
            location=_location_of(node, file_path),
            title=f"Weak cryptographic primitive: '{call_name}'",
            description=f"Call to '{call_name}' uses a primitive considered broken or weak.",
            explanation=(
                "MD5/SHA1 are vulnerable to collisions; DES/RC4 are deprecated. "
                "Using them for authentication, integrity, or confidentiality is unsafe."
            ),
            recommendation=(
                "Use SHA-256 (or stronger) for hashing, bcrypt/argon2 for password "
                "hashing, and AES-GCM or ChaCha20-Poly1305 for symmetric encryption."
            ),
            confidence=0.65,
            agent_id=self.AGENT_ID,
        )


def _is_hardcoded_secret(assignment_node: ASTNode) -> bool:
    """True if assignment's name looks secret and RHS is a string literal."""
    name = (assignment_node.name or "").lower()
    if not any(hint in name for hint in _SECRET_NAME_HINTS):
        return False

    # The value is the first non-identifier child, or per parser convention,
    # we accept any LITERAL descendant. Empty literals are still flagged.
    for child in assignment_node.children:
        if child.node_type == NodeType.LITERAL:
            return _looks_like_string_literal(child)
    return False


def _looks_like_string_literal(literal: ASTNode) -> bool:
    """Treat quoted-string source text as a string literal."""
    text = (literal.source_text or "").strip()
    if not text:
        return False
    return text.startswith(('"', "'")) or text.startswith(("'''", '"""'))


def _is_weak_crypto_call(call_node: ASTNode) -> bool:
    """True if the call name or source matches a known-weak primitive."""
    haystacks = [call_node.name or "", call_node.source_text or ""]
    for pattern in _WEAK_CRYPTO_PATTERNS:
        if any(pattern.search(h) for h in haystacks):
            return True
    return False


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
