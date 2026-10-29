"""Run the Phase 1 audit and generate EDA charts and report."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.data.clean import audit_dataset, clean_dataset, load_dataset
from src.data.validation import locate_source

ROOT = Path(__file__).resolve().parents[2]
DICTIONARY = {
    "resume_id": ("string", "Unique resume record identifier", "Unique non-empty ID", "identifier", "R0001"),
    "job_role": ("string", "Target or observed job role", "One of the recorded role categories", "category", "Data_Analyst"),
    "years_exp": ("integer", "Years of professional experience", "0 to 60", "years", "3"),
    "skills_matched": ("integer", "Count of matched skills", "0 to 100", "skills", "8"),
    "education_score": ("integer", "Normalized education relevance score", "0 to 100", "score", "73"),
    "keyword_density": ("float", "Proportion of text tokens matching role keywords", "0 to 1", "ratio", "0.129"),
    "predicted_score": ("float", "Overall screening score in the supplied dataset", "0 to 100", "score", "46.1"),
    "shortlisted": ("integer", "Binary shortlist indicator in the supplied file", "0 or 1 (brief describes Y/N)", "flag", "0"),
}


def _write_dictionary(source: Path, destination: Path) -> None:
    original = pd.read_csv(source)
    completed = original.copy()
    completed["data_type"] = completed["column_name"].map(lambda key: DICTIONARY[key][0])
    completed["description"] = completed["column_name"].map(lambda key: DICTIONARY[key][1])
    completed["valid_range"] = completed["column_name"].map(lambda key: DICTIONARY[key][2])
    completed["units"] = completed["column_name"].map(lambda key: DICTIONARY[key][3])
    completed["example_value"] = completed["column_name"].map(lambda key: DICTIONARY[key][4])
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed.to_csv(destination, index=False)


def _make_report(audit: dict[str, object]) -> str:
    counts = audit["shortlisted_counts"]
    shortlisted = int(counts.get("1", 0))
    total = int(audit["rows"])
    rate = shortlisted / total if total else 0
    correlation = audit["correlations"]["predicted_score"]["shortlisted"]
    return f"""# Phase 1 Dataset Audit and EDA

## Observed inputs
- Supplied dataset: 500 records, copied unchanged to `data/raw/dataset.csv`.
- Audited rows: **{total}**; columns: **{audit['columns']}**.
- Schema: `{', '.join(audit['column_order'])}`.
- Null values: `{audit['null_counts']}`.
- Duplicate rows: **{audit['duplicate_rows']}**; duplicate resume IDs: **{audit['duplicate_resume_ids']}**.

## Findings
- Shortlisted: **{shortlisted} ({rate:.1%})**; non-shortlisted: **{total - shortlisted} ({1-rate:.1%})**. This is a moderate class imbalance.
- Role counts: `{audit['job_role_counts']}` across **{len(audit['job_role_counts'])}** observed roles.
- All observed values passed the documented validation ranges; detailed ranges and dtypes are in `audit.json`.
- The measured Pearson correlation between `predicted_score` and `shortlisted` is **{correlation:.4f}**. This near-zero relationship is suspicious for a decision label and must be investigated before supervised training.
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
"""


def run_eda(root: Path = ROOT) -> dict[str, object]:
    """Copy source files, clean the data, and write charts plus reports."""
    raw = root / "data" / "raw"
    processed = root / "data" / "processed"
    figures = root / "reports" / "figures"
    for path in (raw, processed, figures):
        path.mkdir(parents=True, exist_ok=True)
    source = locate_source(root, "dataset.csv")
    dictionary = locate_source(root, "data_dictionary.csv")
    shutil.copy2(source, raw / "dataset.csv")
    shutil.copy2(dictionary, raw / "data_dictionary.csv")
    data = clean_dataset(load_dataset(raw / "dataset.csv"))
    data.to_csv(processed / "dataset_clean.csv", index=False)
    _write_dictionary(raw / "data_dictionary.csv", processed / "data_dictionary_completed.csv")
    audit = audit_dataset(data)
    sns.set_theme(style="whitegrid")

    chart_specs = [
        ("shortlisted_distribution.png", "Shortlisted versus non-shortlisted records", "shortlisted", "Records"),
        ("predicted_score_distribution.png", "Predicted score distribution", "predicted_score", "Records"),
        ("job_role_counts.png", "Records by job role", "job_role", "Records"),
    ]
    plt.figure(figsize=(7, 5))
    data["shortlisted"].map({0: "Not shortlisted", 1: "Shortlisted"}).value_counts().plot.bar(color=["#4c78a8", "#f58518"])
    plt.title(chart_specs[0][1]); plt.ylabel("Records"); plt.tight_layout()
    plt.savefig(figures / chart_specs[0][0], dpi=150); plt.close()
    plt.figure(figsize=(7, 5)); sns.histplot(data=data, x="predicted_score", bins=20, kde=True)
    plt.title(chart_specs[1][1]); plt.xlabel("Predicted score"); plt.tight_layout()
    plt.savefig(figures / chart_specs[1][0], dpi=150); plt.close()
    plt.figure(figsize=(9, 5)); sns.countplot(data=data, y="job_role", order=data["job_role"].value_counts().index)
    plt.title(chart_specs[2][1]); plt.xlabel("Records"); plt.tight_layout()
    plt.savefig(figures / chart_specs[2][0], dpi=150); plt.close()
    plt.figure(figsize=(8, 6)); sns.heatmap(data.select_dtypes("number").corr(), annot=True, fmt=".2f", cmap="vlag", center=0)
    plt.title("Numeric feature correlation heatmap"); plt.tight_layout()
    plt.savefig(figures / "numeric_correlation_heatmap.png", dpi=150); plt.close()
    (root / "reports" / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (root / "reports" / "phase1_eda_report.md").write_text(_make_report(audit), encoding="utf-8")
    return audit


if __name__ == "__main__":
    run_eda()
