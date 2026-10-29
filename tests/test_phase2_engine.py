from io import BytesIO

from src.matching.skill_matcher import match_skills
from src.matching.text_similarity import batch_tfidf_similarity, tfidf_similarity
from src.nlp.text_preprocessing import NLPProcessor
from src.parser.pdf_parser import parse_pdf
from src.scoring.scoring_engine import ScoringConfig, calculate_score, screen_resume


def _pdf(text: str) -> BytesIO:
    stream = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length {len(text) + 35} >>
stream
BT /F1 12 Tf 72 720 Td ({text}) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF
"""
    return BytesIO(stream.encode("latin-1"))


def test_valid_pdf_parsing_and_empty_pdf():
    result = parse_pdf(_pdf("Python SQL Bachelor degree"))
    assert result.status == "success"
    assert "Python" in result.text
    assert parse_pdf(_pdf("")).status in {"empty", "success"}


def test_invalid_pdf_handling():
    result = parse_pdf(BytesIO(b"not a pdf"), "candidate")
    assert result.status == "unreadable"
    assert result.text == ""


def test_skill_extraction_synonyms_and_missing_skills():
    processor = NLPProcessor.create()
    result = match_skills(
        "I build services with Python, sklearn and Fast API.",
        "Required: Python, scikit-learn, SQL, FastAPI. Optional: AWS.",
        processor,
    )
    assert {"Python", "scikit-learn", "FastAPI"} <= set(result.matched_skills)
    assert "SQL" in result.missing_skills
    assert result.skill_coverage == 75.0


def test_empty_jd_and_no_matching_skills():
    result = match_skills("Python SQL", "")
    assert result.required_skills == []
    assert result.skill_coverage == 0.0
    assert match_skills("Java", "Required: Python").missing_skills == ["Python"]


def test_tfidf_similarity_behavior():
    assert tfidf_similarity("", "Python") == 0.0
    assert tfidf_similarity("Python SQL", "Python SQL") == 100.0
    assert tfidf_similarity("Java", "Python") == 0.0
    assert batch_tfidf_similarity(["Python SQL", "Java"], "Python SQL") == [100.0, 0.0]


def test_scoring_calculation_and_missing_component_policy():
    skills = match_skills("Python SQL", "Required: Python SQL")
    result = calculate_score(80, skills, 50, 100)
    assert result["final_score"] == 82.5
    missing = calculate_score(80, skills, None, None)
    assert missing["final_score"] == 87.5
    incomplete = calculate_score(80, skills, None, None, ScoringConfig(missing_component_policy="incomplete"))
    assert incomplete["final_score"] is None


def test_public_screening_output_structure(tmp_path):
    path = tmp_path / "resume.pdf"
    path.write_bytes(_pdf("Python SQL Bachelor degree").getvalue())
    result = screen_resume(path, "Required: Python, SQL. Bachelor's degree.", "C-1")
    expected = {
        "candidate_id", "parsing_status", "text_similarity", "skill_coverage",
        "matched_skills", "missing_skills", "experience_match", "education_match",
        "final_score", "score_breakdown", "relevant_evidence", "limitations_or_warnings",
    }
    assert set(result) == expected
    assert result["candidate_id"] == "C-1"
    assert result["parsing_status"] == "success"
    assert result["skill_coverage"] == 100.0
