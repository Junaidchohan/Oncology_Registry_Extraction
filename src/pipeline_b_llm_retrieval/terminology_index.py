"""
terminology_index.py
====================
Builds and manages a local FAISS vector index over the oncology terminology CSV.

Each concept is encoded with a sentence-transformers model. At query time,
a free-text entity value is encoded and compared against all concept embeddings
to retrieve the top-K nearest neighbours.

Index lifecycle
---------------
1.  build()   — encode all concepts, build FAISS index, persist to disk
2.  load()    — restore a pre-built index from disk
3.  search()  — retrieve top-K candidates for a query string

Persistence layout (under terminology/):
    terminology_index.faiss   — FAISS flat index
    terminology_meta.json     — ordered list of concept metadata (parallel to index rows)

Usage:
    python src/pipeline_b_llm_retrieval/terminology_index.py --build
    python src/pipeline_b_llm_retrieval/terminology_index.py --search "invasive ductal carcinoma" --k 5
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[1]
_TERMINOLOGY_CSV = _PROJECT_ROOT / "terminology" / "oncology_terminology.csv"
_INDEX_PATH = _PROJECT_ROOT / "terminology" / "terminology_index.faiss"
_META_PATH = _PROJECT_ROOT / "terminology" / "terminology_meta.json"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # 384-dim, used if sentence_transformers is available
DEFAULT_TOP_K = 5

# Check which encoder backend to use.
# sentence_transformers requires torch+torchvision compatibility; if those are
# broken (common in mixed environments), fall back to sklearn TF-IDF.
# Set env var FORCE_TFIDF=1 to always use TF-IDF regardless.
import os as _os

_ST_AVAILABLE = False
_ST = None

if not _os.environ.get("FORCE_TFIDF"):
    try:
        # Test import chain without actually loading torch model weights
        import importlib as _il
        _st_spec = _il.util.find_spec("sentence_transformers")
        _tv_spec = _il.util.find_spec("torchvision")
        if _st_spec is not None:
            # Quick torchvision sanity-check: try importing without side effects
            if _tv_spec is not None:
                import torchvision as _tv  # noqa — will raise if broken
            from sentence_transformers import SentenceTransformer as _ST_CLS
            _ST = _ST_CLS
            _ST_AVAILABLE = True
    except Exception as _e:
        logger.debug("sentence_transformers backend unavailable (%s); using TF-IDF", _e)
        _ST_AVAILABLE = False
        _ST = None


# ---------------------------------------------------------------------------
# Helper: load CSV concepts
# ---------------------------------------------------------------------------

def _load_concepts() -> List[Dict[str, str]]:
    """Load all concept rows from the terminology CSV."""
    concepts: List[Dict[str, str]] = []
    if not _TERMINOLOGY_CSV.exists():
        raise FileNotFoundError(f"Terminology CSV not found: {_TERMINOLOGY_CSV}")
    with open(_TERMINOLOGY_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            concepts.append({k: v.strip() for k, v in row.items()})
    return concepts


def _concept_to_text(concept: Dict[str, str]) -> str:
    """
    Create a rich text string for embedding a concept.
    Combines concept_name, description, and synonyms.
    """
    parts = [concept.get("concept_name", "")]
    desc = concept.get("description", "")
    if desc:
        parts.append(desc)
    syns = concept.get("synonyms", "")
    if syns:
        parts.extend([s.strip() for s in syns.split(";") if s.strip()])
    return ". ".join(filter(None, parts))


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

class TerminologyIndex:
    """FAISS-backed semantic search index over the oncology terminology."""

    def __init__(self) -> None:
        self._index: Any = None          # faiss.Index
        self._meta: List[Dict[str, str]] = []
        self._encoder: Any = None        # SentenceTransformer or TfidfVectorizer
        self._tfidf_matrix: Any = None   # used only in sklearn backend
        self._backend: str = "none"      # "sentence_transformers" or "sklearn_tfidf"

    # ------------------------------------------------------------------
    # Encoder — dual backend
    # ------------------------------------------------------------------

    def _get_encoder(self) -> Any:
        """Return encoder; prefers sentence_transformers, falls back to sklearn TF-IDF."""
        if self._encoder is None:
            if _ST_AVAILABLE:
                logger.info("Backend: sentence-transformers (%s)", EMBEDDING_MODEL)
                self._encoder = _ST(EMBEDDING_MODEL)
                self._backend = "sentence_transformers"
            else:
                from sklearn.feature_extraction.text import TfidfVectorizer
                logger.info("Backend: sklearn TF-IDF (sentence_transformers unavailable)")
                self._encoder = TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=2048,
                    sublinear_tf=True,
                )
                self._backend = "sklearn_tfidf"
        return self._encoder

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts to L2-normalised float32 vectors."""
        encoder = self._get_encoder()

        if self._backend == "sentence_transformers":
            embeddings = encoder.encode(
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return np.array(embeddings, dtype=np.float32)

        else:  # sklearn_tfidf
            from sklearn.preprocessing import normalize
            if not hasattr(encoder, 'vocabulary_'):  # not fitted yet
                # Should only happen during build(); load uses persisted matrix
                raise RuntimeError("TF-IDF vectorizer not fitted; call build() first.")
            mat = encoder.transform(texts)
            dense = np.array(mat.todense(), dtype=np.float32)
            # L2-normalise so inner product == cosine similarity
            norms = np.linalg.norm(dense, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return dense / norms

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Encode all concepts and build the FAISS index. Saves to disk."""
        import faiss
        import pickle

        concepts = _load_concepts()
        logger.info("Encoding %d concepts...", len(concepts))

        texts = [_concept_to_text(c) for c in concepts]
        encoder = self._get_encoder()

        if self._backend == "sklearn_tfidf":
            # Fit the vectorizer on all concept texts first
            from sklearn.preprocessing import normalize
            mat = encoder.fit_transform(texts)
            dense = np.array(mat.todense(), dtype=np.float32)
            norms = np.linalg.norm(dense, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            embeddings = dense / norms
            # Persist the fitted vectorizer alongside the FAISS index
            enc_path = _INDEX_PATH.with_suffix('.pkl')
            with open(enc_path, 'wb') as f:
                pickle.dump(encoder, f)
            logger.info("TF-IDF vectorizer saved to %s", enc_path)
        else:
            embeddings = self._encode(texts)

        dim = embeddings.shape[1]
        # Use IndexFlatIP (inner product) for cosine similarity on normalised vectors
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        faiss.write_index(index, str(_INDEX_PATH))
        with open(_META_PATH, "w", encoding="utf-8") as f:
            json.dump(concepts, f, indent=2, ensure_ascii=False)

        self._index = index
        self._meta = concepts
        logger.info(
            "Index built: %d vectors (dim=%d) [backend=%s] → %s",
            index.ntotal, dim, self._backend, _INDEX_PATH
        )

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load a pre-built FAISS index from disk."""
        import faiss

        if not _INDEX_PATH.exists() or not _META_PATH.exists():
            raise FileNotFoundError(
                f"Index not found at {_INDEX_PATH}. Run with --build first."
            )
        self._index = faiss.read_index(str(_INDEX_PATH))
        with open(_META_PATH, encoding="utf-8") as f:
            self._meta = json.load(f)

        # Restore TF-IDF vectorizer if it was used during build
        enc_path = _INDEX_PATH.with_suffix('.pkl')
        if enc_path.exists():
            import pickle
            with open(enc_path, 'rb') as f:
                self._encoder = pickle.load(f)
            self._backend = "sklearn_tfidf"
            logger.info("TF-IDF vectorizer restored from %s", enc_path)
        elif _ST_AVAILABLE:
            self._backend = "sentence_transformers"

        logger.info(
            "Index loaded: %d vectors [backend=%s] from %s",
            self._index.ntotal, self._backend, _INDEX_PATH
        )

    def ensure_loaded(self) -> None:
        """Load index if not already loaded; build if index files are absent."""
        if self._index is not None:
            return
        if _INDEX_PATH.exists() and _META_PATH.exists():
            self.load()
        else:
            logger.info("Index not found — building automatically.")
            self.build()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        terminology_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top-K most similar concepts for a query string.

        Parameters
        ----------
        query : str
            Free-text entity value to search.
        top_k : int
            Number of candidates to return.
        terminology_filter : List[str], optional
            If provided, only return concepts from these terminologies.
            E.g. ["ICD-10", "ICD-O-3"]

        Returns
        -------
        List[Dict[str, Any]]
            Ordered list of candidate dicts, each containing:
            {concept_id, concept_name, terminology, code, category,
             description, synonyms, score}
        """
        self.ensure_loaded()
        query_vec = self._encode([query])

        # Search in the full index
        search_k = top_k * 5 if terminology_filter else top_k
        scores, indices = self._index.search(query_vec, min(search_k, self._index.ntotal))

        candidates: List[Dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = dict(self._meta[idx])
            meta["score"] = float(score)
            if terminology_filter and meta.get("terminology") not in terminology_filter:
                continue
            candidates.append(meta)
            if len(candidates) >= top_k:
                break

        return candidates

    def search_multi(
        self,
        query: str,
        terminologies: Dict[str, int],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for candidates from multiple terminologies simultaneously.

        Parameters
        ----------
        query : str
        terminologies : Dict[str, int]
            {terminology_name: top_k_for_that_terminology}

        Returns
        -------
        Dict[str, List[Dict]]
            {terminology_name: [candidates]}
        """
        total_k = sum(terminologies.values()) * 3
        self.ensure_loaded()
        query_vec = self._encode([query])
        scores, indices = self._index.search(query_vec, min(total_k, self._index.ntotal))

        results: Dict[str, List[Dict[str, Any]]] = {t: [] for t in terminologies}
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = dict(self._meta[idx])
            meta["score"] = float(score)
            term = meta.get("terminology", "")
            if term in results and len(results[term]) < terminologies[term]:
                results[term].append(meta)

        return results


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_INDEX_SINGLETON: Optional[TerminologyIndex] = None


def get_index() -> TerminologyIndex:
    """Return the module-level singleton TerminologyIndex, loading/building as needed."""
    global _INDEX_SINGLETON
    if _INDEX_SINGLETON is None:
        _INDEX_SINGLETON = TerminologyIndex()
        _INDEX_SINGLETON.ensure_loaded()
    return _INDEX_SINGLETON


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Build or query the oncology terminology FAISS index.")
    parser.add_argument("--build", action="store_true", help="Build and persist the FAISS index")
    parser.add_argument("--search", metavar="QUERY", help="Search query string")
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="Top-K results")
    parser.add_argument("--filter", nargs="*", metavar="TERMINOLOGY",
                        help="Filter by terminology (e.g. ICD-10 ICD-O-3)")
    args = parser.parse_args()

    idx = TerminologyIndex()

    if args.build:
        idx.build()

    if args.search:
        if not args.build:
            idx.load()
        results = idx.search(args.search, top_k=args.k, terminology_filter=args.filter)
        print(f"\nTop-{args.k} results for: '{args.search}'")
        print("-" * 70)
        for r in results:
            print(f"  [{r['terminology']}] {r['code']:15s} {r['concept_name']:<40s} (score={r['score']:.4f})")
            print(f"    {r.get('description', '')[:80]}")


if __name__ == "__main__":
    main()
