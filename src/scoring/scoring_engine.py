"""Explainable, configurable resume scoring and Flask-facing public interface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.matching.skill_matcher import SkillMatch, match_skills
from src.matching.text_similarity import tfidf_similarity
from src.nlp.text_preprocessing import NLPProcessor
from src.parser.pdf_parser import ParseResult, parse_pdf


@dataclass(frozen=True)
class ScoringConfig:
    """Starting weights; they are assumptions, not validated optimal values."""

    text_similarity_weight: float = 0.50
    skill_coverage_weight: float = 0.30
    experience_weight: float = 0.15
    education_weight: float = 0.05
    shortlist_threshold: float = 70.0
    missing_component_policy: str = "renormalize"

    def weights(self) -> dict[str, float]:
        return {
            "text_similarity": self.text_similarity_weight,
            "skill_coverage": self.skill_coverage_weight,
            "experience_match": self.experience_weight,
            "education_match": self.education_weight,
        }


def _years(text: str) -> float | None:
    match = re.search(r"(?i)(?:at least|minimum of|min\.?|over)?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", text)
    return float(match.group(1)) if match else None


def _component_match(candidate: float | None, requirement: float | None) -> float | None:
    if candidate is None or requirement is None:
        return None
    if requirement <= 0:
        return 100.0
    return round(min(100.0, candidate / requirement * 100), 2)


def _education_match(resume: str, jd: str) -> float | None:
    requirement = re.search(r"(?i)\b(phd|doctorate|master'?s?|bachelor'?s?|degree)\b", jd)
    if not requirement:
        return None
    levels = {"degree": 1, "bachelor": 1, "bachelor's": 1, "master": 2, "master's": 2, "phd": 3, "doctorate": 3}
    candidate = max((value for term, value in levels.items() if re.search(rf"\b{re.escape(term)}\b", resume, re.I)), default=0)
    target = levels.get(requirement.group(1).lower(), 1)
    return round(min(100.0, candidate / target * 100), 2) if candidate else 0.0


def calculate_score(
    text_similarity: float,
    skill_match: SkillMatch,
    experience_match: float | None,
    education_match: float | None,
    config: ScoringConfig = ScoringConfig(),
) -> dict[str, Any]:
    """Calculate a score, renormalizing only available components by policy."""
    components = {
        "text_similarity": text_similarity,
        "skill_coverage": skill_match.skill_coverage,
        "experience_match": experience_match,
        "education_match": education_match,
    }
    weights = config.weights()
    available = {name: value for name, value in components.items() if value is not None}
    warnings: list[str] = []
    if config.missing_component_policy != "renormalize" and len(available) != len(components):
        return {"final_score": None, "components": components, "weighted_components": {}, "warnings": ["Score incomplete because a weighted component is unavailable."]}
    if len(available) != len(components):
        warnings.append("Unavailable components were excluded and remaining weights were renormalized.")
    denominator = sum(weights[name] for name in available)
    weighted = {name: round(value * weights[name] / denominator, 2) for name, value in available.items()}
    return {
        "final_score": round(sum(weighted.values()), 2),
        "components": components,
        "weighted_components": weighted,
        "warnings": warnings,
    }


def screen_resume(
    resume_file: str | Path,
    job_description: str,
    candidate_id: str | None = None,
    scoring_config: ScoringConfig | None = None,
) -> dict[str, Any]:
    """Screen one PDF and return a stable, explainable result dictionary."""
    config = scoring_config or ScoringConfig()
    parsed: ParseResult = parse_pdf(resume_file, candidate_id)
    processor = NLPProcessor.create()
    warnings = list(parsed.warnings) + processor.warnings()
    if not job_description.strip():
        warnings.append("Job description is empty; skill and lexical similarity evidence is unavailable.")
    skills = match_skills(parsed.text, job_description, processor)
    similarity = tfidf_similarity(parsed.text, job_description)
    score = calculate_score(
        similarity,
        skills,
        _component_match(_years(parsed.text), _years(job_description)),
        _education_match(parsed.text, job_description),
        config,
    )
    warnings.extend(score["warnings"])
    if parsed.status != "success":
        warnings.append("Candidate score is based on no extracted resume text and is not suitable for a hiring decision.")
    return {
        "candidate_id": parsed.candidate_id,
        "parsing_status": parsed.status,
        "text_similarity": similarity,
        "skill_coverage": skills.skill_coverage,
        "matched_skills": skills.matched_skills,
        "missing_skills": skills.missing_skills,
        "experience_match": score["components"]["experience_match"],
        "education_match": score["components"]["education_match"],
        "final_score": score["final_score"],
        "score_breakdown": {
            "weights": config.weights(),
            "components": score["components"],
            "weighted_components": score["weighted_components"],
            "shortlist_threshold": config.shortlist_threshold,
            "shortlist_review_aid": score["final_score"] is not None and score["final_score"] >= config.shortlist_threshold,
        },
        "relevant_evidence": skills.explicit_skill_evidence,
        "limitations_or_warnings": warnings,
    }
