"""
pipeline.py  —  Pipeline A: Classical Healthcare NLP
=====================================================
Orchestrates all five stages:

  Stage 1  preprocessing   : section detection, text normalisation
  Stage 2  ner             : multi-model JSL NER
  Stage 3  assertion       : polarity / context classification
  Stage 4  resolution      : entity → medical codes (ICD-10, ICD-O-3, SNOMED)
  Stage 5  assembly        : structured field assembly → schema-compliant JSON

Modes of operation
------------------
LICENSED (JSL_LICENSE_PATH env var set and johnsnowlabs installed):
    Full JSL pipeline using pretrained Healthcare NLP models.

DEMO (JSL not available or license not set):
    Heuristic fallback pipeline using regex/rule-based extraction.
    Produces valid schema-compliant JSON for all 10 reports.
    Useful for CI, testing, and evaluation without a JSL license.

Configuration
-------------
Environment variables:
  JSL_LICENSE_PATH   : path to johnsnowlabs license JSON (required for licensed mode)
  JSL_OUTPUT_LEVEL   : logging verbosity ('WARN' / 'ERROR', default 'ERROR')
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve project root and add common to path
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "common"))
sys.path.insert(0, str(_HERE))

from schema import (  # noqa: E402
    PIPELINE_A,
    FIELD_NAMES,
    empty_output,
    make_field,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSL / Spark initialisation
# ---------------------------------------------------------------------------

_JSL_AVAILABLE = False
_spark = None


def _init_jsl() -> Optional[Any]:
    """
    Attempt to initialise a JSL-licensed Spark session.
    Returns the SparkSession or None if JSL is unavailable.
    """
    global _spark, _JSL_AVAILABLE
    if _spark is not None:
        return _spark

    license_path = os.environ.get("JSL_LICENSE_PATH")
    if not license_path:
        logger.warning(
            "JSL_LICENSE_PATH not set — running in DEMO (heuristic) mode. "
            "To use JSL models, export JSL_LICENSE_PATH=/path/to/license.json"
        )
        return None

    try:
        import johnsnowlabs as jsl
        jsl.settings.json_license_path = license_path
        jsl.install()

        import sparknlp_jsl
        _spark = sparknlp_jsl.start(
            license_keys_path=license_path,
            gpu=False,
        )
        _JSL_AVAILABLE = True
        logger.info("JSL Spark session started (version %s)", _spark.version)
        return _spark
    except Exception as exc:
        logger.error("Failed to initialise JSL: %s — falling back to DEMO mode.", exc)
        return None


# ---------------------------------------------------------------------------
# Heuristic / demo pipeline (no JSL dependency)
# ---------------------------------------------------------------------------

def _heuristic_extract(report_id: str, preprocessed: Dict[str, str]) -> Dict[str, Any]:
    """
    Rule-based extraction for demo mode.
    Uses regex patterns against section text to populate all 21 fields.
    """
    # Import assembly module helpers (regex-based)
    from stages.assembly import (
        _extract_tumor_size, _extract_laterality, _extract_ln_counts,
        _MARGIN_POS_RE, _MARGIN_NEG_RE,
        _LVI_POS_RE, _LVI_NEG_RE, _PNI_POS_RE, _PNI_NEG_RE,
        _MULTI_RE,
    )
    from stages.resolution import (
        _local_lookup, extract_tnm_stage, extract_ajcc_stage,
    )

    output = empty_output(report_id, PIPELINE_A)
    fields = output["fields"]

    full = preprocessed.get("full_text", "")
    clinical = preprocessed.get("CLINICAL_HISTORY", "")
    gross = preprocessed.get("GROSS_DESCRIPTION", "")
    microscopic = preprocessed.get("MICROSCOPIC_DESCRIPTION", "")
    final = preprocessed.get("FINAL_DIAGNOSIS", "")
    combined = microscopic + "\n" + final

    # ---- primary_site & laterality ----------------------------------------
    site_patterns = [
        (re.compile(r"(left|right)\s+(breast|upper\s+outer|upper\s+inner|lower\s+(?:outer|inner))\s*(?:quadrant)?", re.I), "breast"),
        (re.compile(r"(sigmoid\s+colon|rectum|cecum|colon)", re.I), "colon"),
        (re.compile(r"(right|left)\s+(upper|lower)\s+lobe", re.I), "lung"),
    ]
    for pat, organ in site_patterns:
        m = pat.search(clinical + " " + gross)
        if m:
            site_text = m.group(0)
            fields["primary_site"] = make_field(
                value=site_text, state="present", evidence=site_text,
                codes=_local_lookup(site_text, ["ICD-O-3", "ICD-10"])
            )
            lat = _extract_laterality(site_text)
            if lat:
                fields["laterality"] = make_field(value=lat, state="present", evidence=site_text)
            break

    if not fields["laterality"]["value"]:
        lat = _extract_laterality(clinical)
        fields["laterality"] = make_field(
            value=lat or None,
            state="present" if lat else "not_mentioned",
            evidence=lat,
        )

    # ---- histology_type ---------------------------------------------------
    hist_patterns = [
        re.compile(r"(invasive\s+ductal\s+carcinoma[^,.\n]*)", re.I),
        re.compile(r"(invasive\s+lobular\s+carcinoma[^,.\n]*)", re.I),
        re.compile(r"(adenocarcinoma[^,.\n]*)", re.I),
        re.compile(r"(squamous\s+cell\s+carcinoma[^,.\n]*)", re.I),
        re.compile(r"(DCIS|ductal\s+carcinoma\s+in\s+situ[^,.\n]*)", re.I),
    ]
    for pat in hist_patterns:
        m = pat.search(microscopic)
        if m:
            text = m.group(1).strip()
            fields["histology_type"] = make_field(
                value=text, state="present", evidence=text,
                codes=_local_lookup(text, ["ICD-O-3"])
            )
            break

    # ---- tumor_grade ------------------------------------------------------
    grade_pat = re.compile(
        r"(Nottingham\s+Grade\s+[123]|Grade\s+[123]|well[\s-]+differentiated|moderately[\s-]+differentiated|poorly[\s-]+differentiated)",
        re.I,
    )
    m = grade_pat.search(microscopic + " " + final)
    if m:
        text = m.group(1).strip()
        fields["tumor_grade"] = make_field(
            value=text, state="present", evidence=text,
            codes=_local_lookup(text, ["SNOMED"])
        )

    # ---- staging ----------------------------------------------------------
    tnm = extract_tnm_stage(final)
    ajcc = extract_ajcc_stage(final)
    if tnm or ajcc:
        pstage = " -- ".join(filter(None, [tnm, ajcc]))
        fields["pathologic_stage"] = make_field(value=pstage, state="present", evidence=pstage)

    c_tnm = extract_tnm_stage(clinical)
    c_ajcc = extract_ajcc_stage(clinical)
    if c_tnm or c_ajcc:
        cstage = " -- ".join(filter(None, [c_tnm, c_ajcc]))
        fields["clinical_stage"] = make_field(value=cstage, state="present", evidence=cstage)

    # ---- tumor_size -------------------------------------------------------
    size_info = _extract_tumor_size(gross or full)
    if size_info:
        val, unit = size_info
        fields["tumor_size"] = make_field(value=val, unit=unit, state="present",
                                          evidence=f"{val} {unit}")

    # ---- surgical_margins -------------------------------------------------
    if _MARGIN_NEG_RE.search(combined):
        m = _MARGIN_NEG_RE.search(combined)
        fields["surgical_margins"] = make_field(value="Negative", state="present",
                                                 evidence=m.group(0))
    elif _MARGIN_POS_RE.search(combined):
        m = _MARGIN_POS_RE.search(combined)
        fields["surgical_margins"] = make_field(value="Positive", state="present",
                                                 evidence=m.group(0))

    # ---- lymph nodes ------------------------------------------------------
    ln = _extract_ln_counts(combined)
    if ln:
        pos, total = ln
        fields["lymph_nodes_positive"] = make_field(value=pos, state="present",
                                                      evidence=f"{pos}/{total}")
        fields["lymph_nodes_examined"] = make_field(value=total, state="present",
                                                     evidence=f"{pos}/{total}")

    # ---- invasion ---------------------------------------------------------
    if _LVI_NEG_RE.search(combined):
        m = _LVI_NEG_RE.search(combined)
        fields["lymphovascular_invasion"] = make_field(value="Absent", state="absent",
                                                        evidence=m.group(0))
    elif _LVI_POS_RE.search(combined):
        m = _LVI_POS_RE.search(combined)
        fields["lymphovascular_invasion"] = make_field(value="Present", state="present",
                                                        evidence=m.group(0))

    if _PNI_NEG_RE.search(combined):
        m = _PNI_NEG_RE.search(combined)
        fields["perineural_invasion"] = make_field(value="Absent", state="absent",
                                                    evidence=m.group(0))
    elif _PNI_POS_RE.search(combined):
        m = _PNI_POS_RE.search(combined)
        fields["perineural_invasion"] = make_field(value="Present", state="present",
                                                    evidence=m.group(0))

    # ---- metastasis -------------------------------------------------------
    no_mets_pat = re.compile(r"\bno\s+(?:evidence\s+of\s+)?(?:distant\s+)?metastas", re.I)
    mets_pat = re.compile(r"\b(?:brain|liver|bone|lung|distant)\s+metastas", re.I)
    pm0_pat = re.compile(r"\bpM0\b", re.I)

    if pm0_pat.search(final) or no_mets_pat.search(combined):
        fields["distant_metastasis"] = make_field(value="Absent", state="absent",
                                                   evidence="No distant metastasis documented")
    elif mets_pat.search(combined):
        m = mets_pat.search(combined)
        fields["distant_metastasis"] = make_field(value="Present", state="present",
                                                   evidence=m.group(0))

    # ---- biomarkers -------------------------------------------------------
    biomarker_patterns: Dict[str, List[re.Pattern]] = {
        "er_status": [
            re.compile(r"ER\s*(?:status)?[\s:]+([^\n.]+)", re.I),
            re.compile(r"estrogen\s+receptor\s*[\s:]+([^\n.]+)", re.I),
        ],
        "pr_status": [
            re.compile(r"PR\s*(?:status)?[\s:]+([^\n.]+)", re.I),
            re.compile(r"progesterone\s+receptor\s*[\s:]+([^\n.]+)", re.I),
        ],
        "her2_status": [
            re.compile(r"HER2?\s*(?:status|score)?[\s:]+([^\n.]+)", re.I),
        ],
        "kras_mutation": [
            re.compile(r"KRAS\s*(?:mutation|status|codon)?[\s:]+([^\n.]+)", re.I),
        ],
        "egfr_mutation": [
            re.compile(r"EGFR\s*(?:mutation|deletion|status)?[\s:]+([^\n.]+)", re.I),
        ],
    }

    _positive_re = re.compile(r"\b(positive|present|\d\+|detected|mutant)\b", re.I)
    _negative_re = re.compile(r"\b(negative|absent|not\s+detected|wild.type|0%|1\+)\b", re.I)
    _uncertain_re = re.compile(r"\b(equivocal|borderline|pending|indeterminate)\b", re.I)

    for bfield, patterns in biomarker_patterns.items():
        for pat in patterns:
            m = pat.search(microscopic + "\n" + final)
            if m:
                val = m.group(1).strip()[:120]  # cap at 120 chars
                if _uncertain_re.search(val):
                    bstate = "uncertain"
                elif _negative_re.search(val):
                    bstate = "absent"
                elif _positive_re.search(val):
                    bstate = "present"
                else:
                    bstate = "present"
                codes = _local_lookup(bfield.split("_")[0], ["LOINC"])
                fields[bfield] = make_field(value=val, state=bstate, evidence=val, codes=codes)
                break

    # ---- procedure_type ---------------------------------------------------
    procedure_pat = re.compile(
        r"(mastectomy|colectomy|hemicolectomy|lobectomy|biopsy|resection"
        r"|excision|lumpectomy|sigmoidectomy)",
        re.I,
    )
    m = procedure_pat.search(clinical)
    if m:
        text = m.group(1).strip()
        # Try to get fuller procedure name from context
        start = max(0, m.start() - 30)
        context = clinical[start: m.end() + 30].strip()
        fields["procedure_type"] = make_field(
            value=context, state="present", evidence=context,
            codes=_local_lookup(text, ["SNOMED"])
        )

    # ---- prior_treatment --------------------------------------------------
    prior_pat = re.compile(
        r"(neoadjuvant\s+(?:chemotherapy|therapy)[^\n.]*|AC-T\s+regimen[^\n.]*"
        r"|(?:received|prior)\s+(?:chemo|radiation|endocrine|hormonal)[^\n.]*)",
        re.I,
    )
    m = prior_pat.search(clinical)
    if m:
        text = m.group(1).strip()
        fields["prior_treatment"] = make_field(value=text, state="present", evidence=text)
    elif re.search(r"\bno\s+prior\b|\bno\s+previous\b|\bno\s+prior\s+(?:surgery|treatment)\b", clinical, re.I):
        fields["prior_treatment"] = make_field(value="None reported", state="absent",
                                               evidence="No prior treatment documented")

    # ---- tumor_multiplicity -----------------------------------------------
    m = _MULTI_RE.search(full)
    if m:
        fields["tumor_multiplicity"] = make_field(value="Multiple", state="present",
                                                   evidence=m.group(0))
    else:
        fields["tumor_multiplicity"] = make_field(value="Single", state="absent",
                                                   evidence="No multiplicity cues detected")

    return output


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline_a(
    report_id: str,
    report_text: str,
    spark_session: Optional[Any] = None,
    ner_pipeline: Optional[Any] = None,
    assertion_pipeline: Optional[Any] = None,
    resolver_pipelines: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run Pipeline A on a single report.

    If JSL pipelines are provided, uses them; otherwise falls back to heuristic mode.

    Parameters
    ----------
    report_id : str
    report_text : str
    spark_session : SparkSession (optional)
    ner_pipeline : LightPipeline (optional)
    assertion_pipeline : LightPipeline (optional)
    resolver_pipelines : Dict[str, LightPipeline] (optional)

    Returns
    -------
    Dict[str, Any] — schema-compliant output
    """
    from stages.preprocessing import preprocess  # noqa

    preprocessed = preprocess(report_text)

    if ner_pipeline is not None:
        # ---- JSL Licensed Mode -----------------------------------------
        from stages.ner import run_ner  # noqa
        from stages.assertion import map_assertion_to_entities, heuristic_assertion  # noqa
        from stages.resolution import resolve_all  # noqa
        from stages.assembly import assemble_fields  # noqa

        entities = run_ner(ner_pipeline, preprocessed["full_text"])

        # Assertion
        if assertion_pipeline is not None:
            from stages.assertion import run_assertion  # noqa
            assertion_map = run_assertion(assertion_pipeline, preprocessed["full_text"])
            entities = map_assertion_to_entities(entities, assertion_map)
        else:
            for ent in entities:
                ent["assertion_state"] = heuristic_assertion(preprocessed["full_text"], ent)

        # Resolution
        rp = resolver_pipelines or {}
        entities = resolve_all(entities, rp)

        output = assemble_fields(report_id, preprocessed, entities)
        output["model_versions"] = {
            "ner": "ner_oncology_wip + ner_oncology_biomarker_wip + ner_oncology_tnm_wip",
            "assertion": "assertion_oncology_wip",
            "resolution": "sbiobertresolve_icd10cm_augmented_billable + sbiobertresolve_icdo",
            "mode": "licensed_jsl",
        }
    else:
        # ---- Heuristic Demo Mode ----------------------------------------
        output = _heuristic_extract(report_id, preprocessed)
        output["model_versions"] = {
            "mode": "heuristic_demo",
            "note": (
                "JSL license not configured. Set JSL_LICENSE_PATH to use "
                "pretrained Healthcare NLP models."
            ),
        }

    output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
    return output


def build_jsl_pipelines() -> tuple:
    """
    Build all JSL pipelines (NER, assertion, resolvers).
    Returns (spark, ner_pipeline, assertion_pipeline, resolver_pipelines) or
    (None, None, None, None) if JSL is not available.
    """
    spark = _init_jsl()
    if spark is None:
        return None, None, None, None

    from stages.ner import build_ner_pipeline  # noqa
    from stages.assertion import build_assertion_pipeline  # noqa
    from stages.resolution import build_resolver_pipelines  # noqa

    logger.info("Building NER pipeline...")
    ner = build_ner_pipeline(spark)
    logger.info("Building assertion pipeline...")
    assr = build_assertion_pipeline(spark, None)
    logger.info("Building resolver pipelines...")
    resolvers = build_resolver_pipelines(spark)

    return spark, ner, assr, resolvers
