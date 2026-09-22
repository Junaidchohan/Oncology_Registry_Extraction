"""
ner.py
======
Stage 2: Named Entity Recognition using John Snow Labs Spark NLP for Healthcare.

Models used (all licensed JSL Healthcare NLP models):
  - ner_oncology_wip              : comprehensive oncology entities
  - ner_oncology_biomarker_wip    : biomarker and receptor entities
  - ner_oncology_tnm_wip          : TNM staging entities
  - ner_oncology_anatomy_granular_wip : fine-grained anatomical sites
  - ner_oncology_therapy_wip      : treatment and therapy entities

Entity labels produced (across all models):
  Cancer_Dx, Tumor_Finding, Anatomical_Site, Grade, Staging, Tumor_Size,
  Invasion, Lymph_Node, Metastasis, Histological_Type, Biomarker,
  Biomarker_Result, Oncogene, Staging_TNM, Tumor_T_Staging, Node_N_Staging,
  Metastasis_M_Staging, Cancer_Surgery, Chemotherapy, Hormonal_Therapy,
  Immunotherapy, Radiation, Site_Breast, Site_Lung, Site_Liver

Each entity dict has:
  {
      "text": str,
      "label": str,
      "begin": int,
      "end": int,
      "model": str,
      "confidence": float,
  }
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# JSL imports — guarded so the module can be imported for introspection
# without Spark being available.
# ---------------------------------------------------------------------------

_JSL_AVAILABLE = False
try:
    import sparknlp
    import sparknlp_jsl
    from sparknlp.base import DocumentAssembler, LightPipeline
    from sparknlp.annotator import (
        SentenceDetectorDLModel,
        Tokenizer,
        WordEmbeddingsModel,
    )
    from sparknlp_jsl.annotator import (
        MedicalNerModel,
        NerConverterInternalModel,
    )
    import pyspark.sql.functions as F
    _JSL_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

# All JSL NER models to combine. Each tuple: (model_name, output_col_prefix)
NER_MODELS: List[tuple[str, str]] = [
    ("ner_oncology_wip",                   "ner_oncology"),
    ("ner_oncology_biomarker_wip",         "ner_biomarker"),
    ("ner_oncology_tnm_wip",               "ner_tnm"),
    ("ner_oncology_anatomy_granular_wip",   "ner_anatomy"),
    ("ner_oncology_therapy_wip",           "ner_therapy"),
]

# Shared embeddings model for all NER models above
EMBEDDINGS_MODEL = "embeddings_healthcare_100d"

# Section-level model for context routing
SECTION_NER_MODEL = "ner_section_header_clinical"


def build_ner_pipeline(spark_session: Any) -> Any:
    """
    Build a Spark NLP Healthcare multi-NER pipeline.

    Parameters
    ----------
    spark_session : pyspark.sql.SparkSession
        Active Spark session (must have JSL license configured).

    Returns
    -------
    sparknlp.base.LightPipeline
        Ready-to-use light pipeline for single-string inference.
    """
    if not _JSL_AVAILABLE:
        raise RuntimeError(
            "sparknlp / sparknlp_jsl not available. "
            "Install johnsnowlabs and configure a valid JSL license."
        )

    from sparknlp.base import Pipeline as SparkNLPPipeline

    # Stage 1: Document Assembler
    document_assembler = (
        DocumentAssembler()
        .setInputCol("text")
        .setOutputCol("document")
    )

    # Stage 2: Sentence Detector
    sentence_detector = (
        SentenceDetectorDLModel
        .pretrained("sentence_detector_dl_healthcare", "en", "clinical/models")
        .setInputCols(["document"])
        .setOutputCol("sentence")
    )

    # Stage 3: Tokenizer
    tokenizer = (
        Tokenizer()
        .setInputCols(["sentence"])
        .setOutputCol("token")
    )

    # Stage 4: Clinical Word Embeddings
    embeddings = (
        WordEmbeddingsModel
        .pretrained(EMBEDDINGS_MODEL, "en", "clinical/models")
        .setInputCols(["sentence", "token"])
        .setOutputCol("embeddings")
    )

    stages = [document_assembler, sentence_detector, tokenizer, embeddings]

    # Stage 5+: Multiple NER models
    for model_name, col_prefix in NER_MODELS:
        ner_model = (
            MedicalNerModel
            .pretrained(model_name, "en", "clinical/models")
            .setInputCols(["sentence", "token", "embeddings"])
            .setOutputCol(f"{col_prefix}_results")
        )
        ner_converter = (
            NerConverterInternalModel()
            .setInputCols(["sentence", "token", f"{col_prefix}_results"])
            .setOutputCol(f"{col_prefix}_chunks")
        )
        stages.extend([ner_model, ner_converter])

    pipeline = SparkNLPPipeline(stages=stages)
    # Fit on empty DF to create a PipelineModel (all pretrained, no training needed)
    empty_df = spark_session.createDataFrame([[""]]).toDF("text")
    model = pipeline.fit(empty_df)
    return LightPipeline(model)


def run_ner(
    light_pipeline: Any,
    text: str,
) -> List[Dict[str, Any]]:
    """
    Run NER on a single report text using the prebuilt LightPipeline.

    Parameters
    ----------
    light_pipeline : LightPipeline
        Pre-built LightPipeline from build_ner_pipeline().
    text : str
        Full report text.

    Returns
    -------
    List[Dict[str, Any]]
        List of entity dicts with keys: text, label, begin, end, model, confidence.
    """
    results = light_pipeline.fullAnnotate(text)[0]
    entities: List[Dict[str, Any]] = []

    for model_name, col_prefix in NER_MODELS:
        chunks_key = f"{col_prefix}_chunks"
        if chunks_key not in results:
            continue
        for chunk in results[chunks_key]:
            meta = chunk.metadata
            entities.append({
                "text": chunk.result,
                "label": meta.get("entity", "UNKNOWN"),
                "begin": chunk.begin,
                "end": chunk.end,
                "model": model_name,
                "confidence": float(meta.get("confidence", 0.0)),
            })

    # Deduplicate overlapping spans (keep highest confidence)
    return _dedup_entities(entities)


def _dedup_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove overlapping entity spans, keeping the highest-confidence one."""
    entities = sorted(entities, key=lambda e: -e["confidence"])
    kept: List[Dict[str, Any]] = []
    used_spans: set[tuple[int, int]] = set()
    for ent in entities:
        span = (ent["begin"], ent["end"])
        # Check overlap with already-kept spans
        overlaps = any(
            not (ent["end"] < s[0] or ent["begin"] > s[1])
            for s in used_spans
        )
        if not overlaps:
            kept.append(ent)
            used_spans.add(span)
    return sorted(kept, key=lambda e: e["begin"])
