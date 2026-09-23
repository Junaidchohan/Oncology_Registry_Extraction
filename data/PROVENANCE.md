# Data Provenance

## Overview
This document describes the provenance of all 10 synthetic oncology pathology reports used in this project.

---

## Reports (report_001.txt — report_010.txt)

| Field | Value |
|---|---|
| **Source** | Synthetic (no real patient data) |
| **Generation script** | `src/common/generate_reports.py` |
| **Generation model** | OpenAI `gpt-4o-mini` (via API) |
| **Generation date** | 2026-09-22 |
| **Cancer types covered** | Breast (4 reports), Colorectal (3 reports), Lung (3 reports) |
| **Procedure types** | Biopsy and resection (mixed across reports) |
| **PHI status** | No real patient data — all names, ages, dates, and clinical details are entirely fabricated |
| **License** | Freely reusable for research and benchmarking; not derived from any real clinical records |

---

## Design Coverage
Reports were specifically designed to include the following phenomena to stress-test extraction:

| Phenomenon | Reports |
|---|---|
| Negated findings ("no evidence of metastasis") | 001, 003, 005, 007, 009 |
| Uncertain/hedged findings ("suspicious for") | 002, 006, 010 |
| Multiple lesions / multifocal disease | 004, 008 |
| Historical vs. current disease references | 001, 004 |
| Biomarker results (ER, PR, HER2, KRAS, EGFR) | 001–005 |
| TNM staging with AJCC stage | 001, 002, 003, 006, 007 |
| Varied units (cm and mm for tumor size) | Throughout |
| Genuinely missing fields (not_mentioned) | Throughout |

---

## Gold Standard Annotations (report_001.json — report_010.json)

| Field | Value |
|---|---|
| **Source** | Manually created by candidate using the same LLM that generated the reports |
| **Annotation tool** | Manual JSON editing |
| **Annotator** | Project candidate (single annotator) |
| **Inter-annotator agreement** | Not applicable (single annotator) |
| **Independent adjudication** | **NOT performed** |

> ⚠️ **Important Disclaimer:** The gold annotations in `data/gold/` were created by the candidate using the same LLM (`gpt-4o-mini`) that generated the synthetic reports. They are **not an independently adjudicated benchmark** and should be treated as a **candidate-created reference set only**. Metrics computed against this gold standard reflect internal consistency, not external validation. A production evaluation would require annotations from certified oncology coders.

---

## Quality Checks Performed
1. **Schema validation** — All 10 gold JSONs validated against the 21-field schema (`src/common/schema.py`)
2. **State vocabulary check** — All `state` values verified to be one of: `present`, `absent`, `uncertain`, `not_mentioned`, `not_applicable`, `ambiguous`
3. **Code format check** — ICD-O-3 morphology codes verified as `XXXX/X` format; ICD-10 codes as `C##.#` format
4. **PHI review** — Confirmed no real names, DOBs, MRNs, provider names, or facility names
5. **Report structure check** — All 10 reports contain the 4 required sections: CLINICAL HISTORY, GROSS DESCRIPTION, MICROSCOPIC DESCRIPTION, FINAL DIAGNOSIS
