"""Explicit skill extraction and JD-to-resume skill comparison."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Mapping

from src.matching.skill_dictionary import ROLE_SKILLS, SKILL_ALIASES
from src.nlp.text_preprocessing import NLPProcessor


@dataclass(frozen=True)
class SkillMatch:
    """Explainable skill comparison output."""

    required_skills: list[str]
    optional_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    optional_matched_skills: list[str]
    skill_coverage: float
    explicit_skill_evidence: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _explicit_optional(text: str, skills: list[str]) -> tuple[list[str], list[str]]:
    optional_match = re.search(r"(?is)(?:optional|nice to have|preferred)[:\-]?(.*?)(?:\n\n|$)", text)
    if not optional_match:
        return [], skills
    optional_text = optional_match.group(1)
    optional = [skill for skill in skills if re.search(rf"\b{re.escape(skill)}\b", optional_text, re.I)]
    return optional, [skill for skill in skills if skill not in optional]


def extract_skills(text: str, processor: NLPProcessor | None = None) -> list[str]:
    """Extract only skills explicitly present in text."""
    active = processor or NLPProcessor.create()
    return active.extract_phrases(text, SKILL_ALIASES)


def match_skills(
    resume_text: str,
    job_description: str,
    processor: NLPProcessor | None = None,
    terminology: Mapping[str, tuple[str, ...]] = SKILL_ALIASES,
) -> SkillMatch:
    """Match explicitly identified resume skills against explicitly identified JD skills."""
    active = processor or NLPProcessor.create()
    resume_skills = active.extract_phrases(resume_text, terminology)
    jd_skills = active.extract_phrases(job_description, terminology)
    optional, required = _explicit_optional(job_description, jd_skills)
    if not required:
        role_hint = next((role for role in ROLE_SKILLS if role.lower() in job_description.lower()), None)
        if role_hint and re.search(r"\b(?:required|must have|requirements?)\b", job_description, re.I):
            required = [skill for skill in ROLE_SKILLS[role_hint] if skill in jd_skills]
    matched = [skill for skill in required if skill in resume_skills]
    missing = [skill for skill in required if skill not in resume_skills]
    optional_matched = [skill for skill in optional if skill in resume_skills]
    evidence = {skill: "explicit phrase match in resume" for skill in matched}
    coverage = round(100.0 * len(matched) / len(required), 2) if required else 0.0
    return SkillMatch(required, optional, matched, missing, optional_matched, coverage, evidence)
