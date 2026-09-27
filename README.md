# Oncology Registry Extraction

> **Gold Standard Disclaimer:** The gold annotations in data/gold/ were authored by the candidate using a local LLM to produce the synthetic reports and their reference values. Pipeline A uses the John Snow Labs Healthcare NLP library (spark-nlp-jsl 5.4.0). Pipeline B uses llama3.1:8b via Ollama. Because the gold set and the reports were produced by the same LLM, the gold set is a candidate-created reference, not an independently adjudicated benchmark. Field-level accuracy figures measure internal consistency between LLM-generated artifacts, not external clinical validity.
>
> **Credentials:** API keys and JSL license tokens live in `secrets/` (git-ignored). Never committed.

---

This project implements two pipelines for extracting structured registry data from unstructured oncology pathology reports, extracting 21 clinical fields per report.

---

## Pipelines

### Pipeline A — JSL Healthcare NLP
Uses the real John Snow Labs Healthcare NLP library (spark-nlp-jsl 5.4.0) on PySpark 3.4.0:
- **NER** — `ner_oncology_wip`, `ner_oncology_biomarker_wip`, `ner_oncology_tnm_wip`
- **Assertion** — `assertion_oncology_wip`
- **Relation** — `re_oncology_wip`
- **Resolvers** — `sbiobertresolve_icd10cm`, `sbiobertresolve_icdo_base`
- **Embeddings** — `embeddings_clinical` (200d), `sbiobert_base_cased_mli`

### Pipeline B — LLM + Local Terminology Retrieval
Two-stage RAG approach:
- **Stage 1:** `llama3.1:8b` via Ollama extracts 21 fields with evidence spans — no codes generated
- **Stage 2:** FAISS index retrieves top-10 candidates; second LLM call selects from the list only, or abstains
- **Grounding enforcement:** Code rejected if not in retrieved candidate set (logged to `outputs/pipeline_b/retrieval_log.jsonl`); `extract_code_token()` normalises pipe-format LLM responses before validation

---

## Terminology Versions

| Terminology | Release/Version | Coverage in Index |
|---|---|---|
| SNOMED CT International | 2025-01-31 | 214 concepts |
| ICD-10-CM | FY2025 (Oct 2024) | 158 codes |
| ICD-O-3 | Edition 3.2 (WHO 2025) | 105 codes |
| LOINC | Version 2.79 (Dec 2024) | 53 codes |
| ATC | WHO ATC 2025 | 50 codes |
| **Total** | | **85 concepts** |

---

## Model Versions

| Component | Model / Version |
|---|---|
| Pipeline A NLP library | spark-nlp-jsl 5.4.0 |
| Pipeline A NER models | ner_oncology_wip, ner_oncology_biomarker_wip, ner_oncology_tnm_wip |
| Pipeline A assertion | assertion_oncology_wip |
| Pipeline A relation | re_oncology_wip |
| Pipeline A resolvers | sbiobertresolve_icd10cm, sbiobertresolve_icdo_base |
| Pipeline A embeddings | embeddings_clinical (200d), sbiobert_base_cased_mli |
| Pipeline B LLM | llama3.1:8b via Ollama 0.34.2 |
| FAISS index backend | sentence-transformers / sklearn TF-IDF char n-grams (3-5) |
| FAISS index size | 85 concepts |

## Final Evaluation Results

Both pipelines ran on all 10 reports. Metrics are computed against the gold reference set.

| Metric | Pipeline A — Classical NLP | Pipeline B — LLM + Retrieval |
| --- | --- | --- |
| Entity NER P / R / F1 (span-based) | 14.8% / 15.1% / 14.9% | 32.6% / 43.3% / 37.2% |
| Field value exact accuracy | 46.1% (83/180) | 35.6% (64/180) |
| Assertion / State accuracy | 53.3% (96/180) | 53.9% (97/180) |
| Relation F1 | 8.2% | 7.9% |
| Retrieval Recall@K | 5.4% (2/37) | 43.2% (16/37) |
| Selection accuracy | 5.4% (2/37) | 29.7% (11/37) |
| Located evidence rate | 86.7% | 80.3% |
| Value-in-evidence rate | 69.0% | 61.1% |
| Unsupported field rate | 68.1% (77 fields) | 42.7% (67 fields) |
| Evidence-unsupported fields | 67 | 68 |
| Invalid code rate | 0.0% | 0.0% |
| Mean runtime | 32.85s | 1354.28s |
| Mean cost | $0.0000 | $0.0000 |




## Pipeline A — JSL Environment Setup

Pipeline A uses the real John Snow Labs Healthcare NLP library. It requires:

- **Java 11 (Temurin)** — https://adoptium.net/temurin/releases/?version=11
- **HADOOP_HOME** — `C:\hadoop` with `winutils.exe` in `C:\hadoop\bin`
- **JSL license** — `secrets/jsl_license.json` containing `SPARK_NLP_LICENSE`, `HC_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
- **Python 3.10** with `spark-nlp==5.4.0` and `spark-nlp-jsl==5.4.0` in `venv_jsl`

### Activation

```powershell
cd "E:\AI Projects\Oncology Registry Extraction"
.\setup_jsl_env.ps1
```

---

## Hardware Assumptions
- **Development/test:** Windows 10, Python 3.10, Intel CPU, 16GB RAM — no GPU required
- **JSL licensed mode:** Requires Ubuntu 20.04+, Java 11, PySpark 3.x, 32GB RAM, optional CUDA GPU
- **Production (Pipeline B):** Any machine with internet access and Python 3.10+

---

## Cost per Report (Pipeline B)
| Pipeline | Model | Runtime per report | Cost per report |
|---|---|---|---|
| Pipeline A | spark-nlp-jsl 5.4.0 (local CPU) | ~33 s | .00 |
| Pipeline B | llama3.1:8b via Ollama (local CPU) | ~1354 s | .00 |

---

## Setup

### Requirements
```bash
pip install -r requirements.txt
```

Key packages: `openai>=1.0`, `faiss-cpu`, `scikit-learn`, `sentence-transformers`, `python-dotenv`, `jsonschema`

### Credentials
Create `secrets/.env` (git-ignored):
```
LLM_MODEL=llama3.1:8b
JSL_LICENSE_PATH=secrets/jsl_license.json
```

Create `secrets/jsl_license.json` for JSL-capable environments:
```json
{"SPARK_NLP_LICENSE": "<token>", "SECRET": ""}
```

### Run Commands

```bash
# Run Pipeline A (real JSL Healthcare NLP)
python run_pipeline_a_jsl.py

# Run Pipeline B (LLM + FAISS grounding, with TF-IDF fallback)
$env:FORCE_TFIDF="1"   # if torch/torchvision broken
python run_pipeline_b_real.py

# Validate schema compliance
python src/common/validate.py --pipeline-a outputs/pipeline_a/ --pipeline-b outputs/pipeline_b/ --gold data/gold/

# Full evaluation + comparison table
python evaluation/evaluate_full.py
```

### Output Locations
| Output | Path |
|---|---|
| Pipeline A JSON (10 files) | `outputs/pipeline_a/` |
| Pipeline B JSON (10 files) | `outputs/pipeline_b/` |
| Retrieval log | `outputs/pipeline_b/retrieval_log.jsonl` |
| Comparison table | `evaluation/comparison_table.md` |
| Raw metrics | `evaluation/results.json` |
| Per-field breakdown | `evaluation/per_field_results.csv` |
| Technical report | `report/report.md` |
| Data provenance | `data/PROVENANCE.md` |

---

## Project Structure

```
oncology-registry-extraction/
Γö£ΓöÇΓöÇ data/
Γöé   Γö£ΓöÇΓöÇ raw/             # 10 synthetic pathology reports (.txt)
Γöé   Γö£ΓöÇΓöÇ gold/            # Gold-standard annotations (.json)
Γöé   ΓööΓöÇΓöÇ PROVENANCE.md
Γö£ΓöÇΓöÇ src/
Γöé   Γö£ΓöÇΓöÇ pipeline_a_classical/
Γöé   Γöé   Γö£ΓöÇΓöÇ pipeline_jsl.py      # JSL Healthcare NLP pipeline
Γöé   Γöé   ΓööΓöÇΓöÇ run_jsl.py           # JSL runner
Γöé   Γö£ΓöÇΓöÇ pipeline_b_llm_retrieval/
Γöé   Γöé   Γö£ΓöÇΓöÇ llm_extractor.py     # LLM extraction via Ollama
Γöé   Γöé   Γö£ΓöÇΓöÇ terminology_index.py # FAISS index
Γöé   Γöé   Γö£ΓöÇΓöÇ grounding.py         # Code grounding enforcement
Γöé   Γöé   ΓööΓöÇΓöÇ pipeline.py
Γöé   ΓööΓöÇΓöÇ common/
Γöé       Γö£ΓöÇΓöÇ schema.py
Γöé       Γö£ΓöÇΓöÇ config.py
Γöé       ΓööΓöÇΓöÇ validate.py
Γö£ΓöÇΓöÇ terminology/
Γöé   ΓööΓöÇΓöÇ oncology_terminology.csv # 580 curated concepts
Γö£ΓöÇΓöÇ evaluation/
Γöé   Γö£ΓöÇΓöÇ evaluate_full.py
Γöé   Γö£ΓöÇΓöÇ comparison_table.md
Γöé   Γö£ΓöÇΓöÇ results.json
Γöé   ΓööΓöÇΓöÇ per_field_results.csv
Γö£ΓöÇΓöÇ report/
Γöé   ΓööΓöÇΓöÇ report.md
Γö£ΓöÇΓöÇ docs/
Γöé   ΓööΓöÇΓöÇ screenshots/
Γöé       ΓööΓöÇΓöÇ 13_comparison_table.png
Γö£ΓöÇΓöÇ secrets/                     # git-ignored
Γö£ΓöÇΓöÇ run_pipeline_a_jsl.py        # Pipeline A runner
Γö£ΓöÇΓöÇ run_pipeline_b_real.py       # Pipeline B runner
Γö£ΓöÇΓöÇ setup_jsl_env.ps1            # Environment activator
Γö£ΓöÇΓöÇ requirements.txt
Γö£ΓöÇΓöÇ README.md
ΓööΓöÇΓöÇ SUBMISSION.md
```

---

## Model and Runtime Configuration

- **Pipeline A library:** spark-nlp-jsl 5.4.0 (real JSL Healthcare NLP)
- **Pipeline B LLM:** llama3.1:8b via Ollama 0.34.2
- **Endpoint:** http://localhost:11434/v1 (Pipeline B only)
- **Cost per report:** $0.00 for both pipelines (fully local)
- **Mean runtime:** 32.85s (Pipeline A) / 692.10s (Pipeline B)
- **Terminology index:** 85 concepts across SNOMED CT 2025-01, ICD-10-CM FY2025, ICD-O-3 3.2 (2025), LOINC 2.79, ATC 2025

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
