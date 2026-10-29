"""Validation helpers for the supplied and generated resume datasets."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

EXPECTED_COLUMNS: Final[list[str]] = [
    "resume_id", "job_role", "years_exp", "skills_matched",
    "education_score", "keyword_density", "predicted_score", "shortlisted",
]


def validate_dataset(data: pd.DataFrame) -> list[str]:
    """Return all schema and value validation errors found in ``data``."""
    errors: list[str] = []
    if list(data.columns) != EXPECTED_COLUMNS:
        errors.append(f"Expected columns {EXPECTED_COLUMNS}, found {list(data.columns)}")
        return errors
    if data["resume_id"].isna().any() or data["resume_id"].duplicated().any():
        errors.append("resume_id values must be non-null and unique")
    if data["job_role"].isna().any():
        errors.append("job_role values must be non-null")
    for column, (minimum, maximum) in {
        "years_exp": (0, 60), "skills_matched": (0, 100),
        "education_score": (0, 100), "keyword_density": (0, 1),
        "predicted_score": (0, 100), "shortlisted": (0, 1),
    }.items():
        if not pd.api.types.is_numeric_dtype(data[column]):
            errors.append(f"{column} must be numeric")
            continue
        if data[column].isna().any():
            errors.append(f"{column} contains null values")
        if ((data[column] < minimum) | (data[column] > maximum)).any():
            errors.append(f"{column} must be in [{minimum}, {maximum}]")
    return errors


def require_valid_dataset(data: pd.DataFrame) -> None:
    """Raise a clear error when a dataset fails validation."""
    errors = validate_dataset(data)
    if errors:
        raise ValueError("Dataset validation failed:\n- " + "\n- ".join(errors))


def locate_source(root: Path, filename: str) -> Path:
    """Locate canonical or supplied '(1)' source files."""
    candidates = [root / filename, root / filename.replace(".csv", " (1).csv")]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Required source file not found: {filename}")
