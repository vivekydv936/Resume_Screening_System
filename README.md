# AI-Based Resume Screening and Candidate Shortlisting System

This project implements the four-phase HCLTech Career Shaper Project No. 34 prototype: dataset foundation and EDA, offline PDF/NLP matching, Flask/PostgreSQL integration, and measured evaluation/fairness documentation. The original supplied files remain unchanged.

## Setup

```powershell
.\venv312\Scripts\Activate.ps1
pip install -r requirements-dev.txt
# Optional full spaCy model for statistical tokenization:
python -m spacy download en_core_web_sm
```

Use Neon PostgreSQL for local development and deployment by setting `DATABASE_URL`. Production mode requires PostgreSQL. `requirements.txt` contains runtime/Vercel dependencies; install `requirements-dev.txt` for tests, EDA, notebooks, and report generation.

## Deployment

For a local or internal Windows deployment, create a `.env` file from `.env.example`, set a long random `SECRET_KEY`, and run the Waitress WSGI server:

```powershell
Copy-Item .env.example .env
# Edit .env and replace SECRET_KEY before deployment
.\venv312\Scripts\Activate.ps1
pip install -r requirements.txt
python run_production.py
```

The default deployment URL is `http://127.0.0.1:8000`. Set `HOST=0.0.0.0` only when the host is intentionally reachable on a trusted network, and place a reverse proxy with HTTPS and authentication in front of any internet-facing deployment. Set `DATABASE_URL` to a PostgreSQL connection string for local and production use. Never commit `.env`, real resumes, or database credentials.

## Vercel deployment

The repository includes [`vercel.json`](./vercel.json) and [`api/index.py`](./api/index.py) for Vercel's Python serverless runtime.

1. Push the repository to GitHub and import it into Vercel.
2. Keep the framework preset as **Other** and leave the build command empty.
3. Add these Vercel Environment Variables for the **Production** environment:

   ```text
   FLASK_ENV=production
   SECRET_KEY=<a-long-random-secret>
   DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
   MAX_CONTENT_LENGTH=4194304
   MAX_RESUMES=20
   ```

4. Deploy and open the generated Vercel URL. Verify `https://<your-domain>/health` returns `{"status":"ok"}`.

The application uses PostgreSQL when `DATABASE_URL` starts with `postgresql://` or `postgres://`, and creates the `candidates` table automatically on startup. Vercel's request limit makes the deployed default upload limit 4 MB total; use smaller PDFs. Configure the database provider to allow Vercel connections and require TLS (for example, `sslmode=require`). Do not use SQLite on Vercel.

## Run the workflows

```powershell
python -m src.eda.run_eda
python -m src.evaluation.run_evaluation
python -m src.fairness.fairness_audit
python -m src.evaluation.build_documents
pytest
```

Outputs are written to `reports/` and the cleaned canonical copy is written to `data/processed/dataset_clean.csv`. The supplied source files are copied, not modified, to `data/raw/`.

The Phase 2 public interface is `src.scoring.scoring_engine.screen_resume`. Phase 3 exposes the same engine through `app.py` and Flask routes. The PostgreSQL schema is initialized automatically:

```powershell
python app.py
```

The dashboard is available at `http://127.0.0.1:5000`. API routes include `/health`, `/api/screen`, `/api/candidates`, `/api/candidates/<candidate_id>`, `/api/candidates/<candidate_id>/review`, and `/api/candidates.csv`. If `en_core_web_sm` is not installed, the engine uses spaCy's blank English pipeline for tokenization and phrase matching and reports that limitation in the result; it does not claim statistical model processing.

TF-IDF similarity is lexical overlap, not semantic understanding. Scores and the configurable shortlist threshold are decision-support aids only; reviewer decisions must remain separate.

To generate 4,500 reproducible synthetic records into staging (never directly into raw):

```powershell
python -m src.data.generate_synthetic --count 4500
```

Synthetic `shortlisted` values are rule-based demonstrations, not real hiring decisions, and must not be used as evidence of hiring performance without validation.

## Phase 1 architecture

Resume PDF + Job Description -> Flask Application -> PDF Text Extraction -> spaCy Preprocessing -> Skill Extraction -> TF-IDF and Cosine Similarity -> Explainable Scoring -> Candidate Ranking -> Human Review

Phase 4 outputs include `reports/evaluation_report.md`, `reports/fairness_report.md`, `reports/project_report.docx`, `reports/Project_Synopsis_DRAFT_Name_RollNo.docx`, `reports/demo_script.md`, and `reports/ethical_compliance_checklist.md`.

## Source files and limitations

The supplied files use names with `(1)` suffixes, so the workflow detects those names and copies them into canonical raw paths. The brief states that `shortlisted` is a Y/N field, while the actual CSV uses integer 0/1 values. The audit preserves the observed values and records this discrepancy. There are five observed job roles, not the ten suggested for optional synthetic expansion. No demographic fields are present, so demographic fairness cannot be measured from this dataset; controlled counterfactual tests are deferred to the fairness phase.
