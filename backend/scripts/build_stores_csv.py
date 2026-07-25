"""Rebuild `data/stores.csv` with 120 shops, forty in each of three districts.

Names and chains are hand-written; only the coordinates are computed, spread
deterministically over a bounding box per district so re-running this script
produces the same file. The handful of stores the tests name by hand keep their
researched coordinates.

Run from `backend/`: `python scripts/build_stores_csv.py`
"""

import csv
from pathlib import Path
from random import Random

OUTPUT = Path(__file__).resolve().parents[2] / "data" / "stores.csv"

# latitude low, latitude high, longitude low, longitude high
BOXES: dict[str, tuple[float, float, float, float]] = {
    "Bole": (8.9750, 9.0250, 38.7600, 38.8500),
    "Yeka": (9.0150, 9.0850, 38.7650, 38.8600),
    "Arada": (9.0230, 9.0480, 38.7350, 38.7800),
}

# Researched on the ground, so the script must not move them.
FIXED: dict[str, tuple[float, float]] = {
    "Selam Mart": (9.0366, 38.7523),
    "Abebe Shop": (9.0315, 38.7561),
    "Central Supermarket": (8.9971, 38.7878),
    "Shoa Supermarket Megenagna": (9.0189, 38.8003),
    "Merkato Wholesale Corner": (9.0341, 38.7420),
    "mohasbeza.com": (9.0192, 38.7525),
}

# district -> (name, chain, kind)
STORES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "Bole": (
        ("Central Supermarket", "Central Group", "supermarket"),
        ("Shoa Supermarket Bole Medhanialem", "Shoa Supermarket", "supermarket"),
        ("Safeway Supermarket Bole", "Safeway", "supermarket"),
        ("Getfam Supermarket Atlas", "Getfam", "supermarket"),
        ("Queens Supermarket Rwanda", "Queens Supermarket", "supermarket"),
        ("Zemen Supermarket Wollo Sefer", "Zemen Supermarket", "supermarket"),
        ("Selam Retail Bole", "Selam Retail", "supermarket"),
        ("Purpose Black Bole", "Purpose Black", "supermarket"),
        ("Bambis Bole Branch", "Bambis", "supermarket"),
        ("Friendship Mall Market", "", "supermarket"),
        ("Meskel Flower Fresh Market", "", "supermarket"),
        ("Genet Supermarket Gerji", "", "supermarket"),
        ("Gerji Mebrat Haile Market", "", "supermarket"),
        ("Gerji Mini Market", "", "shop"),
        ("Bole Michael Corner Shop", "", "shop"),
        ("Alem Suq Bole Bulbula", "", "shop"),
        ("Arabsa Family Shop", "", "shop"),
        ("Hana Mart Bole Homes", "", "shop"),
        ("Japan Sefer Grocery", "", "shop"),
        ("Cameroon Street Suq", "", "shop"),
        ("Denberua Retail Bole", "", "shop"),
        ("Airport Road Minimarket", "", "shop"),
        ("Lem Hotel Grocery", "", "shop"),
        ("Wollo Sefer Daily Shop", "", "shop"),
        ("Bole Rwanda Suq", "", "shop"),
        ("Bole Arabsa Wholesale", "", "shop"),
        ("Imperial Minimarket Bole", "", "shop"),
        ("Bole Dembel Grocery", "", "shop"),
        ("Woreda 03 Consumer Shop", "", "shop"),
        ("Sunshine Sefer Market", "", "shop"),
        ("Bole Tele Suq", "", "shop"),
        ("Kokeb Minimarket Gerji", "", "shop"),
        ("Yerer Family Shop", "", "shop"),
        ("Bethel Suq Bole", "", "shop"),
        ("Enat Mart Bole Michael", "", "shop"),
        ("Abenezer Shop Bole Bulbula", "", "shop"),
        ("Mekedonia Road Minimarket", "", "shop"),
        ("Tsehay Mart Bole", "", "shop"),
        ("Bole Chefe Grocery", "", "shop"),
        ("Winget Road Suq", "", "shop"),
    ),
    "Yeka": (
        ("Shoa Supermarket Megenagna", "Shoa Supermarket", "supermarket"),
        ("Safeway Supermarket CMC", "Safeway", "supermarket"),
        ("Getfam Supermarket Ayat", "Getfam", "supermarket"),
        ("Queens Supermarket Gurd Shola", "Queens Supermarket", "supermarket"),
        ("Zemen Supermarket Signal", "Zemen Supermarket", "supermarket"),
        ("Selam Retail Kotebe", "Selam Retail", "supermarket"),
        ("Purpose Black Ayat", "Purpose Black", "supermarket"),
        ("Bambis Kebena", "Bambis", "supermarket"),
        ("Zefmesh Grand Mall Market", "", "supermarket"),
        ("Signal Fresh Market", "", "supermarket"),
        ("Ayat Adebabay Market", "", "supermarket"),
        ("Fresh Corner Kebena", "", "shop"),
        ("Hayahulet Corner Shop", "", "shop"),
        ("Megenagna Daily Suq", "", "shop"),
        ("Shola Market Grocery", "", "shop"),
        ("Yeka Abado Family Shop", "", "shop"),
        ("Kara Kore Minimarket", "", "shop"),
        ("Gurd Shola Consumer Shop", "", "shop"),
        ("Kotebe Suq", "", "shop"),
        ("22 Mazoria Minimarket", "", "shop"),
        ("Semen Mazegaja Grocery", "", "shop"),
        ("Kebena Family Shop", "", "shop"),
        ("Ferensay Legasion Suq", "", "shop"),
        ("British Embassy Road Shop", "", "shop"),
        ("CMC Michael Grocery", "", "shop"),
        ("Yeka Michael Suq", "", "shop"),
        ("Haile Gebreselassie Road Suq", "", "shop"),
        ("Meri Loke Minimarket", "", "shop"),
        ("Bethel Yeka Shop", "", "shop"),
        ("Tafo Grocery", "", "shop"),
        ("Wesen Suq Kotebe", "", "shop"),
        ("Abado Consumer Cooperative", "", "shop"),
        ("Gojo Minimarket Yeka", "", "shop"),
        ("Sami Mart Megenagna", "", "shop"),
        ("Rahel Shop Hayahulet", "", "shop"),
        ("Dessie Road Grocery", "", "shop"),
        ("Yeka Hills Minimarket", "", "shop"),
        ("Mesalemiya Suq Yeka", "", "shop"),
        ("Enkulal Fabrica Road Shop", "", "shop"),
        ("Kidane Mehret Grocery", "", "shop"),
    ),
    "Arada": (
        ("Selam Mart", "Selam Retail", "supermarket"),
        ("Shoa Supermarket Piassa", "Shoa Supermarket", "supermarket"),
        ("Safeway Supermarket Arat Kilo", "Safeway", "supermarket"),
        ("Getfam Supermarket Piassa", "Getfam", "supermarket"),
        ("Queens Supermarket Sidist Kilo", "Queens Supermarket", "supermarket"),
        ("Zemen Supermarket Arada", "Zemen Supermarket", "supermarket"),
        ("Bambis Piassa", "Bambis", "supermarket"),
        ("Purpose Black Merkato", "Purpose Black", "supermarket"),
        ("Piassa Fresh Market", "", "supermarket"),
        ("Arada Consumer Cooperative", "", "supermarket"),
        ("mohasbeza.com", "", "online"),
        ("Abebe Shop", "", "shop"),
        ("Merkato Wholesale Corner", "", "shop"),
        ("Arat Kilo Minimarket", "", "shop"),
        ("Sidist Kilo Grocery", "", "shop"),
        ("Amist Kilo Consumer Shop", "", "shop"),
        ("Doro Manekia Suq", "", "shop"),
        ("Serategna Sefer Shop", "", "shop"),
        ("Gojam Berenda Wholesale", "", "shop"),
        ("Autobis Tera Minimarket", "", "shop"),
        ("Tewodros Square Grocery", "", "shop"),
        ("Ras Mekonnen Suq", "", "shop"),
        ("Churchill Avenue Market", "", "shop"),
        ("Menelik Square Shop", "", "shop"),
        ("Ginfle Family Shop", "", "shop"),
        ("Sebategna Minimarket", "", "shop"),
        ("Wonberema Grocery", "", "shop"),
        ("Taitu Street Suq", "", "shop"),
        ("Cinema Ethiopia Grocery", "", "shop"),
        ("Adarash Minimarket", "", "shop"),
        ("Arada Giyorgis Shop", "", "shop"),
        ("Enrico Road Suq", "", "shop"),
        ("Bank Road Minimarket", "", "shop"),
        ("Semien Hotel Road Grocery", "", "shop"),
        ("Kuas Meda Suq", "", "shop"),
        ("Tekle Haymanot Market", "", "shop"),
        ("Yordanos Shop Piassa", "", "shop"),
        ("Meskerem Minimarket Arada", "", "shop"),
        ("Nur Suq Merkato", "", "shop"),
        ("Ras Desta Road Grocery", "", "shop"),
    ),
}


def coordinates(name: str, district: str) -> tuple[float, float]:
    if name in FIXED:
        return FIXED[name]
    south, north, west, east = BOXES[district]
    rng = Random(f"{district}|{name}")
    return round(rng.uniform(south, north), 4), round(rng.uniform(west, east), 4)


def main() -> None:
    for district, rows in STORES.items():
        assert len(rows) == 40, f"{district} has {len(rows)} stores, expected 40"

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["name", "chain", "district", "latitude", "longitude", "kind"])
        for district, rows in STORES.items():
            for name, chain, kind in rows:
                latitude, longitude = coordinates(name, district)
                writer.writerow([name, chain, district, latitude, longitude, kind])

    print(f"wrote {sum(len(rows) for rows in STORES.values())} stores to {OUTPUT}")


if __name__ == "__main__":
    main()
