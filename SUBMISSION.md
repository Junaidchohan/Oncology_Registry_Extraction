# 🧬 Oncology Registry Extraction

### Classical Healthcare NLP vs. LLM + Retrieval-Grounded Terminology

![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-0.34.2-000000?logo=ollama&logoColor=white)
![Model](https://img.shields.io/badge/LLM-llama3.1%3A8b-FF6B6B)
![JSL](https://img.shields.io/badge/JSL%20Healthcare%20NLP-5.4.0-0F766E)
![Terminology](https://img.shields.io/badge/Terminology-580%20concepts-4B8BBE)
![Cost](https://img.shields.io/badge/Cost-%240.00%2Freport-brightgreen)
![Status](https://img.shields.io/badge/Status-Complete-success)

> **Two reproducible pipelines** that transform 10 oncology pathology reports into 21-field structured registry records, evaluated against a gold reference, with full audit trail and quantitative comparison.

**Candidate:** Muhammad Junaid · **Date:** September 24, 2026 · **Commit:** b9c3377

---

## 📊 At a Glance

| | |
|---|---|
| **Reports processed** | 10 (breast, colorectal, lung) |
| **Fields extracted per report** | 21 |
| **Pipelines compared** | 2 (JSL Healthcare NLP · LLM + Retrieval) |
| **NLP Library (Pipeline A)** | spark-nlp-jsl 5.4.0 |
| **LLM (Pipeline B)** | llama3.1:8b via Ollama |
| **Terminology** | 580 concepts · SNOMED CT 2025-01 · ICD-10-CM FY2025 · ICD-O-3 3.2 (2025) · LOINC 2.79 · ATC 2025 |
| **Cost per report** | $0.00 (fully local) |
| **Grounding** | Code-level enforcement — zero hallucinated codes |
| **Audit trail** | Full retrieval log (91 entries) |

---

## 🏗️ Architecture

Two independent pipelines transform the same 10 pathology reports into the same 21-field structured record.

```mermaid
flowchart TB
    Input([📄 Pathology Report<br/>raw narrative text])

    subgraph A["🅰️ Pipeline A — JSL Healthcare NLP"]
        direction TB
        A1[Document + Sentence + Token]
        A2[JSL NER: 3 oncology models]
        A3[JSL Assertion + Relation]
        A4[JSL Resolvers: ICD-10 + ICD-O-3]
        A5[21-field assembly]
        A1 --> A2 --> A3 --> A4 --> A5
    end

    subgraph B["🅱️ Pipeline B — LLM + Retrieval"]
        direction TB
        B1[LLM Extraction<br/>with evidence]
        B2[FAISS Retrieval<br/>top-10 candidates]
        B3[LLM Selection<br/>among candidates]
        B4[Code Enforcer<br/>reject non-retrieved]
        B1 --> B2 --> B3 --> B4
    end

    subgraph T["📚 Local Terminology Index"]
        direction LR
        T1[(FAISS<br/>580 concepts)]
        T2[SNOMED CT]
        T3[ICD-10 / ICD-O-3]
        T4[LOINC]
        T5[ATC]
        T2 -.-> T1
        T3 -.-> T1
        T4 -.-> T1
        T5 -.-> T1
    end

    OutA([📊 Pipeline A Output<br/>10 × 21-field JSON])
    OutB([📊 Pipeline B Output<br/>10 × 21-field JSON<br/>+ retrieval log])
    Eval([📈 Evaluation<br/>Side-by-side comparison])

    Input --> A1
    Input --> B1
    T1 -.-> B2
    A5 --> OutA
    B4 --> OutB
    OutA --> Eval
    OutB --> Eval

    classDef inputStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#0d47a1
    classDef pAStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef pBStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#4a148c
    classDef termStyle fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20
    classDef outStyle fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#880e4f
    classDef evalStyle fill:#e0f7fa,stroke:#00838f,stroke-width:2px,color:#006064

    class Input inputStyle
    class A1,A2,A3,A4,A5 pAStyle
    class B1,B2,B3,B4 pBStyle
    class T1,T2,T3,T4,T5 termStyle
    class OutA,OutB outStyle
    class Eval evalStyle
```

### Pipeline Roles at a Glance

| | 🅰️ Pipeline A | 🅱️ Pipeline B |
|---|---|---|
| **Approach** | JSL Healthcare NLP 5.4.0 | LLM extraction + FAISS retrieval + LLM selection |
| **Strengths** | Fast (33s/report), high code precision (50.0%) | Higher entity F1 (81.0%), higher code recall (30.6%) |
| **Trade-off** | Conservative code assignment (5.6% recall) | Slower (692s/report) |
| **Cost** | $0.00 / report | $0.00 / report |
| **Runtime** | ~33 s / report (CPU) | ~692 s / report (CPU) |

### Why Two Pipelines?

The brief asks for a measured comparison, not a single winner. The results show a clean trade-off:

- Pipeline A (JSL Healthcare NLP 5.4.0) runs in ~33 seconds per report and produces high precision codes (50.0%) when it resolves, but assigns codes conservatively (5.6% recall).
- Pipeline B (llama3.1:8b + FAISS retrieval over 580 concepts) runs in ~692 seconds per report and finds more codes (30.6% recall) with higher entity F1 (81.0%).

Each pipeline has a role: Pipeline A for fast, precise extraction; Pipeline B for higher-recall terminology grounding.

---

## 📈 Results Dashboard

### Headline Metrics

| Metric | Pipeline A (JSL) | Pipeline B (LLM + Retrieval) |
|---|---|---|
| Entity P / R / F1 | 100.0% / 65.2% / 79.0% | 100.0% / 68.1% / 81.0% |
| Entity TP / FP / FN | 137 / 0 / 73 | 143 / 0 / 67 |
| Field value exact accuracy | 11.9% (25/210) | 23.3% (49/210) |
| Assertion / State accuracy | 49.0% (103/210) | 55.7% (117/210) |
| Relation / Macro F1 | 79.0% | 81.0% |
| Terminology precision | 50.0% (2/4) | 17.7% (11/62) |
| Terminology recall | 5.6% (2/36) | 30.6% (11/36) |
| Terminology F1 | 10.0% | 22.4% |
| Unsupported field rate | 0.0% | 0.0% |
| Mean runtime | 32.85s | 692.10s |
| Cost per report | $0.00 | $0.00 |

### What This Shows
- **Pipeline A wins on code precision when it resolves** — the JSL annotator chain produces higher code precision (50.0%). Pipeline B wins on terminology recall (30.6%) through the 580-concept FAISS retrieval.
- **Neither is universally better.** Each has a role. This is the intended outcome of the comparison.

---

## Proof of Execution

All screenshots captured from the local Windows environment after the final JSL rebuild and evaluation.

### 01_pipeline_a_all_jsl.png
![01_pipeline_a_all_jsl.png](docs/screenshots/01_pipeline_a_all_jsl.png)

### 02_pipeline_a_sample.png
![02_pipeline_a_sample.png](docs/screenshots/02_pipeline_a_sample.png)

### 03_retrieval_log.png
![03_retrieval_log.png](docs/screenshots/03_retrieval_log.png)

### 04_terminology_580.png
![04_terminology_580.png](docs/screenshots/04_terminology_580.png)

### 05_comparison_table.png
![05_comparison_table.png](docs/screenshots/05_comparison_table.png)
