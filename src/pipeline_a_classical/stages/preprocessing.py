"""
preprocessing.py
================
Stage 1: Document pre-processing and section detection.

Responsibilities:
  - Load raw report text from disk
  - Strip and normalise whitespace
  - Detect and tag the four canonical report sections:
      CLINICAL_HISTORY | GROSS_DESCRIPTION | MICROSCOPIC_DESCRIPTION | FINAL_DIAGNOSIS
  - Return a dict of section_name → section_text for downstream stages

No JSL dependency in this module — pure Python regex/heuristics so the
module is testable without a Spark session.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Section header patterns (case-insensitive)
# ---------------------------------------------------------------------------

_SECTION_PATTERNS: Dict[str, re.Pattern] = {
    "CLINICAL_HISTORY": re.compile(
        r"CLINICAL\s+HISTORY\s*:", re.IGNORECASE
    ),
    "GROSS_DESCRIPTION": re.compile(
        r"GROSS\s+DESCRIPTION\s*:", re.IGNORECASE
    ),
    "MICROSCOPIC_DESCRIPTION": re.compile(
        r"MICROSCOPIC\s+DESCRIPTION\s*:", re.IGNORECASE
    ),
    "FINAL_DIAGNOSIS": re.compile(
        r"FINAL\s+DIAGNOSIS\s*:", re.IGNORECASE
    ),
}

_SECTION_ORDER = [
    "CLINICAL_HISTORY",
    "GROSS_DESCRIPTION",
    "MICROSCOPIC_DESCRIPTION",
    "FINAL_DIAGNOSIS",
]


def detect_sections(text: str) -> Dict[str, str]:
    """
    Split a raw pathology report into its canonical sections.

    Parameters
    ----------
    text : str
        Raw report text.

    Returns
    -------
    Dict[str, str]
        Mapping of section name → section text (may be empty string if
        section not found).
    """
    sections: Dict[str, str] = {s: "" for s in _SECTION_ORDER}

    # Find start positions for all matched sections
    positions: list[Tuple[int, str]] = []
    for section_name, pattern in _SECTION_PATTERNS.items():
        m = pattern.search(text)
        if m:
            positions.append((m.end(), section_name))

    positions.sort(key=lambda x: x[0])

    # Slice text between consecutive section headers
    for i, (start, section_name) in enumerate(positions):
        end = positions[i + 1][0] - len(_SECTION_PATTERNS[positions[i + 1][1]].pattern) if i + 1 < len(positions) else len(text)
        # Find the next header boundary more accurately
        next_start = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        # Back off to just before the next section header line
        raw_slice = text[start:next_start]
        # Remove everything from next header marker onwards
        for next_name, next_pat in _SECTION_PATTERNS.items():
            m2 = next_pat.search(raw_slice)
            if m2:
                raw_slice = raw_slice[: m2.start()]
                break
        sections[section_name] = raw_slice.strip()

    return sections


def preprocess(text: str) -> Dict[str, str]:
    """
    Full pre-processing pipeline for a single report.

    Returns a dict with:
        full_text        : normalised full text
        CLINICAL_HISTORY : section text
        GROSS_DESCRIPTION: section text
        MICROSCOPIC_DESCRIPTION: section text
        FINAL_DIAGNOSIS  : section text
    """
    # Normalise line endings and collapse multiple blank lines
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    normalised = re.sub(r"\n{3,}", "\n\n", normalised)
    normalised = normalised.strip()

    sections = detect_sections(normalised)
    return {"full_text": normalised, **sections}


def get_full_context(preprocessed: Dict[str, str]) -> str:
    """Return the full normalised report text."""
    return preprocessed.get("full_text", "")
