"""
resolution.py
=============
Stage 4: Entity Resolution — map entity text to standardised medical codes.

JSL resolver models used:
  - sbiobertresolve_icd10cm_augmented_billable  : ICD-10-CM codes
  - sbiobertresolve_icdo                         : ICD-O-3 morphology/topography
  - sbiobertresolve_snomed_findings              : SNOMED CT findings

Each resolver model returns the top-K candidate codes with distances.
We take the top-1 candidate (lowest distance) for each entity.

For biomarkers (LOINC) and drugs (ATC), we use a lightweight local lookup
table (derived from terminology/oncology_terminology.csv) rather than a
full resolver, to keep latency manageable.

Entity label → resolver routing:
  Cancer_Dx, Histological_Type → ICD-O-3 morphology + ICD-10
  Anatomical_Site, Site_*      → ICD-O-3 topography + SNOMED
  Biomarker, Oncogene          → LOINC (local lookup)
  Cancer_Surgery               → SNOMED procedure (local lookup)
  Grade                        → SNOMED (local lookup)
  Staging, Staging_TNM         → AJCC (regex extraction)
  Chemotherapy, Hormonal_Therapy → ATC (local lookup)
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# JSL imports
# ---------------------------------------------------------------------------

_JSL_AVAILABLE = False
try:
    from sparknlp_jsl.annotator import SentenceEntityResolverModel
    _JSL_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Local terminology lookup (fallback + LOINC/ATC routing)
# ---------------------------------------------------------------------------

_TERMINOLOGY_CSV = (
    Path(__file__).resolve().parents[3] / "terminology" / "oncology_terminology.csv"
)


def _load_terminology() -> Dict[str, List[Dict[str, str]]]:
    """
    Load terminology CSV into a dict keyed by terminology name.
    {terminology: [{concept_id, concept_name, code, category, description, synonyms}, ...]}
    """
    lookup: Dict[str, List[Dict[str, str]]] = {}
    if not _TERMINOLOGY_CSV.exists():
        return lookup

    with open(_TERMINOLOGY_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row["terminology"].strip()
            if term not in lookup:
                lookup[term] = []
            lookup[term].append(row)
    return lookup


_TERMINOLOGY: Dict[str, List[Dict[str, str]]] = _load_terminology()


def _local_lookup(
    entity_text: str,
    terminologies: List[str],
    max_results: int = 1,
) -> Dict[str, str]:
    """
    Simple case-insensitive substring lookup against the local terminology index.
    Returns {terminology: code} for the first matching concept.
    """
    text_lower = entity_text.lower()
    found: Dict[str, str] = {}

    for term_name in terminologies:
        rows = _TERMINOLOGY.get(term_name, [])
        best: Optional[Tuple[int, str]] = None  # (match_quality, code)

        for row in rows:
            name_lower = row["concept_name"].lower()
            syns = [s.strip().lower() for s in row.get("synonyms", "").split(";")]
            all_names = [name_lower] + syns

            for candidate in all_names:
                if candidate == text_lower:
                    # Exact match — highest quality (0)
                    if best is None or best[0] > 0:
                        best = (0, row["code"])
                    break
                elif candidate in text_lower or text_lower in candidate:
                    # Partial match — quality 1
                    if best is None or best[0] > 1:
                        best = (1, row["code"])

        if best is not None:
            found[term_name] = best[1]

    return found


# ---------------------------------------------------------------------------
# AJCC/TNM stage extraction (regex-based)
# ---------------------------------------------------------------------------

_TNM_PATTERN = re.compile(
    r"\b((?:[yprc]?)T[0-4][a-z]?\s*(?:[yprc]?)N[0-3][a-z]?\s*(?:[yprc]?)M[0-1][a-z]?)",
    re.IGNORECASE,
)
_STAGE_PATTERN = re.compile(
    r"\bStage\s+(I{1,3}V?[ABC]?|IV[AB]?)\b",
    re.IGNORECASE,
)


def extract_tnm_stage(text: str) -> Optional[str]:
    """Extract the first TNM string found in text, e.g. 'pT2 pN1a pM0'."""
    m = _TNM_PATTERN.search(text)
    return m.group(0).strip() if m else None


def extract_ajcc_stage(text: str) -> Optional[str]:
    """Extract the AJCC stage label, e.g. 'Stage IIB'."""
    m = _STAGE_PATTERN.search(text)
    return m.group(0).strip() if m else None


# ---------------------------------------------------------------------------
# JSL resolver pipeline builder (for ICD-10/ICD-O/SNOMED)
# ---------------------------------------------------------------------------

_RESOLVER_MODELS = {
    "icd10cm": "sbiobertresolve_icd10cm_augmented_billable",
    "icdo": "sbiobertresolve_icdo",
    "snomed": "sbiobertresolve_snomed_findings",
}

_RESOLVER_EMBEDDING = "sbiobert_base_cased_mli"


def build_resolver_pipelines(spark_session: Any) -> Dict[str, Any]:
    """
    Build one LightPipeline per resolver.

    Returns
    -------
    Dict[str, LightPipeline]
        {resolver_key: LightPipeline}, e.g. {"icd10cm": ..., "icdo": ..., "snomed": ...}
    """
    if not _JSL_AVAILABLE:
        return {}

    from sparknlp.base import DocumentAssembler, Pipeline as SparkNLPPipeline, LightPipeline
    from sparknlp.annotator import BertSentenceEmbeddings

    pipelines: Dict[str, Any] = {}
    for key, model_name in _RESOLVER_MODELS.items():
        doc_asm = DocumentAssembler().setInputCol("text").setOutputCol("document")
        bert_emb = (
            BertSentenceEmbeddings
            .pretrained(_RESOLVER_EMBEDDING, "en", "clinical/models")
            .setInputCols(["document"])
            .setOutputCol("sentence_embeddings")
        )
        resolver = (
            SentenceEntityResolverModel
            .pretrained(model_name, "en", "clinical/models")
            .setInputCols(["sentence_embeddings"])
            .setOutputCol("resolution")
            .setDistanceFunction("EUCLIDEAN")
        )
        spark_pipeline = SparkNLPPipeline(stages=[doc_asm, bert_emb, resolver])
        empty_df = spark_session.createDataFrame([[""]]).toDF("text")
        model = spark_pipeline.fit(empty_df)
        pipelines[key] = LightPipeline(model)

    return pipelines


def resolve_entity(
    entity_text: str,
    entity_label: str,
    resolver_pipelines: Dict[str, Any],
) -> Dict[str, str]:
    """
    Resolve an entity to medical codes using JSL resolvers + local lookup.

    Parameters
    ----------
    entity_text : str
    entity_label : str
        NER label (e.g., 'Cancer_Dx', 'Biomarker', 'Anatomical_Site')
    resolver_pipelines : Dict[str, LightPipeline]
        Pre-built resolver pipelines (may be empty if JSL not available).

    Returns
    -------
    Dict[str, str]
        {terminology_name: code}
    """
    codes: Dict[str, str] = {}

    if entity_label in ("Cancer_Dx", "Histological_Type", "Tumor_Finding"):
        # ICD-O-3 morphology + ICD-10
        local = _local_lookup(entity_text, ["ICD-O-3", "ICD-10"])
        codes.update(local)
        if "icdo" in resolver_pipelines and "ICD-O-3" not in codes:
            try:
                res = resolver_pipelines["icdo"].fullAnnotate(entity_text)[0]
                codes["ICD-O-3"] = res["resolution"][0].result
            except Exception:
                pass
        if "icd10cm" in resolver_pipelines and "ICD-10" not in codes:
            try:
                res = resolver_pipelines["icd10cm"].fullAnnotate(entity_text)[0]
                codes["ICD-10"] = res["resolution"][0].result
            except Exception:
                pass

    elif entity_label in ("Anatomical_Site", "Site_Breast", "Site_Lung",
                          "Site_Liver", "Site_Lymph_Node", "Site_Other"):
        local = _local_lookup(entity_text, ["ICD-O-3", "SNOMED"])
        codes.update(local)
        if "snomed" in resolver_pipelines and "SNOMED" not in codes:
            try:
                res = resolver_pipelines["snomed"].fullAnnotate(entity_text)[0]
                codes["SNOMED"] = res["resolution"][0].result
            except Exception:
                pass

    elif entity_label in ("Biomarker", "Oncogene"):
        local = _local_lookup(entity_text, ["LOINC"])
        codes.update(local)

    elif entity_label in ("Cancer_Surgery",):
        local = _local_lookup(entity_text, ["SNOMED"])
        codes.update(local)

    elif entity_label in ("Chemotherapy", "Hormonal_Therapy", "Immunotherapy"):
        local = _local_lookup(entity_text, ["ATC"])
        codes.update(local)

    elif entity_label in ("Grade",):
        local = _local_lookup(entity_text, ["SNOMED"])
        codes.update(local)

    return codes


def resolve_all(
    entities: List[Dict[str, Any]],
    resolver_pipelines: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Resolve all entities to codes and return enriched entity list."""
    resolved = []
    for ent in entities:
        codes = resolve_entity(ent["text"], ent["label"], resolver_pipelines)
        resolved.append({**ent, "codes": codes})
    return resolved
