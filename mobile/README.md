# SuqCheck app

The Expo consumer app. It reads prices, confidence, and evidence from the
SuqCheck API, and it is the only place a shopper submits a price.

## Run it

```bash
npm install
npm start
```

Scan the QR code with Expo Go. The app points at the deployed API by default, so
there is nothing to configure to see real responses.

`npm run web` opens the same app in a browser, which is the quickest way to check
layout and data. Camera capture and location need a real device, so the scan and
receipt flows can only be exercised through Expo Go.

To develop against a backend on your own machine, copy `.env.example` to `.env`
and set `EXPO_PUBLIC_API_URL` to your machine's LAN address. A phone cannot
reach `127.0.0.1`.

## API types

`src/api/types.ts` is generated from the shared contract and must not be edited:

```bash
npm run generate:api
```

Run it after the backend regenerates `contracts/openapi.yaml`. A response shape
that changed shows up as a TypeScript error here rather than as a blank screen on
stage.

## How the code is arranged

| Path | What lives there |
| --- | --- |
| `app/` | Routes. `expo-router` maps files to screens |
| `src/api/` | The generated contract types, the fetch client, and query hooks |
| `src/components/` | Presentation pieces shared by more than one screen |
| `src/features/contribute/` | The three submission flows: receipt, shelf tag, by hand |
| `src/lib/` | Formatting, photo capture, small hooks |
| `src/theme/` | Colour, spacing, and type tokens |

Two rules worth keeping:

- Screens read `confidence_breakdown` and render it. Confidence is never
  recomputed on the device, because the engine already decided it and stored its
  reasoning.
- Every write goes through `src/api/client.ts`, which attaches the anonymous
  `X-Device-Id` the backend rate-limits against.

## What the API can and cannot do

- A product with no accepted evidence has no price: it is absent from search and
  its detail route answers 404. That is a state to render, not a bug.
- `thumbnail_url` is always `null` today, so no screen shows product imagery.
- Distances only exist when the app sends coordinates; otherwise stores are
  ordered by price.
- Uploads must be JPEG, PNG, or WebP under 8MB. The client compresses before
  sending.
- Receipt lines that match nothing come back in the extraction with no decision,
  and are shown as unrecorded rather than as a failure.
