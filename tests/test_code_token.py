"""
tests/test_code_token.py
========================
Unit tests for extract_code_token() in grounding.py.

Covers every format documented in the Task 1 specification.
"""

import sys
from pathlib import Path

# Allow import from src/pipeline_b_llm_retrieval without a package install
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "pipeline_b_llm_retrieval"))

import pytest
from grounding import extract_code_token


class TestExtractCodeToken:
    """All required format variants."""

    # ------------------------------------------------------------------ #
    # Bare codes (no pipe characters)
    # ------------------------------------------------------------------ #

    def test_bare_snomed_code(self):
        assert extract_code_token("369783002") == "369783002"

    def test_bare_icdo3_morphology(self):
        assert extract_code_token("8500/3") == "8500/3"

    def test_bare_loinc(self):
        assert extract_code_token("81197-5") == "81197-5"

    def test_bare_icd10(self):
        assert extract_code_token("C50.4") == "C50.4"

    # ------------------------------------------------------------------ #
    # Three-part pipe format: TERM | CODE | Description
    # ------------------------------------------------------------------ #

    def test_snomed_three_part(self):
        assert extract_code_token("SNOMED | 369783002 | Nottingham Grade 2") == "369783002"

    def test_icdo3_three_part(self):
        assert extract_code_token("ICD-O-3 | 8500/3 | Invasive ductal carcinoma") == "8500/3"

    def test_loinc_three_part(self):
        assert extract_code_token("LOINC | 81197-5 | EGFR mutation panel") == "81197-5"

    def test_icd10_three_part(self):
        assert extract_code_token("ICD-10 | C50.4 | Upper outer quadrant of breast") == "C50.4"

    def test_atc_three_part(self):
        assert extract_code_token("ATC | L01XC03 | Trastuzumab") == "L01XC03"

    # ------------------------------------------------------------------ #
    # Two-part pipe format: TERM | CODE
    # ------------------------------------------------------------------ #

    def test_snomed_two_part(self):
        assert extract_code_token("SNOMED | 369783002") == "369783002"

    def test_loinc_two_part(self):
        assert extract_code_token("LOINC | 81197-5") == "81197-5"

    def test_icdo3_two_part(self):
        assert extract_code_token("ICD-O-3 | 8500/3") == "8500/3"

    # ------------------------------------------------------------------ #
    # Two-part pipe format: CODE | Description (no terminology prefix)
    # ------------------------------------------------------------------ #

    def test_code_then_description(self):
        assert extract_code_token("369783002 | Nottingham Grade 2") == "369783002"

    def test_icdo3_code_then_description(self):
        assert extract_code_token("8500/3 | Invasive ductal carcinoma") == "8500/3"

    # ------------------------------------------------------------------ #
    # Abstention — must return "NONE" exactly, never be treated as a code
    # ------------------------------------------------------------------ #

    def test_none_uppercase(self):
        assert extract_code_token("NONE") == "NONE"

    def test_none_lowercase(self):
        assert extract_code_token("none") == "NONE"

    def test_none_mixed_case(self):
        assert extract_code_token("None") == "NONE"

    def test_abstain_prefix(self):
        assert extract_code_token("ABSTAIN") == "NONE"

    def test_abstain_with_reason(self):
        assert extract_code_token("ABSTAIN - no matching candidate") == "NONE"

    # ------------------------------------------------------------------ #
    # Edge cases
    # ------------------------------------------------------------------ #

    def test_empty_string(self):
        assert extract_code_token("") == ""

    def test_whitespace_only(self):
        # Whitespace-only: no digit found, returns stripped string
        result = extract_code_token("   ")
        assert result == ""

    def test_none_type_returns_empty(self):
        # None Python value (not the string "NONE")
        result = extract_code_token(None)
        assert result == ""

    def test_extra_whitespace_around_pipes(self):
        """Ensure robust stripping around pipe separators."""
        assert extract_code_token("SNOMED  |  369783002  |  Nottingham Grade 2") == "369783002"

    def test_icd10cm_with_dot(self):
        """ICD-10-CM codes like C50.4 — letter prefix then digit then dot."""
        assert extract_code_token("ICD-10-CM | C50.4") == "C50.4"
