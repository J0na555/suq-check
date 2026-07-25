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
and the trigram GIN index used for product-alias matching. The second seeds
`category_price_bounds` for all fourteen categories, which the verification gate
needs before it can reject anything. `USE_FIXTURES=true` keeps all existing API
routes on contract fixtures while the database layer is being built. Setting it
to `false` will only be useful after the read repositories are implemented.

## Price engine and verification gate

`app/services/price_engine.py` owns every number the API reports. Accepted
evidence inside a 30-day window is weighted by source, OCR confidence, and a
seven-day freshness half-life; the price is the weighted median, and confidence
is a weighted blend of volume, agreement, freshness, and diversity, capped at 60
when the newest evidence is stale. The sub-scores are persisted to
`price_estimate.breakdown` in the same shape the product-detail response
returns, so the app's why panel renders stored facts.

`app/services/verification.py` gates incoming prices: outside
`category_price_bounds` rejects, then deviation from a market estimate with
confidence 60 or above decides accepted (under 40%), pending (40% to 150%), or
rejected. Each branch produces the sentence shown in the ingestion log.
`submit_evidence` writes the evidence row and recomputes the affected product
inline when the gate accepts.

## Deploy

`../render.yaml` at the repo root describes the service: Python runtime,
root directory `backend`, `pip install -e .`, and
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, with `/healthz` as the
health check path. Fixture responses read `../contracts/fixtures`, so the whole
repo must be checked out even though the app lives in `backend/`.

`DATABASE_URL` and `MIGRATION_DATABASE_URL` are marked `sync: false`; set both
in the Render dashboard so Neon credentials never enter the repository.
Production sets `USE_FIXTURES=false` so the live API serves the engine and Neon
data. Keep `USE_FIXTURES=true` locally when you want the contract fixtures as a
frontend fallback without a database.

Every push to `main` redeploys. Confirm a deploy with `/healthz`, which answers
without touching Postgres:

```bash
curl https://suq-check-api.onrender.com/healthz
```

The free instance sleeps after inactivity, so the first request following an
idle period takes about 50 seconds. A newly created `.onrender.com` hostname
also returns a plain-text 404 with an `x-render-routing: no-server` header from
some edge locations for the first few minutes; that clears itself and does not
mean the deploy failed.

## Frontend contract

- Base URL: `https://suq-check-api.onrender.com` deployed, `http://127.0.0.1:8000` locally
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

