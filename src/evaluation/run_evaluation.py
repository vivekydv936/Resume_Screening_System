"""Reproducible Phase 4 evaluation using synthetic, manually judged PDF pairs."""

from __future__ import annotations

import json
import math
import tempfile
import time
from pathlib import Path
from typing import Any

from src.scoring.scoring_engine import screen_resume

ROOT = Path(__file__).resolve().parents[2]


def make_pdf(text: str) -> bytes:
    """Create a minimal synthetic text PDF for offline evaluation."""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET"
    return f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {len(stream)} >> stream
{stream}
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
trailer << /Root 1 0 R >> %%EOF
""".encode("latin-1")


CASES = [
    {
        "name": "python_backend_strong",
        "jd": "Required: Python, FastAPI, SQL, REST APIs. 3 years experience.",
        "resume": "Python FastAPI SQL REST APIs. 5 years experience.",
        "relevant": True,
    },
    {
        "name": "python_backend_partial",
        "jd": "Required: Python, FastAPI, SQL, REST APIs. 3 years experience.",
        "resume": "Python and SQL developer. 3 years experience.",
        "relevant": True,
    },
    {
        "name": "unrelated_java",
        "jd": "Required: Python, FastAPI, SQL, REST APIs. 3 years experience.",
        "resume": "Java and Spring developer. 4 years experience.",
        "relevant": False,
    },
    {
        "name": "data_science_strong",
        "jd": "Required: Python, scikit-learn, Machine Learning, Pandas.",
        "resume": "Python, sklearn, machine learning and Pandas projects.",
        "relevant": True,
    },
    {
        "name": "data_science_unrelated",
        "jd": "Required: Python, scikit-learn, Machine Learning, Pandas.",
        "resume": "HR recruitment, communication and Excel.",
        "relevant": False,
    },
    {
        "name": "empty_text",
        "jd": "Required: Python, SQL.",
        "resume": "",
        "relevant": False,
    },
]


def _ndcg(relevances: list[int], k: int) -> float:
    values = relevances[:k]
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(values))
    ideal = sorted(values, reverse=True)
    idcg = sum(value / math.log2(index + 2) for index, value in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg else 0.0


def run_evaluation(root: Path = ROOT) -> dict[str, Any]:
    """Run cases, calculate ranking metrics, and write JSON/Markdown outputs."""
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="resume-eval-") as directory:
        for case in CASES:
            path = Path(directory) / f"{case['name']}.pdf"
            path.write_bytes(make_pdf(case["resume"]))
            started = time.perf_counter()
            result = screen_resume(path, case["jd"], case["name"])
            elapsed = time.perf_counter() - started
            results.append({
                "name": case["name"],
                "expected_relevant": case["relevant"],
                "score": result["final_score"],
                "parsing_status": result["parsing_status"],
                "skill_coverage": result["skill_coverage"],
                "elapsed_seconds": round(elapsed, 6),
            })
    ranked = sorted(results, key=lambda row: (row["score"] is None, -(row["score"] or 0), row["name"]))
    relevant_in_top = sum(int(row["expected_relevant"]) for row in ranked[:3])
    total_relevant = sum(int(row["expected_relevant"]) for row in results)
    metrics = {
        "sample_size": len(results),
        "parsing_success_rate": round(sum(row["parsing_status"] == "success" for row in results) / len(results), 4),
        "average_processing_seconds": round(sum(row["elapsed_seconds"] for row in results) / len(results), 6),
        "precision_at_3": round(relevant_in_top / 3, 4),
        "recall_at_3": round(relevant_in_top / total_relevant, 4),
        "ndcg_at_3": _ndcg([int(row["expected_relevant"]) for row in ranked], 3),
        "ranking_order": [row["name"] for row in ranked],
        "methodology": "Six synthetic PDF cases with manually defined relevance before execution. Relevant means the resume explicitly covers the JD's required skills; these labels are evaluation judgments, not hiring labels.",
    }
    output = {"metrics": metrics, "cases": results}
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "evaluation.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (reports / "evaluation_report.md").write_text(_markdown(output), encoding="utf-8")
    return output


def _markdown(output: dict[str, Any]) -> str:
    metrics = output["metrics"]
    lines = [
        "# Phase 4 Evaluation Report",
        "",
        "## Method",
        metrics["methodology"],
        "The evaluation is separate from the supplied `dataset.csv`; no `predicted_score` or `shortlisted` label was used.",
        "",
        "## Measured metrics",
        f"- Sample size: **{metrics['sample_size']}** synthetic PDFs.",
        f"- Parsing success rate: **{metrics['parsing_success_rate']:.2%}**.",
        f"- Average processing time: **{metrics['average_processing_seconds']:.6f} seconds per PDF**.",
        f"- Precision@3: **{metrics['precision_at_3']:.4f}**.",
        f"- Recall@3: **{metrics['recall_at_3']:.4f}**.",
        f"- NDCG@3: **{metrics['ndcg_at_3']:.4f}**.",
        "",
        "## Limitations",
        "- The sample is small, synthetic, and manually judged; it does not estimate production hiring performance.",
        "- Timing depends on the local Windows interpreter and spaCy fallback/model availability.",
        "- Ranking metrics are only meaningful for these declared synthetic relevance judgments.",
        "- The original labels were not used for supervised classification because Phase 1 found a near-zero correlation between `predicted_score` and `shortlisted` and their provenance is not independently verified.",
        "",
        "## Case results",
        "| Case | Expected relevant | Parsing | Score | Skill coverage | Time (s) |",
        "|---|---:|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['name']} | {row['expected_relevant']} | {row['parsing_status']} | {row['score']} | {row['skill_coverage']} | {row['elapsed_seconds']} |"
        for row in output["cases"]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run_evaluation()
