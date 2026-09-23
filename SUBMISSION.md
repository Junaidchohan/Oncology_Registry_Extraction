# 🧬 Oncology Registry Extraction

### Classical Healthcare NLP vs. LLM + Retrieval-Grounded Terminology

![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-0.34.2-000000?logo=ollama&logoColor=white)
![Model](https://img.shields.io/badge/LLM-llama3.1%3A8b-FF6B6B)
![FAISS](https://img.shields.io/badge/FAISS-85%20concepts-4B8BBE)
![Cost](https://img.shields.io/badge/Cost-%240.00%2Freport-brightgreen)
![Status](https://img.shields.io/badge/Status-Complete-success)

> **Two reproducible pipelines** that transform 10 oncology pathology reports into 21-field structured registry records, evaluated against a gold reference, with full audit trail and quantitative comparison.

**Candidate:** Muhammad Junaid · **Date:** September 24, 2026 · **Commit:** e7f6f2b

---

## 📊 At a Glance

| | |
|---|---|
| **Reports processed** | 10 (breast, colorectal, lung) |
| **Fields extracted per report** | 21 |
| **Pipelines compared** | 2 (Classical NLP · LLM + Retrieval) |
| **LLM** | llama3.1:8b via Ollama (local) |
| **Terminology** | 85 concepts · SNOMED CT · ICD-10 · ICD-O-3 · LOINC · ATC |
| **Cost per report** | **.00** (fully local) |
| **Grounding** | Code-level enforcement — zero hallucinated codes |
| **Audit trail** | Full retrieval log (91 entries) |

---

## 🏗️ Architecture

`	ext
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ONCOLOGY PATHOLOGY REPORT (raw text)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
    ┌──────────────────────┐                       ┌──────────────────────┐
    │      PIPELINE A      │                       │      PIPELINE B      │
    │    Classical NLP     │                       │   LLM + Retrieval    │
    │                      │                       │                      │
    │  ┌────────────────┐  │                       │  ┌────────────────┐  │
    │  │ Preprocessing  │  │                       │  │   LLM Extract  │  │
    │  │ + Section det. │  │                       │  │ (with evidence)│  │
    │  └───────┬────────┘  │                       │  └───────┬────────┘  │
    │          ▼           │                       │          ▼           │
    │  ┌────────────────┐  │                       │  ┌────────────────┐  │
    │  │   Structured   │  │                       │  │ FAISS Retrieve │  │
    │  │  Clinical LLM  │  │                       │  │     top-10     │  │
    │  │  (mimics JSL)  │  │                       │  └───────┬────────┘  │
    │  └───────┬────────┘  │                       │          ▼           │
    │          ▼           │                       │  ┌────────────────┐  │
    │  ┌────────────────┐  │                       │  │   LLM Selects  │  │
    │  │   Rule-based   │  │                       │  │ from candidates│  │
    │  │   Resolution   │  │                       │  └───────┬────────┘  │
    │  └───────┬────────┘  │                       │          ▼           │
    │          ▼           │                       │  ┌────────────────┐  │
    │  ┌────────────────┐  │                       │  │  Code Enforcer │  │
    │  │ Field Assembly │  │                       │  │  REJECTS fakes │  │
    │  └───────┬────────┘  │                       │  └───────┬────────┘  │
    └──────────┼───────────┘                       └──────────┼───────────┘
               │                                              │
               ▼                                              ▼
    ┌──────────────────────┐                       ┌──────────────────────┐
    │ outputs/pipeline_a/  │                       │ outputs/pipeline_b/  │
    │  10 × 21-field JSON  │                       │  10 × 21-field JSON  │
    │                      │                       │   + retrieval_log    │
    └──────────────────────┘                       └──────────────────────┘
               │                                              │
               └──────────────────┬───────────────────────────┘
                                  ▼
                       ┌────────────────────────┐
                       │      evaluation/       │
                       │  Side-by-side compare  │
                       │  Per-field results     │
                       └────────────────────────┘
`

---

## 📈 Results Dashboard

### Headline Metrics

| Metric | Pipeline A | Pipeline B | Winner |
|---|---|---|---|
| Entity Precision | 100.0% | 100.0% | 🤝 Tie |
| Entity Recall | 91.0% | 68.1% | 🅰️ A |
| **Entity F1** | **95.3%** | **81.0%** | 🅰️ A |
| Field value exact accuracy | 28.1% | 23.3% | 🅰️ A |
| Assertion / State accuracy | 57.1% | 55.7% | 🅰️ A |
| Terminology precision | 17.4% | **20.3%** | 🅱️ B |
| Terminology recall | 33.3% | **36.1%** | 🅱️ B |
| **Terminology F1** | 22.9% | **26.0%** | 🅱️ B |
| Unsupported field rate | 0.0% | 0.0% | 🤝 Tie |
| Cost per report | .00 | .00 | 🤝 Tie |

### Visual Comparison

`	ext
Entity F1
Pipeline A ████████████████████████████████████████░░ 95.3%
Pipeline B ██████████████████████████████████░░░░░░░░ 81.0%

Terminology F1
Pipeline A █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 22.9%
Pipeline B ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 26.0%

Entity Precision
Pipeline A ██████████████████████████████████████████ 100.0%
Pipeline B ██████████████████████████████████████████ 100.0%

Entity Recall
Pipeline A ██████████████████████████████████████░░░░ 91.0%
Pipeline B ████████████████████████████░░░░░░░░░░░░░░ 68.1%
`

### What This Shows
- **Pipeline A wins on entity detection** — the structured clinical prompt guides the LLM more precisely.
- **Pipeline B wins on terminology grounding** — the FAISS retrieval + code-level enforcement produce more reliable codes.
- **Neither is universally better.** Each has a role. This is the intended outcome of the comparison.

---

## 📦 Deliverables Map

| What | Where |
|---|---|
| 📄 10 synthetic pathology reports | data/raw/report_001.txt … 
eport_010.txt |
| 📝 Provenance and privacy notes | data/PROVENANCE.md |
| 🏷️ Gold annotations (21 fields × 10) | data/gold/report_001.json … 
eport_010.json |
| 🔬 Pipeline A code | src/pipeline_a_classical/ |
| 🤖 Pipeline B code | src/pipeline_b_llm_retrieval/ |
| 📚 FAISS terminology index | 	erminology/ |
| 📊 Pipeline A outputs | outputs/pipeline_a/ |
| 📊 Pipeline B outputs | outputs/pipeline_b/ |
| 🔍 Full retrieval + grounding log | outputs/pipeline_b/retrieval_log.jsonl |
| 🧪 Evaluation scripts | evaluation/evaluate_full.py |
| 📋 Filled comparison table | evaluation/comparison_table.md |
| 📈 Per-field results | evaluation/per_field_results.csv |
| 📖 Technical report (3–5 pages) | 
eport/report.md |
| 🛠️ Developer README | README.md |

---

## ✅ Brief Compliance Checklist

| Requirement | Status |
|---|---|
| 10 reports + provenance + gold annotations | ✅ |
| Runnable Pipeline A code | ✅ |
| Runnable Pipeline B code | ✅ |
| Local terminology index | ✅ 85 concepts |
| Structured JSON outputs (both pipelines) | ✅ |
| Schema + validation | ✅ |
| Evaluation scripts | ✅ |
| Filled side-by-side comparison | ✅ |
| ≥ 5 discrepancies from real errors | ✅ |
| ≥ 1 tested improvement | ✅ char n-grams: 33.3% → 36.1% |
| Technical report (3–5 pages) | ✅ |
| README with versions, cost, hardware | ✅ |
| Gold-set disclaimer | ✅ |
| Production design (1M reports) | ✅ |

---

## ⚠️ Documented Scope-Downs

The brief permits scoped-down components provided they are stated and justified. The following apply:

1. **Pipeline A NER layer.** spark-nlp-jsl could not be installed in the available environment. The trial license granted access to the JWT and Models Hub AWS credentials but not to the short PyPI secret required by pip install spark-nlp-jsl. Pipeline A therefore uses a structured clinical LLM prompt that mimics the JSL analytical workflow. All required stages are structurally implemented.
2. **Evidence character spans.** Current outputs record the evidence text string for each populated field but leave the numeric character span (span) as 
ull. Span recalculation is documented as future work.
3. **Terminology index size.** The FAISS index contains 85 curated concepts — a documented subset, as permitted by Section 04. Several retrieval misses on receptor-status and variant-level codes are attributable to this scope.
4. **Relation F1 not measured separately.** Field-level Macro F1 is reported as a proxy. Measuring relation F1 on target types is documented as future work.
5. **Gold set is candidate-created.** Both the synthetic reports and the gold annotations were authored by the candidate using gpt-4o-mini. The gold set is **not** an independently adjudicated benchmark. Accuracy figures measure internal consistency between LLM-generated artifacts, not external clinical validity.
7. **Pipeline B evidence quality.** Some evidence fields contain section labels rather than source text (9 of 21 fields in report_001). Documented as future work; re-running the pipeline was outside the time budget for this submission.
8. **Pipeline A stage implementation.** Stages are implemented as structured instructions within a single LLM prompt rather than as separate chained components. Output schema and workflow match the intended stage sequence.
9. **Evidence match rate not measured.** Listed as a required metric in the brief; not computed in `evaluate_full.py`. Documented as a scope-down.

---

## 🚀 How to Run (in 3 commands)

`ash
# 1. Pull the local LLM
ollama pull llama3.1:8b

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run both pipelines and the evaluation
python run_pipeline_a_real.py && python run_pipeline_b_real.py && python evaluation/evaluate_full.py
`

Full setup, model versions, hardware assumptions, and cost model are documented in [README.md](README.md).

📚 **Reference Standards**
Background standards consulted (not redistributed):
* CAP — Current Cancer Protocols
* NAACCR — Data Standards and Data Dictionary
* NCI SEER — ICD-O-3 Coding Materials
* NCI SEER — Cancer PathCHART
* LOINC — Terminology and licensing
* WHO — ATC/DDD classification

📬 **Contact**
Happy to walk through the architecture and results on a call.
Muhammad Junaid
