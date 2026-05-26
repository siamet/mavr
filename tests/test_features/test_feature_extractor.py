"""Tests for FeatureExtractor."""

import numpy as np
import pytest

from src.features.feature_extractor import FeatureExtractor
from src.features.feature_vector import VECTOR_DIM, FeatureVector
from src.metrics.entity_metrics import EntityMetrics
from src.metrics.structural_metrics import StructuralMetrics
from src.metrics.metrics_calculator import MetricsResult


class TestFeatureExtractor:
    @pytest.fixture
    def extractor(self) -> FeatureExtractor:
        return FeatureExtractor()

    def test_vector_shape(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(entity_id="f1", lines_of_code=50)
        fv = extractor.extract("f1", em)
        assert fv.vector.shape == (VECTOR_DIM,)
        assert fv.vector.dtype == np.float32

    def test_syntactic_features_populated(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(
            entity_id="f1",
            lines_of_code=100,
            cyclomatic_complexity=5,
            parameter_count=3,
        )
        fv = extractor.extract("f1", em)
        syn = fv.syntactic_features()
        # LOC=100 with bounds (0,500) => 0.2
        assert syn[0] == pytest.approx(0.2)
        assert syn.sum() > 0

    def test_structural_features_populated(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(entity_id="c1")
        sm = StructuralMetrics(
            entity_id="c1",
            fan_in=10,
            fan_out=5,
            coupling_between_objects=15,
        )
        fv = extractor.extract("c1", em, sm)
        struc = fv.structural_features()
        assert struc.sum() > 0

    def test_semantic_features_zeroed(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(entity_id="f1", lines_of_code=100)
        fv = extractor.extract("f1", em)
        assert fv.semantic_features().sum() == 0.0

    def test_historical_features_zeroed(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(entity_id="f1", lines_of_code=100)
        fv = extractor.extract("f1", em)
        assert fv.historical_features().sum() == 0.0

    def test_all_values_in_0_1(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(
            entity_id="f1",
            lines_of_code=250,
            cyclomatic_complexity=10,
            nesting_depth_max=3,
            parameter_count=5,
            return_count=2,
            branch_count=8,
            loop_count=4,
            call_count=15,
        )
        sm = StructuralMetrics(
            entity_id="f1",
            fan_in=20,
            fan_out=10,
            lack_of_cohesion=0.5,
        )
        fv = extractor.extract("f1", em, sm)
        assert np.all(fv.vector >= 0.0)
        assert np.all(fv.vector <= 1.0)

    def test_extract_all(self, extractor: FeatureExtractor) -> None:
        mr = MetricsResult(
            entity_metrics={
                "f1": EntityMetrics(entity_id="f1", lines_of_code=50),
                "f2": EntityMetrics(entity_id="f2", lines_of_code=100),
            },
            structural_metrics={
                "f1": StructuralMetrics(entity_id="f1", fan_in=2),
            },
        )
        vectors = extractor.extract_all(mr)
        assert "f1" in vectors
        assert "f2" in vectors
        assert vectors["f1"].vector.shape == (VECTOR_DIM,)

    def test_to_dict(self, extractor: FeatureExtractor) -> None:
        em = EntityMetrics(entity_id="f1", lines_of_code=50)
        fv = extractor.extract("f1", em)
        d = fv.to_dict()
        assert d["entity_id"] == "f1"
        assert len(d["vector"]) == VECTOR_DIM
        assert d["dim"] == VECTOR_DIM


class TestFeatureVectorValidation:
    def test_wrong_shape_raises(self) -> None:
        with pytest.raises(ValueError):
            FeatureVector(
                entity_id="f1",
                vector=np.zeros(64, dtype=np.float32),
            )

    def test_correct_shape_ok(self) -> None:
        fv = FeatureVector(
            entity_id="f1",
            vector=np.zeros(VECTOR_DIM, dtype=np.float32),
        )
        assert fv.entity_id == "f1"
