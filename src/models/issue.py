"""Issue model for representing code quality issues and code smells."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from src.models.source_location import SourceLocation


class IssueType(str, Enum):
    """Types of code quality issues."""

    # Architectural smells
    GOD_CLASS = "god_class"
    FEATURE_ENVY = "feature_envy"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    SHOTGUN_SURGERY = "shotgun_surgery"
    PRIMITIVE_OBSESSION = "primitive_obsession"

    # Performance issues
    INEFFICIENT_ALGORITHM = "inefficient_algorithm"
    N_PLUS_ONE_QUERY = "n_plus_one_query"
    MEMORY_LEAK = "memory_leak"
    UNNECESSARY_COMPUTATION = "unnecessary_computation"

    # Security vulnerabilities
    SQL_INJECTION = "sql_injection"
    XSS_VULNERABILITY = "xss_vulnerability"
    COMMAND_INJECTION = "command_injection"
    CODE_INJECTION = "code_injection"
    AUTHENTICATION_ISSUE = "authentication_issue"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    CRYPTO_MISUSE = "crypto_misuse"

    # Maintainability issues
    LONG_METHOD = "long_method"
    COMPLEX_METHOD = "complex_method"
    POOR_NAMING = "poor_naming"
    MISSING_DOCUMENTATION = "missing_documentation"
    DUPLICATE_CODE = "duplicate_code"
    MAGIC_NUMBER = "magic_number"

    # General
    CODE_SMELL = "code_smell"
    BUG = "bug"
    ANTI_PATTERN = "anti_pattern"


class Severity(str, Enum):
    """Severity levels for issues."""

    CRITICAL = "critical"  # Must fix immediately
    HIGH = "high"  # Should fix soon
    MEDIUM = "medium"  # Should fix eventually
    LOW = "low"  # Nice to fix
    INFO = "info"  # Informational only


class Issue(BaseModel):
    """Represents a code quality issue or code smell.

    This model stores information about detected issues, including
    their location, severity, and recommended fixes.

    Attributes:
        id: Unique identifier
        type: Type of issue (from IssueType enum)
        severity: Severity level
        location: Source code location
        title: Short description of the issue
        description: Detailed explanation
        explanation: Why this is an issue
        recommendation: How to fix it
        confidence: Confidence score (0.0 to 1.0)
        agent_id: ID of agent that detected this
        entity_id: ID of affected code entity
        affected_entities: IDs of all affected entities
        metrics: Quantitative metrics related to the issue
        tags: Categorical tags for classification
        detected_at: Timestamp when detected
        metadata: Additional context
    """

    id: str = Field(..., description="Unique identifier")
    type: IssueType = Field(..., description="Issue type")
    severity: Severity = Field(..., description="Severity level")
    location: SourceLocation = Field(..., description="Source location")

    title: str = Field(..., description="Short issue description")
    description: str = Field(..., description="Detailed description")
    explanation: str = Field(..., description="Why this is an issue")
    recommendation: str = Field(..., description="How to fix")

    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Detection confidence (0-1)"
    )

    agent_id: str = Field(..., description="Agent that detected this")
    entity_id: Optional[str] = Field(
        default=None, description="Primary affected entity"
    )
    affected_entities: List[str] = Field(
        default_factory=list, description="All affected entity IDs"
    )

    metrics: Dict[str, float] = Field(
        default_factory=dict, description="Quantitative metrics"
    )
    tags: List[str] = Field(default_factory=list, description="Classification tags")

    detected_at: datetime = Field(
        default_factory=datetime.utcnow, description="Detection timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def is_critical(self) -> bool:
        """Check if this is a critical issue.

        Returns:
            True if severity is critical
        """
        return self.severity == Severity.CRITICAL

    def is_security_related(self) -> bool:
        """Check if this is a security issue.

        Returns:
            True if issue is security-related
        """
        security_types = {
            IssueType.SQL_INJECTION,
            IssueType.XSS_VULNERABILITY,
            IssueType.COMMAND_INJECTION,
            IssueType.CODE_INJECTION,
            IssueType.AUTHENTICATION_ISSUE,
            IssueType.SENSITIVE_DATA_EXPOSURE,
            IssueType.CRYPTO_MISUSE,
        }
        return self.type in security_types

    def add_affected_entity(self, entity_id: str) -> None:
        """Add an affected entity ID.

        Args:
            entity_id: ID of affected entity
        """
        if entity_id not in self.affected_entities:
            self.affected_entities.append(entity_id)

    def priority_score(self) -> float:
        """Calculate priority score for this issue.

        Returns:
            Priority score (0-10, higher = more important)
        """
        severity_scores = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 7.0,
            Severity.MEDIUM: 4.0,
            Severity.LOW: 2.0,
            Severity.INFO: 0.5,
        }

        base_score = severity_scores.get(self.severity, 1.0)

        # Adjust by confidence
        adjusted_score = base_score * self.confidence

        # Boost security issues
        if self.is_security_related():
            adjusted_score *= 1.5

        return min(adjusted_score, 10.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "location": self.location.to_string(),
            "title": self.title,
            "confidence": self.confidence,
            "agent_id": self.agent_id,
            "priority_score": self.priority_score(),
            "is_security": self.is_security_related(),
        }

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "id": "issue_98765",
                "type": "god_class",
                "severity": "high",
                "location": {
                    "file_path": "src/models/user.py",
                    "start_line": 10,
                    "end_line": 250,
                    "symbol_name": "UserManager",
                },
                "title": "God Class detected: UserManager",
                "description": "Class UserManager has too many responsibilities",
                "explanation": "This class handles authentication, authorization, profile management, and notifications",
                "recommendation": "Split into UserAuth, UserProfile, and UserNotifications classes",
                "confidence": 0.92,
                "agent_id": "architecture_agent",
                "entity_id": "entity_12340",
                "metrics": {
                    "num_methods": 45,
                    "num_responsibilities": 7,
                    "cohesion": 0.23,
                },
            }
        }
