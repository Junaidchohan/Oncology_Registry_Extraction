"""
src/pipeline_b_llm_retrieval/reapply_grounding.py
===================================================
Re-applies the fixed grounding logic to the existing Pipeline B extraction outputs.

Does NOT re-run LLM field extraction. Only re-processes the retrieval_log.jsonl
entries that were marked REJECTED_NOT_IN_CANDIDATE_SET, applying the fixed
extract_code_token() helper to see if the token was actually in the candidate set.

Steps
-----
1. Read outputs/pipeline_b/retrieval_log.jsonl
2. For each REJECTED line:
   a. Extract the pure code token from llm_selection.selected_code
   b. Collect the candidate code set from the log entry's candidates dict
   c. If the token is in the candidate set:
      - Update grounding_status to "ACCEPTED"
      - Write the code into the corresponding outputs/pipeline_b/report_XXX.json
3. Write the corrected retrieval log back (overwrite)
4. Print a summary

Usage
-----
    python src/pipeline_b_llm_retrieval/reapply_grounding.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("reapply_grounding")

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]

# Make grounding.py importable
sys.path.insert(0, str(_HERE))
from grounding import extract_code_token  # noqa

RETRIEVAL_LOG = _ROOT / "outputs" / "pipeline_b" / "retrieval_log.jsonl"
OUTPUT_DIR = _ROOT / "outputs" / "pipeline_b"


def _get_candidate_codes(entry: dict) -> dict[str, set[str]]:
    """Return {terminology: {code, ...}} from a log entry's candidates dict."""
    result: dict[str, set[str]] = {}
    for term, cands in entry.get("candidates", {}).items():
        result[term] = {c["code"] for c in cands}
    return result


def main() -> None:
    if not RETRIEVAL_LOG.exists():
        print(f"ERROR: retrieval log not found at {RETRIEVAL_LOG}")
        sys.exit(1)

    lines = RETRIEVAL_LOG.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(ln) for ln in lines if ln.strip()]

    n_total = len(entries)
    n_rejected = sum(1 for e in entries if e.get("grounding_status") == "REJECTED_NOT_IN_CANDIDATE_SET")
    n_newly_accepted = 0
    n_still_rejected = 0
    n_abstained = sum(1 for e in entries if e.get("grounding_status") == "ABSTAINED")
    n_already_accepted = sum(1 for e in entries if e.get("grounding_status") == "ACCEPTED")

    # Load all 10 report JSONs into memory (keyed by report_id)
    report_cache: dict[str, dict] = {}
    for report_file in OUTPUT_DIR.glob("report_*.json"):
        rid = report_file.stem
        report_cache[rid] = json.loads(report_file.read_text(encoding="utf-8"))

    # Process each REJECTED entry
    for entry in entries:
        if entry.get("grounding_status") != "REJECTED_NOT_IN_CANDIDATE_SET":
            continue

        report_id = entry["report_id"]
        field_name = entry["field_name"]
        raw_selection = entry.get("llm_selection", {}).get("selected_code", "")
        terminology_from_llm = entry.get("llm_selection", {}).get("terminology", "")

        code_token = extract_code_token(raw_selection)
        candidates_by_term = _get_candidate_codes(entry)

        # Find which terminology this token belongs to
        matched_term = None
        if code_token and code_token != "NONE":
            # First try the LLM-stated terminology
            if terminology_from_llm and code_token in candidates_by_term.get(terminology_from_llm, set()):
                matched_term = terminology_from_llm
            else:
                # Try all terminologies
                for term, codes in candidates_by_term.items():
                    if code_token in codes:
                        matched_term = term
                        break

        if matched_term:
            # Update the log entry
            entry["grounding_status"] = "ACCEPTED"
            entry["reapply_note"] = (
                f"Accepted after extract_code_token normalisation: "
                f"'{raw_selection}' → '{code_token}'"
            )
            n_newly_accepted += 1
            logger.info(
                "NOW ACCEPTED: %s/%s  raw='%s'  token='%s'  term=%s",
                report_id, field_name, raw_selection, code_token, matched_term,
            )

            # Patch the report JSON
            if report_id in report_cache:
                fields = report_cache[report_id].get("fields", {})
                if field_name in fields:
                    existing_codes = fields[field_name].get("codes", {}) or {}
                    existing_codes[matched_term] = code_token
                    fields[field_name]["codes"] = existing_codes
                    report_cache[report_id]["fields"] = fields
        else:
            n_still_rejected += 1
            if code_token and code_token != "NONE":
                logger.warning(
                    "STILL REJECTED: %s/%s  token='%s' not in any candidate set %s",
                    report_id, field_name, code_token,
                    {t: list(c) for t, c in candidates_by_term.items()},
                )

    # Write corrected report JSONs
    for rid, report_data in report_cache.items():
        out_path = OUTPUT_DIR / (rid + ".json")
        out_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # Write corrected retrieval log
    with open(RETRIEVAL_LOG, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("\n" + "=" * 60)
    print("GROUNDING REAPPLICATION SUMMARY")
    print("=" * 60)
    print(f"  Total log entries processed:  {n_total}")
    print(f"  Already accepted:             {n_already_accepted}")
    print(f"  Previously rejected:          {n_rejected}")
    print(f"    → Newly accepted (fixed):   {n_newly_accepted}")
    print(f"    → Still rejected:           {n_still_rejected}")
    print(f"  Abstained (unchanged):        {n_abstained}")
    print(f"  Retrieval log rewritten to:   {RETRIEVAL_LOG}")
    print(f"  Report JSONs updated:         {len(report_cache)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
