"""Tests for AnalysisPipeline."""

import pytest

from src.pipeline.pipeline import AnalysisPipeline, PipelineResult
from src.pipeline.storage import InMemoryStorage
from src.models.code_entity import EntityType


class TestAnalysisPipeline:
    def test_analyze_single_python_file(self, sample_python_file) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(sample_python_file))

        assert isinstance(result, PipelineResult)
        assert result.files_processed == 1
        assert result.entities_found > 0
        assert result.graph.entity_count > 0
        assert result.processing_time_seconds > 0

    def test_analyze_file_produces_graph(self, sample_python_file) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(sample_python_file))

        # Should have classes and functions
        classes = result.graph.get_entities_by_type(EntityType.CLASS)
        assert len(classes) >= 1
        assert any(c.name == "Calculator" for c in classes)

        # Should have relationships
        assert result.graph.relationship_count > 0

    def test_analyze_file_produces_metrics(self, sample_python_file) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(sample_python_file))

        # Should have entity metrics
        assert len(result.entity_metrics) > 0

        # Should have structural metrics
        assert len(result.structural_metrics) > 0

    def test_analyze_file_produces_feature_vectors(self, sample_python_file) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(sample_python_file))

        assert len(result.feature_vectors) > 0
        for fv in result.feature_vectors.values():
            assert fv.vector.shape == (128,)

    def test_analyze_file_produces_cfgs(self, sample_python_file) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(sample_python_file))

        # Should have CFGs for function-like entities
        assert len(result.cfgs) > 0

    def test_analyze_with_storage(self, sample_python_file) -> None:
        storage = InMemoryStorage()
        pipeline = AnalysisPipeline(storage=storage)
        result = pipeline.analyze_file(str(sample_python_file))

        assert storage.size == 1
        stored = storage.load_result("latest")
        assert stored is result

    def test_analyze_directory(self, fixtures_dir) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_directory(str(fixtures_dir))

        # Should process multiple files
        assert result.files_processed >= 1
        assert result.entities_found > 0

    def test_analyze_nonexistent_file(self) -> None:
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file("/nonexistent/path.py")
        assert result.files_processed == 0

    def test_analyze_unsupported_file(self, tmp_path) -> None:
        # Create a .txt file (unsupported)
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        pipeline = AnalysisPipeline()
        result = pipeline.analyze_file(str(txt_file))
        assert result.files_processed == 0


class TestPipelineIncremental:
    def test_update_file(self, sample_python_file, tmp_path) -> None:
        # Create a temp copy to modify
        import shutil

        temp_file = tmp_path / "sample.py"
        shutil.copy(sample_python_file, temp_file)

        pipeline = AnalysisPipeline()
        result1 = pipeline.analyze_file(str(temp_file))
        original_count = result1.entities_found

        # Modify the file (add a new function)
        with open(temp_file, "a") as f:
            f.write("\n\ndef new_function():\n    return 42\n")

        result2 = pipeline.update_file(str(temp_file), result1)
        assert result2.entities_found >= original_count
