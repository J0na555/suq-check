# 07 — Pitch

Self-contained for the room. Deep numbers live in [05-money.md](05-money.md); strategy in [01-strategy.md](01-strategy.md).

---

## Five-minute timed script

| Time | Beat | Words to hit |
| ---: | --- | --- |
| 0:00–0:40 | Problem | Brands in Addis lose demand signal to unauthorised retail markups. Sagaci-class audits: only ~**25%** of retailers at MRP, ~**75%** above. Agencies are slow and expensive. |
| 0:40–1:40 | Machine | **8 ambassadors**, **15 shops** each, **3 districts**, **40 SKUs** → **4,800 cells** resolved weekly. One photo of the price list shops must post under **Proclamation 813/2013 Art. 15** (Addis **Directive 159/2024**). **12–18 minutes**, **~28 prices**, **90 ETB**/visit. |
| 1:40–2:20 | De-risk | Coverage does **not** depend on consumer adoption. Ambassadors alone visit 100% of shops; crowd is upside. Opposite of Esoko. |
| 2:20–3:10 | Cost twin headlines | **5.9 ETB** fully loaded per verified observation vs **3,160–6,320** WFP F2F. Panel costs ~**110k ETB/month** for one buyer or eight → brands 2–8 at **~95%** incremental gross margin. |
| 3:10–4:00 | Money | Pulse **35k** / Signal **75k** / Pro **150k** ex-VAT. Break-even ~**two** brand seats (~2.1 after 3% WH). Ask: **1.5M ETB** gross (~$9.5k); net need ~**700k** after in-year revenue. |
| 4:00–4:40 | Demo handoff | Live pulse → product with confidence → ingestion log pending outlier → price-list upload if ready. |
| 4:40–5:00 | Ask | Design-partner intro to **Samanu** (or Phibela), incubation seat, Ethio telecom airtime pilot. |

---

## Demo script (judge laptop)

1. Warm the API first (free Render instance ~50s cold).  
2. **Pulse** — districts Bole / Yeka / Arada; do not show a 98%-everywhere screen; thin/stale SKUs should exist.  
3. **Product detail** — big price, confidence ring, expandable why (stored breakdown).  
4. **Ingestion log** — one **pending** row with a readable ±35% reason (e.g. cooking oil outlier).  
5. **Contribute / price-list** — sample image button if live camera fails; store_id pre-picked.  
6. Say out loud what is **not** demoed: points ledger, telebirr payout, GPS enforcement UI, brand API keys.

---

## Fifteen hard questions

**1. Why won't this die like Esoko's price product?**  
Esoko leaned on paid enumerators without a crowd upside or a B2B anchor. We sell brands first; eight fixed routes already cover the panel; crowd is optional freshness ([02](02-comparables-evidence.md)).

**2. Why can't a brand just hire someone for 6,000 birr?**  
One junior at public-sector minimum covers a handful of shops, not 120×40 weekly with OCR, gating, and a multi-brand shared panel. Fully loaded we deliver ~14,550 ambassador observations/month for **57,690 ETB** labour — and the second brand rides the same fixed cost ([05](05-money.md)).

**3. Is photographing price lists legal?**  
Traders must post lists or tags under **813/2013 Art. 15(1)**. We cite live law, not repealed 685/2010. We carry letters stating we are **not** Trade Bureau enforcement ([01](01-strategy.md)).

**4. Won't shops refuse because of Directive 159/2024?**  
Yes, some will — we model **10% refusal**, reserves per district, badges, and a free shop badge programme. Access is the lead risk ([06](06-implementation-90-days.md)).

**5. Is 5.9 ETB real or slide fiction?**  
Derived in [05](05-money.md): capped opex 109,700 / ~18,550 obs. Visit-pay-only is 3.2; ambassador-loaded 3.97; expected fully loaded ~5.0 if rewards undershoot the ceiling. Live token spend is exposed on `/api/analytics/unit-economics`.

**6. Why not just scrape online grocers?**  
Online ≠ duka shelf. Scrapes are a source weight, not the spine. Compliance happens in physical shops.

**7. How do you stop fake crowd photos?**  
Caps (300/day, 2,000/month), hash dedupe, GPS, EXIF, sharpness, ±35% gate to pending, reputation downgrade. Points expire and are non-transferable ([04](04-operating-model.md)).

**8. Are points e-money?**  
Designed not to be: non-transferable, not for sale, 12-month expiry, redeem to airtime/telebirr. Confirm with NBE before scale ([ASSUMPTION] pending counsel).

**9. What if Gemini gets expensive?**  
Even at 7× image resolution mistakes, AI is ~1k ETB/month vs 58k labour. Medium resolution is mandatory on receipts ([05](05-money.md) §3).

**10. Why Samanu first?**  
~10/40 SKUs in the basket — one relationship monetizes a quarter of the panel ([03](03-business-model.md)).

**11. Do you sell exclusivity?**  
No category or district exclusivity in year one — it breaks neutrality and the shared-cost margin story ([03](03-business-model.md)).

**12. When do institutions pay?**  
Conversations month 1; cash often month 9–12. Brands fund the trough ([03](03-business-model.md)).

**13. Is Field Agent SA your price floor?**  
No — it is an **international upper bound**. Primary argument is shared fixed cost and ~95% incremental margin on seats 2–8 ([05](05-money.md)).

**14. What about VAT and withholding?**  
Prices **ex-VAT**; 15% VAT after ~2M turnover; services WH **3%**. Cash break-even ~**2.1** seats, not a tidy two ([05](05-money.md) §7).

**15. What is the ask?**  
**1.5M ETB** gross deployment (~$9,500): ~1.2M ops + 180k stipends + buffer. Net need ~**700k** after ~1.2M in-year revenue. Plus intros to Samanu and Ethio telecom airtime ([05](05-money.md) §9).

---

## Closing line

"We do not need Addis to download an app for the map to turn green. We need eight people, a posted price list the law already requires, and two brands who are tired of guessing."
