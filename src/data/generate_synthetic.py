"""Generate optional, reproducible synthetic records for staging only."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from src.data.validation import EXPECTED_COLUMNS, require_valid_dataset

SEED = 20251029
ROLES: dict[str, tuple[str, ...]] = {
    "Data_Analyst": ("Python", "SQL", "Pandas", "Power BI"),
    "Software_Engineer": ("Python", "Java", "REST APIs", "Git"),
    "HR_Executive": ("Recruitment", "HRIS", "Excel", "Communication"),
    "Project_Manager": ("Agile", "Jira", "Risk Management", "Leadership"),
    "QA_Engineer": ("Testing", "Selenium", "SQL", "API Testing"),
    "ML_Engineer": ("Python", "scikit-learn", "TensorFlow", "MLOps"),
    "Cloud_Engineer": ("AWS", "Docker", "Kubernetes", "Linux"),
    "Cybersecurity_Analyst": ("SIEM", "Python", "Networking", "Risk Management"),
    "UX_Designer": ("Figma", "User Research", "Prototyping", "Usability"),
    "Database_Administrator": ("SQL", "Oracle", "Backup", "Performance Tuning"),
}


def generate_records(count: int, seed: int = SEED) -> pd.DataFrame:
    """Generate domain-shaped records with explicitly rule-based labels."""
    if count < 0:
        raise ValueError("count must be non-negative")
    rng = np.random.default_rng(seed)
    faker = Faker()
    faker.seed_instance(seed)
    roles = list(ROLES)
    rows: list[dict[str, object]] = []
    for index in range(count):
        experience = faker.random_int(min=0, max=15)
        skills = faker.random_int(min=3, max=15)
        education = faker.random_int(min=60, max=100)
        density = float(rng.uniform(0.1, 0.9))
        score = round(min(100, max(0, 0.35 * skills / 15 * 100 + 0.25 * education + 0.2 * density * 100 + 0.2 * experience / 15 * 100)), 1)
        rows.append({
            "resume_id": f"SYN{index + 1:05d}",
            "job_role": faker.random_element(elements=roles),
            "years_exp": experience,
            "skills_matched": skills,
            "education_score": education,
            "keyword_density": round(density, 3),
            "predicted_score": score,
            "shortlisted": int(score >= 70),
        })
    result = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    require_valid_dataset(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=4500)
    parser.add_argument("--output", type=Path, default=Path("data/staging/synthetic_dataset.csv"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_records(args.count).to_csv(args.output, index=False)
    print(f"Wrote {args.count} validated synthetic records to {args.output}")


if __name__ == "__main__":
    main()
