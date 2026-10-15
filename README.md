# TCGPlayerRares

Scrapes TCGPlayer listings for cheap One Piece TCG rares and automatically builds a shopping cart of qualifying cards.

## How it works

1. Reads a list of rare card names/URLs to check from `rares.txt`.
2. For each rare, scrapes current TCGPlayer listings and filters out sellers whose price exceeds a configurable `MAX_PRICE`.
3. For each remaining seller, checks that `quantity_available * price` for that seller's qualifying rares totals more than $5 (TCGPlayer's per-seller minimum).
4. Adds all qualifying rares to the cart.

## Architecture

- **`rares.txt`** — plain text list of rare card names or TCGPlayer URLs to track. Since the pool of rares only changes when new sets release, this list is maintained manually rather than scraped dynamically.
- **Scraper** — fetches current listings/prices for each entry in `rares.txt`.
- **Filter** — applies the `MAX_PRICE` threshold and the $5 per-seller minimum rule.
- **Cart builder** — adds the filtered results to the TCGPlayer cart.

## Configuration

Set as environment variables (see `src/config.py` for defaults):

- `MAX_PRICE` — maximum price per card to consider a rare "cheap".
- `MIN_SELLER_ORDER_TOTAL` — minimum order total (per seller) required to add their listings to the cart.
- `HEADLESS` — set to `false` to watch the browser (useful for first-time login).
- `RARES_FILE` — path to the watchlist, defaults to `rares.txt`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
HEADLESS=false python -m src.main   # first run: log into TCGPlayer when the browser opens
python -m src.main                  # subsequent runs reuse the saved session
```

## Project layout

- `rares.txt` — watchlist of card names/URLs.
- `src/config.py` — tunable thresholds and paths.
- `src/models.py` — `RareCard` / `Listing` data classes.
- `src/rares_loader.py` — parses `rares.txt`.
- `src/scraper.py` — Playwright scraping of TCGPlayer product pages.
- `src/filters.py` — applies `MAX_PRICE` and per-seller minimum rules.
- `src/cart.py` — adds qualifying listings to the cart.
- `src/main.py` — orchestrates the run.

> **Note:** CSS selectors in `scraper.py`/`cart.py` are marked `TODO` placeholders — verify them against TCGPlayer's current DOM before running against the live site.
