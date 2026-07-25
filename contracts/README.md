# Frontend API handoff

`openapi.yaml` is the stable boundary between backend and frontend. It is
generated from the FastAPI/Pydantic schemas and must not be edited by hand.

## Current state

All eleven product operations plus `/healthz` answer from the database when
`USE_FIXTURES=false`, and from the fixtures in `fixtures/` otherwise. Response
shapes are identical either way, so pointing at a deployed stub and pointing at
a seeded database are the same integration.

The fixtures still describe the demo beats the app is built around:

- a 98%-confidence cooking-oil product
- a low-confidence soap product
- nearby cheap and expensive stores
- receipt and shelf-photo extraction results
- the 120 ETB pending-verification outlier
- seven-day rising and falling price trends
- an ingestion log mixing accepted, pending, and rejected evidence

`GET /api/evidence?status=&limit=&offset=` backs the dashboard ingestion log:
one row per evidence submission with its source and gate decision, newest
first. Rows that the gate did not accept carry a human-readable
`rejection_reason`.

Two response details worth planning UI for:

- `thumbnail_url` is always `null`. Use a category placeholder image.
- a product with no accepted evidence has no price, so it does not appear in
  search results and its detail route answers 404.

## Frontend integration

Generate TypeScript types from `contracts/openapi.yaml`:

```bash
npx openapi-typescript contracts/openapi.yaml -o mobile/src/api/types.ts
npx openapi-typescript contracts/openapi.yaml -o dashboard/src/api/types.ts
```

Uploads are `multipart/form-data` with a field named `image`. Manual evidence
uses JSON. Send a stable anonymous `X-Device-Id` header on every write request:
it is what the rate limiter counts against.

Error states the write endpoints can return, all with a `{"detail": "..."}`
body that is safe to show verbatim:

| Status | When | What to do |
| --- | --- | --- |
| 404 | The photographed product is not in the catalog, or a manual report names an unknown product or store | Offer the scan-and-add flow |
| 413 | The image is over 8MB | Re-encode or retake the photo |
| 415 | Not a JPEG, PNG, or WebP | Retake the photo |
| 429 | Over the upload limit for this device or network | Wait `Retry-After` seconds |
| 502 | Gemini could not read the image | Offer a retake, and manual entry as a fallback |

Receipt uploads answer 200 even when nothing matched: every line comes back in
`extraction.items` with `matched_product_id: null`, and `decisions` is empty.
Show the extraction for correction rather than treating it as a failure.

## Change rule

Changes under `backend/` do not require frontend work. Changes to Pydantic
response schemas regenerate this file and must be agreed with the frontend
developer first.

