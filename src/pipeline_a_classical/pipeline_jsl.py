"""
pipeline_jsl.py  --  Pipeline A: Real JSL Healthcare NLP (spark-nlp-jsl 5.4.0)
===============================================================================
Replaces the previous LLM-mimicked implementation with genuine John Snow Labs
Healthcare NLP annotators.

Stage chain
-----------
1.  DocumentAssembler
2.  SentenceDetectorDLModel    (sentence_detector_dl_healthcare)
3.  Tokenizer
4.  WordEmbeddingsModel        (embeddings_clinical)
5a. MedicalNerModel            (ner_oncology_wip)
5b. MedicalNerModel            (ner_oncology_biomarker_wip)
5c. MedicalNerModel            (ner_oncology_tnm_wip)
    NerConverterInternal       (for each NER model)
    ChunkMergeApproach         (merge + deduplicate)
6.  AssertionDLModel           (assertion_oncology_wip)
7.  RelationExtractionModel    (re_oncology_wip)
    PerceptronModel (POS)  + DependencyParserModel  (required by RE)
8a. SentenceEntityResolverModel (sbiobertresolve_icd10cm_augmented_billable)
8b. SentenceEntityResolverModel (sbiobertresolve_icdo)
    BertSentenceEmbeddings     (sbiobert_base_cased_mli)
    Chunk2Doc                  -- adaptor for sentence embeddings
9.  Field assembly into 21-field schema (src/common/schema.py)

Scope-down notes
----------------
- embeddings_clinical (200-d GloVe) for NER/assertion.
- sbiobert_base_cased_mli exclusively for entity resolution.
- If re_oncology_wip unavailable, RE stage is skipped (logged as warning).
- Evidence spans from JSL chunk.begin / chunk.end offsets.
- Tumor size normalised to millimetres.
- pM0 is NEVER inferred from absence of distant-metastasis info.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
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
from stages.preprocessing import preprocess  # noqa: E402
from stages.assembly import (               # noqa: E402
    _extract_tumor_size, _extract_laterality, _extract_ln_counts,
    _MARGIN_POS_RE, _MARGIN_NEG_RE,
    _LVI_POS_RE, _LVI_NEG_RE,
    _PNI_POS_RE, _PNI_NEG_RE,
    _MULTI_RE, _infer_biomarker_field,
)
from stages.resolution import extract_tnm_stage, extract_ajcc_stage  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSL model names
# ---------------------------------------------------------------------------
EMBEDDINGS_MODEL = "embeddings_clinical"
SENT_EMBEDDINGS  = "sbiobert_base_cased_mli"
SD_MODEL         = "sentence_detector_dl_healthcare"
NER_MODELS = [
    ("ner_oncology_wip",           "ner_onc"),
    ("ner_oncology_biomarker_wip", "ner_bio"),
    ("ner_oncology_tnm_wip",       "ner_tnm"),
]
ASSERTION_MODEL = "assertion_oncology_wip"
RE_MODEL        = "re_oncology_wip"
RESOLVER_ICD10  = "sbiobertresolve_icd10cm"
RESOLVER_ICDO   = "sbiobertresolve_icdo_base"

# ---------------------------------------------------------------------------
# Assertion label to schema state
# ---------------------------------------------------------------------------
_ASSERTION_STATE: Dict[str, str] = {
    "Present":                      "present",
    "Absent":                       "absent",
    "Possible":                     "uncertain",
    "Conditional":                  "uncertain",
    "Hypothetical":                 "uncertain",
    "Associated_with_someone_else": "not_mentioned",
}

# ---------------------------------------------------------------------------
# Build the full JSL pipeline
# ---------------------------------------------------------------------------

def build_full_pipeline(spark: Any) -> Any:
    """
    Build and return a fitted Spark NLP PipelineModel.
    Downloads pretrained models on first call (~1-2 GB total).
    """
    from sparknlp.base import DocumentAssembler, Pipeline as SparkPipeline
    from sparknlp.annotator import (
        SentenceDetectorDLModel, Tokenizer, WordEmbeddingsModel,
        BertSentenceEmbeddings, PerceptronModel, DependencyParserModel,
    )
    from sparknlp_jsl.annotator import (
        MedicalNerModel, NerConverterInternal, ChunkMergeApproach,
        AssertionDLModel, RelationExtractionModel,
        SentenceEntityResolverModel, Chunk2Doc,
    )

    logger.info("Stage 1-3: DocumentAssembler + SentenceDetector + Tokenizer")
    doc_assembler = (
        DocumentAssembler()
        .setInputCol("text")
        .setOutputCol("document")
    )
    sentence_detector = (
        SentenceDetectorDLModel
        .pretrained(SD_MODEL, "en", "clinical/models")
        .setInputCols(["document"])
        .setOutputCol("sentence")
    )
    tokenizer = (
        Tokenizer()
        .setInputCols(["sentence"])
        .setOutputCol("token")
    )

    logger.info("Stage 4: WordEmbeddings: %s", EMBEDDINGS_MODEL)
    embeddings = (
        WordEmbeddingsModel
        .pretrained(EMBEDDINGS_MODEL, "en", "clinical/models")
        .setInputCols(["sentence", "token"])
        .setOutputCol("embeddings")
    )

    stages = [doc_assembler, sentence_detector, tokenizer, embeddings]
    chunk_cols = []

    # Stage 5: Multiple NER models (all share same embeddings)
    for model_name, col_prefix in NER_MODELS:
        logger.info("Stage 5: NER model: %s", model_name)
        ner = (
            MedicalNerModel
            .pretrained(model_name, "en", "clinical/models")
            .setInputCols(["sentence", "token", "embeddings"])
            .setOutputCol(f"{col_prefix}_tags")
        )
        converter = (
            NerConverterInternal()
            .setInputCols(["sentence", "token", f"{col_prefix}_tags"])
            .setOutputCol(f"{col_prefix}_chunks")
        )
        stages.extend([ner, converter])
        chunk_cols.append(f"{col_prefix}_chunks")

    logger.info("Stage 5c: ChunkMerge")
    chunk_merge = (
        ChunkMergeApproach()
        .setInputCols(chunk_cols)
        .setOutputCol("merged_chunk")
    )
    stages.append(chunk_merge)

    # Stage 6: Assertion
    logger.info("Stage 6: Assertion: %s", ASSERTION_MODEL)
    assertion = (
        AssertionDLModel
        .pretrained(ASSERTION_MODEL, "en", "clinical/models")
        .setInputCols(["sentence", "merged_chunk", "embeddings"])
        .setOutputCol("assertion")
    )
    stages.append(assertion)

    # Stage 7: Relation Extraction (optional -- skip if model unavailable)
    try:
        logger.info("Stage 7: POS tagger for RE")
        pos = (
            PerceptronModel
            .pretrained("pos_clinical", "en", "clinical/models")
            .setInputCols(["sentence", "token"])
            .setOutputCol("pos")
        )
        logger.info("Stage 7: Dependency Parser")
        dep = (
            DependencyParserModel
            .pretrained("dependency_conllu", "en")
            .setInputCols(["sentence", "pos", "token"])
            .setOutputCol("dependencies")
        )
        logger.info("Stage 7: RE model: %s", RE_MODEL)
        re_model = (
            RelationExtractionModel
            .pretrained(RE_MODEL, "en", "clinical/models")
            .setInputCols(["embeddings", "pos", "merged_chunk", "dependencies"])
            .setOutputCol("relations")
            .setRelationPairs([
                "Biomarker-Biomarker_Result",
                "Tumor_Finding-Anatomical_Site",
                "Tumor_Finding-Tumor_Size",
            ])
        )
        stages.extend([pos, dep, re_model])
        logger.info("RE stage added successfully.")
    except Exception as exc:
        logger.warning("RE model unavailable (%s) -- skipping RE stage.", exc)

    # Stage 8: Resolvers (require Bert sentence embeddings)
    logger.info("Stage 8: Chunk2Doc + BertSentenceEmbeddings: %s", SENT_EMBEDDINGS)
    chunk2doc = (
        Chunk2Doc()
        .setInputCols(["merged_chunk"])
        .setOutputCol("chunk_doc")
    )
    sbert = (
        BertSentenceEmbeddings
        .pretrained(SENT_EMBEDDINGS, "en", "clinical/models")
        .setInputCols(["chunk_doc"])
        .setOutputCol("chunk_embeddings")
        .setCaseSensitive(False)
    )
    stages.extend([chunk2doc, sbert])

    logger.info("Stage 8a: ICD-10-CM resolver: %s", RESOLVER_ICD10)
    resolver_icd10 = (
        SentenceEntityResolverModel
        .pretrained(RESOLVER_ICD10, "en", "clinical/models")
        .setInputCols(["chunk_embeddings"])
        .setOutputCol("icd10_resolution")
        .setDistanceFunction("EUCLIDEAN")
    )
    stages.append(resolver_icd10)

    logger.info("Stage 8b: ICD-O-3 resolver: %s", RESOLVER_ICDO)
    resolver_icdo = (
        SentenceEntityResolverModel
        .pretrained(RESOLVER_ICDO, "en", "clinical/models")
        .setInputCols(["chunk_embeddings"])
        .setOutputCol("icdo_resolution")
        .setDistanceFunction("EUCLIDEAN")
    )
    stages.append(resolver_icdo)

    logger.info("Fitting pipeline on empty DataFrame ...")
    pipeline = SparkPipeline(stages=stages)
    empty_df = spark.createDataFrame([[""]]).toDF("text")
    model = pipeline.fit(empty_df)
    logger.info("Pipeline fitted and ready.")
    return model


def make_light_pipeline(model: Any) -> Any:
    from sparknlp.base import LightPipeline
    return LightPipeline(model)


# ---------------------------------------------------------------------------
# Annotate a single report
# ---------------------------------------------------------------------------

def annotate(light_pipeline: Any, text: str) -> Dict[str, Any]:
    """Run the full pipeline on one report text."""
    results = light_pipeline.fullAnnotate(text)[0]

    # Merged entity chunks
    chunks = []
    for chunk in results.get("merged_chunk", []):
        meta = chunk.metadata
        chunks.append({
            "text":       chunk.result,
            "label":      meta.get("entity", "UNKNOWN"),
            "begin":      chunk.begin,
            "end":        chunk.end,
            "confidence": float(meta.get("confidence", 0.0)),
        })

    # Assertion (1-to-1 with merged_chunk)
    assertion_anns = results.get("assertion", [])
    for i, chunk in enumerate(chunks):
        if i < len(assertion_anns):
            raw = assertion_anns[i].result
        else:
            raw = "Present"
        chunk["assertion_state"] = _ASSERTION_STATE.get(raw, "present")

    # Relations
    relations = []
    for rel in results.get("relations", []):
        relations.append({
            "relation": rel.result,
            "entity1":  rel.metadata.get("chunk1", ""),
            "entity2":  rel.metadata.get("chunk2", ""),
        })

    # Build code maps
    icd10_codes: Dict[str, str] = {}
    icdo_codes:  Dict[str, str] = {}
    for res_ann in results.get("icd10_resolution", []):
        icd10_codes[res_ann.metadata.get("chunk", res_ann.result)] = res_ann.result
    for res_ann in results.get("icdo_resolution", []):
        icdo_codes[res_ann.metadata.get("chunk", res_ann.result)] = res_ann.result

    for chunk in chunks:
        codes: Dict[str, str] = {}
        if chunk["text"] in icd10_codes:
            codes["ICD-10-CM"] = icd10_codes[chunk["text"]]
        if chunk["text"] in icdo_codes:
            codes["ICD-O-3"] = icdo_codes[chunk["text"]]
        chunk["codes"] = codes

    return {"chunks": chunks, "relations": relations}


# ---------------------------------------------------------------------------
# Size normalisation
# ---------------------------------------------------------------------------

def _size_to_mm(value: str, unit: str) -> Tuple[str, str]:
    """Normalise tumour size to millimetres."""
    try:
        v = float(value)
        if unit.lower() == "cm":
            return str(round(v * 10, 1)), "mm"
        return value, "mm"
    except (ValueError, TypeError):
        return value, unit


# ---------------------------------------------------------------------------
# Field assembly
# ---------------------------------------------------------------------------

def assemble(
    report_id: str,
    text: str,
    annotation: Dict[str, Any],
    preprocessed: Dict[str, str],
) -> Dict[str, Any]:
    """Map JSL annotation results to the 21-field schema."""
    output = empty_output(report_id, PIPELINE_A)
    fields = output["fields"]
    chunks = annotation["chunks"]

    microscopic = preprocessed.get("MICROSCOPIC_DESCRIPTION", "")
    final_diag  = preprocessed.get("FINAL_DIAGNOSIS", "")
    clinical    = preprocessed.get("CLINICAL_HISTORY", "")
    gross       = preprocessed.get("GROSS_DESCRIPTION", "")
    combined    = "\n".join([microscopic, final_diag])

    site_candidates: List[Dict] = []

    for chunk in chunks:
        label = chunk["label"]
        ctext = chunk["text"]
        state = chunk.get("assertion_state", "present")
        begin = chunk["begin"]
        end   = chunk["end"]
        span  = [begin, end]
        codes = chunk.get("codes", {})

        # primary_site
        if label in ("Anatomical_Site", "Site_Breast", "Site_Lung",
                     "Site_Liver", "Site_Lymph_Node", "Site_Other",
                     "Site_Other_Body_Part"):
            site_candidates.append(chunk)

        # histology_type
        if label in ("Cancer_Dx", "Histological_Type", "Tumor_Finding"):
            if state == "present" and not fields["histology_type"]["value"]:
                fields["histology_type"] = make_field(
                    value=ctext, state=state, evidence=ctext, span=span, codes=codes
                )

        # tumor_grade
        if label == "Grade" and not fields["tumor_grade"]["value"]:
            fields["tumor_grade"] = make_field(
                value=ctext, state=state, evidence=ctext, span=span, codes=codes
            )

        # staging (pT/pN go to pathologic_stage; cT/cN go to clinical_stage)
        if label in ("Staging", "Staging_TNM", "Tumor_T_Staging", "Node_N_Staging"):
            if re.search(r"\b[ycr]?p[TN]", ctext, re.I):
                if not fields["pathologic_stage"]["value"]:
                    fields["pathologic_stage"] = make_field(
                        value=ctext, state=state, evidence=ctext, span=span
                    )
            elif re.search(r"\bc[TN]", ctext, re.I):
                if not fields["clinical_stage"]["value"]:
                    fields["clinical_stage"] = make_field(
                        value=ctext, state=state, evidence=ctext, span=span
                    )

        # M-stage -- ONLY from explicit annotation, never inferred
        if label == "Metastasis_M_Staging":
            if "M0" in ctext and not fields["distant_metastasis"]["value"]:
                fields["distant_metastasis"] = make_field(
                    value="pM0", state="absent", evidence=ctext, span=span
                )
            elif "M1" in ctext and not fields["distant_metastasis"]["value"]:
                fields["distant_metastasis"] = make_field(
                    value="pM1", state="present", evidence=ctext, span=span
                )

        # tumor_size (NER)
        if label == "Tumor_Size" and not fields["tumor_size"]["value"]:
            size_info = _extract_tumor_size(ctext)
            if size_info:
                raw_val, raw_unit = size_info
                norm_val, norm_unit = _size_to_mm(raw_val, raw_unit)
                fields["tumor_size"] = make_field(
                    value=norm_val, unit=norm_unit, state=state, evidence=ctext, span=span
                )

        # lymph_nodes
        if label in ("Lymph_Node", "Lymph_Node_Biopy"):
            ln = _extract_ln_counts(ctext)
            if ln:
                pos, total = ln
                if not fields["lymph_nodes_positive"]["value"]:
                    fields["lymph_nodes_positive"] = make_field(
                        value=pos, state=state, evidence=ctext, span=span
                    )
                if not fields["lymph_nodes_examined"]["value"]:
                    fields["lymph_nodes_examined"] = make_field(
                        value=total, state=state, evidence=ctext, span=span
                    )

        # distant_metastasis (explicit Metastasis entity)
        if label == "Metastasis" and not fields["distant_metastasis"]["value"]:
            fields["distant_metastasis"] = make_field(
                value=ctext, state=state, evidence=ctext, span=span, codes=codes
            )

        # biomarkers
        if label in ("Biomarker", "Biomarker_Result", "Oncogene"):
            bf = _infer_biomarker_field(ctext)
            if bf and bf in FIELD_NAMES and not fields[bf]["value"]:
                fields[bf] = make_field(
                    value=ctext, state=state, evidence=ctext, span=span, codes=codes
                )

        # procedure_type
        if label == "Cancer_Surgery" and not fields["procedure_type"]["value"]:
            fields["procedure_type"] = make_field(
                value=ctext, state=state, evidence=ctext, span=span, codes=codes
            )

        # prior_treatment
        if label in ("Chemotherapy", "Hormonal_Therapy", "Immunotherapy",
                     "Radiation", "Response_To_Treatment",
                     "Unspecific_Therapy", "Line_Of_Therapy"):
            if not fields["prior_treatment"]["value"]:
                fields["prior_treatment"] = make_field(
                    value=ctext, state=state, evidence=ctext, span=span, codes=codes
                )

    # Primary site -- prefer present + longest text
    if site_candidates:
        present_sites = [c for c in site_candidates if c.get("assertion_state") == "present"]
        best = max(present_sites or site_candidates, key=lambda c: len(c["text"]))
        fields["primary_site"] = make_field(
            value=best["text"],
            state=best.get("assertion_state", "present"),
            evidence=best["text"],
            span=[best["begin"], best["end"]],
            codes=best.get("codes", {}),
        )
        lat = _extract_laterality(best["text"])
        if lat and not fields["laterality"]["value"]:
            fields["laterality"] = make_field(
                value=lat, state="present", evidence=best["text"]
            )

    # --- Rule-based fallbacks ---

    # Tumor size from gross text
    if not fields["tumor_size"]["value"]:
        size_info = _extract_tumor_size(gross or text)
        if size_info:
            raw_val, raw_unit = size_info
            norm_val, norm_unit = _size_to_mm(raw_val, raw_unit)
            fields["tumor_size"] = make_field(
                value=norm_val, unit=norm_unit, state="present",
                evidence=f"{raw_val} {raw_unit}"
            )

    # Laterality from clinical text
    if not fields["laterality"]["value"]:
        lat = _extract_laterality(clinical + " " + gross)
        if lat:
            fields["laterality"] = make_field(
                value=lat, state="present", evidence="Laterality from report text"
            )
        else:
            fields["laterality"] = make_field(state="not_applicable")

    # Surgical margins
    if not fields["surgical_margins"]["value"]:
        m = _MARGIN_NEG_RE.search(combined)
        if m:
            fields["surgical_margins"] = make_field(
                value="Negative", state="present", evidence=m.group(0)
            )
        else:
            m = _MARGIN_POS_RE.search(combined)
            if m:
                fields["surgical_margins"] = make_field(
                    value="Positive", state="present", evidence=m.group(0)
                )

    # LVI
    if not fields["lymphovascular_invasion"]["value"]:
        m = _LVI_NEG_RE.search(combined)
        if m:
            fields["lymphovascular_invasion"] = make_field(
                value="Absent", state="absent", evidence=m.group(0)
            )
        else:
            m = _LVI_POS_RE.search(combined)
            if m:
                fields["lymphovascular_invasion"] = make_field(
                    value="Present", state="present", evidence=m.group(0)
                )

    # PNI
    if not fields["perineural_invasion"]["value"]:
        m = _PNI_NEG_RE.search(combined)
        if m:
            fields["perineural_invasion"] = make_field(
                value="Absent", state="absent", evidence=m.group(0)
            )
        else:
            m = _PNI_POS_RE.search(combined)
            if m:
                fields["perineural_invasion"] = make_field(
                    value="Present", state="present", evidence=m.group(0)
                )

    # LN ratio from regex
    if not (fields["lymph_nodes_examined"]["value"] and fields["lymph_nodes_positive"]["value"]):
        ln = _extract_ln_counts(combined)
        if ln:
            pos, total = ln
            if not fields["lymph_nodes_positive"]["value"]:
                fields["lymph_nodes_positive"] = make_field(
                    value=pos, state="present", evidence=f"{pos}/{total}"
                )
            if not fields["lymph_nodes_examined"]["value"]:
                fields["lymph_nodes_examined"] = make_field(
                    value=total, state="present", evidence=f"{pos}/{total}"
                )

    # Tumor multiplicity
    if not fields["tumor_multiplicity"]["value"]:
        m = _MULTI_RE.search(text)
        if m:
            fields["tumor_multiplicity"] = make_field(
                value="Multiple", state="present", evidence=m.group(0)
            )
        else:
            fields["tumor_multiplicity"] = make_field(
                value="Single", state="absent",
                evidence="No multiplicity cues detected"
            )

    # Pathologic staging from regex fallback
    if not fields["pathologic_stage"]["value"]:
        tnm = extract_tnm_stage(final_diag)
        ajcc = extract_ajcc_stage(final_diag)
        if tnm or ajcc:
            stage_val = " -- ".join(filter(None, [tnm, ajcc]))
            fields["pathologic_stage"] = make_field(
                value=stage_val, state="present", evidence=stage_val
            )

    if not fields["clinical_stage"]["value"]:
        ajcc = extract_ajcc_stage(clinical)
        if ajcc:
            fields["clinical_stage"] = make_field(
                value=ajcc, state="present", evidence=ajcc
            )

    return output


# ---------------------------------------------------------------------------
# Cached session / pipeline
# ---------------------------------------------------------------------------

_spark_session   = None
_light_pipeline  = None


def start_spark(
    secret: str = "5.4.0-0e2bf7e015ecf5ffc656c250cd1a03605ade4312",
    gpu: bool = False,
    license_file: Optional[str] = None,
) -> Any:
    """
    Start (or return cached) JSL SparkSession.

    Loads HC_LICENSE JWT and AWS credentials from the license JSON file and
    injects them into os.environ so sparknlp_jsl.start() can find them.
    """
    global _spark_session
    if _spark_session is not None:
        return _spark_session

    # --- Load license keys from JSON file ---
    _license_candidates = [
        license_file,
        r"C:\Users\junai\.johnsnowlabs\licenses\license_number_0_for_Spark-Healthcare.json",
        str(Path.home() / ".johnsnowlabs" / "licenses" / "license_number_0_for_Spark-Healthcare.json"),
    ]
    for lf in _license_candidates:
        if lf and Path(lf).exists():
            with open(lf, "r", encoding="utf-8") as fh:
                lic = json.load(fh)
            jwt = lic.get("HC_LICENSE", "")
            if jwt:
                os.environ.setdefault("SPARK_NLP_LICENSE", jwt)
                os.environ.setdefault("JSL_NLP_LICENSE",   jwt)
            aws_key    = lic.get("AWS_ACCESS_KEY_ID", "")
            aws_secret = lic.get("AWS_SECRET_ACCESS_KEY", "")
            if aws_key:
                os.environ.setdefault("AWS_ACCESS_KEY_ID",     aws_key)
                os.environ.setdefault("AWS_SECRET_ACCESS_KEY", aws_secret)
            logger.info("Loaded JSL license from: %s", lf)
            break
    else:
        logger.warning(
            "JSL license file not found — ensure SPARK_NLP_LICENSE is set in environment."
        )

    import sparknlp_jsl
    _spark_session = sparknlp_jsl.start(secret=secret, gpu=gpu)
    logger.info("JSL Spark session ready (Spark %s)", _spark_session.version)
    return _spark_session


def load_pipeline(spark: Any) -> Any:
    global _light_pipeline
    if _light_pipeline is not None:
        return _light_pipeline
    model = build_full_pipeline(spark)
    _light_pipeline = make_light_pipeline(model)
    return _light_pipeline


def run_report(
    report_id: str,
    report_text: str,
    light_pipeline: Any,
) -> Tuple[Dict[str, Any], float]:
    """Run the JSL pipeline on a single report. Returns (output_dict, elapsed_sec)."""
    t0 = time.perf_counter()
    preprocessed = preprocess(report_text)
    annotation   = annotate(light_pipeline, preprocessed["full_text"])
    output       = assemble(report_id, preprocessed["full_text"], annotation, preprocessed)
    elapsed      = time.perf_counter() - t0

    output["run_timestamp"] = datetime.now(timezone.utc).isoformat()
    output["model_versions"] = {
        "spark_nlp":             "5.4.0",
        "spark_nlp_jsl":         "5.4.0",
        "ner_oncology":          "ner_oncology_wip",
        "ner_biomarker":         "ner_oncology_biomarker_wip",
        "ner_tnm":               "ner_oncology_tnm_wip",
        "assertion":             "assertion_oncology_wip",
        "relation":              "re_oncology_wip",
        "resolver_icd10":        "sbiobertresolve_icd10cm",
        "resolver_icdo":         "sbiobertresolve_icdo_base",
        "embeddings":            "embeddings_clinical",
        "sentence_embeddings":   "sbiobert_base_cased_mli",
        "mode":                  "licensed_jsl_real",
    }
    return output, elapsed


# ---------------------------------------------------------------------------
# Batch run (all 10 reports)
# ---------------------------------------------------------------------------

def run_all(
    data_dir: Path,
    output_dir: Path,
    secret: str = "5.4.0-0e2bf7e015ecf5ffc656c250cd1a03605ade4312",
    gpu: bool = False,
) -> None:
    """Run JSL pipeline on all reports; write JSON + _run_summary.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    spark = start_spark(secret=secret, gpu=gpu)
    lp    = load_pipeline(spark)

    report_files = sorted(data_dir.glob("report_*.txt"))
    if not report_files:
        raise FileNotFoundError(f"No report_*.txt files in {data_dir}")

    runtimes:     List[float] = []
    field_counts: List[int]   = []
    successes:    List[str]   = []
    failures:     List[str]   = []

    for rf in report_files:
        report_id = rf.stem
        logger.info("Processing %s ...", report_id)
        try:
            text = rf.read_text(encoding="utf-8")
            output, elapsed = run_report(report_id, text, lp)

            out_path = output_dir / f"{report_id}.json"
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(output, fh, indent=2, ensure_ascii=False)

            n_pop = sum(1 for v in output["fields"].values() if v.get("value") is not None)
            runtimes.append(elapsed)
            field_counts.append(n_pop)
            successes.append(report_id)
            logger.info("  OK %s -- %d/21 fields -- %.1f s", report_id, n_pop, elapsed)

        except Exception as exc:
            logger.exception("  FAIL %s: %s", report_id, exc)
            failures.append(report_id)

    # _run_summary.json
    summary = {
        "pipeline":               "pipeline_a_classical_jsl",
        "n_reports":              len(report_files),
        "n_success":              len(successes),
        "n_failure":              len(failures),
        "failed_reports":         failures,
        "mean_runtime_sec":       round(sum(runtimes) / len(runtimes), 2) if runtimes else 0,
        "mean_fields_populated":  round(sum(field_counts) / len(field_counts), 1) if field_counts else 0,
        "cost_usd":               0.0,
        "model_name":             "llama3.1:8b",
        "spark_nlp_version":      "5.4.0",
        "spark_nlp_jsl_version":  "5.4.0",
        "models_used": [
            "sentence_detector_dl_healthcare",
            "embeddings_clinical",
            "ner_oncology_wip",
            "ner_oncology_biomarker_wip",
            "ner_oncology_tnm_wip",
            "assertion_oncology_wip",
            "re_oncology_wip",
            "sbiobert_base_cased_mli",
            "sbiobertresolve_icd10cm",
            "sbiobertresolve_icdo_base",
        ],
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "_run_summary.json"
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    logger.info("=== Pipeline A JSL Run Complete ===")
    logger.info("Processed : %d / %d", len(successes), len(report_files))
    logger.info("Mean fields: %.1f / 21", summary["mean_fields_populated"])
    logger.info("Mean time  : %.1f s / report", summary["mean_runtime_sec"])
    if failures:
        logger.warning("Failed: %s", failures)
    logger.info("Summary -> %s", summary_path)
