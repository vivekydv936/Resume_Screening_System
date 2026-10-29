from pathlib import Path

import pandas as pd
import pytest

from src.data.clean import audit_dataset, clean_dataset
from src.data.generate_synthetic import generate_records
from src.data.validation import EXPECTED_COLUMNS, validate_dataset

ROOT = Path(__file__).resolve().parents[1]


def test_supplied_dataset_has_expected_schema_and_values():
    data = pd.read_csv(ROOT / "dataset (1).csv")
    assert validate_dataset(data) == []
    assert list(data.columns) == EXPECTED_COLUMNS
    assert len(data) == 500
    assert data["resume_id"].is_unique


def test_cleaning_preserves_required_schema():
    cleaned = clean_dataset(pd.read_csv(ROOT / "dataset (1).csv"))
    assert list(cleaned.columns) == EXPECTED_COLUMNS
    assert audit_dataset(cleaned)["duplicate_rows"] == 0


def test_invalid_range_is_reported():
    data = pd.read_csv(ROOT / "dataset (1).csv")
    data.loc[0, "keyword_density"] = 2
    assert any("keyword_density" in error for error in validate_dataset(data))


def test_synthetic_generation_is_reproducible_and_valid():
    first = generate_records(25)
    second = generate_records(25)
    pd.testing.assert_frame_equal(first, second)
    assert validate_dataset(first) == []


def test_missing_source_is_explicit():
    from src.data.validation import locate_source
    with pytest.raises(FileNotFoundError):
        locate_source(ROOT / "does-not-exist", "dataset.csv")
