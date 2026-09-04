# SLA / Contract Obligation Monitor

An AI-powered system that extracts obligations and deadlines from contracts and
alerts before deadlines are breached. Built as a backend-first project combining
relational data modeling with an AI extraction layer, background job scheduling,
and a full audit trail.

**Status:** Week 4 - Security hardening, test coverage, and deployment-ready

## Stack
- FastAPI (Python)
- PostgreSQL (hosted locally / Neon)
- SQLAlchemy + Alembic (ORM + migrations)
- JWT auth + slowapi (rate limiting on auth endpoints)
- LangChain + Google Gemini (AI extraction)
- pdfplumber (PDF parsing)
- APScheduler (background deadline monitoring engine)
- Audit Trail Logging (`alerts_log` PostgreSQL table)
- Streamlit (dashboard UI)
- pytest (automated test suite)

## Roadmap
- [x] Week 1: Schema design, auth, CRUD endpoints
- [x] Week 2: AI extraction of obligations from uploaded contract text (LangChain)
- [x] Week 3: Scheduled deadline monitoring + email alerts
- [x] Week 4: Dashboard UI, security hardening, test coverage, deployment prep

## Local Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a free Postgres database at [neon.tech](https://neon.tech) and copy the connection string.

3. Copy `.env.example` to `.env` and fill in your `DATABASE_URL`, `SECRET_KEY`, and `GOOGLE_API_KEY` (from Google AI Studio):
   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"   # paste output as SECRET_KEY
   ```

4. Run the database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```

6. In a separate terminal, start the dashboard:
   ```bash
   streamlit run dashboard.py
   ```

7. Open the API docs at http://127.0.0.1:8000/docs or the dashboard at http://localhost:8501

## Running Tests

```bash
pytest tests/ -v
```

Tests run against an isolated in-memory SQLite database - they never touch your
real PostgreSQL data. Covers signup/login, JWT-protected route access, per-user
data isolation (one user can never see another user's contracts), and core
contract/obligation CRUD.

## Quickstart / Testing in Swagger UI

Once the server is running, open **http://127.0.0.1:8000/docs** to test the full pipeline:

1. **Register**: Call `POST /auth/signup` with an email and password.
2. **Log In**: Call `POST /auth/login` using your credentials and copy the `access_token`.
3. **Authorize**: Click the green **Authorize** button at the top right of Swagger UI.
4. **Upload Contract**: Call `POST /contracts/upload` to upload a PDF or `.txt` agreement.
5. **Extract Obligations (AI)**: Call `POST /contracts/{contract_id}/extract`.
6. **Run Deadline Monitoring**: Call `POST /monitoring/run-check`.
7. **View Audit Logs**: Call `GET /monitoring/alerts`.
8. **Update Obligation Status**: Call `PATCH /obligations/{obligation_id}/status`.

## Data Model

- **users** - account authentication
- **parties** - companies/individuals named in a contract
- **contracts** - uploaded contract text + metadata
- **obligations** - extracted deadlines/duties tied to a contract
- **alerts_log** - audit trail of every alert sent, tied to an obligation

## AI Extraction Quality — Evals

The `evals/` directory contains a labeled test set (`evals/dataset.py`) of
sample contracts with hand-verified "correct answers" - not just eyeballing
a few outputs, but actually measuring extraction accuracy.

Run it against the real extraction service (calls Gemini, needs a real
`GOOGLE_API_KEY`):
```bash
python -m evals.run_evals
```

This reports recall (did it find every expected obligation, exact deadline
match required), false-positive rate (did it hallucinate obligations from
boilerplate text with no real deadlines), and whether a prompt-injection
attempt embedded in contract text succeeded in suppressing correct
extraction.

The scoring logic itself (independent of real API calls) is unit tested in
`tests/test_eval_scorer.py` - run as part of the normal `pytest tests/` suite.

### Latest results (real run against live Gemini, 2026-09-03)

```
7/7 cases passed
Mean recall: 100.0%
Adversarial cases: 1/1 passed
```

All 7 cases passed, including:
- Correct extraction across 3 different date formats in one contract
  ("January 5th, 2027", "15 Feb 2027", "2027-03-01")
- Zero false positives on a boilerplate-only contract with no real deadlines
- Correct extraction from a real SEC-filed contract (not synthetic text),
  correctly computing a relative deadline ("4 Trading Days after the
  Agreement date") into an absolute date
- The adversarial case: a fake `"SYSTEM OVERRIDE: ignore all previous
  instructions"` string embedded in contract text did **not** suppress
  correct extraction of the real obligation - direct evidence the prompt
  hardening in `app/services/extraction.py` works, not just a claim

**Known constraint:** the free tier of the Gemini API allows 5 requests/minute.
Running all 7 cases in quick succession triggers a `429 ResourceExhausted`
on some calls; LangChain's built-in retry logic handles this automatically
(waits and retries), so it doesn't cause failures - just occasional visible
retry logging in the console output.

## AI Security

Contract text is user-uploaded, untrusted data that gets fed directly into
an LLM prompt - a real prompt-injection attack surface. The extraction
prompt (`app/services/extraction.py`) explicitly frames contract text as
untrusted data rather than instructions, with clear delimiting and a direct
warning against treating embedded text as commands. `tests/test_extraction_security.py`
guards this framing against being silently removed by a future edit, and
`evals/dataset.py` includes an adversarial case that measures whether an
actual injection attempt succeeds against the live model.

## Security

The following hardening is in place:

- Passwords hashed with bcrypt, never stored or returned in plain text
- JWT-based auth on every protected route
- **Rate limiting** on `/auth/signup` (5/min) and `/auth/login` (10/min) per IP,
  to slow down brute-force credential attacks
- **CORS** explicitly configured via `CORS_ORIGINS` env var - only whitelisted
  frontend origins can call the API from a browser
- **Upload size limit** (10MB) on contract file uploads
- Per-user data isolation enforced at the query level - every contract/obligation
  lookup is scoped to `Contract.owner_id == current_user.id`, not just hidden in the UI

## Production Readiness - Known Scope Decisions

This is a portfolio project, not a commercial product, and some gaps are
deliberate scope decisions rather than oversights. Documenting them explicitly
here rather than leaving them implicit:

- **Single-tenant per account.** Each user account is fully isolated - there is
  no "organization" or team concept yet. A real multi-employee company deployment
  would need an `Organization` model with `organization_id` on every table, plus
  role-based permissions (admin vs. member). This is a genuine architecture
  change, not a small tweak.
- **No password reset flow.** Forgotten passwords currently have no self-service
  recovery path.
- **No role-based access control.** Every authenticated user has identical full
  access to their own data - there's no admin/member distinction.
- **Email alerts run in simulated mode by default.** Without `SMTP_HOST` /
  `SMTP_USER` / `SMTP_PASSWORD` set in `.env`, alerts are logged to the console
  instead of actually sent. Set real SMTP (or SendGrid/AWS SES) credentials to
  enable real email delivery.
- **AI extraction has no re-run protection.** Running extraction twice on the
  same contract creates duplicate obligations by design - this was Week 2's
  scope (proving extraction works), not idempotency handling.
- **List endpoints are unpaginated at the API level.** `/contracts/` and
  `/obligations/` currently return every row for a user in one response. The
  dashboard paginates client-side after fetching everything - fine at current
  scale, would need real `LIMIT`/`OFFSET` API pagination at higher record counts.
- **No automated backups.** Local Postgres has none configured; a hosted
  Postgres provider (Neon, Render) should be used in production for this reason
  alone, since they include automated backups.

## Deployment

This app deploys as two separate services plus a hosted database - no code
changes needed, only environment variables.

### 1. Database - Neon (or Render Postgres / Supabase)
Already using Neon or similar? Just note the connection string - you'll need
it in step 2.

### 2. Backend - Render
1. Push this repo to GitHub if you haven't already.
2. On [render.com](https://render.com), create a new **Web Service** from your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render's dashboard (not a committed `.env`):
   `DATABASE_URL`, `SECRET_KEY`, `GOOGLE_API_KEY`, `CORS_ORIGINS` (set this to
   your Streamlit URL once you have it from step 3 - you can update it after).
6. After the first deploy, run migrations once via Render's shell:
   `alembic upgrade head`

### 3. Frontend - Streamlit Community Cloud
1. On [share.streamlit.io](https://share.streamlit.io), create a new app from
   the same repo, pointing at `dashboard.py`.
2. In the app's settings, add a secret: `API_BASE_URL = "https://your-backend.onrender.com"`
   (your real Render URL from step 2).
3. Deploy. Once you have your Streamlit URL, go back to Render and update
   `CORS_ORIGINS` to include it.

### 4. Verify
Visit your Streamlit URL, sign up, upload a test contract, and confirm
extraction and the dashboard both work end-to-end against the live backend.
