"""Load, audit, and clean the Phase 1 dataset without changing raw inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.data.validation import EXPECTED_COLUMNS, require_valid_dataset


def load_dataset(path: Path) -> pd.DataFrame:
    """Load a CSV and enforce the required eight-column schema."""
    data = pd.read_csv(path)
    require_valid_dataset(data)
    return data


def audit_dataset(data: pd.DataFrame) -> dict[str, Any]:
    """Return reproducible descriptive audit results for a validated dataset."""
    require_valid_dataset(data)
    numeric = data.select_dtypes(include="number")
    return {
        "rows": int(len(data)),
        "columns": int(len(data.columns)),
        "column_order": list(data.columns),
        "dtypes": {key: str(value) for key, value in data.dtypes.items()},
        "null_counts": {key: int(value) for key, value in data.isna().sum().items()},
        "duplicate_rows": int(data.duplicated().sum()),
        "duplicate_resume_ids": int(data["resume_id"].duplicated().sum()),
        "numeric_ranges": {
            key: {"min": float(value.min()), "max": float(value.max())}
            for key, value in numeric.items()
        },
        "job_role_counts": {key: int(value) for key, value in data["job_role"].value_counts().items()},
        "shortlisted_counts": {str(key): int(value) for key, value in data["shortlisted"].value_counts().items()},
        "correlations": numeric.corr().round(4).to_dict(),
        "grouped_shortlist_rate": (
            data.groupby("job_role", observed=True)["shortlisted"].mean().round(4).to_dict()
        ),
    }


def clean_dataset(data: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy while preserving the exact required schema."""
    cleaned = data.copy()
    cleaned["resume_id"] = cleaned["resume_id"].astype("string").str.strip()
    cleaned["job_role"] = cleaned["job_role"].astype("string").str.strip()
    for column in EXPECTED_COLUMNS[2:]:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="raise")
    require_valid_dataset(cleaned)
    return cleaned[EXPECTED_COLUMNS]
