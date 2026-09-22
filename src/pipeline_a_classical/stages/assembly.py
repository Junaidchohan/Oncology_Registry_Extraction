"""
assembly.py
===========
Stage 5: Structured Field Assembly

Maps enriched entities (NER label + assertion state + codes) to the 21
assessment fields defined in src/common/schema.py.

Entity label → field routing table:
┌─────────────────────────────────┬────────────────────────────────────────────┐
│ NER Label                       │ Target Field(s)                            │
├─────────────────────────────────┼────────────────────────────────────────────┤
│ Cancer_Dx, Histological_Type    │ histology_type, primary_site               │
│ Tumor_Finding                   │ histology_type (secondary)                 │
│ Anatomical_Site, Site_*         │ primary_site, laterality                   │
│ Grade                           │ tumor_grade                                │
│ Staging, Staging_TNM            │ pathologic_stage, clinical_stage           │
│ Tumor_T_Staging                 │ pathologic_stage (component)               │
│ Node_N_Staging                  │ lymph_nodes_positive (component)           │
│ Metastasis_M_Staging            │ distant_metastasis                         │
│ Tumor_Size                      │ tumor_size                                 │
│ Invasion                        │ lymphovascular_invasion / perineural_inv.  │
│ Lymph_Node                      │ lymph_nodes_examined / lymph_nodes_positive│
│ Metastasis                      │ distant_metastasis                         │
│ Biomarker (ER)                  │ er_status                                  │
│ Biomarker (PR)                  │ pr_status                                  │
│ Biomarker (HER2)                │ her2_status                                │
│ Oncogene (KRAS)                 │ kras_mutation                              │
│ Oncogene (EGFR)                 │ egfr_mutation                              │
│ Cancer_Surgery                  │ procedure_type                             │
│ Chemotherapy, Hormonal_Therapy  │ prior_treatment                            │
│ Response_To_Treatment           │ prior_treatment                            │
└─────────────────────────────────┴────────────────────────────────────────────┘

Fields that cannot be reliably extracted from NER alone (multi-entity):
  - laterality     : extracted from anatomical site text ("left"/"right")
  - surgical_margins : detected from regex patterns in FINAL_DIAGNOSIS section
  - lymph_nodes_examined / positive : extracted from "X/Y" ratio patterns
  - tumor_multiplicity : detected from multiplicity cues
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import schema
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from schema import FIELD_NAMES, VALID_STATES, make_field, empty_output, PIPELINE_A  # noqa

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

# Tumor size: e.g. "2.3 cm", "15 mm", "2.3 x 2.1 x 1.8 cm"
_SIZE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?)?\s*(cm|mm)\b",
    re.IGNORECASE,
)

# LN ratio: e.g. "4/18", "3/24", "0/12"
_LN_RATIO_RE = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")

# Laterality keywords
_LEFT_RE = re.compile(r"\b(left|ipsilateral)\b", re.IGNORECASE)
_RIGHT_RE = re.compile(r"\b(right|contralateral)\b", re.IGNORECASE)
_BILATERAL_RE = re.compile(r"\b(bilateral|bilaterally)\b", re.IGNORECASE)

# Margin patterns
_MARGIN_POS_RE = re.compile(
    r"\b(margin[s]?\s*(?:are\s*)?(?:positive|involved|close|at\s*margin)|CRM\s*:\s*positive|tumor\s*at\s*(?:inked|margin))\b",
    re.IGNORECASE,
)
_MARGIN_NEG_RE = re.compile(
    r"\b(margin[s]?\s*(?:are\s*)?(?:negative|clear|free|uninvolved)|all\s*(?:surgical\s*)?margin[s]?\s*(?:are\s*)?negative)\b",
    re.IGNORECASE,
)

# Invasion keywords
_LVI_POS_RE = re.compile(r"\b(lymphovascular\s*invasion\s*(?:is\s*)?(?:identified|present|noted))\b", re.IGNORECASE)
_LVI_NEG_RE = re.compile(r"\b(no\s*lymphovascular\s*invasion|lymphovascular\s*invasion\s*(?:is\s*)?(?:absent|not\s*identified|not\s*seen))\b", re.IGNORECASE)
_PNI_POS_RE = re.compile(r"\b(perineural\s*invasion\s*(?:is\s*)?(?:identified|present|noted))\b", re.IGNORECASE)
_PNI_NEG_RE = re.compile(r"\b(no\s*perineural\s*invasion|perineural\s*invasion\s*(?:is\s*)?(?:absent|not\s*identified|not\s*seen))\b", re.IGNORECASE)

# Multiplicity
_MULTI_RE = re.compile(
    r"\b(multifocal|multicentric|satellite\s*nodule|multiple\s*lesion[s]?|synchronous|two\s*(?:distinct|separate)\s*(?:lesion[s]?|mass(?:es)?)|lesion\s*[AB])\b",
    re.IGNORECASE,
)

# Biomarker keywords
_BIOMARKER_KEYWORDS: Dict[str, str] = {
    "er": "er_status",
    "estrogen receptor": "er_status",
    "pr": "pr_status",
    "progesterone receptor": "pr_status",
    "pgr": "pr_status",
    "her2": "her2_status",
    "her-2": "her2_status",
    "erbb2": "her2_status",
    "kras": "kras_mutation",
    "egfr": "egfr_mutation",
}

_LATERALITY_RE_MAP = {
    "Left": _LEFT_RE,
    "Right": _RIGHT_RE,
    "Bilateral": _BILATERAL_RE,
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _first_match(pattern: re.Pattern, text: str) -> Optional[re.Match]:
    return pattern.search(text)


def _extract_laterality(site_text: str) -> Optional[str]:
    for label, pat in _LATERALITY_RE_MAP.items():
        if pat.search(site_text):
            return label
    return None


def _extract_tumor_size(text: str) -> Optional[tuple]:
    """Return (value_str, unit) or None."""
    m = _SIZE_RE.search(text)
    if m:
        return m.group(1), m.group(2).lower()
    return None


def _extract_ln_counts(text: str) -> Optional[tuple]:
    """Extract (positive, examined) from first LN ratio found."""
    m = _LN_RATIO_RE.search(text)
    if m:
        return m.group(1), m.group(2)
    return None


def _infer_biomarker_field(entity_text: str) -> Optional[str]:
    """Map entity text to a biomarker field name."""
    lower = entity_text.lower()
    for keyword, field in _BIOMARKER_KEYWORDS.items():
        if keyword in lower:
            return field
    return None


# ---------------------------------------------------------------------------
# Core assembly function
# ---------------------------------------------------------------------------

def assemble_fields(
    report_id: str,
    preprocessed: Dict[str, str],
    entities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Assemble a schema-compliant output dict from NER+assertion+resolution entities.

    Parameters
    ----------
    report_id : str
    preprocessed : Dict[str, str]
        Output of preprocessing.preprocess() — {section_name: section_text}
    entities : List[Dict[str, Any]]
        Enriched entity list from resolution.resolve_all()

    Returns
    -------
    Dict[str, Any]
        Schema-compliant output dict (without run_timestamp/model_versions, filled by pipeline.py)
    """
    output = empty_output(report_id, PIPELINE_A)
    fields = output["fields"]

    full_text = preprocessed.get("full_text", "")
    microscopic = preprocessed.get("MICROSCOPIC_DESCRIPTION", "")
    final_diag = preprocessed.get("FINAL_DIAGNOSIS", "")
    clinical = preprocessed.get("CLINICAL_HISTORY", "")
    gross = preprocessed.get("GROSS_DESCRIPTION", "")

    combined_text = "\n".join([microscopic, final_diag])

    # -----------------------------------------------------------------------
    # Entity-driven field population
    # -----------------------------------------------------------------------

    primary_site_candidates: List[Dict[str, Any]] = []
    histology_candidates: List[Dict[str, Any]] = []
    staging_candidates: List[Dict[str, Any]] = []
    treatment_candidates: List[Dict[str, Any]] = []
    procedure_candidates: List[Dict[str, Any]] = []

    for ent in entities:
        label = ent["label"]
        text = ent["text"]
        state = ent.get("assertion_state", "present")
        begin = ent.get("begin", None)
        end = ent.get("end", None)
        span = [begin, end] if begin is not None and end is not None else None
        codes = ent.get("codes", {})

        # ---- primary_site ------------------------------------------------
        if label in ("Anatomical_Site", "Site_Breast", "Site_Lung",
                     "Site_Liver", "Site_Lymph_Node", "Site_Other"):
            primary_site_candidates.append(ent)

        # ---- histology_type ----------------------------------------------
        if label in ("Cancer_Dx", "Histological_Type", "Tumor_Finding"):
            histology_candidates.append(ent)
            if state == "present" and not fields["histology_type"]["value"]:
                fields["histology_type"] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

        # ---- tumor_grade -------------------------------------------------
        if label == "Grade":
            if not fields["tumor_grade"]["value"]:
                fields["tumor_grade"] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

        # ---- staging -----------------------------------------------------
        if label in ("Staging", "Staging_TNM"):
            staging_candidates.append(ent)
            # Classify as pathologic vs clinical based on prefix
            if re.search(r"\b[ycr]?p[TN]", text, re.I):
                if not fields["pathologic_stage"]["value"]:
                    fields["pathologic_stage"] = make_field(
                        value=text, state=state, evidence=text, span=span, codes=codes
                    )
            elif re.search(r"\bc[TN]", text, re.I):
                if not fields["clinical_stage"]["value"]:
                    fields["clinical_stage"] = make_field(
                        value=text, state=state, evidence=text, span=span, codes=codes
                    )

        # ---- tumor_size --------------------------------------------------
        if label == "Tumor_Size":
            size_info = _extract_tumor_size(text)
            if size_info and not fields["tumor_size"]["value"]:
                val, unit = size_info
                fields["tumor_size"] = make_field(
                    value=val, unit=unit, state=state, evidence=text, span=span
                )

        # ---- lymph_nodes -------------------------------------------------
        if label == "Lymph_Node":
            ln = _extract_ln_counts(text)
            if ln:
                pos, total = ln
                if not fields["lymph_nodes_positive"]["value"]:
                    fields["lymph_nodes_positive"] = make_field(
                        value=pos, state=state, evidence=text, span=span
                    )
                if not fields["lymph_nodes_examined"]["value"]:
                    fields["lymph_nodes_examined"] = make_field(
                        value=total, state=state, evidence=text, span=span
                    )

        # ---- metastasis --------------------------------------------------
        if label in ("Metastasis", "Metastasis_M_Staging"):
            if not fields["distant_metastasis"]["value"]:
                fields["distant_metastasis"] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

        # ---- biomarkers --------------------------------------------------
        if label in ("Biomarker", "Oncogene"):
            biomarker_field = _infer_biomarker_field(text)
            if biomarker_field and not fields[biomarker_field]["value"]:
                fields[biomarker_field] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

        # ---- procedure_type ----------------------------------------------
        if label in ("Cancer_Surgery",):
            procedure_candidates.append(ent)
            if not fields["procedure_type"]["value"]:
                fields["procedure_type"] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

        # ---- prior_treatment ---------------------------------------------
        if label in ("Chemotherapy", "Hormonal_Therapy", "Immunotherapy",
                     "Radiation", "Response_To_Treatment"):
            treatment_candidates.append(ent)
            if not fields["prior_treatment"]["value"]:
                fields["prior_treatment"] = make_field(
                    value=text, state=state, evidence=text, span=span, codes=codes
                )

    # -----------------------------------------------------------------------
    # Primary site: prefer the most specific site entity
    # -----------------------------------------------------------------------
    if primary_site_candidates:
        # Prefer entities with "present" state; choose longest text (most specific)
        present_sites = [e for e in primary_site_candidates if e.get("assertion_state") == "present"]
        best = max(present_sites or primary_site_candidates, key=lambda e: len(e["text"]))
        fields["primary_site"] = make_field(
            value=best["text"],
            state=best.get("assertion_state", "present"),
            evidence=best["text"],
            span=[best.get("begin"), best.get("end")] if best.get("begin") is not None else None,
            codes=best.get("codes", {}),
        )
        # Laterality
        lat = _extract_laterality(best["text"])
        if lat and not fields["laterality"]["value"]:
            fields["laterality"] = make_field(value=lat, state="present", evidence=best["text"])

    # -----------------------------------------------------------------------
    # Rule-based extraction for fields not well-covered by NER
    # -----------------------------------------------------------------------

    # Tumor size (from text if NER missed it)
    if not fields["tumor_size"]["value"]:
        size_info = _extract_tumor_size(gross or full_text)
        if size_info:
            val, unit = size_info
            fields["tumor_size"] = make_field(
                value=val, unit=unit, state="present",
                evidence=f"Extracted from gross description: {val} {unit}"
            )

    # Laterality (from full text if not already set)
    if not fields["laterality"]["value"]:
        lat = _extract_laterality(clinical + " " + gross)
        if lat:
            fields["laterality"] = make_field(value=lat, state="present",
                                               evidence="Laterality inferred from report text")
        else:
            fields["laterality"] = make_field(state="not_applicable")

    # Surgical margins
    if not fields["surgical_margins"]["value"]:
        if _MARGIN_POS_RE.search(combined_text):
            m = _MARGIN_POS_RE.search(combined_text)
            fields["surgical_margins"] = make_field(
                value="Positive", state="present", evidence=m.group(0)
            )
        elif _MARGIN_NEG_RE.search(combined_text):
            m = _MARGIN_NEG_RE.search(combined_text)
            fields["surgical_margins"] = make_field(
                value="Negative", state="present", evidence=m.group(0)
            )

    # Lymphovascular invasion
    if not fields["lymphovascular_invasion"]["value"]:
        if _LVI_NEG_RE.search(combined_text):
            m = _LVI_NEG_RE.search(combined_text)
            fields["lymphovascular_invasion"] = make_field(
                value="Absent", state="absent", evidence=m.group(0)
            )
        elif _LVI_POS_RE.search(combined_text):
            m = _LVI_POS_RE.search(combined_text)
            fields["lymphovascular_invasion"] = make_field(
                value="Present", state="present", evidence=m.group(0)
            )

    # Perineural invasion
    if not fields["perineural_invasion"]["value"]:
        if _PNI_NEG_RE.search(combined_text):
            m = _PNI_NEG_RE.search(combined_text)
            fields["perineural_invasion"] = make_field(
                value="Absent", state="absent", evidence=m.group(0)
            )
        elif _PNI_POS_RE.search(combined_text):
            m = _PNI_POS_RE.search(combined_text)
            fields["perineural_invasion"] = make_field(
                value="Present", state="present", evidence=m.group(0)
            )

    # Lymph nodes from ratio pattern (final diagnosis or microscopic)
    if not fields["lymph_nodes_examined"]["value"] or not fields["lymph_nodes_positive"]["value"]:
        ln = _extract_ln_counts(combined_text)
        if ln:
            pos, total = ln
            if not fields["lymph_nodes_positive"]["value"]:
                fields["lymph_nodes_positive"] = make_field(
                    value=pos, state="present", evidence=f"{pos}/{total} LN ratio"
                )
            if not fields["lymph_nodes_examined"]["value"]:
                fields["lymph_nodes_examined"] = make_field(
                    value=total, state="present", evidence=f"{pos}/{total} LN ratio"
                )

    # Tumor multiplicity
    if not fields["tumor_multiplicity"]["value"]:
        m = _MULTI_RE.search(full_text)
        if m:
            fields["tumor_multiplicity"] = make_field(
                value="Multiple", state="present", evidence=m.group(0)
            )
        else:
            fields["tumor_multiplicity"] = make_field(
                value="Single", state="absent", evidence="No multiplicity cues detected"
            )

    # Staging from final diagnosis text patterns
    if not fields["pathologic_stage"]["value"]:
        from stages.resolution import extract_tnm_stage, extract_ajcc_stage  # noqa
        tnm = extract_tnm_stage(final_diag)
        ajcc = extract_ajcc_stage(final_diag)
        if tnm or ajcc:
            stage_val = " -- ".join(filter(None, [tnm, ajcc]))
            fields["pathologic_stage"] = make_field(
                value=stage_val, state="present", evidence=stage_val
            )

    if not fields["clinical_stage"]["value"]:
        from stages.resolution import extract_ajcc_stage  # noqa
        ajcc = extract_ajcc_stage(clinical)
        if ajcc:
            fields["clinical_stage"] = make_field(
                value=ajcc, state="present", evidence=ajcc
            )

    return output
