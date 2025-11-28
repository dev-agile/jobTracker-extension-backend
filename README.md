# FastAPI Boilerplate

This is a minimal, well-structured FastAPI boilerplate with SQLAlchemy database integration.

Quick start:

1. Copy `.env.example` to `.env` and set `DATABASE_URL`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Project structure:

- `app/` - application package
  - `api/` - routers for versioned API
  - `core/` - configuration
  - `crud/` - database CRUD helpers
  - `db/` - database setup and Base
  - `models/` - SQLAlchemy models
  - `schemas/` - Pydantic schemas
  - `deps.py` - dependency helpers
  - `main.py` - FastAPI application entry

