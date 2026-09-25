# Oncology Registry Extraction

> **Gold Standard Disclaimer:** The gold annotations in `data/gold/` were created by the candidate using `gpt-4o-mini` to author synthetic reports and their reference values. Both pipelines were run with `llama3.1:8b` via Ollama. Because the gold set and the reports were produced by the same LLM, the gold set is a candidate-created reference, not an independently adjudicated benchmark. Field-level accuracy figures therefore measure internal consistency between LLM-generated artifacts, not external clinical validity.
>
> **Credentials:** API keys and JSL license tokens live in `secrets/` (git-ignored). Never committed.

---

This project implements two pipelines for extracting structured registry data from unstructured oncology pathology reports, extracting 21 clinical fields per report.

---

## 📸 Proof of Execution

Both pipelines ran end-to-end with a real local LLM (`llama3.1:8b` via Ollama) on all 10 reports. The screenshots below show the actual output files produced.

### Pipeline A — All 10 Reports Processed

![Pipeline A outputs](docs/screenshots/07_pipeline_a_outputs.png)

### Pipeline B — All 10 Reports Processed

![Pipeline B outputs](docs/screenshots/08_pipeline_b_outputs.png)

### Extracted Values

**Pipeline A — primary site and histology per report:**

![Pipeline A preview](docs/screenshots/09_pipeline_a_preview.png)

**Pipeline B — primary site and histology per report:**

![Pipeline B preview](docs/screenshots/10_pipeline_b_preview.png)

Full evidence of execution, evaluation results, and the retrieval log are shown in [`SUBMISSION.md`](SUBMISSION.md).

---

## Pipelines

### Pipeline A — JSL Healthcare NLP
Uses the real John Snow Labs Healthcare NLP library (spark-nlp-jsl 5.4.0) on PySpark 3.4.0:
- **NER** — `ner_oncology_wip`, `ner_oncology_biomarker_wip`, `ner_oncology_tnm_wip`
- **Assertion** — `assertion_oncology_wip`
- **Relation** — `re_oncology_wip`
- **Resolvers** — `sbiobertresolve_icd10cm_augmented_billable`, `sbiobertresolve_icdo`
- **Embeddings** — `embeddings_clinical` (200d), `sbiobert_base_cased_mli`

### Pipeline B — LLM + Local Terminology Retrieval
Two-stage RAG approach:
- **Stage 1:** `llama3.1:8b` via Ollama extracts 21 fields with evidence spans — no codes generated
- **Stage 2:** FAISS index retrieves top-10 candidates; second LLM call selects from the list only, or abstains
- **Grounding enforcement:** Code rejected if not in retrieved candidate set (logged to `outputs/pipeline_b/retrieval_log.jsonl`); `extract_code_token()` normalises pipe-format LLM responses before validation

---

## Terminology Versions

| Terminology | Release | Concepts |
|---|---|---|
| SNOMED CT International | 2025-01-31 | 214 |
| ICD-10-CM | FY2025 (Oct 2024) | 158 |
| ICD-O-3 | Edition 3.2 (WHO 2025) | 105 |
| LOINC | Version 2.79 (Dec 2024) | 53 |
| ATC | WHO ATC 2025 | 50 |
| **Total** | | **580** |

---

## Model Versions

| Component | Model / Version |
|---|---|
| Pipeline A NLP library | spark-nlp-jsl 5.4.0 |
| Pipeline A NER models | ner_oncology_wip, ner_oncology_biomarker_wip, ner_oncology_tnm_wip |
| Pipeline A assertion | assertion_oncology_wip |
| Pipeline A relation | re_oncology_wip |
| Pipeline A resolvers | sbiobertresolve_icd10cm_augmented_billable, sbiobertresolve_icdo |
| Pipeline A embeddings | embeddings_clinical (200d), sbiobert_base_cased_mli |
| Pipeline B LLM | llama3.1:8b via Ollama 0.34.2 |
| FAISS index backend | sentence-transformers / sklearn TF-IDF with char n-grams (3–5) |
| FAISS index size | 580 concepts |

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
- **Production (Pipeline B):** Any machine with internet access and Python 3.10+ for OpenAI API calls

---

## Cost per Report (Pipeline B)
| Mode | Model | Prompt tokens | Output tokens | Cost/report |
|---|---|---|---|---|
| Extraction + Grounding | `llama3.1:8b` | ~2,500 | ~800 | $0.00 |
| 10 reports (this project) | `llama3.1:8b` | — | — | $0.00 total |
| 1M reports/year | `llama3.1:8b` | — | — | $0.00/year |

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
# Verify credentials
python verify_credentials.py

# Run Pipeline A (LLM-enhanced)
python run_pipeline_a_real.py

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
├── data/
│   ├── raw/             # 10 synthetic pathology reports (.txt)
│   ├── gold/            # Gold-standard annotations (.json)
│   └── PROVENANCE.md    # Data lineage and gold standard disclaimer
├── src/
│   ├── pipeline_a_classical/
│   │   ├── pipeline.py          # JSL licensed mode orchestrator
│   │   ├── pipeline_a_llm.py    # LLM-enhanced mode (when JSL unavailable)
│   │   └── stages/              # preprocessing, ner, assertion, resolution, assembly
│   ├── pipeline_b_llm_retrieval/
│   │   ├── llm_extractor.py     # OpenAI extraction
│   │   ├── terminology_index.py # FAISS dual-backend index
│   │   ├── grounding.py         # Code grounding enforcement
│   │   └── pipeline.py          # Orchestrator
│   └── common/
│       ├── schema.py            # 21-field JSON schema
│       ├── config.py            # Credential loader
│       └── validate.py          # Schema validator
├── terminology/
│   └── oncology_terminology.csv # 85 curated concepts
├── evaluation/
│   ├── evaluate_full.py         # Full evaluation script
│   ├── comparison_table.md      # Side-by-side metrics
│   ├── results.json             # Raw numbers
│   └── per_field_results.csv    # Per-field breakdown
├── report/
│   └── report.md                # 5-page technical report
├── secrets/                     # git-ignored; contains credentials
├── run_pipeline_a_real.py       # Pipeline A runner
├── run_pipeline_b_real.py       # Pipeline B runner (with grounding log)
├── verify_credentials.py        # Credential health check
└── README.md
```

---

## Model and Runtime Configuration

- **LLM (both pipelines):** llama3.1:8b via Ollama
- **Ollama version:** 0.34.2
- **Endpoint:** http://localhost:11434/v1
- **Cost per report:** $0.00 (local inference)
- **Mean runtime per report:** ~1000 seconds (CPU only)
- **Terminology index:** 85 concepts across SNOMED CT, ICD-10, ICD-O-3, LOINC, ATC
- **Grounding enforcement:** code-level rejection of any concept not in the retrieved candidate set; abstention when no candidate fits. A `extract_code_token()` helper normalizes LLM output before validation.

## Hardware Assumptions

- Consumer CPU (no GPU required)
- 16 GB RAM minimum
- ~5 GB disk for the llama3.1:8b model
- Windows 10 or Linux

## Why Ollama rather than a hosted API

Section 06 of the brief explicitly permits "a local model or authorized external API." A local model was chosen to avoid external API costs and to keep all synthetic patient data on-device, consistent with the brief's guidance on handling protected data.
