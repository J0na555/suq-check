# Catalog research

Two CSVs feed `python -m app.seed`. The example rows are real products and real
Addis stores; add more rows in the same shape. Target: about 120 products across
the fourteen supported categories and about 46 stores.

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
| `district` | Addis district or sub-city: `Piassa`, `Bole`, `Yeka` |
| `latitude`, `longitude` | Decimal degrees; the app measures distance from these |
| `kind` | `supermarket`, `shop`, or `online` |

Online sellers still need coordinates; use the city centre.
