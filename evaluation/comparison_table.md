# Pipeline Evaluation: Side-by-Side Comparison

*Generated: 2026-09-26T10:53:30.035112Z*

| Metric | Pipeline A — Classical NLP | Pipeline B — LLM + Retrieval |
| --- | --- | --- |
| Entity P / R / F1 | 100.0% / 65.2% / 79.0% | 100.0% / 68.1% / 81.0% |
| Entity TP / FP / FN | 137 / 0 / 73 | 143 / 0 / 67 |
| Field value exact accuracy | 11.9% (25/210) | 23.3% (49/210) |
| Assertion / State accuracy | 49.0% (103/210) | 55.7% (117/210) |
| Relation / Macro F1 (field-level) | 79.0% | 81.0% |
| Terminology code precision | 50.0% (2/4) | 17.7% (11/62) |
| Terminology code recall (Recall@K) | 5.6% (2/36) | 30.6% (11/36) |
| Terminology F1 | 10.0% | 22.4% |
| Unsupported field rate | 0.0% (0 fields) | 0.0% (0 fields) |
| Mean runtime per report | 32.85s | 692.10s |
| Mean cost per report | $0.0000 | $0.0000 |
| Total cost (10 reports) | $0.0000 | $0.0000 |
