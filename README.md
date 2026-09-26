# Oncology Registry Extraction

> **Gold Standard Disclaimer:** The gold annotations in data/gold/ were authored by the candidate using a local LLM to produce the synthetic reports and their reference values. Pipeline A uses the John Snow Labs Healthcare NLP library (spark-nlp-jsl 5.4.0). Pipeline B uses llama3.1:8b via Ollama. Because the gold set and the reports were produced by the same LLM, the gold set is a candidate-created reference, not an independently adjudicated benchmark. Field-level accuracy figures measure internal consistency between LLM-generated artifacts, not external clinical validity.
>
> **Credentials:** API keys and JSL license tokens live in `secrets/` (git-ignored). Never committed.

---

This project implements two pipelines for extracting structured registry data from unstructured oncology pathology reports, extracting 21 clinical fields per report.

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
