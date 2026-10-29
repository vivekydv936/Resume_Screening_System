# AI Resume Screening & Candidate Shortlisting

Recruiters enter a job description and upload PDF resumes. The application extracts text, identifies explicit skills, calculates TF-IDF similarity and explainable component scores, ranks candidates, and records the recruiter's final decision separately from the automated recommendation.

> **Decision-support tool:** scores are not hiring probabilities or final hiring decisions. Human review is required.

## Features

- Multi-resume PDF upload with extension, content, and size validation
- Temporary processing with no default raw-resume retention
- PDF extraction using `pdfminer.six`
- spaCy normalization and phrase-based skill extraction
- Domain skill dictionary with synonym mapping
- TF-IDF and cosine similarity
- Explainable scoring:
  - Text similarity: 50%
  - Required skill coverage: 30%
  - Relevant experience: 15%
  - Education: 5%
- Ranked candidates with matched and missing skills
- Human review: shortlist, reject, and needs-review
- Reviewer notes stored independently from automated scores
- PostgreSQL persistence
- CSV export
- Evaluation and counterfactual fairness reports
- Responsive Flask dashboard

## Architecture

```text
JD + PDF Resumes
       |
       v
Flask Application
       |
PDFMiner -> spaCy -> Skill Matching -> TF-IDF -> Explainable Scoring
       |
       v
Candidate Ranking -> Human Review -> PostgreSQL
```

## Technology

| Area | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL |
| PDF processing | pdfminer.six |
| NLP | spaCy, PhraseMatcher |
| Matching | Skill dictionary, TF-IDF, cosine similarity |
| Frontend | HTML, CSS, Bootstrap, JavaScript |
| Deployment | Vercel Python runtime + Neon PostgreSQL |
| Testing | pytest |

## Project structure

```text
app.py                    Flask application and API routes
api/index.py              Vercel serverless entrypoint
vercel.json               Vercel configuration
src/parser/               PDF parsing
src/nlp/                  Text preprocessing
src/matching/             Skills and similarity
src/scoring/              Explainable scoring engine
src/data/                 Dataset validation and cleaning
src/eda/                  Exploratory data analysis
src/evaluation/           Evaluation and report generation
src/fairness/             Counterfactual fairness audit
templates/                Recruiter dashboard
static/                   Frontend assets
tests/                    Unit and integration tests
reports/                  Project documentation and results
```

## Local setup

Production mode requires PostgreSQL. Neon PostgreSQL can be used for both local development and Vercel.

```powershell
.\venv312\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
```

Create `.env` from [.env.example](./.env.example) and set your private values:

```env
FLASK_ENV=development
SECRET_KEY=<locally-generated-secret>
DATABASE_URL=<your-Neon-PostgreSQL-connection-string>
MAX_CONTENT_LENGTH=4194304
MAX_RESUMES=20
```

Generate a secret locally:

```powershell
.\venv312\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run the application:

```powershell
python app.py
```

Open `http://127.0.0.1:5000` and verify `http://127.0.0.1:5000/health`.

The PostgreSQL `candidates` table is initialized automatically. Never commit `.env`, database credentials, real resumes, or generated database files.

## Vercel deployment

The repository includes [vercel.json](./vercel.json) and [api/index.py](./api/index.py). Vercel auto-detects the Python function from the `api/` directory; no explicit runtime string is required.

1. Push the repository to GitHub and import it into Vercel.
2. Select the **Other** framework preset.
3. Leave the build command empty.
4. Add these Production environment variables:

   ```text
   FLASK_ENV=production
   SECRET_KEY=<long-random-secret>
   DATABASE_URL=<your-Neon-PostgreSQL-connection-string>
   MAX_CONTENT_LENGTH=4194304
   MAX_RESUMES=20
   ```

5. Deploy and verify:

   ```text
   https://<your-domain>/health
   ```

Expected response:

```json
{"status":"ok"}
```

Use a TLS-enabled Neon connection string. Vercel uploads are limited to 4 MB by the application configuration, so use compact PDFs. Do not use SQLite for Vercel persistence.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/screen` | Process a JD and PDF resumes |
| GET | `/api/candidates` | List ranked candidates |
| GET | `/api/candidates/<candidate_id>` | Candidate details |
| POST | `/api/candidates/<candidate_id>/review` | Save human review |
| GET | `/api/candidates.csv` | Export results |

## Tests and workflows

```powershell
pytest -q
python -m src.eda.run_eda
python -m src.evaluation.run_evaluation
python -m src.fairness.fairness_audit
python -m src.evaluation.build_documents
```

The verified test suite contains **16 passing tests**. Evaluation results are based on the documented synthetic evaluation set and do not establish real-world hiring performance.

## Responsible AI and privacy

- Automated scores are review aids, not final hiring decisions.
- Reviewer decisions are stored separately from computed scores.
- Candidate IDs do not depend on names or filenames.
- Raw PDFs are processed temporarily and are not retained by default.
- The dataset has no validated demographic attributes.
- Counterfactual tests do not prove that the system is fair.
- TF-IDF measures lexical overlap, not semantic understanding.
- Authentication and role-based access control require additional production work.
- DPDP Act 2023 applicability and institutional compliance require manual review.

## Documentation

- [Evaluation report](./reports/evaluation_report.md)
- [Fairness report](./reports/fairness_report.md)
- [Technical project report](./reports/project_report.docx)
- [Synopsis draft](./reports/Project_Synopsis_DRAFT_Name_RollNo.docx)
- [Demo script](./reports/demo_script.md)
- [Ethical compliance checklist](./reports/ethical_compliance_checklist.md)

## Deployment status

Configured for **Vercel + Neon PostgreSQL** and verified locally with PostgreSQL-backed startup, Vercel entrypoint import, `/health`, the full **16-test** suite, and zero Pylance diagnostics.
