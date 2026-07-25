# 04 — Operating model

The 40 / 120 / 8 machine. Money figures cite [05-money.md](05-money.md).

---

## 1. SKU basket and selection method

**Method (not guesswork):** run a **10-shop pre-audit**, count shelf facings, take the **top 2–4 SKUs per category**. Packaged household essentials only (oil, sugar, rice, flour, salt, pasta, coffee, tea, milk, soap, detergent, toothpaste, shampoo, water). Fresh produce deferred — quality/weight variance makes a point price meaningless.

**Named brands available for the list:** Tena oil, Chef Luca pasta, 555 laundry soap, Aura, Astco flour, Aquasafe (all **Samanu**); Largo / Repi (**Repi Wilmar**); Phibela; Addis Modjo; Omo / Lifebuoy (**Unilever Dukem**); Wush Wush, Gumaro, Addis Red Label tea (**Ethio Agri-CEFT / MIDROC**); Shola milk (**Lamme Dairy**); One Water (**Mogle / Abbahawa**); Abyssinia Springs; Wonji / Metehara sugar; imported rice; salt; Colgate; Sunsilk.

**Commercial consequence:** Samanu alone owns roughly **10 of 40 SKUs** — one sale monetizes ~a quarter of the basket and makes them the obvious first customer.

---

## 2. Districts and routes

| District | Shops | Ambassadors | Notes |
| --- | ---: | ---: | --- |
| Bole | 40 | ~2–3 | |
| Yeka (Megenagna) | 40 | ~2–3 | Normalize naming: **Yeka**, not mixed with Megenagna as a separate district |
| Arada (Piassa) | 40 | ~2–3 | Normalize to **Arada** — Piassa is the colloquial label, not a second district |
| **Total** | **120** | **8** | 15 shops each |

Per ambassador: **3 shops/day × 5 days** ≈ 9–10 hours/week including travel. Fixed routes; no self-selected wandering.

**Shop access risk:** under Addis Directive 159/2024, shops experience price-list photography as enforcement-adjacent. Model **10% refusal** ([ASSUMPTION]), not zero. Mitigations: written non-cooperation-with-enforcement commitment, branded ID + explainer letter, shop-facing value (free "price-posted" badge later), **~15-shop reserve list per district**.

---

## 3. Visit protocol (12–18 minutes)

1. GPS check-in within **50 m** of the registered shop  
2. One photo of the **legally posted price list** (primary yield)  
3. **5–8 shelf-zone photos** covering the 40-SKU basket  
4. Out-of-stock flags for missing SKUs  
5. Submit  

Yield: **~28 priced observations + ~12 OOS resolutions** per visit. Pay: **90 ETB** per approved visit (+ allowances/bonus in [05](05-money.md)).

---

## 4. Verification and confidence (business rules)

### Gate

1. Reject if outside category price bounds.  
2. If a trusted market estimate exists (confidence ≥ 60):  
   - deviation **&lt; 35%** → accept  
   - **35%–150%** → pending review  
   - **&gt; 150%** → reject with a human-readable reason  
3. No prior estimate → bootstrap-accept.

Plausibility band **±35%** is the documented product rule (aligned in the verification service).

### Source weights (target business ranking)

Highest trust should be GPS-fenced, audited ambassador visits. Intended weights:

| Source | Weight | Role |
| --- | ---: | --- |
| Partner / brand CSV | 1.0 | Contracted |
| Receipt | 0.9 | Paid transaction |
| **Ambassador store visit / price list** | **≥ 0.95** (target) | Panel spine |
| Scrape | 0.75 | Online shelves |
| Shelf photo (crowd) | 0.55 | Spot check |
| Community manual | 0.4 | Lowest |

Freshness: `0.5 ** (age_days / 7)`. Final weight = source × OCR confidence × freshness. Market price = **weighted median**; spread = (p75 − p25) / median. Confidence blends volume, agreement, freshness, diversity; stale data capped (see engine).

### Spot audit

Coordinator re-visits **10% of shops weekly**; disagreement above the pending band triggers ambassador coaching or route reassignment.

---

## 5. Consumer points

Scale: **1 point = 0.10 ETB**. Redemption threshold **1,000 points = 100 ETB** (telebirr P2P 1–100 ETB is free — rail cost zero; caps fraud exposure per payout).

| Action | Points | ETB | Typical obs | ETB/obs |
| --- | ---: | ---: | ---: | ---: |
| Receipt (≥3 basket items matched) | 50 | 5 | ~5 | 1.00 |
| Posted price list (≥10 lines) | 120 | 12 | ~25 | 0.48 |
| Single shelf tag / product+price | 15 | 1.5 | 1 | 1.50 |
| Gap bounty (SKU×shop) | +100 | 10 | 1 | — |
| First submission from new shop | +200 | 20 | — | — |
| 7-day streak | +100 | 10 | — | — |
| Referral | 10% of referee approved pts for 90 days | — | — | cap 500 pts (Field Agent-style) |

**Controls:** 300 pts/user/day and 2,000 pts/user/month (ceiling **200 ETB/bad actor**); points pend 24h and forfeit on rejection; three rejections → reputation downgrade (evidence still accepted, earnings stop). Automated gates: perceptual hash dedupe, GPS-to-shop, EXIF time, sharpness, receipt-number uniqueness, ±35% plausibility → review.

Points are non-transferable, not for sale, expire at **12 months** (stay out of e-money classification). **[ASSUMPTION] Confirm with NBE before scaling.**

Reward pool ceilings and expected spend: [05-money.md](05-money.md) §4.

---

## 6. Payout rails (preference order)

1. **Ethio telecom airtime top-up** — no cash-out; precedent in WFP mVAM (~$0.50 airtime) and ATI 8028; natural ask while Ethio telecom is a hackathon partner.  
2. **telebirr Bulk Payment** from a funded trust account once merchant onboarding completes (licence, TIN, bank account → App ID / Key / short code; sandbox separate). Merchant receiving fee **0.8%** (min 1 / max 100 ETB); settlement T+1. Scale context (23 July 2026): 60.6M customers, 440,100 merchants.  
3. **Manual telebirr P2P** for the first weeks (20–50 payouts/month is acceptable).

---

## 7. Weekly cadence

| Day | Activity |
| --- | --- |
| Mon–Fri | Ambassador routes (3 shops/day) |
| Rolling | Crowd submissions + automated gate |
| Fri | Coordinator spot-audit sample |
| Sat | Pending queue clear; route exceptions |
| Sun | Weekly brand digest generation; gap-bounty board refresh |

Roles: **8 ambassadors**, **1 PT field/data coordinator**, founders on sales + product, no full-time finance hire in months 1–6.

---

## 8. Legal and registration checklist

- [ ] Trade Competition and Consumers Protection **Proclamation 813/2013 Art. 15(1)** — duty to post price list or affix tags (repealed 685/2010; **do not cite Art. 23 of 685**).  
- [ ] Addis **Directive 159/2024** (Village Trade Control Procedure) — local enforcement layer; 2–3 controllers/village.  
- [ ] Business licence + TIN.  
- [ ] telebirr merchant / Bulk Payment onboarding.  
- [ ] VAT watch at **2M ETB** turnover ([05](05-money.md) §7).  
- [ ] Written shop non-enforcement letter + ID badges.  
- [ ] NBE informal check before points look like e-money.  
- [ ] Privacy: no retention of full-resolution personal photos beyond thumbnails needed for audit.

---

## Appendix A — Engine reconciliation (for backend)

Business story vs current technical plan / code. Backend should converge on this appendix; until then, pitch Q&A must not pretend these exist.

| Topic | Business rule | Current code / plan.md | Required change |
| --- | --- | --- | --- |
| Plausibility band | ±35% pending | Was 40%; target **0.35** | Keep `PENDING_DEVIATION = 0.35` |
| `store_visit` weight | Highest-trust panel spine (≥0.95) | 0.6 (below scrape 0.75) | Raise above scrape; ideally ≥ receipt after GPS audit |
| `shelf_photo` | Crowd spot | 0.55 | OK as crowd tier |
| Ambassador entity | Routes, visits, GPS, approval | **Not modelled** | Add visit table or encode as `store_visit` + payload |
| Price-list source | Flagship ingest | Needs dedicated extract + `STORE_VISIT` | `extract_price_list` + `/api/evidence/price-list` |
| OOS flags | ~1,440 cells/week productized | **Not modelled** | Nullable OOS evidence or status |
| Points / reputation / caps | Full table above | **Not modelled** | Defer post-demo; do not demo fake balances |
| telebirr / airtime | Payout rails | **Not modelled** | Manual ops OK for MVP |
| Brand API keys / CSV | Signal feature | **Not modelled** | Dashboard export stub acceptable |
| Priced Gemini model | Cost model = **2.5 Flash** @ $0.30/$2.50 | Deploy must agree | Align `GEMINI_MODEL` + comments; ~1,000 ETB/mo holds either nearby Flash tier |

**Explicitly out of scope for the demo pass:** ambassador tables, GPS enforcement, OOS flags, points ledger, payouts, brand API keys. Say so in pitch Q&A rather than inventing UI.
