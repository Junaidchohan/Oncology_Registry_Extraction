"""
llm_extractor.py
================
LLM-based field extraction for Pipeline B.

Backend (auto-selected by environment, loaded from secrets/.env):
  LLM_API_BASE set → OpenAI-compatible local model (default: Ollama at localhost:11434)
  OPENAI_API_KEY   → API key for the backend (default: "ollama" for local Ollama)
  LLM_MODEL        → Model name (default: "llama3.1:8b")

IMPORTANT: There is NO silent fallback to TF-IDF or heuristics.
If the LLM call fails for any reason, an exception is raised immediately
and execution stops. This ensures the pipeline never silently degrades.

The LLM is asked to:
  a) Extract all 21 fields from the report text.
  b) Provide verbatim evidence spans for each extracted value.
  c) NOT generate codes — grounding.py handles all code selection via FAISS.

Output format (before grounding):
    {
        "primary_site":   {"value": "...", "unit": null, "state": "present", "evidence": "..."},
        "histology_type": {...},
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
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Path setup + load secrets/.env immediately
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))

# Load .env before anything else so env vars are available
_ENV_FILE = _PROJECT_ROOT / "secrets" / ".env"
try:
    from dotenv import load_dotenv
    if _ENV_FILE.exists():
        load_dotenv(dotenv_path=_ENV_FILE, override=False)
        logging.getLogger(__name__).debug("Loaded secrets/.env from %s", _ENV_FILE)
except ImportError:
    pass  # python-dotenv not installed; rely on env vars set externally

from schema import FIELD_NAMES, FIELD_DESCRIPTIONS, VALID_STATES  # noqa

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# Compact system prompt — avoids token overflow on small local models
_SYSTEM_PROMPT = """You are a clinical data extractor for an oncology cancer registry. 
Extract exactly 20 fields (plus repeatable arrays) from pathology reports. Reply ONLY with valid JSON, no markdown.
States: present|absent|uncertain|not_mentioned|not_applicable|ambiguous.
For tumor_size: numeric value only, unit in 'unit' field (cm or mm).
For lymph node counts: integers only. Do NOT generate codes."""

# Minimal user prompt — no field descriptions, no template JSON, keeps tokens low
_USER_PROMPT_TEMPLATE = """Extract these 20 fields from the oncology pathology report below.
Return ONLY a flat JSON object (with biomarkers and anticancer_medication as arrays). Use null for missing values.

Fields: specimen, procedure, primary_tumor_site, laterality, histological_type,
tumor_behavior, tumor_grade, tumor_size (value+unit), tumor_focality,
tumor_extension, lymphovascular_invasion, perineural_invasion, surgical_margins,
lymph_nodes_examined, positive_lymph_nodes, pathologic_t, pathologic_n, pathologic_m.

Array fields:
- biomarkers: array of objects {{"assay": "...", "result": "...", "lesion_id": "...", "evidence": "...", "span": null}}
- anticancer_medication: array of strings or objects

Each non-array field: {{"value": ..., "unit": null, "state": "...", "evidence": "verbatim quote or null"}}

REPORT:
{report_text}"""


def _build_user_prompt(report_text: str) -> str:
    return _USER_PROMPT_TEMPLATE.format(report_text=report_text)


# ---------------------------------------------------------------------------
# LLM Extractor — Ollama / OpenAI-compatible API
# ---------------------------------------------------------------------------

class OpenAIExtractor:
    """
    Calls an OpenAI-compatible API (Ollama, LM Studio, OpenAI cloud, etc.)
    to extract all 21 fields from a pathology report.

    Defaults to local Ollama at http://localhost:11434/v1 with model llama3.1:8b.

    HARD FAILURE: if the API call fails for any reason, raises RuntimeError.
    There is NO fallback to heuristics or TF-IDF.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0")

        # Read from env with Ollama-friendly defaults
        self.model = model or os.environ.get("LLM_MODEL", "llama3.1:8b")
        self.temperature = temperature
        self.max_tokens = max_tokens

        key = api_key or os.environ.get("OPENAI_API_KEY", "ollama")
        base = api_base or os.environ.get("LLM_API_BASE", "http://localhost:11434/v1")

        from openai import OpenAI
        import httpx
        # Set a long transport-level timeout so slow CPU models don't get cut off.
        # 900s (15 min) is generous even for llama3.1:8b on CPU.
        _timeout = httpx.Timeout(connect=10.0, read=900.0, write=30.0, pool=10.0)
        self.client = OpenAI(api_key=key, base_url=base, http_client=httpx.Client(timeout=_timeout))
        logger.info("LLM extractor ready: model=%s  base_url=%s", self.model, base)

    def extract(self, report_text: str) -> Dict[str, Any]:
        """
        Call the LLM using streaming to keep the connection alive during slow
        CPU inference (avoids httpx ReadTimeout on long generations).

        Raises RuntimeError on any API failure — no silent fallback.
        """
        user_msg = _build_user_prompt(report_text)

        # Use streaming so Ollama keeps the TCP connection alive token-by-token.
        # Collect all chunks then parse as normal JSON.
        try:
            chunks = []
            with self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        chunks.append(delta)
            raw = "".join(chunks)
        except Exception as exc:
            raise RuntimeError(
                f"LLM API call failed (model={self.model}, base={self.client.base_url}): {exc}"
            ) from exc

        if not raw or not raw.strip():
            raise RuntimeError(
                f"LLM returned empty response (model={self.model}). "
                "Check that Ollama is running and the model is pulled."
            )

        return _parse_llm_json(raw)


# ---------------------------------------------------------------------------
# JSON parsing utilities — handles Ollama quirks (fences, trailing commas)
# ---------------------------------------------------------------------------

def _parse_llm_json(raw: str) -> Dict[str, Any]:
    """
    Robustly parse LLM JSON output.
    Handles: markdown fences, trailing commas, extra text before/after JSON.
    On parse failure raises RuntimeError (not silent fallback).
    """
    # Strip markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    # Remove trailing commas before } or ] (common LLM quirk)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    data: Dict[str, Any] = {}
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract the outermost JSON object
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"LLM output could not be parsed as JSON.\n"
                    f"Raw output (first 500 chars): {raw[:500]}\n"
                    f"Parse error: {exc}"
                ) from exc
        else:
            raise RuntimeError(
                f"LLM output contains no JSON object.\n"
                f"Raw output (first 500 chars): {raw[:500]}"
            )

    # Normalise: ensure all 21 fields are present with correct keys
    normalised: Dict[str, Any] = {}
    for fname in FIELD_NAMES:
        field = data.get(fname, {})
        if not isinstance(field, dict):
            field = {}
        value = field.get("value")
        # Convert numeric values to string for consistency
        if isinstance(value, (int, float)):
            value = str(value)
        normalised[fname] = {
            "value": value,
            "unit": field.get("unit"),
            "state": _normalise_state(field.get("state", "not_mentioned")),
            "evidence": field.get("evidence"),
            "span": field.get("span"),
            "codes": field.get("codes", {}),
        }

    return normalised


def _normalise_state(state: Any) -> str:
    """Normalise a raw state string to a valid schema state."""
    VALID = {"present", "absent", "uncertain", "not_mentioned", "not_applicable", "ambiguous"}
    if not isinstance(state, str):
        return "not_mentioned"
    s = state.lower().strip().replace(" ", "_").replace("-", "_")
    if s in VALID:
        return s
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
        "not_stated": "not_mentioned",
        "missing": "not_mentioned",
    }
    return aliases.get(s, "not_mentioned")


# ---------------------------------------------------------------------------
# Factory — always returns LLM extractor, never falls back to heuristics
# ---------------------------------------------------------------------------

def get_extractor() -> OpenAIExtractor:
    """
    Return an LLM extractor pointed at Ollama (or any configured API base).

    HARD REQUIREMENT: raises RuntimeError if the openai package is missing.
    NEVER falls back to DeterministicExtractor / heuristics.
    Call verify_connection() after this to confirm Ollama is reachable.
    """
    extractor = OpenAIExtractor()
    logger.info(
        "LLM extractor initialised: model=%s  base_url=%s",
        extractor.model, extractor.client.base_url,
    )
    return extractor


def verify_connection(extractor: OpenAIExtractor) -> None:
    """
    Send a trivial request to the LLM to confirm it is reachable.
    Raises RuntimeError immediately if Ollama is not responding.
    """
    logger.info("Verifying LLM connection (model=%s)...", extractor.model)
    try:
        resp = extractor.client.chat.completions.create(
            model=extractor.model,
            messages=[{"role": "user", "content": "Reply with the single word: READY"}],
            max_tokens=10,
            temperature=0,
        )
        reply = resp.choices[0].message.content.strip()
        logger.info("LLM connection verified. Response: '%s'", reply)
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach LLM at {extractor.client.base_url} with model '{extractor.model}'.\n"
            f"Error: {exc}\n\n"
            "Fix: ensure Ollama is running (`ollama serve`) and the model is pulled "
            f"(`ollama pull {extractor.model}`)."
        ) from exc
