# SuqCheck business dashboard

Live market intelligence for brands and market analysts. The dashboard is
read-only and consumes the same FastAPI contract as the Expo app.

## Setup

```bash
npm install
cp .env.example .env.local
npm run generate:api
npm run dev
```

Open <http://localhost:3000>. Set `NEXT_PUBLIC_API_URL` to a local or deployed
API base URL without a trailing slash.

## Data mapping

- Overview: `GET /api/pulse`, `/api/analytics/trends`, and `/api/evidence`
- Evidence: `GET /api/evidence?status=&limit=&offset=`
- Trends: `GET /api/analytics/trends?period_days=`
- Economics: `GET /api/analytics/unit-economics?period_days=`

The UI never replaces a failed live request with fixture numbers. Loading,
empty, API cold-start, stale, and retry states are presented explicitly.

## Contract and checks

Regenerate `src/api/types.ts` whenever the backend Pydantic response schemas
change:

```bash
npm run generate:api
npm run lint
npm run typecheck
npm run build
```

## Deployment

Production: [https://suq-check.vercel.app/](https://suq-check.vercel.app/).
Set `NEXT_PUBLIC_API_URL` in the Vercel project env before the production build.
