# SLA / Contract Obligation Monitor

An AI-powered system that extracts obligations and deadlines from contracts and
alerts before deadlines are breached. Built as a backend-first project combining
relational data modeling with an AI extraction layer.

**Status:** Week 2 - AI extraction layer (PDF parsing, LangChain + Gemini 3.6 Flash, structured output)

## Stack
- FastAPI (Python)
- PostgreSQL (hosted locally / Neon)
- SQLAlchemy + Alembic (ORM + migrations)
- JWT auth
- LangChain + Google Gemini 3.6 Flash (AI extraction)
- pdfplumber (PDF parsing)

## Roadmap
- [x] Week 1: Schema design, auth, CRUD endpoints
- [x] Week 2: AI extraction of obligations from uploaded contract text (LangChain)
- [ ] Week 3: Scheduled deadline monitoring + email alerts
- [ ] Week 4: Dashboard UI + deployment

## Local Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a free Postgres database at [neon.tech](https://neon.tech) and copy the connection string.

3. Copy `.env.example` to `.env` and fill in your `DATABASE_URL` and a generated `SECRET_KEY`:
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

## Data Model

- **users** - single-user auth for now
- **parties** - companies/individuals named in a contract
- **contracts** - uploaded contract text + metadata
- **obligations** - extracted deadlines/duties tied to a contract
- **alerts_log** - audit trail of every alert sent, tied to an obligation
