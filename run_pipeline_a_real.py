"""
run_pipeline_a_real.py  —  Run Pipeline A (LLM-enhanced) on all 10 reports
===========================================================================
Usage:
    python run_pipeline_a_real.py

Requires:
    OPENAI_API_KEY set in secrets/.env or environment.
    No JSL license needed for this mode.

Hard-fails if API key is missing or API call fails.
"""

import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "common"))
sys.path.insert(0, str(_ROOT / "src" / "pipeline_a_classical"))

# Load credentials first — will raise if key missing
from config import OPENAI_API_KEY  # noqa
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set. Check secrets/.env")
    sys.exit(1)

from pipeline_a_llm import run_pipeline_a_llm, _get_client  # noqa

# Paths
INPUT_DIR = _ROOT / "data" / "raw"
OUTPUT_DIR = _ROOT / "outputs" / "pipeline_a"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    client = _get_client()
    report_files = sorted(INPUT_DIR.glob("report_*.txt"))

    if not report_files:
        print(f"ERROR: No report files found in {INPUT_DIR}")
        sys.exit(1)

    print(f"\nPipeline A (LLM-Enhanced Clinical NLP)")
    print(f"Model: {__import__('config').LLM_MODEL}")
    print(f"Reports: {len(report_files)}")
    print("=" * 60)

    total_cost = 0.0
    total_time = 0.0
    total_fields = 0
    results_summary = []

    for report_file in report_files:
        rid = report_file.stem
        text = report_file.read_text(encoding="utf-8")

        t0 = time.time()
        try:
            output = run_pipeline_a_llm(rid, text, client=client)
        except RuntimeError as e:
            print(f"  [FATAL] {rid}: {e}")
            sys.exit(1)
        elapsed = time.time() - t0

        out_path = OUTPUT_DIR / (rid + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        mv = output.get("model_versions", {})
        cost = mv.get("cost_usd", 0.0)
        populated = sum(
            1 for v in output["fields"].values()
            if v.get("value") or v.get("state") == "present"
        )
        coded = sum(1 for v in output["fields"].values() if v.get("codes"))

        total_cost += cost
        total_time += elapsed
        total_fields += populated
        results_summary.append({
            "report_id": rid,
            "fields_populated": populated,
            "fields_coded": coded,
            "tokens_in": mv.get("tokens_in", 0),
            "tokens_out": mv.get("tokens_out", 0),
            "cost_usd": cost,
            "elapsed_sec": elapsed,
        })

        print(f"  {rid}: {populated}/21 fields populated, {coded} with codes | "
              f"${cost:.4f} | {elapsed:.1f}s")

    n = len(report_files)
    print("\n" + "=" * 60)
    print(f"PIPELINE A SUMMARY")
    print(f"  Reports processed:      {n}")
    print(f"  Mean fields populated:  {total_fields / n:.1f}/21")
    print(f"  Total cost:             ${total_cost:.4f}")
    print(f"  Mean cost per report:   ${total_cost / n:.4f}")
    print(f"  Mean runtime per report:{total_time / n:.2f}s")
    print(f"  Outputs written to:     {OUTPUT_DIR}")

    # Save summary
    summary_path = OUTPUT_DIR / "_run_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "pipeline": "Pipeline A (LLM-Enhanced Clinical NLP)",
            "model": __import__("config").LLM_MODEL,
            "n_reports": n,
            "total_cost_usd": total_cost,
            "mean_cost_per_report_usd": total_cost / n,
            "mean_runtime_sec": total_time / n,
            "mean_fields_populated": total_fields / n,
            "per_report": results_summary,
        }, f, indent=2)

if __name__ == "__main__":
    main()
