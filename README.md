# Oncology Registry Extraction

This project automates the extraction of unstructured oncology pathology reports into structured registry formats (demographics, TNM staging, histology, procedures, biomarkers) using dual Natural Language Processing (NLP) pipelines.

## Pipelines

1. **Pipeline A (Classical Healthcare NLP)**
   - Utilizes John Snow Labs `spark-nlp-jsl` for section detection, NER, assertion status, and entity resolution.
   - Includes a deterministic regex-based heuristic fallback mode for offline/unlicensed execution.

2. **Pipeline B (LLM + Local Terminology Retrieval)**
   - Uses an LLM (OpenAI API or local) for deterministic span extraction.
   - Grounds outputs using a local FAISS index against an oncology terminology dictionary (SNOMED, ICD-O-3, ICD-10, LOINC, ATC).
   - Employs a dual-backend FAISS encoder: `sentence-transformers` (all-MiniLM-L6-v2) or `sklearn` TF-IDF with character n-grams.

## Setup and Dependencies

**Prerequisites:** Python 3.10+

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Key dependencies: `johnsnowlabs`, `pyspark`, `spark-nlp-jsl`, `sentence-transformers`, `faiss-cpu`, `scikit-learn`, `openai`, `jsonschema`.*

2. Environment Variables (Optional):
   - `JSL_LICENSE_PATH`: Path to your JSL license JSON file for Pipeline A (otherwise runs in heuristic mode).
   - `OPENAI_API_KEY`: Key for Pipeline B extraction (otherwise runs in deterministic fallback mode).
   - `FORCE_TFIDF=1`: Forces Pipeline B to use the TF-IDF backend for FAISS (useful if `torch/torchvision` dependencies conflict on Windows).

## Running the Pipelines

You can run both pipelines and the evaluation script automatically:

```bash
# Windows PowerShell
$env:FORCE_TFIDF="1"
bash run_all.sh
python evaluation/evaluate.py
```

Outputs will be saved in `outputs/pipeline_a/` and `outputs/pipeline_b/`.

## Hardware and Cost Assumptions
- **Hardware:** Both pipelines run efficiently on CPU in heuristic/TF-IDF mode (<0.1s per report). Full JSL models or `sentence-transformers` benefit from 16GB RAM and a basic CUDA GPU.
- **Cost:** Offline heuristic execution is $0.00. Using `gpt-4o-mini` for Pipeline B extraction costs approximately $0.001 per pathology report.
