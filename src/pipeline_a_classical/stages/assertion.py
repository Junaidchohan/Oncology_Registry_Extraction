"""
assertion.py
============
Stage 3: Assertion / context detection using JSL Healthcare NLP.

Model used:
  assertion_oncology_wip — classifies each clinical entity span into:
    Present      → state: "present"
    Absent       → state: "absent"
    Possible     → state: "uncertain"
    Conditional  → state: "uncertain"
    Hypothetical → state: "uncertain"
    Associated_with_someone_else → state: "not_mentioned" (family history context)

The assertion model is run as a separate pipeline stage that takes the
entity chunks from Stage 2 and classifies their polarity/context.
"""

from __future__ import annotations

from typing import Any, Dict, List

_JSL_AVAILABLE = False
try:
    from sparknlp.base import LightPipeline
    from sparknlp_jsl.annotator import AssertionDLModel
    _JSL_AVAILABLE = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Assertion label → schema state mapping
# ---------------------------------------------------------------------------

_ASSERTION_STATE_MAP: Dict[str, str] = {
    "Present":                       "present",
    "Absent":                        "absent",
    "Possible":                      "uncertain",
    "Conditional":                   "uncertain",
    "Hypothetical":                  "uncertain",
    "Associated_with_someone_else":  "not_mentioned",   # family history
}

ASSERTION_MODEL = "assertion_oncology_wip"


def build_assertion_pipeline(spark_session: Any, embeddings_model: Any) -> Any:
    """
    Build a JSL assertion detection pipeline.

    Parameters
    ----------
    spark_session : SparkSession
    embeddings_model : pre-loaded WordEmbeddingsModel (reuse from NER pipeline)

    Returns
    -------
    LightPipeline
    """
    if not _JSL_AVAILABLE:
        raise RuntimeError("sparknlp_jsl not available.")

    from sparknlp.base import DocumentAssembler, Pipeline as SparkNLPPipeline
    from sparknlp.annotator import SentenceDetectorDLModel, Tokenizer, WordEmbeddingsModel
    from sparknlp_jsl.annotator import MedicalNerModel, NerConverterInternalModel

    document_assembler = DocumentAssembler().setInputCol("text").setOutputCol("document")
    sentence_detector = (
        SentenceDetectorDLModel
        .pretrained("sentence_detector_dl_healthcare", "en", "clinical/models")
        .setInputCols(["document"]).setOutputCol("sentence")
    )
    tokenizer = Tokenizer().setInputCols(["sentence"]).setOutputCol("token")
    embeddings = (
        WordEmbeddingsModel
        .pretrained("embeddings_healthcare_100d", "en", "clinical/models")
        .setInputCols(["sentence", "token"]).setOutputCol("embeddings")
    )
    ner = (
        MedicalNerModel
        .pretrained("ner_oncology_wip", "en", "clinical/models")
        .setInputCols(["sentence", "token", "embeddings"])
        .setOutputCol("ner_results")
    )
    ner_converter = (
        NerConverterInternalModel()
        .setInputCols(["sentence", "token", "ner_results"])
        .setOutputCol("ner_chunks")
    )
    assertion = (
        AssertionDLModel
        .pretrained(ASSERTION_MODEL, "en", "clinical/models")
        .setInputCols(["document", "ner_chunks", "embeddings"])
        .setOutputCol("assertion")
    )

    pipeline = SparkNLPPipeline(stages=[
        document_assembler, sentence_detector, tokenizer,
        embeddings, ner, ner_converter, assertion
    ])
    empty_df = spark_session.createDataFrame([[""]]).toDF("text")
    model = pipeline.fit(empty_df)
    return LightPipeline(model)


def run_assertion(
    light_pipeline: Any,
    text: str,
) -> Dict[str, str]:
    """
    Run assertion detection on the report text.

    Returns
    -------
    Dict[str, str]
        Mapping of entity span (begin, end) tuple → assertion state string.
        Key format: "{begin}_{end}" for JSON serializability.
    """
    results = light_pipeline.fullAnnotate(text)[0]
    assertion_map: Dict[str, str] = {}

    assertion_annotations = results.get("assertion", [])
    ner_chunks = results.get("ner_chunks", [])

    # Build chunk index by position
    chunk_by_pos = {(c.begin, c.end): c for c in ner_chunks}

    for ann in assertion_annotations:
        raw_label = ann.result
        state = _ASSERTION_STATE_MAP.get(raw_label, "uncertain")
        key = f"{ann.begin}_{ann.end}"
        assertion_map[key] = state

    return assertion_map


def map_assertion_to_entities(
    entities: List[Dict[str, Any]],
    assertion_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Attach assertion states to entity dicts from the NER stage.

    Entities that have no assertion annotation default to "present".
    """
    enriched = []
    for ent in entities:
        key = f"{ent['begin']}_{ent['end']}"
        state = assertion_map.get(key, "present")
        enriched.append({**ent, "assertion_state": state})
    return enriched


# ---------------------------------------------------------------------------
# Heuristic assertion (fallback when JSL not available)
# ---------------------------------------------------------------------------

import re

_NEGATION_PATTERNS = [
    re.compile(r"\b(no|not|none|without|absent|negative|never|nor|neither|deny|denied|free of|not identified|not seen|not present)\b", re.I),
]
_UNCERTAINTY_PATTERNS = [
    re.compile(r"\b(suspicious|possible|possibly|probable|probably|cannot exclude|may be|might|could be|questionable|indeterminate|pending|equivocal|borderline)\b", re.I),
]

_NEGATION_WINDOW = 60  # characters before the entity to look for negation


def heuristic_assertion(text: str, entity: Dict[str, Any]) -> str:
    """
    Simple rule-based assertion as a fallback when JSL is not available.
    Checks a window before and around the entity span for negation/uncertainty cues.
    """
    begin = entity.get("begin", 0)
    window_start = max(0, begin - _NEGATION_WINDOW)
    context = text[window_start: begin + len(entity.get("text", "")) + 20]

    for pat in _NEGATION_PATTERNS:
        if pat.search(context):
            return "absent"

    for pat in _UNCERTAINTY_PATTERNS:
        if pat.search(context):
            return "uncertain"

    return "present"
