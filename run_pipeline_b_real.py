"""
run_pipeline_b_real.py — Run Pipeline B (LLM + FAISS grounding) on all 10 reports
==================================================================================
Usage:
    $env:FORCE_TFIDF="1"   # if sentence-transformers is broken
    python run_pipeline_b_real.py

Two-stage LLM grounding:
  Stage 1: LLM extracts all 21 fields (value, state, evidence)
  Stage 2: For each codeable field, retrieve top-10 FAISS candidates,
           present them to the LLM, instruct it to select from the candidate
           list only, or abstain. Enforce in code: reject any code not in set.

Logs all retrieval queries and selections to:
    outputs/pipeline_b/retrieval_log.jsonl

Hard-fails if OPENAI_API_KEY is missing.
"""

import importlib.util
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "common"))

from config import OPENAI_API_KEY, LLM_MODEL  # noqa

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set. Cannot run Pipeline B. Check secrets/.env")
    sys.exit(1)

# Load pipeline_b modules via spec to avoid name collision with pipeline_a
def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_llm_mod = _load_module("llm_extractor_b", _ROOT / "src/pipeline_b_llm_retrieval/llm_extractor.py")
_grounding_mod = _load_module("grounding_b", _ROOT / "src/pipeline_b_llm_retrieval/grounding.py")
_term_mod = _load_module("terminology_index_b", _ROOT / "src/pipeline_b_llm_retrieval/terminology_index.py")
_schema_mod = _load_module("schema_b", _ROOT / "src/common/schema.py")

from openai import OpenAI  # noqa

INPUT_DIR = _ROOT / "data" / "raw"
OUTPUT_DIR = _ROOT / "outputs" / "pipeline_b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVAL_LOG = OUTPUT_DIR / "retrieval_log.jsonl"

# Fields that need code grounding
CODEABLE_FIELDS = {
    "primary_site", "histology_type", "tumor_grade", "clinical_stage",
    "pathologic_stage", "surgical_margins", "lymphovascular_invasion",
    "perineural_invasion", "distant_metastasis", "er_status", "pr_status",
    "her2_status", "kras_mutation", "egfr_mutation", "procedure_type", "prior_treatment",
}

FIELD_TERMINOLOGIES = {
    "primary_site": ["ICD-O-3", "SNOMED"],
    "histology_type": ["ICD-O-3", "ICD-10"],
    "tumor_grade": ["SNOMED"],
    "clinical_stage": ["SNOMED"],
    "pathologic_stage": ["SNOMED"],
    "surgical_margins": ["SNOMED"],
    "lymphovascular_invasion": ["SNOMED"],
    "perineural_invasion": ["SNOMED"],
    "distant_metastasis": ["ICD-10", "SNOMED"],
    "er_status": ["LOINC"],
    "pr_status": ["LOINC"],
    "her2_status": ["LOINC"],
    "kras_mutation": ["LOINC"],
    "egfr_mutation": ["LOINC"],
    "procedure_type": ["SNOMED"],
    "prior_treatment": ["ATC", "SNOMED"],
}

_GROUNDING_SYSTEM = """\
You are a medical coding specialist. You will be given:
1. An extracted clinical concept from a pathology report
2. A numbered list of candidate terminology codes retrieved from a local index

Your task: Select the BEST matching code from the candidate list, or reply "NONE" if no candidate is a good match.

STRICT RULES:
- You may ONLY select a code that appears in the candidate list.
- Do NOT generate or recall codes from memory.
- Reply with ONLY a JSON object: {"selected_code": "<code>", "selected_name": "<name>", "terminology": "<terminology>", "reason": "<brief reason>"}
- Or if no match: {"selected_code": "NONE", "reason": "<why no candidate fits>"}
"""


def _grounding_prompt(field_name: str, value: str, candidates_by_term: dict) -> str:
    lines = [f"Field: {field_name}", f"Extracted value: \"{value}\"", "", "Candidate codes:"]
    idx = 1
    code_map = {}
    for term, cands in candidates_by_term.items():
        for c in cands:
            lines.append(f"  [{idx}] {term} | {c['code']} | {c['concept_name']} | score={c['score']:.3f}")
            code_map[c["code"]] = {"name": c["concept_name"], "terminology": term}
            idx += 1
    lines.append("")
    lines.append("Select the best matching code, or reply NONE.")
    return "\n".join(lines), code_map


def _grounding_call(client, field_name: str, value: str, candidates: dict, report_id: str, rid_log: list):
    """Two-stage LLM grounding: retrieve candidates → LLM selects from list."""
    if not candidates or not value:
        return {}

    prompt, code_map = _grounding_prompt(field_name, value, candidates)
    valid_codes = set(code_map.keys())

    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _GROUNDING_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        elapsed = time.time() - t0
        raw = resp.choices[0].message.content
        sel = json.loads(raw)
    except Exception as e:
        logging.getLogger(__name__).warning("Grounding LLM call failed for %s/%s: %s", report_id, field_name, e)
        return {}

    selected_code = sel.get("selected_code", "NONE")
    log_entry = {
        "report_id": report_id,
        "field_name": field_name,
        "query": value,
        "candidates": {t: [{"code": c["code"], "name": c["concept_name"], "score": round(c["score"], 4)} for c in cands]
                       for t, cands in candidates.items()},
        "llm_selection": sel,
        "elapsed_sec": round(elapsed, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = {}
    if selected_code and selected_code != "NONE":
        if selected_code in valid_codes:
            meta = code_map[selected_code]
            result = {meta["terminology"]: selected_code}
            log_entry["grounding_status"] = "ACCEPTED"
        else:
            logging.getLogger(__name__).warning(
                "GROUNDING REJECTION: LLM selected code '%s' for %s/%s not in candidate set %s",
                selected_code, report_id, field_name, valid_codes
            )
            log_entry["grounding_status"] = "REJECTED_NOT_IN_CANDIDATE_SET"
    else:
        log_entry["grounding_status"] = "ABSTAINED"

    rid_log.append(log_entry)
    return result


def main():
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Warm up FAISS index
    logging.info("Loading FAISS terminology index...")
    idx = _term_mod.get_index()
    logging.info("Index ready.")

    report_files = sorted(INPUT_DIR.glob("report_*.txt"))
    if not report_files:
        print(f"ERROR: No report files in {INPUT_DIR}")
        sys.exit(1)

    print(f"\nPipeline B (LLM + Local Terminology Retrieval)")
    print(f"Model: {LLM_MODEL} | Index: 85 concepts | Two-stage grounding")
    print("=" * 60)

    total_cost = 0.0
    total_time = 0.0
    total_fields = 0
    total_codes = 0
    all_log_entries = []
    results_summary = []

    for report_file in report_files:
        rid = report_file.stem
        text = report_file.read_text(encoding="utf-8")
        rid_log = []
        t_report_start = time.time()
        cost_report = 0.0
        tok_in = 0
        tok_out = 0

        # --- Stage 1: LLM extraction ---
        from llm_extractor import OpenAIExtractor  # uses global sys.path
        extractor = _llm_mod.OpenAIExtractor(
            model=LLM_MODEL,
            api_key=OPENAI_API_KEY,
        )
        try:
            t0 = time.time()
            fields = extractor.extract(text)
            el = time.time() - t0
        except Exception as e:
            print(f"  [FATAL] {rid}: LLM extraction failed: {e}")
            sys.exit(1)

        # Rough cost estimate for extraction call
        cost_extract = 0.0  # placeholder; detailed accounting via run summary

        # --- Stage 2: FAISS retrieval + LLM grounding ---
        grounded_fields = {}
        for fname, fdict in fields.items():
            val = fdict.get("value")
            state = fdict.get("state", "not_mentioned")
            if fname not in CODEABLE_FIELDS or not val or state in ("not_mentioned", "not_applicable"):
                grounded_fields[fname] = {**fdict, "codes": {}}
                continue

            terms = FIELD_TERMINOLOGIES.get(fname, [])
            query_map = {t: 10 for t in terms}
            candidates_by_term = idx.search_multi(val, query_map)

            codes = _grounding_call(client, fname, val, candidates_by_term, rid, rid_log)
            grounded_fields[fname] = {**fdict, "codes": codes}

        all_log_entries.extend(rid_log)

        t_report_elapsed = time.time() - t_report_start

        # Build output
        FIELD_NAMES = _schema_mod.FIELD_NAMES
        PIPELINE_B = _schema_mod.PIPELINE_B
        output = _schema_mod.empty_output(rid, PIPELINE_B)
        for fname in FIELD_NAMES:
            if fname in grounded_fields:
                fd = grounded_fields[fname]
                output["fields"][fname] = {
                    "value": fd.get("value"),
                    "unit": fd.get("unit"),
                    "state": fd.get("state", "not_mentioned"),
                    "evidence": fd.get("evidence"),
                    "span": fd.get("span"),
                    "codes": fd.get("codes", {}),
                }

        output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
        output["model_versions"] = {
            "mode": "llm_retrieval",
            "llm_model": LLM_MODEL,
            "faiss_index": "terminology/terminology_index.faiss",
            "n_concepts": 85,
            "grounding": "two_stage_llm_selection",
            "elapsed_sec": round(t_report_elapsed, 3),
        }

        out_path = OUTPUT_DIR / (rid + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        populated = sum(1 for v in output["fields"].values() if v.get("value") or v.get("state") == "present")
        coded = sum(1 for v in output["fields"].values() if v.get("codes"))
        total_fields += populated
        total_codes += coded
        total_time += t_report_elapsed

        grounding_accepted = sum(1 for e in rid_log if e.get("grounding_status") == "ACCEPTED")
        grounding_abstained = sum(1 for e in rid_log if e.get("grounding_status") == "ABSTAINED")
        print(f"  {rid}: {populated}/21 fields | {coded} coded | "
              f"grounding: {grounding_accepted} accepted, {grounding_abstained} abstained | "
              f"{t_report_elapsed:.1f}s")

        results_summary.append({
            "report_id": rid,
            "fields_populated": populated,
            "fields_coded": coded,
            "grounding_accepted": grounding_accepted,
            "grounding_abstained": grounding_abstained,
            "elapsed_sec": t_report_elapsed,
        })

    # Write retrieval log
    with open(RETRIEVAL_LOG, "w", encoding="utf-8") as f:
        for entry in all_log_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    n = len(report_files)
    print("\n" + "=" * 60)
    print(f"PIPELINE B SUMMARY")
    print(f"  Reports processed:          {n}")
    print(f"  Mean fields populated:      {total_fields / n:.1f}/21")
    print(f"  Mean fields coded:          {total_codes / n:.1f}")
    print(f"  Mean runtime per report:    {total_time / n:.2f}s")
    print(f"  Retrieval log:              {RETRIEVAL_LOG}")
    print(f"  Outputs written to:         {OUTPUT_DIR}")

    summary_path = OUTPUT_DIR / "_run_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "pipeline": "Pipeline B (LLM + Local Terminology Retrieval)",
            "model": LLM_MODEL,
            "n_reports": n,
            "mean_runtime_sec": total_time / n,
            "mean_fields_populated": total_fields / n,
            "mean_fields_coded": total_codes / n,
            "per_report": results_summary,
        }, f, indent=2)


if __name__ == "__main__":
    main()
