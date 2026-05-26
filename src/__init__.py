"""Mavr.

A research-level multi-agent system that autonomously analyzes codebases,
detects quality issues, and proposes semantically-preserving refactorings
using Graph Neural Networks, Large Language Models, and Reinforcement Learning.
"""

__version__ = "0.1.0"
__author__ = "siamet"
__email__ = "siamet@protonmail.com"

# Package-level imports for convenience
from src.models.code_entity import CodeEntity
from src.models.issue import Issue
from src.models.refactoring import Refactoring
from src.models.source_location import SourceLocation

__all__ = [
    "CodeEntity",
    "Issue",
    "Refactoring",
    "SourceLocation",
]
