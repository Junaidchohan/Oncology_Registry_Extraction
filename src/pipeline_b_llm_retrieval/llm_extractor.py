"""
llm_extractor.py
================
LLM-based field extraction for Pipeline B.

Supports three backends (auto-selected by environment):

1. OPENAI_API_KEY set → OpenAI API (gpt-4o-mini by default)
2. LLM_API_BASE set   → OpenAI-compatible local model (Ollama, LM Studio, etc.)
3. Neither set        → DeterministicExtractor (regex/heuristic, fully offline)

The LLM is asked to:
  a) Extract all 21 fields from the report text.
  b) For each field with a code-able value, describe the concept in natural
     language (not generate a code directly — grounding.py handles code selection).

Output format (before grounding):
    {
        "primary_site":     {"value": "...", "unit": null, "state": "present", "evidence": "..."},
        "histology_type":   {...},
        ...
    }
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))

from schema import FIELD_NAMES, FIELD_DESCRIPTIONS, VALID_STATES  # noqa

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert oncology pathologist and clinical NLP specialist.
Your task is to extract structured information from an oncology pathology report.

Rules:
- Extract ONLY information explicitly stated in the report.
- Do NOT infer, hallucinate, or assume information not present.
- For each field, assign ONE of these states:
    present       — information is explicitly stated as occurring/positive
    absent        — information is explicitly stated as not occurring/negative
    uncertain     — report uses hedging ("suspicious", "possible", "pending", "equivocal")
    not_mentioned — field is simply not discussed in the report
    not_applicable — field is logically irrelevant (e.g. ER status for lung squamous)
    ambiguous     — contradictory or unclear information in the report
- Provide a short evidence string (verbatim or near-verbatim from the report).
- For tumor_size, extract ONLY the numeric value; put the unit (cm or mm) in "unit".
- For lymph_nodes_examined and lymph_nodes_positive, extract ONLY the integer count.
- Respond ONLY with valid JSON. No explanations outside the JSON.
"""

_FIELD_LIST = "\n".join(
    f"  {i+1:2d}. {name}: {FIELD_DESCRIPTIONS[name]}"
    for i, name in enumerate(FIELD_NAMES)
)

_USER_PROMPT_TEMPLATE = """\
Extract the following 21 oncology fields from the pathology report below.

FIELDS TO EXTRACT:
{field_list}

Return ONLY a JSON object with this exact structure:
{{
  "primary_site":            {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "histology_type":          {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "tumor_grade":             {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "clinical_stage":          {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "pathologic_stage":        {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "tumor_size":              {{"value": ..., "unit": "cm"|"mm"|null, "state": "...", "evidence": ...}},
  "laterality":              {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "surgical_margins":        {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "lymph_nodes_examined":    {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "lymph_nodes_positive":    {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "lymphovascular_invasion": {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "perineural_invasion":     {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "distant_metastasis":      {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "er_status":               {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "pr_status":               {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "her2_status":             {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "kras_mutation":           {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "egfr_mutation":           {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "procedure_type":          {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "prior_treatment":         {{"value": ..., "unit": null, "state": "...", "evidence": ...}},
  "tumor_multiplicity":      {{"value": ..., "unit": null, "state": "...", "evidence": ...}}
}}

PATHOLOGY REPORT:
{report_text}
"""


def _build_user_prompt(report_text: str) -> str:
    return _USER_PROMPT_TEMPLATE.format(
        field_list=_FIELD_LIST,
        report_text=report_text,
    )


# ---------------------------------------------------------------------------
# OpenAI / compatible API extractor
# ---------------------------------------------------------------------------

class OpenAIExtractor:
    """
    Calls an OpenAI-compatible API (OpenAI, Ollama, LM Studio, etc.)
    to extract all 21 fields from a report.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.max_tokens = max_tokens

        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        base = api_base or os.environ.get("LLM_API_BASE", None)

        from openai import OpenAI
        self.client = OpenAI(api_key=key, base_url=base)
        logger.info("OpenAI extractor: model=%s base=%s", self.model, base or "default")

    def extract(self, report_text: str) -> Dict[str, Any]:
        """Call the LLM and parse the JSON response."""
        user_msg = _build_user_prompt(report_text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return _parse_llm_json(raw)


# ---------------------------------------------------------------------------
# Deterministic heuristic extractor (offline fallback)
# ---------------------------------------------------------------------------

class DeterministicExtractor:
    """
    Regex/rule-based extractor that runs entirely offline.
    Produces valid schema output without any LLM.
    Used when no LLM API is configured.
    """

    def extract(self, report_text: str) -> Dict[str, Any]:
        """Extract all 21 fields using deterministic heuristics."""
        # Reuse Pipeline A's heuristic extraction logic (import from sibling)
        sys.path.insert(0, str(_PROJECT_ROOT / "src" / "pipeline_a_classical"))
        from pipeline import _heuristic_extract  # noqa
        from stages.preprocessing import preprocess  # noqa

        preprocessed = preprocess(report_text)
        # _heuristic_extract returns a full output dict; we just need the fields
        output = _heuristic_extract("_temp_", preprocessed)
        return output["fields"]  # dict of field_name → field_dict


# ---------------------------------------------------------------------------
# JSON parsing utilities
# ---------------------------------------------------------------------------

def _parse_llm_json(raw: str) -> Dict[str, Any]:
    """
    Parse LLM JSON output. Handles common model quirks:
    - Markdown code fences
    - Trailing commas
    - Missing fields (fills with empty)
    """
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM JSON; returning empty extraction.")
                data = {}
        else:
            data = {}

    # Normalise: ensure all 21 fields present with correct keys
    normalised: Dict[str, Any] = {}
    for fname in FIELD_NAMES:
        field = data.get(fname, {})
        if not isinstance(field, dict):
            field = {}
        normalised[fname] = {
            "value": field.get("value"),
            "unit": field.get("unit"),
            "state": _normalise_state(field.get("state", "not_mentioned")),
            "evidence": field.get("evidence"),
            "span": field.get("span"),
            "codes": field.get("codes", {}),
        }

    return normalised


def _normalise_state(state: Any) -> str:
    """Normalise a raw state string to a valid schema state."""
    if not isinstance(state, str):
        return "not_mentioned"
    s = state.lower().strip().replace(" ", "_")
    if s in VALID_STATES:
        return s
    # Common LLM aliases
    aliases = {
        "yes": "present",
        "no": "absent",
        "positive": "present",
        "negative": "absent",
        "n/a": "not_applicable",
        "na": "not_applicable",
        "not_available": "not_mentioned",
        "unknown": "not_mentioned",
        "possible": "uncertain",
        "suspected": "uncertain",
    }
    return aliases.get(s, "not_mentioned")


# ---------------------------------------------------------------------------
# Factory: choose the right extractor
# ---------------------------------------------------------------------------

def get_extractor() -> Any:
    """
    Auto-select the best available extractor.
    Priority: OpenAI API > local OpenAI-compatible API > deterministic fallback.
    """
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_BASE"):
        try:
            extractor = OpenAIExtractor()
            logger.info("Using OpenAI/compatible LLM extractor.")
            return extractor
        except (ImportError, Exception) as e:
            logger.warning("Could not initialise OpenAI extractor (%s). Falling back.", e)

    logger.info(
        "Using DeterministicExtractor (offline mode). "
        "Set OPENAI_API_KEY or LLM_API_BASE to enable LLM extraction."
    )
    return DeterministicExtractor()
