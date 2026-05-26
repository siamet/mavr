"""Feature vector representation for code entities."""

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

VECTOR_DIM = 128

SYNTACTIC_SLICE = slice(0, 32)
STRUCTURAL_SLICE = slice(32, 64)
SEMANTIC_SLICE = slice(64, 96)
HISTORICAL_SLICE = slice(96, 128)


@dataclass
class FeatureVector:
    """128-dimensional feature vector for a code entity.

    Layout:
        [0:32]   Syntactic features (from AST metrics)
        [32:64]  Structural features (from graph metrics)
        [64:96]  Semantic features (reserved for CodeBERT, zeroed)
        [96:128] Historical features (reserved for git, zeroed)
    """

    entity_id: str
    vector: np.ndarray  # shape (128,), dtype float32

    def __post_init__(self) -> None:
        if self.vector.shape != (VECTOR_DIM,):
            raise ValueError(f"Vector must have shape ({VECTOR_DIM},), got {self.vector.shape}")

    def syntactic_features(self) -> np.ndarray:
        """Return the syntactic feature slice."""
        return self.vector[SYNTACTIC_SLICE]

    def structural_features(self) -> np.ndarray:
        """Return the structural feature slice."""
        return self.vector[STRUCTURAL_SLICE]

    def semantic_features(self) -> np.ndarray:
        """Return the semantic feature slice (reserved)."""
        return self.vector[SEMANTIC_SLICE]

    def historical_features(self) -> np.ndarray:
        """Return the historical feature slice (reserved)."""
        return self.vector[HISTORICAL_SLICE]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entity_id": self.entity_id,
            "vector": self.vector.tolist(),
            "dim": VECTOR_DIM,
        }
