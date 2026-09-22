"""
run.py  —  Pipeline B entry point
===================================
Reads all reports from data/raw/, runs Pipeline B (LLM + Retrieval),
and writes JSON outputs to outputs/pipeline_b/.

Usage:
    python src/pipeline_b_llm_retrieval/run.py
    python src/pipeline_b_llm_retrieval/run.py --input data/raw/ --output outputs/pipeline_b/
    python src/pipeline_b_llm_retrieval/run.py --report-id report_001
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))
sys.path.insert(0, str(_HERE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pipeline_b")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Pipeline B — LLM + Local Terminology Retrieval."
    )
    parser.add_argument(
        "--input",
        default=str(_PROJECT_ROOT / "data" / "raw"),
        help="Directory containing raw report .txt files",
    )
    parser.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "outputs" / "pipeline_b"),
        help="Directory to write JSON outputs",
    )
    parser.add_argument(
        "--report-id",
        default=None,
        help="Process only this report ID (e.g. report_001). Default: all.",
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Force rebuild the FAISS terminology index before running.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Optionally rebuild FAISS index
    # -----------------------------------------------------------------------
    if args.build_index:
        logger.info("Rebuilding terminology FAISS index...")
        from terminology_index import TerminologyIndex  # noqa
        TerminologyIndex().build()

    # -----------------------------------------------------------------------
    # Collect report files
    # -----------------------------------------------------------------------
    if args.report_id:
        report_files = [input_dir / f"{args.report_id}.txt"]
    else:
        report_files = sorted(input_dir.glob("report_*.txt"))

    if not report_files:
        logger.error("No report files found in %s", input_dir)
        sys.exit(1)

    logger.info("Found %d report(s) to process.", len(report_files))

    # -----------------------------------------------------------------------
    # Warm up pipeline components (one-time cost)
    # -----------------------------------------------------------------------
    from pipeline import build_pipeline_b_components, run_pipeline_b  # noqa

    logger.info("Initialising Pipeline B components...")
    extractor, grounding_engine = build_pipeline_b_components()

    # -----------------------------------------------------------------------
    # Process reports
    # -----------------------------------------------------------------------
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
            output = run_pipeline_b(
                report_id=report_id,
                report_text=report_text,
                extractor=extractor,
                grounding_engine=grounding_engine,
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
        coded = sum(
            1 for v in output["fields"].values() if v.get("codes")
        )
        logger.info(
            "  ✓ %s — %d/21 fields populated | %d fields with codes → %s",
            report_id, non_empty, coded, out_path.name,
        )
        results_summary.append((report_id, non_empty, coded))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    logger.info("\n=== Pipeline B Summary ===")
    if results_summary:
        avg_fields = sum(c for _, c, _ in results_summary) / len(results_summary)
        avg_coded = sum(c for _, _, c in results_summary) / len(results_summary)
        logger.info(
            "Processed %d reports | avg %.1f/21 fields populated | avg %.1f fields with grounded codes",
            len(results_summary), avg_fields, avg_coded,
        )
    logger.info("Outputs written to: %s", output_dir)


if __name__ == "__main__":
    main()
