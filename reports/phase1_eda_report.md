# Phase 1 Dataset Audit and EDA

## Observed inputs
- Supplied dataset: 500 records, copied unchanged to `data/raw/dataset.csv`.
- Audited rows: **500**; columns: **8**.
- Schema: `resume_id, job_role, years_exp, skills_matched, education_score, keyword_density, predicted_score, shortlisted`.
- Null values: `{'resume_id': 0, 'job_role': 0, 'years_exp': 0, 'skills_matched': 0, 'education_score': 0, 'keyword_density': 0, 'predicted_score': 0, 'shortlisted': 0}`.
- Duplicate rows: **0**; duplicate resume IDs: **0**.

## Findings
- Shortlisted: **173 (34.6%)**; non-shortlisted: **327 (65.4%)**. This is a moderate class imbalance.
- Role counts: `{'HR_Executive': 120, 'QA_Engineer': 104, 'Data_Analyst': 102, 'Software_Engineer': 87, 'Project_Manager': 87}` across **5** observed roles.
- All observed values passed the documented validation ranges; detailed ranges and dtypes are in `audit.json`.
- The measured Pearson correlation between `predicted_score` and `shortlisted` is **-0.0085**. This near-zero relationship is suspicious for a decision label and must be investigated before supervised training.
- Feature correlations with `shortlisted` are weak in this sample; this does not establish model quality or causality.

## Limitations
- The brief describes `shortlisted` as Y/N, while the supplied CSV uses integer 0/1; the observed encoding is preserved.
- No demographic attributes are present, so demographic fairness cannot be estimated from this dataset.
- No timestamps or anomaly columns were added because the required schema is exactly eight columns.
- Synthetic labels are rule-based demonstrations, not real hiring decisions.

## Architecture
Resume PDF + Job Description -> Flask Application -> PDF Text Extraction -> spaCy Preprocessing -> Skill Extraction -> TF-IDF and Cosine Similarity -> Explainable Scoring -> Candidate Ranking -> Human Review

## Next phase
Phase 2 will implement PDF extraction, NLP preprocessing, skill extraction, TF-IDF similarity, explainable scoring, and focused unit tests.
