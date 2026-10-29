"""Flask entry point for the resume screening prototype."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_file
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from src.scoring.scoring_engine import screen_resume

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
IS_VERCEL = os.environ.get("VERCEL") == "1"
DEFAULT_DATABASE = (
    "/tmp/screening.sqlite3"
    if IS_VERCEL
    else str(ROOT / "data" / "screening.sqlite3")
)
DEFAULT_MAX_CONTENT_LENGTH = 4 * 1024 * 1024 if IS_VERCEL else 10 * 1024 * 1024
DATABASE_COLUMNS = (
    "candidate_id", "session_id", "parsing_status", "text_similarity",
    "skill_coverage", "matched_skills", "missing_skills", "experience_match",
    "education_match", "final_score", "score_breakdown", "evidence", "warnings",
    "review_decision", "reviewer_notes", "reviewed_at", "created_at",
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    parsing_status TEXT NOT NULL,
    text_similarity REAL,
    skill_coverage REAL,
    matched_skills TEXT NOT NULL,
    missing_skills TEXT NOT NULL,
    experience_match REAL,
    education_match REAL,
    final_score REAL,
    score_breakdown TEXT NOT NULL,
    evidence TEXT NOT NULL,
    warnings TEXT NOT NULL,
    review_decision TEXT,
    reviewer_notes TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
"""


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE", DEFAULT_DATABASE),
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_CONTENT_LENGTH", DEFAULT_MAX_CONTENT_LENGTH)),
        MAX_RESUMES=int(os.environ.get("MAX_RESUMES", 20)),
        MAX_RESUME_BYTES=DEFAULT_MAX_CONTENT_LENGTH,
        ENVIRONMENT=os.environ.get("FLASK_ENV", "development"),
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    )
    if test_config:
        app.config.update(test_config)
    if app.config["ENVIRONMENT"] == "production" and app.config["SECRET_KEY"] == "dev-only-change-me":
        raise RuntimeError("Set a non-default SECRET_KEY before production deployment.")
    app.config["SESSION_COOKIE_SECURE"] = app.config["ENVIRONMENT"] == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    database = app.config["DATABASE_URL"] or app.config["DATABASE"]
    if app.config["ENVIRONMENT"] == "production" and not _is_postgres(database):
        raise RuntimeError("Set DATABASE_URL to a PostgreSQL connection string before production deployment.")
    if not _is_postgres(database):
        Path(database).parent.mkdir(parents=True, exist_ok=True)
    init_db(database)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.errorhandler(413)
    def request_too_large(_):
        return _error("The upload is too large.", 413)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/screen")
    def screen():
        job_description = request.form.get("job_description", "").strip()
        files = request.files.getlist("resumes")
        if not job_description:
            return _error("A job description is required.", 400)
        if not files or not any(file.filename for file in files):
            return _error("At least one PDF resume is required.", 400)
        if len(files) > app.config["MAX_RESUMES"]:
            return _error(f"Upload at most {app.config['MAX_RESUMES']} resumes.", 400)
        session_id = uuid4().hex
        results = []
        for upload in files:
            if not upload.filename or Path(upload.filename).suffix.lower() != ".pdf":
                return _error("Only PDF resume files are accepted.", 400)
            candidate_id = uuid4().hex
            safe_name = secure_filename(upload.filename)
            if not safe_name:
                return _error("One uploaded filename is invalid.", 400)
            with tempfile.TemporaryDirectory(prefix="resume-screen-") as directory:
                path = Path(directory) / safe_name
                upload.save(path)
                if path.stat().st_size > app.config["MAX_RESUME_BYTES"]:
                    return _error("Each resume must be at most 10 MB.", 413)
                with path.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        return _error("The uploaded file is not a valid PDF.", 400)
                try:
                    result = screen_resume(path, job_description, candidate_id)
                except Exception:
                    return _error("A resume could not be processed.", 422)
            _save_candidate(database, session_id, result)
            results.append(result)
        return jsonify({"session_id": session_id, "candidates": _sorted(results)})

    @app.get("/api/candidates")
    def candidates():
        return jsonify({"candidates": _sorted(_load_candidates(database))})

    @app.get("/api/candidates/<candidate_id>")
    def candidate(candidate_id: str):
        item = _load_candidate(database, candidate_id)
        if item is None:
            return _error("Candidate not found.", 404)
        return jsonify(item)

    @app.post("/api/candidates/<candidate_id>/review")
    def review(candidate_id: str):
        payload = request.get_json(silent=True) or {}
        decision = payload.get("decision")
        notes = str(payload.get("notes", "")).strip()
        if decision not in {"shortlist", "reject", "needs-review"}:
            return _error("Decision must be shortlist, reject, or needs-review.", 400)
        if decision != "needs-review" and not notes:
            return _error("Reviewer notes are required for an override decision.", 400)
        if not _load_candidate(database, candidate_id):
            return _error("Candidate not found.", 404)
        _save_review(database, candidate_id, decision, notes)
        return jsonify(_load_candidate(database, candidate_id))

    @app.get("/api/candidates.csv")
    def export_csv():
        output = io.StringIO()
        rows = _load_candidates(database)
        fields = ["candidate_id", "parsing_status", "final_score", "skill_coverage", "review_decision", "reviewer_notes"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)
        return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="screening_results.csv")

    return app


def init_db(database: str) -> None:
    with _connect(database) as connection:
        if _is_postgres(database):
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA)
        else:
            connection.executescript(SCHEMA)
        connection.commit()


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _save_candidate(database: str, session_id: str, result: dict[str, Any]) -> None:
    with _connect(database) as connection:
        connection.execute(
            """INSERT INTO candidates
            (candidate_id, session_id, parsing_status, text_similarity, skill_coverage,
             matched_skills, missing_skills, experience_match, education_match, final_score,
             score_breakdown, evidence, warnings, review_decision, reviewer_notes, reviewed_at, created_at)
            VALUES ({placeholders}, CURRENT_TIMESTAMP)""".format(
                placeholders=", ".join([_placeholder(database)] * 16)
            ),
            (
                result["candidate_id"], session_id, result["parsing_status"], result["text_similarity"],
                result["skill_coverage"], json.dumps(result["matched_skills"]), json.dumps(result["missing_skills"]),
                result["experience_match"], result["education_match"], result["final_score"],
                json.dumps(result["score_breakdown"]), json.dumps(result["relevant_evidence"]),
                json.dumps(result["limitations_or_warnings"]), None, None, None,
            ),
        )
        connection.commit()


def _save_review(database: str, candidate_id: str, decision: str, notes: str) -> None:
    with _connect(database) as connection:
        marker = _placeholder(database)
        connection.execute(
            f"UPDATE candidates SET review_decision={marker}, reviewer_notes={marker}, reviewed_at=CURRENT_TIMESTAMP WHERE candidate_id={marker}",
            (decision, notes, candidate_id),
        )
        connection.commit()


def _load_candidates(database: str) -> list[dict[str, Any]]:
    with _connect(database) as connection:
        cursor = connection.execute("SELECT * FROM candidates")
        rows = cursor.fetchall()
        if _is_postgres(database):
            rows = [dict(zip(DATABASE_COLUMNS, row)) for row in rows]
        else:
            rows = [dict(row) for row in rows]
    result = []
    for row in rows:
        item = dict(row)
        for field in ("matched_skills", "missing_skills", "score_breakdown", "evidence", "warnings"):
            item[field] = json.loads(item[field])
        item["relevant_evidence"] = item.pop("evidence")
        item["limitations_or_warnings"] = item.pop("warnings")
        result.append(item)
    return result


def _is_postgres(database: str) -> bool:
    return database.startswith(("postgresql://", "postgres://"))


def _placeholder(database: str) -> str:
    return "%s" if _is_postgres(database) else "?"


def _connect(database: str):
    if _is_postgres(database):
        import psycopg
        url = database.replace("postgres://", "postgresql://", 1)
        return psycopg.connect(url, connect_timeout=10)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def _load_candidate(database: str, candidate_id: str) -> dict[str, Any] | None:
    return next((item for item in _load_candidates(database) if item["candidate_id"] == candidate_id), None)


def _sorted(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: (item["final_score"] is None, -(item["final_score"] or 0), item["candidate_id"]))


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["ENVIRONMENT"] != "production")
