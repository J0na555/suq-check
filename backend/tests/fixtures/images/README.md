# OCR sample images

Camera-style fixture photos for Gemini extraction paths. Each image mixes
Amharic (Ethiopic script) and English product names from the SuqCheck basket.

| File | Use with |
|------|----------|
| `price_list_posted.jpg` | `POST /api/evidence/price-list` — posted retail list (~25 lines) |
| `receipt_amharic.jpg` | `POST /api/evidence/receipt` — bilingual till receipt |
| `shelf_tag.jpg` | `POST /api/evidence/shelf` — single-SKU shelf price tag |

These are rendered stand-ins for field photos (Addis shops) so the OCR path
has Amharic text before demo day. Replace with real captures when available;
keep the same filenames so sample-image buttons keep working.

Regenerate with: `python tests/fixtures/images/_generate.py`
