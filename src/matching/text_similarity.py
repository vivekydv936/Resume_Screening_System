"""Reusable lexical TF-IDF similarity for resumes and job descriptions."""

from __future__ import annotations

from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def tfidf_similarity(resume_text: str, job_description: str) -> float:
    """Return lexical cosine similarity normalized to 0-100."""
    if not resume_text.strip() or not job_description.strip():
        return 0.0
    try:
        vectors = TfidfVectorizer(lowercase=True, ngram_range=(1, 2)).fit_transform(
            [resume_text, job_description]
        )
        return round(float(cosine_similarity(vectors[0:1], vectors[1:2])[0, 0] * 100), 2)
    except ValueError:
        return 0.0


def batch_tfidf_similarity(resume_texts: Sequence[str], job_description: str) -> list[float]:
    """Score multiple resumes against one JD using a shared vocabulary."""
    if not job_description.strip():
        return [0.0 for _ in resume_texts]
    texts = list(resume_texts) + [job_description]
    try:
        vectors = TfidfVectorizer(lowercase=True, ngram_range=(1, 2)).fit_transform(texts)
    except ValueError:
        return [0.0 for _ in resume_texts]
    return [round(float(cosine_similarity(vectors[index:index + 1], vectors[-1:])[0, 0] * 100), 2) for index in range(len(resume_texts))]
