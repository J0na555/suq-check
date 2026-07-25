# Frontend API handoff

`openapi.yaml` is the stable boundary between backend and frontend. It is
generated from the FastAPI/Pydantic schemas and must not be edited by hand.

## Current state

All ten product operations plus `/healthz` are available from the fixture-backed
API. The fixtures include:

- a 98%-confidence cooking-oil product
- a low-confidence soap product
- nearby cheap and expensive stores
- receipt and shelf-photo extraction results
- the 120 ETB pending-verification outlier
- seven-day rising and falling price trends

The backend will replace these fixtures with database queries one route at a
time. Response shapes stay unchanged.

## Frontend integration

Generate TypeScript types from `contracts/openapi.yaml`:

```bash
npx openapi-typescript contracts/openapi.yaml -o mobile/src/api/types.ts
npx openapi-typescript contracts/openapi.yaml -o dashboard/src/api/types.ts
```

Uploads are `multipart/form-data` with a field named `image`. Manual evidence
uses JSON. Send a stable anonymous `X-Device-Id` header on evidence requests;
the backend will use it for deduplication and rate limiting in a later step.

## Change rule

Changes under `backend/` do not require frontend work. Changes to Pydantic
response schemas regenerate this file and must be agreed with the frontend
developer first.

