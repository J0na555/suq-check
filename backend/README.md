# SuqCheck API

The first backend milestone is a fixture-backed API. Its response schemas are
the contract with the Expo app and dashboard; later backend steps replace one
fixture route at a time without changing those response shapes.

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive documentation.

## Database

Copy `.env.example` to `.env`. Neon provides two connection strings:

- `DATABASE_URL`: pooled hostname containing `-pooler`; used by the API
- `MIGRATION_DATABASE_URL`: direct hostname without `-pooler`; used by Alembic

Keep both credentials in `.env` and never commit them. The API deliberately
uses no local SQLAlchemy pool when connected through Neon's PgBouncer endpoint,
avoiding double pooling.

Create or upgrade the schema:

```bash
alembic upgrade head
```

Inspect the current revision:

```bash
alembic current
```

The initial migration creates `pg_trgm`, the seven planned tables, constraints,
and the trigram GIN index used for product-alias matching. `USE_FIXTURES=true`
keeps all existing API routes on contract fixtures while the database layer is
being built. Setting it to `false` will only be useful after the read
repositories are implemented.

## Frontend contract

- Base URL: `http://127.0.0.1:8000` locally
- OpenAPI document: `../contracts/openapi.yaml`
- Upload endpoints use `multipart/form-data` with an `image` field
- Manual evidence uses JSON
- Anonymous write requests may send `X-Device-Id`
- Prices are numbers in ETB; timestamps and dates are ISO 8601

Generate the checked-in OpenAPI document after changing a schema:

```bash
python scripts/export_openapi.py
```

Schema changes are shared changes. Coordinate them with the frontend developer;
implementation changes inside `backend/` are backend-only.

