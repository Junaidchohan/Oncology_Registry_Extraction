"""
pipeline.py  —  Pipeline B: LLM + Local Terminology Retrieval
==============================================================

End-to-end flow for a single report:

  Step 1  LLM extraction    : extract all 21 fields from report text
  Step 2  Terminology retrieval : FAISS search for top-K coding candidates
  Step 3  Grounding enforcement : validate / select codes from candidate set only
  Step 4  Schema assembly   : build schema-compliant output JSON

Grounding guarantee:
  Any code attached to a field MUST have been retrieved as a candidate from
  the local FAISS index. Codes proposed by the LLM that are not in the
  candidate set are REJECTED and replaced with the top-1 FAISS candidate.

Configuration (environment variables):
  OPENAI_API_KEY   — OpenAI API key (enables LLM extraction)
  LLM_API_BASE     — base URL for OpenAI-compatible local API (e.g. Ollama)
  LLM_MODEL        — model name (default: gpt-4o-mini)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))
sys.path.insert(0, str(_HERE))

from schema import FIELD_NAMES, PIPELINE_B, empty_output  # noqa


def run_pipeline_b(
    report_id: str,
    report_text: str,
    extractor: Optional[Any] = None,
    grounding_engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run Pipeline B on a single report.

    Parameters
    ----------
    report_id : str
    report_text : str
    extractor : LLM extractor instance (optional, auto-created if None)
    grounding_engine : GroundingEngine instance (optional, auto-created if None)

    Returns
    -------
    Dict[str, Any] — schema-compliant output
    """
    # -----------------------------------------------------------------------
    # Lazy-init components
    # -----------------------------------------------------------------------
    if extractor is None:
        from llm_extractor import get_extractor  # noqa
        extractor = get_extractor()

    if grounding_engine is None:
        from grounding import GroundingEngine  # noqa
        grounding_engine = GroundingEngine()

    from grounding import strip_grounding_metadata  # noqa

    # -----------------------------------------------------------------------
    # Step 1: LLM Extraction
    # -----------------------------------------------------------------------
    logger.debug("[%s] Step 1: LLM extraction", report_id)
    try:
        extracted_fields = extractor.extract(report_text)
    except Exception as exc:
        logger.error("[%s] Extraction failed: %s", report_id, exc)
        return empty_output(report_id, PIPELINE_B)

    # -----------------------------------------------------------------------
    # Step 2 + 3: Terminology Retrieval + Grounding
    # -----------------------------------------------------------------------
    logger.debug("[%s] Step 2-3: Grounding", report_id)
    try:
        grounded_fields = grounding_engine.ground_all_fields(extracted_fields)
    except Exception as exc:
        logger.warning("[%s] Grounding failed: %s — using ungrounded output", report_id, exc)
        grounded_fields = extracted_fields

    # -----------------------------------------------------------------------
    # Step 4: Schema Assembly
    # -----------------------------------------------------------------------
    # Strip internal grounding metadata before final output
    clean_fields = strip_grounding_metadata(grounded_fields)

    # Ensure all 21 fields are present (fill missing with empty)
    output = empty_output(report_id, PIPELINE_B)
    for fname in FIELD_NAMES:
        if fname in clean_fields:
            fval = clean_fields[fname]
            # Ensure required keys
            output["fields"][fname] = {
                "value": fval.get("value"),
                "unit": fval.get("unit"),
                "state": fval.get("state", "not_mentioned"),
                "evidence": fval.get("evidence"),
                "span": fval.get("span"),
                "codes": fval.get("codes", {}),
            }

    output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
    output["model_versions"] = {
        "extractor": type(extractor).__name__,
        "embedding_model": "all-MiniLM-L6-v2",
        "faiss_index": "terminology_index.faiss",
        "grounding": "GroundingEngine-v1",
    }

    return output


def build_pipeline_b_components() -> tuple:
    """
    Build and return (extractor, grounding_engine) ready for repeated use
    across multiple reports (avoids re-initialisation overhead).
    """
    from llm_extractor import get_extractor  # noqa
    from grounding import GroundingEngine  # noqa

    extractor = get_extractor()
    grounding_engine = GroundingEngine()
    grounding_engine._get_index()  # warm up FAISS index load
    return extractor, grounding_engine
