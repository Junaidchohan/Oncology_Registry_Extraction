"""
run.py  —  Pipeline A entry point
==================================
Reads all reports from data/raw/, runs Pipeline A, and writes JSON outputs
to outputs/pipeline_a/.

Usage:
    python src/pipeline_a_classical/run.py
    python src/pipeline_a_classical/run.py --input data/raw/ --output outputs/pipeline_a/
    python src/pipeline_a_classical/run.py --report-id report_001  # single report
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))
sys.path.insert(0, str(_HERE))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pipeline_a")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Pipeline A — Classical Healthcare NLP extraction."
    )
    parser.add_argument(
        "--input",
        default=str(_PROJECT_ROOT / "data" / "raw"),
        help="Directory containing raw report .txt files",
    )
    parser.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "outputs" / "pipeline_a"),
        help="Directory to write JSON outputs",
    )
    parser.add_argument(
        "--report-id",
        default=None,
        help="Process only this report ID (e.g. report_001). Default: all reports.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect report files
    if args.report_id:
        report_files = [input_dir / f"{args.report_id}.txt"]
    else:
        report_files = sorted(input_dir.glob("report_*.txt"))

    if not report_files:
        logger.error("No report files found in %s", input_dir)
        sys.exit(1)

    logger.info("Found %d report(s) to process.", len(report_files))

    # Initialise JSL pipelines (or None for heuristic mode)
    from pipeline import build_jsl_pipelines, run_pipeline_a  # noqa

    logger.info("Initialising JSL pipelines (may take a while on first run)...")
    spark, ner_pipeline, assertion_pipeline, resolver_pipelines = build_jsl_pipelines()

    mode = "licensed_jsl" if spark is not None else "heuristic_demo"
    logger.info("Running in mode: %s", mode)

    # Process each report
    results_summary = []
    for report_file in report_files:
        report_id = report_file.stem
        logger.info("Processing %s ...", report_id)

        try:
            report_text = report_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error("Report file not found: %s", report_file)
            continue

        try:
            output = run_pipeline_a(
                report_id=report_id,
                report_text=report_text,
                spark_session=spark,
                ner_pipeline=ner_pipeline,
                assertion_pipeline=assertion_pipeline,
                resolver_pipelines=resolver_pipelines,
            )
        except Exception as exc:
            logger.exception("Error processing %s: %s", report_id, exc)
            continue

        out_path = output_dir / f"{report_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        non_empty = sum(
            1 for v in output["fields"].values() if v.get("value") is not None
        )
        logger.info("  ✓ %s — %d/21 fields populated → %s", report_id, non_empty, out_path.name)
        results_summary.append((report_id, non_empty))

    logger.info("\n=== Pipeline A Summary ===")
    total = sum(c for _, c in results_summary)
    logger.info(
        "Processed %d reports | avg %.1f/21 fields populated",
        len(results_summary),
        total / len(results_summary) if results_summary else 0,
    )
    logger.info("Outputs written to: %s", output_dir)


if __name__ == "__main__":
    main()
