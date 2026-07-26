# SuqCheck

Evidence-backed retail price intelligence for Addis Ababa staples.

Shoppers look up prices and submit evidence (receipt, shelf tag, posted price list, or by hand). Brands and analysts read the same feed on a live dashboard. Every price comes from weighted evidence — nothing sets a price directly — and each estimate carries a confidence score with a human-readable breakdown.

API: [suq-check-api.onrender.com](https://suq-check-api.onrender.com) · Dashboard: [suq-check.vercel.app](https://suq-check.vercel.app/) · Docs: [`docs/00-onepager.md`](docs/00-onepager.md)

## Repo layout

| Path | Role |
| --- | --- |
| [`backend/`](backend/) | FastAPI + Neon Postgres, price engine, verification gate, Gemini OCR |
| [`mobile/`](mobile/) | Expo consumer app (SDK 54) |
| [`dashboard/`](dashboard/) | Next.js brand / analyst dashboard |
| [`contracts/`](contracts/) | Shared OpenAPI + response fixtures |
| [`data/`](data/) | Seed CSVs (products, stores) |
| [`docs/`](docs/) | Strategy, unit economics, pitch |

`contracts/openapi.yaml` is the boundary between backend and frontends. Regenerate it from FastAPI after schema changes; do not edit it by hand.

## Quick start

### API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # fill Neon + Gemini keys as needed
uvicorn app.main:app --reload
```

- Interactive docs: http://127.0.0.1:8000/docs
- Health: `GET /healthz`
- `USE_FIXTURES=true` serves [`contracts/fixtures/`](contracts/fixtures/) without a database
- `USE_FIXTURES=false` serves the engine and Neon (run `alembic upgrade head` first)

Details: [`backend/README.md`](backend/README.md)

### Mobile

```bash
cd mobile
npm install
npm start
```

Defaults to the deployed API. For a local backend, copy `.env.example` → `.env` and set `EXPO_PUBLIC_API_URL` to your machine's LAN IP (phones cannot reach `127.0.0.1`).

Details: [`mobile/README.md`](mobile/README.md)

### Dashboard

```bash
cd dashboard
npm install
cp .env.example .env.local
npm run generate:api
npm run dev
```

Open http://localhost:3000. Set `NEXT_PUBLIC_API_URL` to the API base URL (no trailing slash).

Details: [`dashboard/README.md`](dashboard/README.md)

## Try it / demo

You do not need an App Store or Play Store listing to let people use the product.

| Surface | How to share |
| --- | --- |
| Dashboard | Open [suq-check.vercel.app](https://suq-check.vercel.app/) in any browser |
| Mobile (usual path) | Expo Go — install from the store, scan the QR from `npm start` in `mobile/` |
| API | [suq-check-api.onrender.com](https://suq-check-api.onrender.com) (docs at `/docs`) |

### Mobile with Expo Go

The app targets **Expo SDK 54** so stock Expo Go from the Play Store / App Store can open it. It already points at the deployed API, so testers need no env setup.

```bash
cd mobile
npm install
npm start
```

Share the QR. Use a tunnel (`n` in the Expo CLI, or `npx expo start --tunnel`) when phones are not on the same Wi‑Fi. Camera and location need a real device; `npm run web` is fine for layout only.

Before a live demo, hit `https://suq-check-api.onrender.com/healthz` once so the free Render instance is awake (cold start ~50s).

### Installable builds later

For a downloadable app without Expo Go, use [EAS Build](https://docs.expo.dev/build/introduction/) for an Android APK / internal link, or TestFlight on iOS (Apple Developer account required). Full store release is possible (`com.suqcheck.app` in `mobile/app.json`) but slower; Expo Go or an EAS internal build is enough for demos and early testers.

## Shared contract

After backend schema changes:

```bash
cd backend && python scripts/export_openapi.py
cd ../mobile && npm run generate:api
cd ../dashboard && npm run generate:api
```

Uploads are `multipart/form-data` with an `image` field. Writes may send `X-Device-Id` for anonymous rate limiting. Prices are ETB; timestamps are ISO 8601.

## How pricing works

```text
photo / manual / scrape
        │
        ▼
   normalize (alias → trigram → Gemini)
        │
        ▼
 verification gate (bounds + deviation)
        │
   accepted / pending / rejected
        │
        ▼
  price engine (weighted median + confidence)
        │
        ▼
   FastAPI → Expo app + dashboard
```

- Evidence is the only write path for prices
- Confidence is computed server-side and stored with a breakdown; clients render it, they do not recompute it
- Accepted evidence in a 30-day window is weighted by source, OCR confidence, and freshness

Technical design: [`plan.md`](plan.md)

## Deploy

| Surface | Host | URL |
| --- | --- | --- |
| API | Render (`suq-check-api` in [`render.yaml`](render.yaml)) | https://suq-check-api.onrender.com |
| Dashboard | Vercel | https://suq-check.vercel.app/ |

Set `DATABASE_URL`, `MIGRATION_DATABASE_URL`, and `GEMINI_API_KEY` on the Render API service. Point the dashboard's `NEXT_PUBLIC_API_URL` at the API.

The free API instance sleeps when idle; the first request after inactivity can take ~50s.

## Catalog seed

[`data/products.csv`](data/products.csv) and [`data/stores.csv`](data/stores.csv) feed `python -m app.seed` (from `backend/`). Shape and coverage rules: [`data/README.md`](data/README.md).

## Further reading

- [`docs/00-onepager.md`](docs/00-onepager.md) — product and unit-economics summary
- [`docs/01-strategy.md`](docs/01-strategy.md) through [`docs/07-pitch.md`](docs/07-pitch.md) — full business pack
- [`split.md`](split.md) — hackathon team tracks
