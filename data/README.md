# Catalog research

Two CSVs feed `python -m app.seed`. The rows are real products and real Addis
stores; add more in the same shape. The committed files hold the basket the
pitch describes: 40 products across the fourteen supported categories, and 120
shops split evenly between Bole, Yeka, and Arada.

## products.csv

| Column | Notes |
| --- | --- |
| `canonical_name` | How the app shows it, size included: `Hayat Cooking Oil 1L` |
| `brand` | Brand only, no size |
| `category` | One of `cooking_oil`, `sugar`, `rice`, `flour`, `salt`, `pasta`, `coffee`, `tea`, `milk`, `soap`, `detergent`, `toothpaste`, `shampoo`, `bottled_water` |
| `size_value` | Number only: `1`, `175`, `500` |
| `size_unit` | One of `ml`, `l`, `g`, `kg`, `piece` |
| `barcode` | Leave empty unless you read it off the pack |
| `base_price_etb` | A typical Addis price today; the generator varies it per store and per day |
| `coverage` | `rich`, `normal`, `thin`, or `stale` |

`coverage` decides how much evidence the seed invents, which is what makes the
confidence numbers differ between products:

- `rich` reports from many stores every day, so confidence lands in the nineties
- `normal` a few stores reporting most days
- `thin` one or two stores reporting rarely, so confidence sits in the seventies
- `stale` nothing reported for the last two weeks, so confidence is capped at 60

Give most rows `normal`, a handful `rich`, and leave a few `thin` and `stale` on
purpose. A demo where every price is 98% confident proves nothing.

Prices outside the range in `category_price_bounds` are rejected by the
verification gate, so keep `base_price_etb` plausible for the pack size.

## stores.csv

| Column | Notes |
| --- | --- |
| `name` | Branch name as written on the shop |
| `chain` | Empty for independent shops |
| `district` | Exactly one of `Bole`, `Yeka`, `Arada` |
| `latitude`, `longitude` | Decimal degrees; the app measures distance from these |
| `kind` | `supermarket`, `shop`, or `online` |

`district` is free text in the database, so a neighbourhood written where a
sub-city belongs — `Piassa` instead of `Arada` — silently splits the district
breakdown in two. Write the sub-city, and put the neighbourhood in `name`.

Online sellers still need coordinates; use the city centre. They are the only
kind the seed's weekly store-visit pass skips, since nobody walks into a website.

`scripts/build_stores_csv.py` regenerates this file from a hand-written list of
names and chains, spreading coordinates over a bounding box per district. Edit
the script rather than the CSV when adding shops in bulk.
