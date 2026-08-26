# SLA / Contract Obligation Monitor

An AI-powered system that extracts obligations and deadlines from contracts and
alerts before deadlines are breached. Built as a backend-first project combining
relational data modeling with an AI extraction layer.

**Status:** Week 3 - Scheduled deadline monitoring, audit trail logging, and email alerts

## Stack
- FastAPI (Python)
- PostgreSQL (hosted locally / Neon)
- SQLAlchemy + Alembic (ORM + migrations)
- JWT auth
- LangChain + Google Gemini 3.6 Flash (AI extraction)
- pdfplumber (PDF parsing)
- APScheduler (Background deadline monitoring engine)
- Audit Trail Logging (`alerts_log` PostgreSQL table)

## Roadmap
- [x] Week 1: Schema design, auth, CRUD endpoints
- [x] Week 2: AI extraction of obligations from uploaded contract text (LangChain)
- [x] Week 3: Scheduled deadline monitoring + email alerts
- [ ] Week 4: Dashboard UI + deployment

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

6. Open interactive API docs at http://127.0.0.1:8000/docs

## Quickstart / Testing in Swagger UI

Once the server is running, open **http://127.0.0.1:8000/docs** to test the full pipeline:

1. **Register**: Call `POST /auth/signup` with an email and password.
2. **Log In**: Call `POST /auth/login` using your credentials and copy the `access_token`.
3. **Authorize**: Click the green **Authorize 🔒** button at the top right of Swagger UI, fill in your credentials, and click Authorize.
4. **Upload Contract**: Call `POST /contracts/upload` to upload a PDF (`.pdf`) or Text (`.txt`) agreement. Copy the returned contract `id`.
5. **Extract Obligations (AI)**: Call `POST /contracts/{contract_id}/extract` with your contract `id`. Gemini 3.6 Flash will extract all obligations, deadlines, and penalty clauses into PostgreSQL.
6. **Run Deadline Monitoring**: Call `POST /monitoring/run-check` to trigger an immediate deadline check across all obligations. Evaluates deadlines and updates statuses (`pending` -> `upcoming` / `breached`).
7. **View Audit Logs**: Call `GET /monitoring/alerts` to inspect the permanent audit log of all generated alerts.
8. **Update Obligation Status**: Call `PATCH /obligations/{obligation_id}/status` with `{"status": "completed"}` once an obligation is resolved so monitoring skips it.

## Data Model

- **users** - single-user auth for now
- **parties** - companies/individuals named in a contract
- **contracts** - uploaded contract text + metadata
- **obligations** - extracted deadlines/duties tied to a contract
- **alerts_log** - audit trail of every alert sent, tied to an obligation
