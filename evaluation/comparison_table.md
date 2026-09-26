# Pipeline Evaluation: Side-by-Side Comparison

*Generated: 2026-09-26T14:46:04.186778Z*

Denominator: 180/200 fields evaluated (20 fields x 10 reports = 200; biomarkers and anticancer_medication arrays deferred to Phase 2)

| Metric | Pipeline A — Classical NLP | Pipeline B — LLM + Retrieval |
| --- | --- | --- |
| Entity P / R / F1 | 88.5% / 80.7% / 84.4% | 87.6% / 79.8% / 83.5% |
| Entity TP / FP / FN | 100 / 13 / 24 | 99 / 14 / 25 |
| Field value exact accuracy | 46.1% (83/180) | 52.2% (94/180) |
| Assertion / State accuracy | 53.3% (96/180) | 52.8% (95/180) |
| Relation F1 (not implemented — deferred to Phase 2) | — | — |
| Terminology code precision | 50.0% (2/4) | 17.2% (11/64) |
| Terminology code recall (Recall@K) | 5.4% (2/37) | 29.7% (11/37) |
| Terminology F1 | 9.8% | 21.8% |
| Unsupported field rate | 11.4% (13 fields) | 12.3% (14 fields) |
| Mean runtime per report | 32.85s | 692.10s |
| Mean cost per report | $0.0000 | $0.0000 |
| Total cost (10 reports) | $0.0000 | $0.0000 |

Array fields (biomarkers, anticancer_medication) are not scored in this table. Phase 2 will add per-assay comparison and per-drug comparison.
