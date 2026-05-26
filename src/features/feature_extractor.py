"""Generates 128-dim feature vectors from computed metrics."""

from typing import Dict, Optional

import numpy as np
import numpy.typing as npt

from src.features.feature_vector import (
    VECTOR_DIM,
    SYNTACTIC_SLICE,
    STRUCTURAL_SLICE,
    FeatureVector,
)
from src.features.normalizer import FeatureNormalizer
from src.metrics.entity_metrics import EntityMetrics
from src.metrics.structural_metrics import StructuralMetrics
from src.metrics.metrics_calculator import MetricsResult


# Ordered list of syntactic metric fields to pack into the vector
_SYNTACTIC_FIELDS = [
    "lines_of_code",
    "logical_lines",
    "cyclomatic_complexity",
    "nesting_depth_max",
    "nesting_depth_avg",
    "parameter_count",
    "return_count",
    "branch_count",
    "loop_count",
    "comment_count",
    "call_count",
]

# Ordered list of structural metric fields
_STRUCTURAL_FIELDS = [
    "fan_in",
    "fan_out",
    "afferent_coupling",
    "efferent_coupling",
    "coupling_between_objects",
    "lack_of_cohesion",
    "depth_of_inheritance",
    "number_of_children",
    "instability",
    "abstractness",
]


class FeatureExtractor:
    """Generates 128-dim feature vectors from entity and structural metrics."""

    def __init__(self, normalizer: Optional[FeatureNormalizer] = None) -> None:
        self._normalizer = normalizer or FeatureNormalizer()

    def extract(
        self,
        entity_id: str,
        entity_metrics: EntityMetrics,
        structural_metrics: Optional[StructuralMetrics] = None,
    ) -> FeatureVector:
        """Generate a feature vector for one entity.

        Args:
            entity_id: The entity's ID.
            entity_metrics: AST-based metrics.
            structural_metrics: Graph-based metrics (optional).

        Returns:
            A 128-dimensional FeatureVector.
        """
        vec = np.zeros(VECTOR_DIM, dtype=np.float32)

        # Pack syntactic features into [0:32]
        syn = self._build_syntactic(entity_metrics)
        vec[SYNTACTIC_SLICE] = syn

        # Pack structural features into [32:64]
        if structural_metrics is not None:
            struc = self._build_structural(structural_metrics)
            vec[STRUCTURAL_SLICE] = struc

        # [64:96] semantic = zeroed (deferred)
        # [96:128] historical = zeroed (deferred)

        return FeatureVector(entity_id=entity_id, vector=vec)

    def extract_all(self, metrics_result: MetricsResult) -> Dict[str, FeatureVector]:
        """Generate feature vectors for all entities in a MetricsResult."""
        vectors: Dict[str, FeatureVector] = {}
        for eid, em in metrics_result.entity_metrics.items():
            sm = metrics_result.structural_metrics.get(eid)
            vectors[eid] = self.extract(eid, em, sm)
        return vectors

    def _build_syntactic(self, m: EntityMetrics) -> npt.NDArray[np.float32]:
        """Build normalized syntactic feature array (32 dims)."""
        arr: npt.NDArray[np.float32] = np.zeros(32, dtype=np.float32)
        for i, field_name in enumerate(_SYNTACTIC_FIELDS):
            if i >= 32:
                break
            raw = getattr(m, field_name, 0)
            arr[i] = self._normalizer.normalize(float(raw), field_name)
        return arr

    def _build_structural(self, m: StructuralMetrics) -> npt.NDArray[np.float32]:
        """Build normalized structural feature array (32 dims)."""
        arr: npt.NDArray[np.float32] = np.zeros(32, dtype=np.float32)
        for i, field_name in enumerate(_STRUCTURAL_FIELDS):
            if i >= 32:
                break
            raw = getattr(m, field_name, 0)
            arr[i] = self._normalizer.normalize(float(raw), field_name)
        return arr
