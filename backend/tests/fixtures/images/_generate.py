"""Render Amharic/English OCR fixture photos for demo and local testing."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent
AMH = "/usr/share/fonts/noto/NotoSansEthiopic-Regular.ttf"
AMH_B = "/usr/share/fonts/noto/NotoSansEthiopic-Bold.ttf"
LAT = "/usr/share/fonts/liberation/LiberationMono-Regular.ttf"
LAT_B = "/usr/share/fonts/liberation/LiberationMono-Bold.ttf"
if not Path(LAT).exists():
    LAT = "/usr/share/fonts/gnu-free/FreeMono.ttf"
    LAT_B = "/usr/share/fonts/gnu-free/FreeMonoBold.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def paper_bg(w: int, h: int, tint: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (w, h), tint)
    px = img.load()
    rng = random.Random(42)
    for _ in range(w * h // 40):
        x, y = rng.randrange(w), rng.randrange(h)
        n = rng.randint(-18, 12)
        r, g, b = px[x, y]
        px[x, y] = (
            max(0, min(255, r + n)),
            max(0, min(255, g + n)),
            max(0, min(255, b + n)),
        )
    return img


def aging(img: Image.Image, seed: int) -> Image.Image:
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    r, g, b = img.split()
    r = ImageEnhance.Brightness(r).enhance(1.02)
    b = ImageEnhance.Brightness(b).enhance(0.97)
    img = Image.merge("RGB", (r, g, b))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = img.size
    for i in range(40):
        a = int(40 * (1 - i / 40))
        d.rectangle([i, i, w - 1 - i, h - 1 - i], outline=(20, 15, 10, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def make_price_list() -> None:
    w, h = 900, 1400
    img = paper_bg(w, h, (252, 250, 240))
    d = ImageDraw.Draw(img)
    title = font(AMH_B, 36)
    sub = font(AMH, 22)
    row_f = font(AMH, 20)
    row_lat = font(LAT, 18)
    price_f = font(LAT_B, 20)
    d.rectangle([30, 30, w - 30, h - 30], outline=(30, 30, 30), width=3)
    d.rectangle([40, 40, w - 40, 160], outline=(30, 30, 30), width=2)
    d.text((w // 2, 55), "\u12e8\u1238\u1240\u1326\u127d \u12cb\u130b \u12dd\u122d\u12dd\u122d", font=title, fill=(20, 20, 20), anchor="ma")
    d.text((w // 2, 100), "POSTED RETAIL PRICE LIST \u2014 Dir. 159/2024", font=row_lat, fill=(40, 40, 40), anchor="ma")
    d.text((w // 2, 130), "\u1230\u120b\u121d \u121b\u122d\u1275 / Selam Mart \u2014 \u1266\u120c | 20/07/2026", font=sub, fill=(50, 50, 50), anchor="ma")

    items = [
        ("\u1203\u12eb\u1275 \u12e8\u121d\u130d\u1265 \u12d8\u12ed\u1275 1\u120a", "Hayat Cooking Oil 1L", "340.00"),
        ("\u1238\u130b \u1290\u132d \u1235\u12b3\u122d 1\u12aa\u130d", "Shega White Sugar 1kg", "205.00"),
        ("\u1274\u1293 \u12e8\u12a0\u1260\u1263 \u12d8\u12ed\u1275 1\u120a", "Tena Sunflower Oil 1L", "355.00"),
        ("\u1274\u1293 \u12e8\u12a0\u1260\u1263 \u12d8\u12ed\u1275 3\u120a", "Tena Sunflower Oil 3L", "1,020.00"),
        ("\u1278\u134d \u1209\u12ab \u121b\u12ab\u122e\u1292 500\u130d", "Chef Luca Macaroni 500g", "92.00"),
        ("\u1278\u134d \u1209\u12ab \u1235\u1353\u130c\u1272 500\u130d", "Chef Luca Spaghetti 500g", "90.00"),
        ("555 \u12e8\u120d\u1265\u1235 \u1233\u1219\u1293 200\u130d", "555 Laundry Soap 200g", "45.00"),
        ("\u12a0\u12cd\u122b \u12f1\u1244\u1275 500\u130d", "Aura Detergent Powder 500g", "215.00"),
        ("\u12a0\u1235\u1275\u12ae \u12f1\u1244\u1275 1\u12aa\u130d", "Astco Wheat Flour 1kg", "105.00"),
        ("\u12a0\u12a9\u12cb\u1234\u134d \u12cd\u1203 1\u120a", "Aquasafe Drinking Water 1L", "28.00"),
        ("\u120b\u122d\u130e \u121b\u12ab\u122e\u1292 500\u130d", "Largo Macaroni 500g", "88.00"),
        ("\u122c\u1352 \u12e8\u120d\u1265\u1235 \u1233\u1219\u1293 400\u130d", "Repi Laundry Soap 400g", "78.00"),
        ("\u134a\u1264\u120b \u12cd\u1203 600\u121a\u120a", "Phibela Natural Water 600ml", "22.00"),
        ("\u12a0\u12f2\u1235 \u121e\u1306 \u12d8\u12ed\u1275 5\u120a", "Addis Modjo Edible Oil 5L", "1,560.00"),
        ("\u12a6\u121e \u12f1\u1244\u1275 1\u12aa\u130d", "Omo Detergent Powder 1kg", "410.00"),
        ("\u120b\u12ed\u134d\u1266\u12ed \u1233\u1219\u1293 175\u130d", "Lifebuoy Soap 175g", "82.00"),
        ("\u12cd\u123d \u12cd\u123d \u123b\u12ed 100\u130d", "Wush Wush Green Tea 100g", "145.00"),
        ("\u1309\u121b\u122e \u123b\u12ed 250\u130d", "Gumaro Black Tea 250g", "190.00"),
        ("\u123e\u120b \u12c8\u1270\u1275 1\u120a", "Shola Full Cream Milk 1L", "96.00"),
        ("\u12cb\u1295\u1302 \u1235\u12b3\u122d 1\u12aa\u130d", "Wonji White Sugar 1kg", "198.00"),
        ("\u1218\u1270\u1211\u122b \u1235\u12b3\u122d 5\u12aa\u130d", "Metehara White Sugar 5kg", "960.00"),
        ("\u1230\u1295\u12cb\u12ed\u1275 \u1229\u12dd 5\u12aa\u130d", "Sunwhite Imported Rice 5kg", "780.00"),
        ("\u12a0\u134d\u12f0\u122b \u1328\u12cd 1\u12aa\u130d", "Afdera Iodized Salt 1kg", "38.00"),
        ("\u12ae\u120d\u130c\u1275 \u1276\u1273\u120d 75\u121a\u120a", "Colgate Total 75ml", "118.00"),
        ("\u1230\u1295\u1232\u120d\u12ad \u123b\u121d\u1351 350\u121a\u120a", "Sunsilk Shampoo 350ml", "380.00"),
    ]
    y = 180
    d.text((55, y), "\u1270.\u1241", font=row_lat, fill=(0, 0, 0))
    d.text((110, y), "\u12d5\u1243 / Item", font=row_f, fill=(0, 0, 0))
    d.text((w - 160, y), "\u12cb\u130b (\u1265\u122d)", font=row_f, fill=(0, 0, 0))
    y += 28
    d.line([50, y, w - 50, y], fill=(0, 0, 0), width=2)
    y += 12
    for i, (amh, eng, price) in enumerate(items, 1):
        if i % 2 == 0:
            d.rectangle([50, y - 4, w - 50, y + 40], fill=(238, 236, 220))
        d.text((55, y), f"{i:02d}", font=row_lat, fill=(20, 20, 20))
        d.text((110, y), amh, font=row_f, fill=(20, 20, 20))
        d.text((110, y + 22), eng, font=row_lat, fill=(60, 60, 60))
        d.text((w - 55, y + 10), price, font=price_f, fill=(10, 10, 10), anchor="rm")
        y += 44
    d.text(
        (w // 2, h - 55),
        "\u1273\u122a\u134d \u1260\u1265\u122d | Prices in ETB | \u1245\u122c\u1273: 8335",
        font=sub,
        fill=(40, 40, 40),
        anchor="ma",
    )
    aging(img, 7).save(OUT / "price_list_posted.jpg", "JPEG", quality=88)


def make_receipt() -> None:
    w, h = 480, 900
    img = paper_bg(w, h, (248, 248, 245))
    d = ImageDraw.Draw(img)
    head = font(AMH_B, 26)
    body = font(AMH, 18)
    mono = font(LAT, 16)
    mono_b = font(LAT_B, 16)
    y = 30
    d.text((w // 2, y), "\u1230\u120b\u121d \u121b\u122d\u1275", font=head, fill=(0, 0, 0), anchor="ma")
    y += 34
    d.text((w // 2, y), "SELAM MART \u2014 BOLE", font=mono_b, fill=(0, 0, 0), anchor="ma")
    y += 22
    d.text((w // 2, y), "\u1272\u1295: 0001234567 | TIN", font=mono, fill=(40, 40, 40), anchor="ma")
    y += 20
    d.text((w // 2, y), "Tel: 011-661-2244", font=mono, fill=(40, 40, 40), anchor="ma")
    y += 28
    d.line([30, y, w - 30, y], fill=(0, 0, 0))
    y += 12
    d.text((30, y), "\u12f0\u1228\u1230\u129d \u1241. / Rec#: 004821", font=mono, fill=(0, 0, 0))
    y += 22
    d.text((30, y), "\u1240\u1295 / Date: 20/07/2026 14:32", font=mono, fill=(0, 0, 0))
    y += 22
    d.text((30, y), "\u12ab\u1232\u12e8\u122d: \u1204\u1208\u1295", font=body, fill=(0, 0, 0))
    y += 26
    d.line([30, y, w - 30, y], fill=(0, 0, 0))
    y += 14

    lines = [
        ("\u1203\u12eb\u1275 \u12d8\u12ed\u1275 1\u120a", "HAYAT OIL 1L", 1, 340.00),
        ("\u1238\u130b \u1235\u12b3\u122d 1\u12aa\u130d", "SHEGA SUGAR 1KG", 2, 205.00),
        ("\u12a0\u12a9\u12cb\u1234\u134d \u12cd\u1203 1\u120a", "AQUASAFE 1L", 3, 28.00),
        ("\u1278\u134d \u1209\u12ab \u121b\u12ab\u122e\u1292", "CHEF LUCA MAC 500G", 1, 92.00),
        ("\u120b\u12ed\u134d\u1266\u12ed \u1233\u1219\u1293", "LIFEBUOY 175G", 2, 82.00),
        ("\u12a0\u134d\u12f0\u122b \u1328\u12cd 1\u12aa\u130d", "AFDERA SALT 1KG", 1, 38.00),
    ]
    subtotal = 0.0
    for amh, eng, qty, unit in lines:
        total = qty * unit
        subtotal += total
        d.text((30, y), amh, font=body, fill=(0, 0, 0))
        d.text((w - 30, y), f"{total:7.2f}", font=mono, fill=(0, 0, 0), anchor="ra")
        y += 22
        d.text((30, y), f"  {eng}", font=mono, fill=(50, 50, 50))
        y += 18
        d.text((30, y), f"  {qty} x {unit:.2f}", font=mono, fill=(50, 50, 50))
        y += 24

    d.line([30, y, w - 30, y], fill=(0, 0, 0))
    y += 14
    vat = round(subtotal * 0.15, 2)
    grand = subtotal + vat
    for label, val in [
        ("\u1295\u12d1\u1235 \u12f5\u121d\u122d / Subtotal", subtotal),
        ("\u126b\u1275 15% / VAT", vat),
        ("\u1320\u1245\u120b\u120b / TOTAL", grand),
    ]:
        weight = mono_b if "TOTAL" in label else mono
        d.text((30, y), label, font=weight, fill=(0, 0, 0))
        d.text((w - 30, y), f"{val:8.2f}", font=mono_b, fill=(0, 0, 0), anchor="ra")
        y += 24
    y += 10
    d.line([30, y, w - 30, y], fill=(0, 0, 0))
    y += 16
    d.text((w // 2, y), "\u12a5\u1293\u1218\u1230\u130d\u1293\u1208\u1295 \u2014 Thank you!", font=body, fill=(0, 0, 0), anchor="ma")
    y += 28
    d.text((w // 2, y), "**** FISCAL ****", font=mono, fill=(0, 0, 0), anchor="ma")
    aging(img, 3).save(OUT / "receipt_amharic.jpg", "JPEG", quality=85)


def make_shelf_tag() -> None:
    w, h = 640, 400
    img = paper_bg(w, h, (255, 252, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, w - 20, h - 20], fill=(255, 230, 60), outline=(20, 20, 20), width=4)
    d.rectangle([40, 40, w - 40, h - 40], fill=(255, 250, 220), outline=(40, 40, 40), width=2)
    brand = font(AMH_B, 34)
    name = font(AMH, 28)
    lat = font(LAT_B, 22)
    price = font(LAT_B, 72)
    d.text((w // 2, 70), "\u1274\u1293", font=brand, fill=(10, 10, 10), anchor="ma")
    d.text((w // 2, 115), "TENA SUNFLOWER OIL", font=lat, fill=(20, 20, 20), anchor="ma")
    d.text((w // 2, 155), "\u12e8\u12a0\u1260\u1263 \u12d8\u12ed\u1275 1 \u120a\u1275\u122d", font=name, fill=(30, 30, 30), anchor="ma")
    d.text((w // 2, 200), "1 LITRE", font=lat, fill=(50, 50, 50), anchor="ma")
    d.rectangle([80, 230, w - 80, 340], fill=(20, 20, 20))
    d.text((w // 2, 285), "355.00", font=price, fill=(255, 230, 60), anchor="mm")
    d.text((w // 2, 360), "\u1265\u122d / ETB", font=lat, fill=(20, 20, 20), anchor="ma")
    aging(img, 11).save(OUT / "shelf_tag.jpg", "JPEG", quality=90)


def main() -> None:
    make_price_list()
    make_receipt()
    make_shelf_tag()
    (OUT / "README.md").write_text(
        """# OCR sample images

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
""",
        encoding="utf-8",
    )
    for path in sorted(OUT.iterdir()):
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".md", ".py"}:
            print(f"{path.name:28} {path.stat().st_size:8d} bytes")


if __name__ == "__main__":
    main()
