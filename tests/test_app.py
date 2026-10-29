from io import BytesIO

import pytest

from app import create_app


def pdf(text: str) -> bytes:
    return f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {len(text) + 35} >> stream
BT /F1 12 Tf 72 720 Td ({text}) Tj ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
trailer << /Root 1 0 R >> %%EOF
""".encode("latin-1")


@pytest.fixture()
def client(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")}).test_client()


def upload(client, names=("a.pdf",)):
    return client.post(
        "/api/screen",
        data={
            "job_description": "Required: Python, SQL. Bachelor's degree.",
            "resumes": [(BytesIO(pdf("Python SQL Bachelor degree")), name) for name in names],
        },
        content_type="multipart/form-data",
    )


def test_health_and_validation(client):
    assert client.get("/health").json == {"status": "ok"}
    assert client.get("/health").headers["X-Content-Type-Options"] == "nosniff"
    assert client.post("/api/screen").status_code == 400
    assert client.post("/api/screen", data={"job_description": "Python"}).status_code == 400
    response = client.post("/api/screen", data={"job_description": "Python", "resumes": [(BytesIO(b"bad"), "a.txt")]}, content_type="multipart/form-data")
    assert response.status_code == 400
    response = client.post("/api/screen", data={"job_description": "Python", "resumes": [(BytesIO(b"not-a-pdf"), "a.pdf")]}, content_type="multipart/form-data")
    assert response.status_code == 400


def test_success_ranking_detail_review_and_csv(client):
    response = upload(client, ("one.pdf", "two.pdf"))
    assert response.status_code == 200
    items = response.json["candidates"]
    assert len(items) == 2
    assert items[0]["final_score"] >= items[1]["final_score"]
    candidate_id = items[0]["candidate_id"]
    assert client.get(f"/api/candidates/{candidate_id}").status_code == 200
    review = client.post(f"/api/candidates/{candidate_id}/review", json={"decision": "shortlist", "notes": "Reviewed against the JD."})
    assert review.status_code == 200
    assert review.json["review_decision"] == "shortlist"
    assert client.get("/api/candidates.csv").status_code == 200


def test_review_requires_notes_for_override(client):
    candidate_id = upload(client).json["candidates"][0]["candidate_id"]
    assert client.post(f"/api/candidates/{candidate_id}/review", json={"decision": "reject"}).status_code == 400
    assert client.post(f"/api/candidates/{candidate_id}/review", json={"decision": "needs-review"}).status_code == 200


def test_missing_candidate(client):
    assert client.get("/api/candidates/not-found").status_code == 404
