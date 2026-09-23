"""
grounding.py
============
Terminology grounding and code validation for Pipeline B.

Grounding enforces that any code attached to an extracted field:
  1. Was retrieved as a candidate from the local FAISS index (the candidate set).
  2. Was explicitly selected by the LLM from that candidate set (or NONE).
  3. Is not hallucinated — any code not in the candidate set is rejected.

Grounding pipeline per field
-----------------------------
1. LLM extracts field value (e.g. "invasive ductal carcinoma, Grade 3").
2. FAISS retrieves top-K candidates from relevant terminologies.
3. LLM (or deterministic rule) selects the best-matching code from candidates.
4. Grounding validator checks: selected code ∈ candidate set → ACCEPT.
5. If selected code ∉ candidate set → REJECT, code set to {} with warning.

For offline mode (no LLM), a best-match selector picks the top-1 candidate
by cosine score from the FAISS results.

Field → terminology routing
-----------------------------
primary_site         → ICD-O-3 (topography), SNOMED (anatomical sites)
histology_type       → ICD-O-3 (morphology), ICD-10
tumor_grade          → SNOMED
clinical_stage       → SNOMED (AJCC stage)
pathologic_stage     → SNOMED (AJCC stage)
tumor_size           → (no code; numeric value only)
laterality           → (no code)
surgical_margins     → SNOMED
lymph_nodes_examined → (no code; count only)
lymph_nodes_positive → (no code; count only)
lymphovascular_invasion → SNOMED
perineural_invasion  → SNOMED
distant_metastasis   → ICD-10, SNOMED
er_status            → LOINC
pr_status            → LOINC
her2_status          → LOINC
kras_mutation        → LOINC
egfr_mutation        → LOINC
procedure_type       → SNOMED
prior_treatment      → ATC, SNOMED
tumor_multiplicity   → (no code)
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Code-token extraction helper
# ---------------------------------------------------------------------------

def extract_code_token(selection: str) -> str:
    """Extract the pure code from an LLM selection string.

    Handles formats such as:
      - "369783002"
      - "SNOMED | 369783002 | Nottingham Grade 2"
      - "SNOMED | 369783002"
      - "ICD-O-3 | 8500/3 | Invasive ductal carcinoma"
      - "LOINC | 81197-5"
      - "369783002 | Nottingham Grade 2"
      - "ICD-10 | C50.4 | ..."
      - "ICD-10-CM | C50.4"
      - "NONE" / "ABSTAIN" (abstention — returned as-is)
    """
    if not selection:
        return ""
    s = str(selection).strip()
    if s.upper() == "NONE" or s.upper().startswith("ABSTAIN"):
        return "NONE"

    # Known terminology name tokens to skip (they contain digits but are NOT codes)
    _TERMINOLOGY_NAMES = {
        "ICD-O-3", "ICD-10", "ICD-10-CM", "ICD-O", "SNOMED", "LOINC", "ATC",
        "ICD-9", "ICD-9-CM", "ICDO", "ICDO3", "SNOMEDCT",
    }

    # Split on pipe and pick the first segment containing a digit and no spaces
    # that is not a known terminology name token.
    if "|" in s:
        for part in [p.strip() for p in s.split("|")]:
            if (
                part
                and any(c.isdigit() for c in part)
                and " " not in part
                and part.upper() not in _TERMINOLOGY_NAMES
            ):
                return part

    # Otherwise: try to match a code-like token (letters, digits, dots, slashes, hyphens)
    m = re.search(r"([A-Za-z]?\d[\w\.\-/]*)", s)
    if m:
        return m.group(1)
    return s



# ---------------------------------------------------------------------------
# Field → terminologies to retrieve from
# ---------------------------------------------------------------------------

FIELD_TERMINOLOGY_MAP: Dict[str, List[str]] = {
    "primary_site":             ["ICD-O-3", "SNOMED"],
    "histology_type":           ["ICD-O-3", "ICD-10"],
    "tumor_grade":              ["SNOMED"],
    "clinical_stage":           ["SNOMED"],
    "pathologic_stage":         ["SNOMED"],
    "tumor_size":               [],            # numeric only
    "laterality":               [],
    "surgical_margins":         ["SNOMED"],
    "lymph_nodes_examined":     [],            # count only
    "lymph_nodes_positive":     [],            # count only
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
    "tumor_multiplicity":       [],
}

# How many candidates to retrieve per terminology per field
_TOP_K_PER_TERMINOLOGY = 3


class GroundingEngine:
    """
    Wraps the FAISS index and enforces grounding for all 21 fields.
    """

    def __init__(self, top_k: int = _TOP_K_PER_TERMINOLOGY) -> None:
        self.top_k = top_k
        self._idx = None   # lazy-loaded TerminologyIndex

    def _get_index(self):
        if self._idx is None:
            _HERE = Path(__file__).resolve().parent
            sys.path.insert(0, str(_HERE))
            from terminology_index import get_index  # noqa
            self._idx = get_index()
        return self._idx

    # ------------------------------------------------------------------
    # Candidate retrieval
    # ------------------------------------------------------------------

    def retrieve_candidates(
        self,
        field_name: str,
        entity_value: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve terminology candidates for a given field and entity value.

        Returns
        -------
        Dict[str, List[candidate_dict]]
            {terminology_name: [candidates ordered by score]}
        """
        terminologies = FIELD_TERMINOLOGY_MAP.get(field_name, [])
        if not terminologies or not entity_value:
            return {}

        idx = self._get_index()
        query_terminologies = {t: self.top_k for t in terminologies}
        return idx.search_multi(entity_value, query_terminologies)

    # ------------------------------------------------------------------
    # Code selection
    # ------------------------------------------------------------------

    def select_best_code(
        self,
        candidates: Dict[str, List[Dict[str, Any]]],
        llm_selected: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Select the best code per terminology from candidates.

        Strategy:
        1. If llm_selected provides a code (after token extraction) that IS in
           the candidate set → use it.
        2. If llm_selected code is NOT in candidate set → reject (log warning).
           No fallback to top-1 — grounding enforcer must be strict.
        3. If no llm_selected → abstain for that terminology.

        Parameters
        ----------
        candidates : Dict[str, List[candidate_dict]]
        llm_selected : Dict[str, str] (optional)
            {terminology: code} as suggested by the LLM.

        Returns
        -------
        Dict[str, str]
            Grounded {terminology: code} mapping.
        """
        codes: Dict[str, str] = {}

        for terminology, cand_list in candidates.items():
            if not cand_list:
                continue

            candidate_codes: Set[str] = {c["code"] for c in cand_list}

            if llm_selected and terminology in llm_selected:
                raw_proposed = llm_selected[terminology]
                proposed = extract_code_token(raw_proposed)

                if proposed == "NONE":
                    # LLM explicitly abstained
                    logger.info(
                        "GROUNDING ABSTAIN: LLM abstained for %s.",
                        terminology,
                    )
                elif proposed in candidate_codes:
                    codes[terminology] = proposed
                else:
                    logger.warning(
                        "GROUNDING REJECTION: normalised code '%s' (raw: '%s') for %s "
                        "is not in candidate set %s.",
                        proposed, raw_proposed, terminology, candidate_codes,
                    )
                    # No fallback — strict grounding enforcer

        return codes

    # ------------------------------------------------------------------
    # Full field grounding
    # ------------------------------------------------------------------

    def ground_field(
        self,
        field_name: str,
        field_dict: Dict[str, Any],
        llm_codes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply grounding to a single field dict.

        1. Retrieve candidates for the field's extracted value.
        2. Select and validate codes.
        3. Attach grounded codes to the field dict.
        4. Attach candidate metadata for transparency.

        Parameters
        ----------
        field_name : str
        field_dict : Dict[str, Any]
            Extracted field (from LLM or heuristic).
        llm_codes : Dict[str, str] (optional)
            LLM-proposed codes for grounding validation.
        """
        value = field_dict.get("value")
        if not value or field_dict.get("state") in ("not_mentioned", "not_applicable"):
            return {**field_dict, "codes": {}, "grounding_candidates": {}}

        candidates = self.retrieve_candidates(field_name, value)
        grounded_codes = self.select_best_code(candidates, llm_codes)

        # Flatten candidate metadata for output transparency
        grounding_candidates = {
            t: [{"code": c["code"], "name": c["concept_name"], "score": round(c["score"], 4)}
                for c in cands]
            for t, cands in candidates.items()
        }

        return {
            **field_dict,
            "codes": grounded_codes,
            "grounding_candidates": grounding_candidates,
        }

    def ground_all_fields(
        self,
        extracted_fields: Dict[str, Any],
        llm_codes_per_field: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Apply grounding to all 21 fields.

        Parameters
        ----------
        extracted_fields : Dict[str, Any]
            {field_name: field_dict} from LLM extraction.
        llm_codes_per_field : Dict[str, Dict[str, str]] (optional)
            {field_name: {terminology: code}} — LLM's code proposals.

        Returns
        -------
        Dict[str, Any]
            Grounded fields with validated codes and candidate metadata.
        """
        grounded: Dict[str, Any] = {}
        llm_codes_per_field = llm_codes_per_field or {}

        for field_name, field_dict in extracted_fields.items():
            llm_codes = llm_codes_per_field.get(field_name)
            try:
                grounded[field_name] = self.ground_field(field_name, field_dict, llm_codes)
            except Exception as exc:
                logger.warning("Grounding failed for field '%s': %s", field_name, exc)
                grounded[field_name] = {**field_dict, "codes": {}, "grounding_candidates": {}}

        return grounded


# ---------------------------------------------------------------------------
# Schema cleanup: strip internal grounding_candidates before final output
# ---------------------------------------------------------------------------

def strip_grounding_metadata(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove grounding_candidates from field dicts (not part of final schema).
    Call this before writing the output JSON.
    """
    cleaned: Dict[str, Any] = {}
    for fname, fdict in fields.items():
        cleaned[fname] = {k: v for k, v in fdict.items() if k != "grounding_candidates"}
    return cleaned
