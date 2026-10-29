# Phase 4 Evaluation Report

## Method
Six synthetic PDF cases with manually defined relevance before execution. Relevant means the resume explicitly covers the JD's required skills; these labels are evaluation judgments, not hiring labels.
The evaluation is separate from the supplied `dataset.csv`; no `predicted_score` or `shortlisted` label was used.

## Measured metrics
- Sample size: **6** synthetic PDFs.
- Parsing success rate: **83.33%**.
- Average processing time: **0.086508 seconds per PDF**.
- Precision@3: **1.0000**.
- Recall@3: **1.0000**.
- NDCG@3: **1.0000**.

## Limitations
- The sample is small, synthetic, and manually judged; it does not estimate production hiring performance.
- Timing depends on the local Windows interpreter and spaCy fallback/model availability.
- Ranking metrics are only meaningful for these declared synthetic relevance judgments.
- The original labels were not used for supervised classification because Phase 1 found a near-zero correlation between `predicted_score` and `shortlisted` and their provenance is not independently verified.

## Case results
| Case | Expected relevant | Parsing | Score | Skill coverage | Time (s) |
|---|---:|---|---:|---:|---:|
| python_backend_strong | True | success | 93.46 | 100.0 | 0.137794 |
| python_backend_partial | True | success | 44.46 | 50.0 | 0.078233 |
| unrelated_java | False | success | 22.84 | 0.0 | 0.077097 |
| data_science_strong | True | success | 52.52 | 100.0 | 0.077592 |
| data_science_unrelated | False | success | 0.0 | 0.0 | 0.076414 |
| empty_text | False | empty | 0.0 | 0.0 | 0.07192 |
