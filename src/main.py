"""Main entry point for the multi-agent code review system."""

import argparse
import os
import sys
from src.utils.logger import setup_logging, get_logger
from src.config.settings import get_settings
from src.pipeline.pipeline import AnalysisPipeline, PipelineResult

logger = get_logger(__name__)


def analyze_path(path: str) -> None:
    """Analyze a file or directory through the full pipeline.

    Args:
        path: Path to a source file or directory.
    """
    logger.info(f"Analyzing: {path}")
    pipeline = AnalysisPipeline()

    if os.path.isdir(path):
        result = pipeline.analyze_directory(path)
    elif os.path.isfile(path):
        result = pipeline.analyze_file(path)
    else:
        print(f"Error: '{path}' is not a valid file or directory")
        return

    _print_results(result, path)


def _print_results(result: PipelineResult, path: str) -> None:
    """Print pipeline results to stdout."""
    print(f"\n=== Analysis Results for {path} ===")
    print(f"  Files processed:    {result.files_processed}")
    print(f"  Entities found:     {result.entities_found}")
    print(f"  Relationships:      {result.graph.relationship_count}")
    print(f"  Processing time:    {result.processing_time_seconds:.2f}s")

    # Entity breakdown
    from src.models.code_entity import EntityType

    for etype in EntityType:
        entities = result.graph.get_entities_by_type(etype)
        if entities:
            print(f"  {etype.value:15s}:   {len(entities)}")

    # Metrics summary
    if result.entity_metrics:
        complexities = [m.cyclomatic_complexity for m in result.entity_metrics.values()]
        avg_cc = sum(complexities) / len(complexities)
        max_cc = max(complexities)
        print(f"\n  Avg complexity:     {avg_cc:.1f}")
        print(f"  Max complexity:     {max_cc}")

    # Feature vectors
    print(f"  Feature vectors:    {len(result.feature_vectors)}")

    # CFGs
    print(f"  CFGs built:         {len(result.cfgs)}")

    # Taint flows
    if result.taint_flows:
        unsanitized = [f for f in result.taint_flows if not f.sanitized]
        print(f"\n  Taint flows found:  {len(result.taint_flows)}")
        print(f"  Unsanitized:        {len(unsanitized)}")
        for flow in unsanitized[:5]:
            print(f"    [{flow.sink.vulnerability}] {flow.source.name} -> {flow.sink.name}")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Multi-Agent AI System for Automated Code Review & Refactoring"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze code files")
    analyze_parser.add_argument("path", help="Path to file or directory to analyze")

    # Version command
    subparsers.add_parser("version", help="Show version information")

    args = parser.parse_args()

    # Setup logging
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    # Handle commands
    if args.command == "analyze":
        analyze_path(args.path)
        return 0

    elif args.command == "version":
        print("Multi-Agent Code Review System v0.2.0")
        print("Phase 1: Core Analysis Pipeline")
        return 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
