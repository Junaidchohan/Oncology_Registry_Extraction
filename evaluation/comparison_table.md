# Pipeline Evaluation: Side-by-Side Comparison

*Generated: 2026-09-23T21:52:02.474726Z*

| Metric | Pipeline A — Classical NLP | Pipeline B — LLM + Retrieval |
| --- | --- | --- |
| Entity P / R / F1 | 100.0% / 91.0% / 95.3% | 100.0% / 68.1% / 81.0% |
| Entity TP / FP / FN | 191 / 0 / 19 | 143 / 0 / 67 |
| Field value exact accuracy | 28.1% (59/210) | 23.3% (49/210) |
| Assertion / State accuracy | 57.1% (120/210) | 55.7% (117/210) |
| Relation / Macro F1 (field-level) | 95.3% | 81.0% |
| Terminology code precision | 17.4% (12/69) | 20.3% (13/64) |
| Terminology code recall (Recall@K) | 33.3% (12/36) | 36.1% (13/36) |
| Terminology F1 | 22.9% | 26.0% |
| Unsupported field rate | 0.0% (0 fields) | 0.0% (0 fields) |
| Mean runtime per report | 1002.49s | 977.85s |
| Mean cost per report | $0.0000 | $0.0000 |
| Total cost (10 reports) | $0.0000 | $0.0000 |
