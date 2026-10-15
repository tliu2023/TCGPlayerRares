# TCGPlayerRares

Scrapes TCGPlayer listings for cheap One Piece TCG rares and automatically builds a shopping cart of qualifying cards.

## How it works

Runs as two separate steps:

1. **Scrape** (`src/main.py`) — reads `rares.txt`, scrapes current TCGPlayer listings for each rare, and accumulates a running per-seller total across every rare. Writes:
   - `seller_summary.txt` — human-readable, one line per seller whose running total exceeds `MIN_SELLER_ORDER_TOTAL` (TCGPlayer's $5 per-seller minimum), sorted cheapest cents/rare first.
   - `cart_targets.json` — machine-readable, the same qualifying sellers plus the exact product IDs to buy from each.
2. **Add to cart** (`src/add_to_cart.py`) — reads `cart_targets.json` and for each seller pages through that seller's own filtered search results (foil, Rare, Near Mint, that seller only) adding matching products straight from the results list, building up a guest cart. When run headed (`HEADLESS=false`), the browser stays open afterward so you can log in and/or checkout manually - logging in at that point carries the guest cart over to your account.

Splitting these into two steps means you can review `seller_summary.txt` before spending anything, and re-run just the cart step without re-scraping.

## Architecture

- **`rares.txt`** — plain text list of rare card names or TCGPlayer URLs to track. Since the pool of rares only changes when new sets release, this list is maintained manually rather than scraped dynamically.
- **Scraper** (`src/scraper.py`) — fetches current listings/prices for each entry in `rares.txt`, paging through results until a listing exceeds `MAX_PRICE`.
- **Filter/Aggregator** (`src/filters.py`) — accumulates a running per-seller total across all rares and applies the `MAX_PRICE`/`MIN_SELLER_ORDER_TOTAL` rules.
- **Cart** (`src/cart.py`) — adds a seller's qualifying listings to the cart via their filtered search-results page.

## Configuration

Set as environment variables (see `src/config.py` for defaults):

- `MAX_PRICE` — maximum price per card to consider a rare "cheap" (default `0.15`).
- `MIN_SELLER_ORDER_TOTAL` — minimum order total (per seller) required to add their listings to the cart (default `5.00`).
- `HEADLESS` — set to `false` to watch the browser, and to keep it open afterward for manual login/checkout.
- `RARES_FILE` — path to the watchlist, defaults to `rares.txt`.
- `SELLER_SUMMARY_FILE` / `CART_TARGETS_FILE` — output paths for the two scrape artifacts, both overwritten each run.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

Using `make` (see `Makefile`):

```bash
make scrape                                  # step 1: scrape + write seller_summary.txt / cart_targets.json
make scrape RARES_FILE=rares_test_op16.txt   # scrape a smaller test list
make scrape HEADLESS=false                   # watch the scrape happen

make add-to-cart                             # step 2: add qualifying listings to the cart
make add-to-cart HEADLESS=false              # watch items get added
```

Or directly:

```bash
python -m src.main           # step 1
python -m src.add_to_cart    # step 2
```

## Project layout

- `rares.txt` — watchlist of card names/URLs.
- `seller_summary.txt` — generated per run: one line per qualifying seller (total $, rare count, cents/rare, storefront URL).
- `cart_targets.json` — generated per run: per-seller product IDs for the add-to-cart step.
- `src/config.py` — tunable thresholds and paths.
- `src/models.py` — `RareCard` / `Listing` / `SellerAggregate` data classes.
- `src/rares_loader.py` — parses `rares.txt`.
- `src/scraper.py` — Playwright scraping of TCGPlayer product pages.
- `src/filters.py` — `SellerAggregator`: running per-seller totals, `summary()`, and `qualifying_targets()`.
- `src/cart.py` — adds a seller's qualifying listings to the cart via their search-results page.
- `src/main.py` — step 1 entry point (scrape).
- `src/add_to_cart.py` — step 2 entry point (cart-add).
- `Makefile` — `make scrape` / `make add-to-cart` shortcuts.

