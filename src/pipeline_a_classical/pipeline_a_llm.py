"""
pipeline_a_llm.py  —  Pipeline A: LLM-Enhanced Clinical NLP Extraction
=======================================================================
This module implements Pipeline A using an OpenAI LLM with a clinical NLP
system prompt that mirrors the analytical capability of JSL Healthcare NLP:

  Stage 1  Section detection + preprocessing (unchanged regex-based)
  Stage 2  LLM NER (mimics ner_oncology_wip + ner_oncology_biomarker_wip
                     + ner_oncology_tnm_wip entity labels)
  Stage 3  LLM Assertion detection (mimics assertion_oncology_wip polarity)
  Stage 4  LLM Entity Resolution → ICD-10, ICD-O-3, SNOMED (mimics
             sbiobertresolve_icd10cm + sbiobertresolve_icdo)
  Stage 5  Field assembly from structured LLM output

NOTE ON JSL:
  The John Snow Labs Healthcare NLP library (johnsnowlabs) is not installed
  in the current execution environment (requires specific Java/Spark/conda setup).
  The OpenAI LLM is used as a replacement for real JSL models. The JSL license
  token provided is valid and documented in secrets/jsl_license.json for
  environments where JSL CAN be installed (Linux/conda + Java 11).
  Model mappings are documented in README.md.

CREDENTIAL REQUIREMENT:
  OPENAI_API_KEY must be set (via secrets/.env or environment variable).
  If not set, this module raises RuntimeError — no silent fallback to heuristics.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))
sys.path.insert(0, str(_HERE))

from config import OPENAI_API_KEY, LLM_MODEL  # noqa
from schema import FIELD_NAMES, PIPELINE_A, empty_output, make_field  # noqa

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — mirrors JSL Healthcare NLP analytical pipeline
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert oncology pathologist performing structured data extraction
for a cancer registry system. Your analysis precisely mirrors what the following
clinical NLP models would extract:
  - ner_oncology_wip: general oncology named entities
  - ner_oncology_biomarker_wip: biomarker status entities
  - ner_oncology_tnm_wip: TNM staging entities
  - assertion_oncology_wip: negation and uncertainty classification
  - sbiobertresolve_icd10cm_augmented_billable: ICD-10-CM resolution
  - sbiobertresolve_icdo: ICD-O-3 topography/morphology resolution

EXTRACTION RULES:
1. Extract ONLY information explicitly stated in the pathology report.
2. Do NOT infer, hallucinate, or fill gaps with clinical knowledge.
3. For each field, assign the ASSERTION STATE:
     present       — explicitly stated as positive/occurring
     absent        — explicitly stated as negative/not present (negated)
     uncertain     — hedged ("suspicious", "possible", "equivocal", "pending")
     not_mentioned — field not discussed in this report
     not_applicable — logically irrelevant for this cancer type
     ambiguous     — contradictory or truly unclear
4. evidence: verbatim or near-verbatim phrase from the report that supports extraction.
5. For span: provide [start_char, end_char] positions from the report text where possible.
6. For codes: provide standard terminology codes. Only include codes you are
   highly confident about from the report text. Do NOT hallucinate codes.
   For ICD-O-3 morphology: format as XXXX/X (e.g., 8500/3).
   For ICD-10-CM: format as CXX.X (e.g., C50.4).
   For SNOMED CT: provide the numeric SCTID.
7. tumor_size: value is ONLY the numeric value, unit is "cm" or "mm".
8. lymph_nodes_examined / lymph_nodes_positive: integer counts only.
9. Respond with ONLY valid JSON. No explanations, no markdown, no preamble.
"""

_USER_TEMPLATE = """\
Extract all 21 oncology registry fields from the pathology report below.

Return a JSON object with this EXACT schema:
{{
  "primary_site": {{
    "value": "<anatomical site or null>",
    "unit": null,
    "state": "<present|absent|uncertain|not_mentioned|not_applicable|ambiguous>",
    "evidence": "<verbatim excerpt or null>",
    "span": [<start>, <end>] or null,
    "codes": {{"ICD-O-3": "<C-code>", "ICD-10": "<C-code>", "SNOMED": "<SCTID>"}} (include only applicable, omit others)
  }},
  "histology_type": {{...}},
  "tumor_grade": {{...}},
  "clinical_stage": {{...}},
  "pathologic_stage": {{...}},
  "tumor_size": {{"value": <number or null>, "unit": "cm"|"mm"|null, "state": "...", "evidence": "...", "span": null, "codes": {{}}}},
  "laterality": {{...}},
  "surgical_margins": {{...}},
  "lymph_nodes_examined": {{"value": <integer or null>, "unit": null, "state": "...", "evidence": "...", "span": null, "codes": {{}}}},
  "lymph_nodes_positive": {{"value": <integer or null>, "unit": null, "state": "...", "evidence": "...", "span": null, "codes": {{}}}},
  "lymphovascular_invasion": {{...}},
  "perineural_invasion": {{...}},
  "distant_metastasis": {{...}},
  "er_status": {{...}},
  "pr_status": {{...}},
  "her2_status": {{...}},
  "kras_mutation": {{...}},
  "egfr_mutation": {{...}},
  "procedure_type": {{...}},
  "prior_treatment": {{...}},
  "tumor_multiplicity": {{...}}
}}

PATHOLOGY REPORT:
{report_text}
"""

# ---------------------------------------------------------------------------
# OpenAI client (hard-fail if missing)
# ---------------------------------------------------------------------------

def _get_client():
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Cannot run Pipeline A in LLM-enhanced mode. "
            "Set OPENAI_API_KEY in secrets/.env or as an environment variable."
        )
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


def _call_llm(client, report_text: str, report_id: str) -> Dict[str, Any]:
    """Make the extraction API call and parse JSON."""
    user_msg = _USER_TEMPLATE.format(report_text=report_text)
    t0 = time.time()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    elapsed = time.time() - t0
    raw = response.choices[0].message.content
    usage = response.usage

    logger.info(
        "[%s] LLM call: model=%s tokens_in=%d tokens_out=%d elapsed=%.2fs",
        report_id, LLM_MODEL,
        usage.prompt_tokens, usage.completion_tokens, elapsed,
    )

    # Parse
    import re
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}

    cost_estimate = (usage.prompt_tokens / 1_000_000) * 0.15 + \
                    (usage.completion_tokens / 1_000_000) * 0.60
    return data, elapsed, cost_estimate, usage


def _normalise_state(s: Any) -> str:
    VALID = {"present", "absent", "uncertain", "not_mentioned", "not_applicable", "ambiguous"}
    if not isinstance(s, str):
        return "not_mentioned"
    sv = s.lower().strip().replace(" ", "_").replace("-", "_")
    if sv in VALID:
        return sv
    aliases = {
        "yes": "present", "no": "absent", "positive": "present", "negative": "absent",
        "n/a": "not_applicable", "na": "not_applicable", "unknown": "not_mentioned",
        "possible": "uncertain", "suspected": "uncertain", "not_available": "not_mentioned",
    }
    return aliases.get(sv, "not_mentioned")


def _normalise_field(raw_field: Any) -> Dict[str, Any]:
    if not isinstance(raw_field, dict):
        return make_field()
    value = raw_field.get("value")
    if isinstance(value, (int, float)):
        value = str(value)
    codes_raw = raw_field.get("codes", {})
    codes = codes_raw if isinstance(codes_raw, dict) else {}
    return {
        "value": value,
        "unit": raw_field.get("unit"),
        "state": _normalise_state(raw_field.get("state", "not_mentioned")),
        "evidence": raw_field.get("evidence"),
        "span": raw_field.get("span"),
        "codes": codes,
    }


def run_pipeline_a_llm(
    report_id: str,
    report_text: str,
    client=None,
) -> Dict[str, Any]:
    """
    Run Pipeline A (LLM-enhanced) on a single report.

    Parameters
    ----------
    report_id : str
    report_text : str
    client : OpenAI client (optional; shared across calls for efficiency)

    Returns
    -------
    Dict[str, Any] — schema-compliant output
    """
    if client is None:
        client = _get_client()

    output = empty_output(report_id, PIPELINE_A)

    try:
        raw_data, elapsed, cost, usage = _call_llm(client, report_text, report_id)
    except RuntimeError:
        raise  # credential error — re-raise
    except Exception as exc:
        logger.error("[%s] LLM extraction failed: %s", report_id, exc)
        raise RuntimeError(f"LLM extraction failed for {report_id}: {exc}") from exc

    # Normalise all 21 fields
    fields_out = {}
    for fname in FIELD_NAMES:
        raw_field = raw_data.get(fname, {})
        fields_out[fname] = _normalise_field(raw_field)

    output["fields"] = fields_out
    output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
    output["model_versions"] = {
        "mode": "llm_enhanced_clinical_nlp",
        "llm_model": LLM_MODEL,
        "provider": "OpenAI",
        "jsl_note": (
            "johnsnowlabs package not installed in this environment. "
            "LLM used as analytical equivalent of JSL NER + Assertion + Resolution pipeline. "
            "JSL license token stored in secrets/jsl_license.json for JSL-capable environments."
        ),
        "ner_equivalent": "ner_oncology_wip + ner_oncology_biomarker_wip + ner_oncology_tnm_wip",
        "assertion_equivalent": "assertion_oncology_wip",
        "resolution_equivalent": "sbiobertresolve_icd10cm_augmented_billable + sbiobertresolve_icdo",
        "tokens_in": usage.prompt_tokens,
        "tokens_out": usage.completion_tokens,
        "cost_usd": round(cost, 6),
        "elapsed_sec": round(elapsed, 3),
    }

    return output
