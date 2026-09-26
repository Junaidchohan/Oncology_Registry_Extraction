"""
schema.py
=========
Shared output JSON schema for the Oncology Registry Extraction project.

All pipeline outputs MUST conform to this schema.
Both Pipeline A (Classical NLP) and Pipeline B (LLM + Retrieval) write JSON
files that validate against OUTPUT_JSON_SCHEMA.

21 extraction fields:
  primary_site, histology_type, tumor_grade, clinical_stage, pathologic_stage,
  tumor_size, laterality, surgical_margins, lymph_nodes_examined,
  lymph_nodes_positive, lymphovascular_invasion, perineural_invasion,
  distant_metastasis, er_status, pr_status, her2_status, kras_mutation,
  egfr_mutation, procedure_type, prior_treatment, tumor_multiplicity

Field state vocabulary:
  present | absent | uncertain | not_mentioned | not_applicable | ambiguous
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_A: str = "pipeline_a_classical"
PIPELINE_B: str = "pipeline_b_llm_retrieval"
VALID_PIPELINES: frozenset[str] = frozenset({PIPELINE_A, PIPELINE_B})

FIELD_NAMES: List[str] = [
    "specimen",
    "procedure",
    "primary_tumor_site",
    "laterality",
    "histological_type",
    "tumor_behavior",
    "tumor_grade",
    "tumor_size",
    "tumor_focality",
    "tumor_extension",
    "lymphovascular_invasion",
    "perineural_invasion",
    "surgical_margins",
    "lymph_nodes_examined",
    "positive_lymph_nodes",
    "pathologic_t",
    "pathologic_n",
    "pathologic_m",
    "biomarkers",
    "anticancer_medication",
]

VALID_STATES: frozenset[str] = frozenset({
    "present",
    "not_mentioned",
    "negative",
    "not_assessed",
    "not_applicable",
    "ambiguous",
})

# ---------------------------------------------------------------------------
# Default / empty field
# ---------------------------------------------------------------------------

EMPTY_FIELD: Dict[str, Any] = {
    "value": None,
    "unit": None,
    "state": "not_mentioned",
    "evidence": None,
    "span": None,
    "codes": {},
}


def make_field(
    value: Optional[str] = None,
    unit: Optional[str] = None,
    state: str = "not_mentioned",
    evidence: Optional[str] = None,
    span: Optional[List[int]] = None,
    codes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create a schema-compliant field dict."""
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state '{state}'. Must be one of {sorted(VALID_STATES)}")
    return {
        "value": value,
        "unit": unit,
        "state": state,
        "evidence": evidence,
        "span": span,
        "codes": codes or {},
    }


def empty_output(report_id: str, pipeline: str) -> Dict[str, Any]:
    """Return a schema-compliant empty extraction output."""
    if pipeline not in VALID_PIPELINES:
        raise ValueError(f"Invalid pipeline '{pipeline}'.")
    return {
        "report_id": report_id,
        "pipeline": pipeline,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_versions": {},
        "fields": {f: copy.deepcopy(EMPTY_FIELD) for f in FIELD_NAMES},
    }


# ---------------------------------------------------------------------------
# JSON Schema (Draft-07) for jsonschema validation
# ---------------------------------------------------------------------------

_FIELD_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["value", "unit", "state", "evidence", "span", "codes"],
    "additionalProperties": False,
    "properties": {
        "value": {"type": ["string", "null"]},
        "unit": {"type": ["string", "null"]},
        "state": {"type": "string", "enum": sorted(VALID_STATES)},
        "evidence": {"type": ["string", "null"]},
        "span": {
            "oneOf": [
                {"type": "null"},
                {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2,
                },
            ]
        },
        "codes": {"type": "object", "additionalProperties": {"type": "string"}},
    },
}

OUTPUT_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "OncologyExtractionOutput",
    "description": (
        "Schema for structured extraction outputs from oncology pathology reports. "
        "Produced by Pipeline A (Classical NLP) and Pipeline B (LLM + Retrieval)."
    ),
    "type": "object",
    "required": ["report_id", "pipeline", "run_timestamp", "model_versions", "fields"],
    "additionalProperties": False,
    "properties": {
        "report_id": {
            "type": "string",
            "pattern": "^report_[0-9]{3}$",
            "description": "Report identifier, e.g. report_001",
        },
        "pipeline": {
            "type": "string",
            "enum": sorted(VALID_PIPELINES),
            "description": "Pipeline that produced this output",
        },
        "run_timestamp": {
            "type": ["string", "null"],
            "description": "ISO-8601 UTC timestamp of when the pipeline ran",
        },
        "model_versions": {
            "type": "object",
            "description": "Map of model/component name to version or identifier",
            "additionalProperties": {"type": "string"},
        },
        "fields": {
            "type": "object",
            "description": "Extracted oncology fields",
            "required": FIELD_NAMES,
            "additionalProperties": False,
            "properties": {
                **{name: _FIELD_SCHEMA for name in FIELD_NAMES if name not in ("biomarkers", "anticancer_medication")},
                "biomarkers": {"type": "array"},
                "anticancer_medication": {"type": "array"}
            },
        },
    },
}

# ---------------------------------------------------------------------------
# Field-level descriptions (for prompts and documentation)
# ---------------------------------------------------------------------------

FIELD_DESCRIPTIONS: Dict[str, str] = {
    "primary_site": "Primary anatomical site of the tumor (e.g., 'Left breast, upper outer quadrant')",
    "histology_type": "Histological type of the tumor (e.g., 'Invasive ductal carcinoma, NST')",
    "tumor_grade": "Histological grade (e.g., 'Nottingham Grade 2', 'Well differentiated')",
    "clinical_stage": "Clinical TNM stage assigned pre-operatively (e.g., 'cT2a cN2 cM1b -- Stage IVA')",
    "pathologic_stage": "Pathologic TNM stage assigned post-operatively (e.g., 'pT2 pN1a pM0 -- Stage IIB')",
    "tumor_size": "Greatest dimension of the tumor (numeric value only; unit in 'unit' field)",
    "laterality": "Side of body (Left / Right / Bilateral / Not applicable)",
    "surgical_margins": "Status of resection margins (e.g., 'Negative (closest 2.0 cm)')",
    "lymph_nodes_examined": "Total number of lymph nodes examined (integer as string)",
    "lymph_nodes_positive": "Number of lymph nodes positive for metastasis (integer as string)",
    "lymphovascular_invasion": "Lymphovascular invasion status (Present / Absent)",
    "perineural_invasion": "Perineural invasion status (Present / Absent)",
    "distant_metastasis": "Distant metastasis status with site if known (e.g., 'Present (brain)')",
    "er_status": "Estrogen receptor status (e.g., 'Positive (Allred 8/8, >95%, 3+)')",
    "pr_status": "Progesterone receptor status (e.g., 'Positive (Allred 6/8, 60%, 2+)')",
    "her2_status": "HER2/neu status (e.g., 'Negative (1+ IHC)', 'Positive (3+ IHC)')",
    "kras_mutation": "KRAS mutation status and variant (e.g., 'Mutant (p.G12D)' or 'Wild-type')",
    "egfr_mutation": "EGFR mutation status and variant (e.g., 'Exon 19 deletion (Del E746-A750)')",
    "procedure_type": "Surgical or biopsy procedure type (e.g., 'Modified radical mastectomy')",
    "prior_treatment": "Any prior oncologic treatment (e.g., 'Neoadjuvant chemotherapy (AC-T, 6 cycles)')",
    "tumor_multiplicity": "Whether multiple synchronous lesions are present (Single / Multifocal / Multicentric)",
}
