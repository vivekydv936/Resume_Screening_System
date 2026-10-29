"""Counterfactual fairness checks without inferring protected attributes."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from src.evaluation.run_evaluation import make_pdf
from src.scoring.scoring_engine import screen_resume

ROOT = Path(__file__).resolve().parents[2]

PAIRS = [
    ("name_pair_1", "Alex Morgan", "Jordan Lee"),
    ("name_pair_2", "Priya Shah", "Michael Chen"),
    ("cue_pair_1", "She is a candidate", "He is a candidate"),
    ("cue_pair_2", "female candidate", "male candidate"),
]
JD = "Required: Python, SQL, Machine Learning. 3 years experience."
QUALIFICATIONS = "Python SQL Machine Learning. 5 years experience. Bachelor degree."


def run_fairness_audit(root: Path = ROOT) -> dict[str, Any]:
    """Compare scores while holding job-relevant qualifications constant."""
    rows = []
    with tempfile.TemporaryDirectory(prefix="resume-fairness-") as directory:
        for name, first_cue, second_cue in PAIRS:
            results = []
            for index, cue in enumerate((first_cue, second_cue), start=1):
                path = Path(directory) / f"{name}-{index}.pdf"
                path.write_bytes(make_pdf(f"{cue}. {QUALIFICATIONS}"))
                results.append(screen_resume(path, JD, f"{name}-{index}"))
            first, second = results
            rows.append({
                "pair": name,
                "first_cue": first_cue,
                "second_cue": second_cue,
                "text_similarity_difference": round(first["text_similarity"] - second["text_similarity"], 4),
                "final_score_difference": round((first["final_score"] or 0) - (second["final_score"] or 0), 4),
                "first_matched_skills": first["matched_skills"],
                "second_matched_skills": second["matched_skills"],
                "rank_changed": (first["final_score"] or 0) != (second["final_score"] or 0),
            })
    output = {
        "pairs_tested": len(rows),
        "changed_pairs": sum(row["final_score_difference"] != 0 for row in rows),
        "results": rows,
        "limitations": [
            "The supplied dataset has no validated gender, age, or name attributes, so group-level fairness metrics are not valid.",
            "These are controlled text counterfactuals, not evidence about real demographic groups.",
            "Name and pronoun tokens can change lexical TF-IDF similarity even when qualifications are identical.",
            "No protected attribute is intentionally used by the scoring formula.",
        ],
    }
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "fairness.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (reports / "fairness_report.md").write_text(_markdown(output), encoding="utf-8")
    return output


def _markdown(output: dict[str, Any]) -> str:
    lines = [
        "# Fairness Audit Report",
        "",
        "## Data availability",
        "The supplied eight-column dataset contains no validated gender, age, or name fields. Group-level demographic parity, equal opportunity, and related metrics were therefore not calculated.",
        "",
        "## Controlled counterfactual method",
        f"{output['pairs_tested']} pairs were created. Each pair kept the same explicit job-relevant qualifications and changed only a name, pronoun, or gender cue. The files were temporary and deleted after scoring.",
        "",
        "## Results",
        f"- Pairs with a non-zero final-score difference: **{output['changed_pairs']} of {output['pairs_tested']}**.",
        "",
        "| Pair | TF-IDF difference | Final-score difference | Matched skills equal |",
        "|---|---:|---:|---|",
    ]
    lines.extend(
        f"| {row['pair']} | {row['text_similarity_difference']} | {row['final_score_difference']} | {row['first_matched_skills'] == row['second_matched_skills']} |"
        for row in output["results"]
    )
    lines.extend([
        "",
        "## Interpretation and limitations",
        *[f"- {item}" for item in output["limitations"]],
        "",
        "## Recommendations",
        "- Keep demographic cues out of the scoring features where they are not job-relevant.",
        "- Consider redacting names and pronouns before lexical similarity scoring if operationally appropriate.",
        "- Re-run group-level metrics only after obtaining lawful, consented, validated demographic data and an approved evaluation protocol.",
        "- Preserve human review and record overrides; this prototype must not make autonomous hiring decisions.",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run_fairness_audit()
