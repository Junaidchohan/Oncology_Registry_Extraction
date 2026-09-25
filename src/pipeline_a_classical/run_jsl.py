"""
run_jsl.py  --  Entry point for Pipeline A (JSL real models)
=============================================================
Usage:
    # Single report
    python src/pipeline_a_classical/run_jsl.py --report-id report_001

    # All 10 reports
    python src/pipeline_a_classical/run_jsl.py

Reads  : data/raw/report_NNN.txt
Writes : outputs/pipeline_a/report_NNN.json
         outputs/pipeline_a/_run_summary.json

Environment (set before running):
    $env:JAVA_HOME   = "C:\Program Files\Eclipse Adoptium\jdk-11.0.32.101-hotspot"
    $env:HADOOP_HOME = "C:\hadoop"
    (or run: .\setup_jsl_env.ps1)
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

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("pipeline_a_jsl")

HC_SECRET = "5.4.0-0e2bf7e015ecf5ffc656c250cd1a03605ade4312"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Pipeline A with real JSL Healthcare NLP annotators."
    )
    parser.add_argument(
        "--input",
        default=str(_PROJECT_ROOT / "data" / "raw"),
        help="Directory with raw report .txt files",
    )
    parser.add_argument(
        "--output",
        default=str(_PROJECT_ROOT / "outputs" / "pipeline_a"),
        help="Directory to write JSON outputs",
    )
    parser.add_argument(
        "--report-id",
        default=None,
        help="Process only this report (e.g. report_001). Default: all reports.",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        default=False,
        help="Use GPU-optimised Spark session.",
    )
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    from pipeline_jsl import start_spark, load_pipeline, run_report, run_all  # noqa

    if args.report_id:
        # Single report mode
        spark = start_spark(secret=HC_SECRET, gpu=args.gpu)
        lp    = load_pipeline(spark)

        rf = input_dir / f"{args.report_id}.txt"
        if not rf.exists():
            logger.error("File not found: %s", rf)
            sys.exit(1)

        logger.info("Processing single report: %s", args.report_id)
        text = rf.read_text(encoding="utf-8")
        output, elapsed = run_report(args.report_id, text, lp)

        # Print entity table
        from stages.preprocessing import preprocess  # noqa
        from pipeline_jsl import annotate  # noqa
        preprocessed = preprocess(text)
        ann = annotate(lp, preprocessed["full_text"])
        print("\n=== EXTRACTED ENTITIES ===")
        print(f"{'Text':<40} {'Label':<30} {'Assertion':<15} {'Codes'}")
        print("-" * 100)
        for c in ann["chunks"]:
            codes_str = str(c.get("codes", {}))
            print(f"{c['text'][:39]:<40} {c['label']:<30} {c.get('assertion_state', 'present'):<15} {codes_str}")

        print("\n=== FINAL JSON ===")
        print(json.dumps(output, indent=2))

        out_path = output_dir / f"{args.report_id}.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False)

        n_pop = sum(1 for v in output["fields"].values() if v.get("value") is not None)
        print(f"\n[RESULT] {args.report_id}: {n_pop}/21 fields populated | {elapsed:.1f}s")

    else:
        # All reports
        run_all(
            data_dir=input_dir,
            output_dir=output_dir,
            secret=HC_SECRET,
            gpu=args.gpu,
        )


if __name__ == "__main__":
    main()
