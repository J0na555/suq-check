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

