"""
run_pipeline_b_real.py  —  Pipeline B: LLM + Local Terminology Retrieval
=========================================================================
Runs Pipeline B on all 10 reports using:
  - Ollama (llama3.1:8b) for LLM field extraction  [Stage 1]
  - FAISS terminology index (85 concepts) for retrieval  [Stage 2]
  - Second LLM call to select code from FAISS candidates  [Stage 3]
  - Deterministic code rejection if not in candidate set  [Stage 4]

All configuration is loaded from secrets/.env (Ollama defaults):
  LLM_API_BASE=http://localhost:11434/v1
  LLM_MODEL=llama3.1:8b
  OPENAI_API_KEY=ollama

Outputs:
  outputs/pipeline_b/report_001.json ... report_010.json
  outputs/pipeline_b/retrieval_log.jsonl

HARD RULE: No fallback to heuristics. If Ollama is unreachable, stops immediately.
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
logger = logging.getLogger("pipeline_b")

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src" / "common"))
sys.path.insert(0, str(_ROOT / "src" / "pipeline_b_llm_retrieval"))

# Load config (pulls secrets/.env)
from config import OPENAI_API_KEY, LLM_API_BASE, LLM_MODEL  # noqa

logger.info("Config: model=%s  base=%s  key_prefix=%s", LLM_MODEL, LLM_API_BASE, OPENAI_API_KEY[:6])

# Load modules explicitly to avoid name collisions
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_llm_mod   = _load("llm_extractor_b",   _ROOT / "src/pipeline_b_llm_retrieval/llm_extractor.py")
_term_mod  = _load("terminology_index_b", _ROOT / "src/pipeline_b_llm_retrieval/terminology_index.py")
_schema_mod = _load("schema_b",          _ROOT / "src/common/schema.py")

from openai import OpenAI  # noqa

INPUT_DIR  = _ROOT / "data" / "raw"
OUTPUT_DIR = _ROOT / "outputs" / "pipeline_b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVAL_LOG = OUTPUT_DIR / "retrieval_log.jsonl"

FIELD_TERMINOLOGIES = {
    "primary_site":             ["ICD-O-3", "SNOMED"],
    "histology_type":           ["ICD-O-3", "ICD-10"],
    "tumor_grade":              ["SNOMED"],
    "clinical_stage":           ["SNOMED"],
    "pathologic_stage":         ["SNOMED"],
    "surgical_margins":         ["SNOMED"],
    "lymphovascular_invasion":  ["SNOMED"],
    "perineural_invasion":      ["SNOMED"],
    "distant_metastasis":       ["ICD-10", "SNOMED"],
    "er_status":                ["LOINC"],
    "pr_status":                ["LOINC"],
    "her2_status":              ["LOINC"],
    "kras_mutation":            ["LOINC"],
    "egfr_mutation":            ["LOINC"],
    "procedure_type":           ["SNOMED"],
    "prior_treatment":          ["ATC", "SNOMED"],
}

_GROUNDING_SYSTEM = """\
You are a medical coding specialist. You will be given a clinical concept extracted from a
pathology report and a numbered list of candidate terminology codes retrieved from a local index.

Select the BEST matching code from the candidate list, or reply NONE if no candidate fits well.

RULES (mandatory):
- You may ONLY select a code that appears in the provided candidate list.
- Do NOT recall codes from memory.
- Do NOT generate new codes.
- Reply with ONLY valid JSON — no markdown, no extra text.

Response format:
{"selected_code": "<code from list or NONE>", "terminology": "<terminology name>", "concept_name": "<preferred name>", "reason": "<one sentence>"}
"""


def _grounding_prompt(field_name: str, value: str, candidates_by_term: dict) -> tuple:
    lines = [f"Field: {field_name}", f'Extracted concept: "{value}"', "", "Candidate codes:"]
    idx = 1
    code_map = {}
    for term, cands in candidates_by_term.items():
        for c in cands:
            lines.append(f"  [{idx}] {term} | {c['code']} | {c['concept_name']} | score={c['score']:.3f}")
            code_map[c["code"]] = {"name": c["concept_name"], "terminology": term}
            idx += 1
    lines += ["", 'Select the best code from the list above, or reply {"selected_code": "NONE", ...}']
    return "\n".join(lines), code_map


def _grounding_call(client, field_name: str, value: str, candidates: dict,
                    report_id: str, rid_log: list) -> dict:
    """Stage 3: LLM selects from FAISS candidates. Enforces no out-of-set codes."""
    if not candidates or not value:
        return {}

    prompt, code_map = _grounding_prompt(field_name, value, candidates)
    valid_codes = set(code_map.keys())

    t0 = time.time()
    try:
        import httpx
        import re as _re
        _timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
        # Use streaming for grounding calls too to avoid read timeouts
        chunks = []
        with client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _GROUNDING_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    chunks.append(delta)
        elapsed = time.time() - t0
        raw = "".join(chunks).strip()
        # Strip markdown fences if present
        raw = _re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = _re.sub(r"\s*```\s*$", "", raw)
        sel = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("Grounding JSON parse error for %s/%s: %s | raw: %s", report_id, field_name, e, raw[:200])
        return {}
    except Exception as e:
        # Hard fail on connection error — do not silently skip
        raise RuntimeError(f"Grounding LLM call failed for {report_id}/{field_name}: {e}") from e

    selected_code = sel.get("selected_code", "NONE")

    # Normalise: LLM sometimes returns "TERM | CODE | Name" instead of bare code.
    # Extract the bare code if it is present in valid_codes anywhere in the string.
    if selected_code and selected_code.upper() != "NONE":
        if selected_code not in valid_codes:
            # Try to find a valid code embedded in the string (e.g. "ICD-O-3 | 8140/3 | ...")
            for vc in valid_codes:
                if vc in selected_code:
                    logger.info(
                        "Grounding code normalised for %s/%s: '%s' → '%s'",
                        report_id, field_name, selected_code, vc
                    )
                    selected_code = vc
                    break

    log_entry = {
        "report_id": report_id,
        "field_name": field_name,
        "query": value,
        "candidates": {
            t: [{"code": c["code"], "name": c["concept_name"], "score": round(c["score"], 4)}
                for c in cands]
            for t, cands in candidates.items()
        },
        "llm_selection": sel,
        "elapsed_sec": round(elapsed, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result = {}
    if selected_code and selected_code.upper() != "NONE":
        if selected_code in valid_codes:
            meta = code_map[selected_code]
            result = {meta["terminology"]: selected_code}
            log_entry["grounding_status"] = "ACCEPTED"
        else:
            logger.warning(
                "GROUNDING REJECTION: '%s' not in candidate set for %s/%s. Candidate set: %s",
                selected_code, report_id, field_name, valid_codes
            )
            log_entry["grounding_status"] = "REJECTED_NOT_IN_CANDIDATE_SET"
    else:
        log_entry["grounding_status"] = "ABSTAINED"

    rid_log.append(log_entry)
    return result


def main():
    # Build components
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=LLM_API_BASE)

    # Step 0: Verify Ollama connection before processing anything
    logger.info("Verifying LLM connection...")
    _llm_mod.verify_connection(_llm_mod.OpenAIExtractor())
    logger.info("LLM connection OK.")

    # Warm up FAISS index
    logger.info("Loading FAISS terminology index...")
    idx = _term_mod.get_index()
    logger.info("Index loaded.")

    extractor = _llm_mod.get_extractor()

    report_files = sorted(INPUT_DIR.glob("report_*.txt"))
    if not report_files:
        print(f"ERROR: No report files found in {INPUT_DIR}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Pipeline B: LLM + Local Terminology Retrieval")
    print(f"  LLM:   {LLM_MODEL} @ {LLM_API_BASE}")
    print(f"  Index: 85 FAISS concepts (TF-IDF char n-grams)")
    print(f"  Reports: {len(report_files)}")
    print(f"{'='*60}")

    all_log_entries = []
    results_summary = []
    total_time = 0.0
    total_fields = 0
    total_codes = 0

    FIELD_NAMES = _schema_mod.FIELD_NAMES
    PIPELINE_B  = _schema_mod.PIPELINE_B

    for report_file in report_files:
        rid = report_file.stem
        text = report_file.read_text(encoding="utf-8")
        rid_log = []
        t_start = time.time()

        # --- Stage 1: LLM extraction ---
        logger.info("[%s] Stage 1: LLM field extraction...", rid)
        fields = extractor.extract(text)  # raises RuntimeError if LLM fails

        # --- Stage 2+3: FAISS retrieval + LLM grounding per codeable field ---
        logger.info("[%s] Stage 2-3: Terminology retrieval + grounding...", rid)
        grounded_fields = {}
        for fname, fdict in fields.items():
            val = fdict.get("value")
            state = fdict.get("state", "not_mentioned")
            terms = FIELD_TERMINOLOGIES.get(fname, [])

            if not terms or not val or state in ("not_mentioned", "not_applicable"):
                grounded_fields[fname] = {**fdict, "codes": {}}
                continue

            # Retrieve top-10 candidates per terminology
            query_map = {t: 10 for t in terms}
            candidates_by_term = idx.search_multi(val, query_map)

            # LLM selects from candidates (Stage 3) — enforced in code (Stage 4)
            codes = _grounding_call(client, fname, val, candidates_by_term, rid, rid_log)
            grounded_fields[fname] = {**fdict, "codes": codes}

        all_log_entries.extend(rid_log)
        t_elapsed = time.time() - t_start

        # Build schema-compliant output
        output = _schema_mod.empty_output(rid, PIPELINE_B)
        for fname in FIELD_NAMES:
            if fname in grounded_fields:
                fd = grounded_fields[fname]
                output["fields"][fname] = {
                    "value":    fd.get("value"),
                    "unit":     fd.get("unit"),
                    "state":    fd.get("state", "not_mentioned"),
                    "evidence": fd.get("evidence"),
                    "span":     fd.get("span"),
                    "codes":    fd.get("codes", {}),
                }

        output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
        output["model_versions"] = {
            "mode":        "llm_retrieval_ollama",
            "llm_model":   LLM_MODEL,
            "llm_base":    LLM_API_BASE,
            "faiss_index": "terminology/terminology_index.faiss",
            "n_concepts":  85,
            "grounding":   "two_stage_llm_selection",
            "elapsed_sec": round(t_elapsed, 3),
        }

        out_path = OUTPUT_DIR / (rid + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        populated = sum(1 for v in output["fields"].values() if v.get("value") or v.get("state") == "present")
        coded     = sum(1 for v in output["fields"].values() if v.get("codes"))
        g_accepted  = sum(1 for e in rid_log if e.get("grounding_status") == "ACCEPTED")
        g_abstained = sum(1 for e in rid_log if e.get("grounding_status") == "ABSTAINED")
        g_rejected  = sum(1 for e in rid_log if e.get("grounding_status") == "REJECTED_NOT_IN_CANDIDATE_SET")

        total_time   += t_elapsed
        total_fields += populated
        total_codes  += coded

        print(f"  {rid}: {populated}/21 fields | {coded} coded | "
              f"grounding: {g_accepted} accepted / {g_abstained} abstained / {g_rejected} rejected | "
              f"{t_elapsed:.1f}s")

        results_summary.append({
            "report_id": rid,
            "fields_populated": populated,
            "fields_coded": coded,
            "grounding_accepted": g_accepted,
            "grounding_abstained": g_abstained,
            "grounding_rejected": g_rejected,
            "elapsed_sec": round(t_elapsed, 3),
        })

    # Write retrieval log
    with open(RETRIEVAL_LOG, "w", encoding="utf-8") as f:
        for entry in all_log_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    n = len(report_files)
    print(f"\n{'='*60}")
    print(f"PIPELINE B COMPLETE")
    print(f"  Reports processed:          {n}")
    print(f"  Mean fields populated:      {total_fields/n:.1f}/21")
    print(f"  Mean fields with codes:     {total_codes/n:.1f}")
    print(f"  Mean runtime per report:    {total_time/n:.1f}s")
    print(f"  Total runtime:              {total_time:.1f}s")
    print(f"  Retrieval log:              {RETRIEVAL_LOG}")
    print(f"  Output directory:           {OUTPUT_DIR}")
    print(f"{'='*60}")

    # Write summary
    summary_path = OUTPUT_DIR / "_run_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "pipeline": "Pipeline B (LLM + Local Terminology Retrieval)",
            "llm_model": LLM_MODEL,
            "llm_base": LLM_API_BASE,
            "n_reports": n,
            "mean_runtime_sec": round(total_time / n, 3),
            "mean_fields_populated": round(total_fields / n, 1),
            "mean_fields_coded": round(total_codes / n, 1),
            "per_report": results_summary,
        }, f, indent=2)


if __name__ == "__main__":
    main()
