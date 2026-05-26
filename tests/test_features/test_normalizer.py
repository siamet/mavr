"""Tests for FeatureNormalizer."""

import pytest

from src.features.normalizer import FeatureNormalizer


class TestFeatureNormalizer:
    @pytest.fixture
    def norm(self) -> FeatureNormalizer:
        return FeatureNormalizer()

    def test_normalize_within_bounds(self, norm: FeatureNormalizer) -> None:
        # lines_of_code bounds = (0, 500)
        assert norm.normalize(250, "lines_of_code") == pytest.approx(0.5)

    def test_normalize_at_min(self, norm: FeatureNormalizer) -> None:
        assert norm.normalize(0, "lines_of_code") == 0.0

    def test_normalize_at_max(self, norm: FeatureNormalizer) -> None:
        assert norm.normalize(500, "lines_of_code") == 1.0

    def test_normalize_clamps_above(self, norm: FeatureNormalizer) -> None:
        assert norm.normalize(1000, "lines_of_code") == 1.0

    def test_normalize_clamps_below(self, norm: FeatureNormalizer) -> None:
        assert norm.normalize(-10, "lines_of_code") == 0.0

    def test_unknown_metric_uses_0_1(self, norm: FeatureNormalizer) -> None:
        assert norm.normalize(0.5, "unknown_metric") == 0.5

    def test_set_bounds(self, norm: FeatureNormalizer) -> None:
        norm.set_bounds("custom", 0, 100)
        assert norm.normalize(50, "custom") == pytest.approx(0.5)

    def test_zero_range_bounds(self, norm: FeatureNormalizer) -> None:
        norm.set_bounds("const", 5, 5)
        assert norm.normalize(5, "const") == 0.0

    def test_complexity_normalization(self, norm: FeatureNormalizer) -> None:
        # cyclomatic_complexity bounds = (1, 50)
        val = norm.normalize(25, "cyclomatic_complexity")
        assert 0.0 < val < 1.0
