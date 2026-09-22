# Oncology Registry Extraction

This project is aimed at extracting information for oncology registries using various natural language processing pipelines.

## Project Structure

- `data/`: Contains raw and gold standard data.
- `src/`: Source code for the extraction pipelines.
  - `pipeline_a_classical/`: Classical NLP approaches.
  - `pipeline_b_llm_retrieval/`: LLM and retrieval-based approaches.
  - `common/`: Shared utilities and code.
- `terminology/`: Terminologies, ontologies, and dictionaries used.
- `outputs/`: Generated outputs from the pipelines.
- `evaluation/`: Scripts and results for evaluating pipeline performance.
- `report/`: Generated reports and summaries.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure the paths and parameters in `config.yaml`.
3. Place the data in the `data/raw` and `data/gold` directories.
