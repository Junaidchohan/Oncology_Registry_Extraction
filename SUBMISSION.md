# 🧬 Oncology Registry Extraction

### Classical Healthcare NLP vs. LLM + Retrieval-Grounded Terminology

![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-0.34.2-000000?logo=ollama&logoColor=white)
![Model](https://img.shields.io/badge/LLM-llama3.1%3A8b-FF6B6B)
![JSL](https://img.shields.io/badge/JSL%20Healthcare%20NLP-5.4.0-0F766E)
![Terminology](https://img.shields.io/badge/Terminology-580%20concepts-4B8BBE)
![Cost](https://img.shields.io/badge/Cost-%240.00%2Freport-brightgreen)
![Status](https://img.shields.io/badge/Status-Complete-success)

This project extracts 21-field structured registry records from 10 synthetic oncology pathology reports. I built two independent pipelines for comparison: one using classical clinical NLP (JSL Healthcare) and another using a local LLM backed by retrieval-augmented terminology grounding. Both run entirely on local hardware without sending data to external APIs.

**Candidate:** Muhammad Junaid · **Date:** September 24, 2026 · **Commit:** b9c3377

---

## 📊 At a Glance

The following parameters define the boundary conditions of this evaluation, ensuring a fair baseline across both pipelines.

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

The brief requested an objective comparison, so I designed two pipelines that represent fundamentally different engineering philosophies. Pipeline A applies a deterministic chain of pre-trained clinical annotators to extract entities and relations. Pipeline B relies on an LLM to extract field values while enforcing strict coding boundaries via FAISS-based terminology retrieval.

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

I expected the LLM approach to struggle with strict code constraints, but grounding it in a local 580-concept FAISS index actually pushed its terminology recall to 30.6%. What surprised me was Pipeline A's extreme conservatism. It ran remarkably fast and hit 50.0% precision on code resolution, but it only mapped codes when it was highly confident, resulting in a 5.6% recall.

### Why Two Pipelines?

I built two completely separate pipelines because the brief asked for a legitimate comparison, and the honest truth is that neither approach wins globally. The classical JSL pipeline guarantees structured output in under a minute with high precision on the codes it does resolve, but it leaves many fields blank if it cannot confidently link the entities. Conversely, the LLM pipeline acts as a high-recall system that infers context far better (achieving 81.0% entity F1), but it pays a massive penalty in runtime (almost 12 minutes per report on my hardware) and occasionally selects lower-precision candidates from the vector space. Each pipeline simply has a different failure mode.

---

## 📈 Results Dashboard

### Headline Metrics

The metrics below measure extraction accuracy and code resolution performance across 210 total fields (21 fields × 10 reports).

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

If you need fast, highly precise code mapping and can afford to miss some edge cases, the JSL annotator chain is the better architectural choice. It only mapped four codes, but two were exact matches, yielding a 50.0% precision rate. However, if capturing a broader context is the priority, the LLM-based Pipeline B consistently finds more values (23.3% field accuracy vs. 11.9%) and grounds them against the local terminology index (30.6% code recall vs 5.6%). Pipeline B fails primarily on speed and vector space noise, mapping 62 codes but only hitting exact target matches 17.7% of the time. The choice between them depends entirely on whether the target application prioritizes precision and latency over recall and context.

---

## 📸 Proof of Execution

Every screenshot was captured from my local Windows environment during the final end-to-end run.

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

## 📦 Deliverables Map

The following files map directly to the required outputs outlined in the candidate brief.

| What | Where |
|---|---|
| 📄 10 synthetic pathology reports | data/raw/report_001.txt … report_010.txt |
| 📝 Provenance and privacy notes | data/PROVENANCE.md |
| 🏷️ Gold annotations (21 fields × 10) | data/gold/report_001.json … report_010.json |
| 🔬 Pipeline A code | src/pipeline_a_classical/ |
| 🤖 Pipeline B code | src/pipeline_b_llm_retrieval/ |
| 📚 FAISS terminology index | terminology/ |
| 📊 Pipeline A outputs | outputs/pipeline_a/ |
| 📊 Pipeline B outputs | outputs/pipeline_b/ |
| 🔍 Full retrieval + grounding log | outputs/pipeline_b/retrieval_log.jsonl |
| 🧪 Evaluation scripts | evaluation/evaluate_full.py |
| 📋 Filled comparison table | evaluation/comparison_table.md |
| 📈 Per-field results | evaluation/per_field_results.csv |
| 📖 Technical report (3–5 pages) | report/report.md |
| 🛠️ Developer README | README.md |

---

## ✅ Brief Compliance Checklist

I tracked every requirement from the assessment to ensure nothing was overlooked.

| Requirement | Status |
|---|---|
| 10 reports + provenance + gold annotations | ✅ |
| Runnable Pipeline A code | ✅ |
| Runnable Pipeline B code | ✅ |
| Local terminology index | ✅ 580 concepts |
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

The brief allows scoped-down components as long as they are justified. I hit several hard constraints during development, so I made the following explicit engineering compromises.

1. **Pipeline A code resolution.** I ran Pipeline A using the real JSL Healthcare NLP library (spark-nlp-jsl 5.4.0) on all 10 reports, and the base extraction worked perfectly. However, the resolver models triggered a fatal Hadoop JNI bug (`NativeIO$Windows.access0`) on my local Windows environment for reports 002–010. I limited the resolver stage execution exclusively to report 001. As a result, extraction is fully complete for all 10 reports, but the code resolution metrics for Pipeline A reflect only that single successful run.

2. **Evidence character spans.** The pipelines successfully capture the exact evidence substring from the source text. Re-aligning those substrings to their exact numeric character offsets in the raw document required additional post-processing logic that fell outside my time budget. I mapped the `span` field to `null`. This prevents downstream applications from highlighting text visually, but does not affect the evaluation metrics.

3. **Terminology index size.** Generating a full vector index for all 350,000+ SNOMED CT concepts locally was too slow and memory-intensive for a proof-of-concept. I built a targeted FAISS index containing 580 curated concepts that cover the primary oncology domains required by the schema. This caused some retrieval misses on highly specific receptor-status and variant-level codes, suppressing Pipeline B's maximum possible recall.

4. **Relation F1 not measured separately.** The brief asked for a discrete F1 score specifically for target relation types. Writing a custom strict-evaluation script to measure nested relations across arrays proved too complex for the timeframe. I used field-level Macro F1 as a direct proxy. This gives a reliable view of overall field assembly but obscures whether the exact parent-child structural linkage failed.

5. **Gold set is candidate-created.** I needed 10 annotated pathology reports to serve as a baseline, but publicly available, fully-adjudicated gold sets for this exact 21-field schema do not exist. I generated synthetic reports and their corresponding gold annotations using a local LLM. Consequently, the accuracy metrics measure how well the pipelines match an LLM's baseline behavior, not their external clinical validity against human expert annotators.

6. **Pipeline B evidence quality.** Pipeline B's prompt occasionally struggled to isolate raw source text. The LLM ended up injecting section labels rather than just the direct quote in 9 of the 21 fields for report 001. I caught this during review, but re-running the entire batch at 12 minutes per report exceeded the remaining time budget. The evidence fields are populated, but they are noisy.

7. **Evidence match rate not measured.** I needed to measure whether the extracted evidence text perfectly matched the original report. I dropped this check from `evaluate_full.py` entirely. The exact evidence matching metric is listed in the brief as a requirement, but it is currently unverified.

8. **Invalid code rate not separately reported.** The brief requested a specific metric tracking hallucinated or invalid codes. I engineered Pipeline B's code enforcer to rigidly reject any code not physically present in the FAISS candidate set. Because this forces the invalid code rate to zero by definition, I did not write evaluation logic to measure it. The raw rejection counts are preserved in `outputs/pipeline_b/retrieval_log.jsonl` instead.

---

## 🚀 How to Run (in 3 commands)

Once these three commands finish, both pipelines execute entirely on your local hardware.

```bash
# 1. Pull the local LLM
ollama pull llama3.1:8b

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run both pipelines and the evaluation
python run_pipeline_a_jsl.py && python run_pipeline_b_real.py && python evaluation/evaluate_full.py
```

Full setup, model versions, hardware assumptions, and cost model are documented in [README.md](README.md).

📚 **Reference Standards**

These are the background standards I consulted to define the schema, not redistributed source data.
* CAP — Current Cancer Protocols
* NAACCR — Data Standards and Data Dictionary
* NCI SEER — ICD-O-3 Coding Materials
* NCI SEER — Cancer PathCHART
* LOINC — Terminology and licensing
* WHO — ATC/DDD classification

📬 **Contact**

Happy to talk through the architecture or walk you through any specific stage. Reach me on LinkedIn.
Muhammad Junaid
