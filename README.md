# Oncology Registry Extraction

This project extracts 21-field structured registry records from unstructured oncology pathology reports. It compares two independent architectures: a classical clinical NLP pipeline (JSL Healthcare) and a large language model pipeline grounded by FAISS terminology retrieval.

## Project Structure

```
oncology-registry-extraction/
|-- data/
|   |-- raw/                    # 10 synthetic pathology reports (.txt)
|   |-- gold/                   # Gold-standard annotations (.json)
|   \-- PROVENANCE.md
|-- src/
|   |-- pipeline_a_classical/   # JSL Healthcare NLP pipeline
|   |-- pipeline_b_llm_retrieval/  # LLM + retrieval pipeline
|   \-- common/                 # schema, config, validate
|-- terminology/
|   \-- oncology_terminology.csv    # 580 curated concepts
|-- evaluation/
|   |-- evaluate_full.py
|   |-- render_report.py
|   |-- comparison_table.md
|   |-- results.json
|   \-- per_field_results.csv
|-- report/
|   \-- report.md
|-- docs/
|   \-- screenshots/
|-- README.md
|-- SUBMISSION.md
|-- requirements.txt
|-- config.yaml
|-- setup_jsl_env.ps1
|-- run_pipeline_a_jsl.py
\-- run_pipeline_b_real.py
```

## Requirements

- Python version: 3.10
- Java version: Java 11 (required by spark-nlp-jsl)
- spark-nlp-jsl 5.4.0
- Ollama 0.34.2 with llama3.1:8b
- Hardware assumptions: Intel CPU, 16GB RAM, Windows 10 (Pipeline A requires 32GB RAM for full execution)

## Setup

1. Clone the repository:
   `git clone https://github.com/Junaidchohan/Oncology_Registry_Extraction.git`
2. Create and activate environment:
   `python -m venv .venv`
      `python -m venv .venv`
   `.venv/Scripts/activate` (Windows)
   `source .venv/bin/activate` (macOS/Linux)
3. Install dependencies:
   `pip install -r requirements.txt`
4. Place JSL license:
   Create `secrets/jsl_license.json` containing `SPARK_NLP_LICENSE` and credentials.
5. Start Ollama and pull model:
   `ollama serve` (in a separate terminal)
   `ollama pull llama3.1:8b`

## Running the pipelines

Pipeline A (Classical NLP):
`python run_pipeline_a_jsl.py`
- Expected runtime: ~33s per report (~5.5 minutes for 10 reports).
- Scope-down note: If Pipeline A crashes on Windows with Hadoop JNI error (NativeIO$Windows.access0), note that execution is frozen at commit 16e665e.

Pipeline B (LLM + Retrieval):
`python run_pipeline_b_real.py`
- Expected runtime: ~1354s per report (~3.75 hours for 10 reports).

## Running the evaluation

`python evaluation/evaluate_full.py`
`python evaluation/render_report.py`

## Terminology

- SNOMED CT 2025-01-31
- ICD-10-CM FY2025
- ICD-O-3 Edition 3.2
- LOINC Version 2.79
- ATC WHO 2025
- Index size: 580 concepts

## Results

| Metric | Pipeline A - Classical NLP | Pipeline B - LLM + Retrieval |
| --- | --- | --- |
| Entity NER P / R / F1 (span-based) | 14.8% / 15.1% / 14.9% | 32.6% / 43.3% / 37.2% |
| Field value exact accuracy | 46.1% (83/180) | 35.6% (64/180) |
| Assertion / State accuracy | 70.0% (126/180) | 53.9% (97/180) |
| Relation F1 | 21.1% | 25.8% |
| Retrieval Recall@K | 5.4% (2/37) | 43.2% (16/37) |
| Selection accuracy | 5.4% (2/37) | 29.7% (11/37) |
| Located evidence rate | 86.7% | 80.3% |
| Value-in-evidence rate | 69.0% | 61.1% |
| Unsupported field rate | 68.1% (77 fields) | 42.7% (67 fields) |
| Evidence-unsupported fields | 59 | 68 |
| Invalid code rate | 0.0% | 0.0% |
| Mean runtime | 32.85s | 1354.28s |
| Mean cost | $0.0000 | $0.0000 |

## Scope-downs and limitations

- Pipeline A code resolution is frozen at commit 16e665e due to a Hadoop JNI limitation on Windows.
- Gold annotations are candidate-created, not independently adjudicated.
- Terminology index is a curated subset of 580 concepts.
- tumor_size_to_lesion and biomarker_result_to_assay relation scores are 0% because lesion_id is not emitted.

## Model and API cost

- $0.00 per report (fully local inference).

## Contact

Muhammad Junaid
