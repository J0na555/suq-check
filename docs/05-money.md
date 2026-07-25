# 05 — Money

Source of truth for every cost, price, and cash figure cited elsewhere. All other docs point here rather than re-deriving.

FX basis throughout: **158 ETB/USD** ([ASSUMPTION] round rate for pitch maths; NBE indicative was 159.79 on 23 July 2026).

---

## 1. Coverage arithmetic (corrected)

Panel: **40 SKUs × 120 shops = 4,800 cells**, refreshed weekly.

Ambassadors visit **100% of shops every week**. They do **not** deliver a price for every SKU: yield is **~28 of 40 present** per shop ([ASSUMPTION] from a 10-shop facing pre-audit method in [04-operating-model.md](04-operating-model.md)).

| Outcome | Weekly | Share of 4,800 |
| --- | ---: | ---: |
| Verified price | 120 × 28 = **3,360** | 70% |
| Verified out-of-stock | **~1,440** | 30% |
| Cells *resolved* | **4,800** | 100% |

Out-of-stock is a sellable product (compliance and distribution signal), not a coverage gap.

Monthly ambassador observations: 3,360 × 4.33 ≈ **14,550** ([ASSUMPTION] 4.33 weeks/month).

Crowd upside (not a dependency): **~4,000** verified observations/month at steady state ([ASSUMPTION]). Combined volume ≈ **18,550**/month.

---

## 2. Ambassador pay

| Component | Per ambassador | Source |
| --- | ---: | --- |
| Visit pay | 15 shops × 4.33 × 90 = **5,845** ETB | 90 ETB/approved visit |
| Transport + data | 200 × 4.33 ≈ **866** ETB | weekly allowance |
| Quality bonus | **500** ETB | 95%+ approval, zero missed visits |
| **Total** | **7,211** ETB/month | |

All eight: **57,690 ETB/month** (~$365 at 158).

Sanity: ~40 hours/month → ~170 ETB/hour ≈ 5× the stated 34.62 ETB minimum hourly wage (public-sector reference; Ethiopia has no statutory private minimum). Deliberately above entry admin/CS (6,000–12,000 ETB/month) because a rejected visit costs more than the pay saved.

---

## 3. AI cost (Gemini 2.5 Flash)

List prices: **$0.30 / 1M input**, **$2.50 / 1M output** (Google Gemini API pricing for 2.5 Flash). Image tokens: **258** at medium resolution, **~1,806** at high. Vertex defaults to high; medium must be set explicitly or image cost rises ~7×.

| Path | Tokens (approx.) | Cost | Per observation |
| --- | --- | ---: | ---: |
| Price list (high) | 1,806 image + 700 prompt in; ~1,000 out for ~25 lines | ~0.52 ETB/photo | **0.021 ETB** |
| Receipt (medium) | 258 image + prompt in; ~300 out | ~0.16 ETB/receipt | **0.03 ETB** |

Budget with retries + normalization pass: **0.05 ETB per verified observation** → **~900–1,000 ETB/month** at 18,550 observations. Line item in the opex table: **1,000 ETB**.

---

## 4. Steady-state monthly opex (months 4–6)

Two bases: **capped** (reward pool at its hard ceiling) and **expected** (rewards driven by earn-table volume).

| Line | Capped (ETB) | Expected (ETB) | Notes |
| --- | ---: | ---: | --- |
| Ambassadors | 57,690 | 57,690 | §2 |
| Field/data coordinator (PT) | 15,000 | 15,000 | also runs 10% weekly spot audit |
| Consumer rewards | 20,000 | **~3,000** | ceiling vs ~0.7 ETB/obs × 4,000 crowd obs ([ASSUMPTION] blend from earn table in [04](04-operating-model.md)) |
| Gemini | 1,000 | 1,000 | §3 |
| Infra (hosting, storage, Telegram) | 8,000 | 8,000 | [ASSUMPTION] |
| Contingency 8% | 8,000 | ~6,800 | of non-contingency subtotal |
| **Total** | **~109,700** | **~93,000** | ~$694 / ~$590 |

Reward pool policy: **20,000 ETB ceiling months 1–3**, **35,000 months 4–6**, ~60% steered to gap bounties. The pool is a **ceiling, not a forecast**.

---

## 5. Cost per observation

| Label | Formula | ETB |
| --- | --- | ---: |
| Visit-pay only | 90 / 28 | **3.2** |
| Ambassador-loaded | 57,690 / 14,550 | **3.97** |
| Crowd (expected) | ~0.7 from earn table | **~0.7** |
| AI | §3 | **0.05** |
| **Marginal blended** | (14,550×3.97 + 4,000×0.7) / 18,550 + 0.05 | **~3.35** |
| **Fully loaded (capped)** | 109,700 / 18,550 | **~5.9** |
| **Fully loaded (expected)** | 93,000 / 18,550 | **~5.0** |
| Full 28-price shop audit | 5.9 × 28 | **~165** |

Headline for slides and [00-onepager.md](00-onepager.md): **5.9 ETB fully loaded (capped pool)**. Always say which base.

### Benchmarks (same units as published sources)

| Benchmark | ETB | Unit | Source |
| --- | ---: | --- | --- |
| WFP face-to-face price questionnaire | 3,160–6,320 | questionnaire | WFP mVAM HIF evaluation: $20–40; ×158 |
| Field Agent SA retail audit mission | 1,550–3,900 | store mission | R100–400 / live Stock & Price R160–180 at ~9.74 ETB/ZAR — **labelled international upper bound**, not the primary pricing argument |
| Premise cost-per-capture | 9.5–63 | capture | Premise published $0.06–0.40 |
| SuqCheck fully loaded | **5.9** | observation | this model |

Field-agency alternative for **monthly** coverage of 120 Addis shops at FA-equivalent rates: **186,000–468,000 ETB/month** (120 × 1,550–3,900). Used only as a buyer's-alternative ceiling; primary justification is shared fixed cost (§7).

---

## 6. Brand price card (VAT-exclusive)

All list prices below are **exclusive of VAT**. Ethiopia VAT is **15%**; registration threshold **2,000,000 ETB** taxable turnover (Proclamation 1341/2024; Directive 1104/2025). The ramp crosses the threshold around **months 6–7** ([ASSUMPTION] cumulative brand revenue), after which invoices add 15% VAT on top of these figures.

| Product | Scope | Price (ETB/month ex-VAT) | ≈ USD |
| --- | --- | ---: | ---: |
| **Pulse** | 1 category, weekly, 120 shops, 3 districts, dashboard + weekly report | 35,000 | $220 |
| **Signal** | ≤3 categories, competitor set, compliance alerts, OOS flags, district breakdown, CSV | 75,000 | $475 |
| **Signal Pro** | All categories, shop-level, API, custom gap campaigns, monthly review | 150,000 | $950 |
| Gap-task campaign | Brand-funded capture pool + **30%** management fee; min pool 25,000 | variable | — |
| Launch audit | One-off new-SKU check across 120 shops | 60,000 | — |

Discounts: **15%** annual prepay; first two design partners: **3-month pilot at 50%**.

### Shared-fixed-cost margin (primary pricing argument)

Panel opex is ~**110,000 ETB/month** whether one brand or eight buy it. Incremental cost of brand 2–8 ≈ Gemini share + support ≈ **near zero**.

| Brands on panel | Illustrative MRR (ex-VAT) | Gross margin on incremental seats |
| --- | ---: | --- |
| 1× Pulse | 35,000 | still below opex |
| Pulse + Signal | 110,000 | covers capped opex |
| Each further Signal-class seat | +75,000 | **~95%** gross ([ASSUMPTION] incremental cost ≤ ~4,000 ETB) |

This — not the South African field-agent conversion — is the margin story on the one-pager.

---

## 7. Tax treatment

| Item | Rate / rule | Source |
| --- | --- | --- |
| Withholding on services | **3%** (not 2%); threshold 10,000 ETB | Income Tax Proclamation 1395/2025 |
| VAT | **15%**; register at 2,000,000 ETB turnover | Proc. 1341/2024; Dir. 1104/2025 |
| Category A | Applicable once books/threshold hit | same income-tax regime |
| Minimum alternative tax | **2.5%** of turnover when it exceeds ordinary tax | same |

Cash break-even: need net receipts ≈ 109,700 after 3% WH → gross invoices ≈ **109,700 / 0.97 ≈ 113,100 ETB**. At Pulse+Signal mix (110,000), short by ~3k → **~2.1 average subscriptions**, not a clean "two".

---

## 8. Twelve-month ramp and cash trough

Revenue figures are **ex-VAT**, before withholding.

| Month | Brands / mix | MRR (ETB) | Notes |
| ---: | --- | ---: | --- |
| 1–3 | Design-partner pilot (free) | 0 | Coverage build; logo/testimonial swap |
| 4 | 1× Pulse | 35,000 | First cash |
| 5 | 1× Pulse | 35,000 | [ASSUMPTION] hold |
| 6 | 1× Signal + 1× Pulse | 110,000 | Ops break-even on capped opex |
| 7–8 | +1 Pulse or Signal | ~145–185,000 | [ASSUMPTION] |
| 9 | 3 brands + 1 gap campaign | ~200,000 | |
| 12 | 2× Signal + 1× Pulse + 1× Signal Pro + institutional amortisation | ~335,000 + ~100,000 = **~435,000** | ~$2,750/mo; ~$33k ARR |

Cumulative operating deficit (before founder stipends) peaks around **months 4–5 at ~355,000 ETB** ([ASSUMPTION] path-dependent on exact hiring week).

In-year revenue if ramp holds: roughly **1.2M ETB** ([ASSUMPTION] sum of monthly MRR path).

---

## 9. Funding ask arithmetic

| Component | ETB | Notes |
| --- | ---: | --- |
| Ramped 12-month data ops | ~1,200,000 | below full-year 109.7k×12 if early months are lighter |
| Two founder stipends | 2 × 15,000 × 6 = **180,000** | six months |
| Buffer | ~120,000 | |
| **Gross deployment** | **1,500,000** | ≈ $9,500 at 158 |
| Forecast in-year revenue | ~1,200,000 | §8 |
| **Net capital need** | **~700,000** | present both; lead with gross honesty |

Ask is deliberately small for incubation partners; do not inflate runway theatre.

---

## 10. Changelog (numbers that moved vs the raw pitch draft)

| Topic | Old claim | Corrected | Why |
| --- | --- | --- | --- |
| Coverage | Ambassadors deliver "100% of 4,800 cells" as prices | 100% shops visited; 4,800 cells *resolved*; ~3,360 prices + ~1,440 OOS | 28/40 yield contradicts 100% priced cells |
| Visit-pay unit cost | Mixed into "3.2 fully loaded" storytelling | **3.2** = visit-pay only; **3.97** = ambassador-loaded | Avoid understating fully loaded |
| Crowd rewards | 20,000 treated as expected spend | **~3,000 expected**; 20,000/35,000 = ceiling | Earn table × volume |
| Opex | Single 109,700 figure | Show **109,700 capped** and **~93,000 expected** | Honest range |
| Marginal blend | ~2.9 | **~3.35** | Uses 3.97 ambassador-loaded + expected rewards |
| Fully loaded | 5.9 only | **5.9 capped / ~5.0 expected** | Same |
| Break-even | "two subscriptions" | **~2.1 after 3% withholding** | Tax was absent |
| VAT | Silent | Prices **ex-VAT**; 15% after ~2M threshold | Law |
| Withholding | Implicit 2% folklore | **3%** | Proc. 1395/2025 |
| Pricing argument | Led with Field Agent SA conversion | Shared fixed cost / **~95%** incremental margin; FA = upper bound | Stronger and local |
| Funding | 1.5M as opaque runway | **1.5M gross** vs **~700k net** after in-year revenue | Arithmetic |
| Legal cite | Informal "Directive 159" only | **813/2013 Art. 15(1)** + Addis **Directive 159/2024**; do not cite repealed 685/2010 Art. 23 | Live law |
| Shop access | Assumed 0% refusal | **10% refusal** + reserve list | 159/2024 enforcement optics |
| Gemini model | Pitch priced 2.5 Flash | Keep **2.5 Flash** as cost basis; ~1,000 ETB/mo holds if 3.5 Flash is within same order | Align docs and deploy comment |
