# Pipeline Evaluation: Side-by-Side Comparison

*Generated: 2026-09-26T07:51:09.701997Z*

| Metric | Pipeline A — Classical NLP | Pipeline B — LLM + Retrieval |
| --- | --- | --- |
| Entity P / R / F1 | 100.0% / 62.9% / 77.2% | 100.0% / 68.1% / 81.0% |
| Entity TP / FP / FN | 132 / 0 / 78 | 143 / 0 / 67 |
| Field value exact accuracy | 10.5% (22/210) | 23.3% (49/210) |
| Assertion / State accuracy | 50.0% (105/210) | 55.7% (117/210) |
| Relation / Macro F1 (field-level) | 77.2% | 81.0% |
| Terminology code precision | 0.0% (0/0) | 17.7% (11/62) |
| Terminology code recall (Recall@K) | 0.0% (0/36) | 30.6% (11/36) |
| Terminology F1 | 0.0% | 22.4% |
| Unsupported field rate | 0.0% (0 fields) | 0.0% (0 fields) |
| Mean runtime per report | 32.85s | 692.10s |
| Mean cost per report | $0.0000 | $0.0000 |
| Total cost (10 reports) | $0.0000 | $0.0000 |
