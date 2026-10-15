"""Project-wide configuration. Override via environment variables of the same name."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Maximum price (USD) per card for a listing to be considered "cheap".
MAX_PRICE = float(os.getenv("MAX_PRICE", "0.15"))

# TCGPlayer enforces a minimum order total per seller.
MIN_SELLER_ORDER_TOTAL = float(os.getenv("MIN_SELLER_ORDER_TOTAL", "5.00"))

# Input list of rares to check (names or TCGPlayer URLs).
RARES_FILE = Path(os.getenv("RARES_FILE", ROOT_DIR / "rares.txt"))

# Playwright persistent browser profile, reused so the TCGPlayer guest-cart
# session (and any cookies from manually logging in) survives between runs.
BROWSER_PROFILE_DIR = Path(os.getenv("BROWSER_PROFILE_DIR", ROOT_DIR / ".auth" / "browser_profile"))

HEADLESS = os.getenv("HEADLESS", "true").lower() != "false"

# TCGPlayer's bot protection blocks headless Chromium's default UA/viewport
# (confirmed live: with these defaults .listing-item never renders, but a
# normal-Chrome UA + real viewport size loads it fine). Only needed when
# HEADLESS is true; headed Chromium doesn't need spoofing.
HEADLESS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
HEADLESS_VIEWPORT = {"width": 1728, "height": 1117}

# TCGPlayer remembers the listings-per-page/sort choice via a cookie rather
# than a URL param (confirmed live: "product-display-settings=sort=price+
# shipping&size=50"). 50 is the site's max page size, cutting page count for
# high-inventory rares by ~5x versus the default of 10.
LISTINGS_PER_PAGE = int(os.getenv("LISTINGS_PER_PAGE", "50"))

TCGPLAYER_SEARCH_URL = "https://www.tcgplayer.com/search/one-piece-card-game/product"
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))

# Per-seller summary is written here every run, overwriting the previous one.
SELLER_SUMMARY_FILE = Path(os.getenv("SELLER_SUMMARY_FILE", ROOT_DIR / "seller_summary.txt"))

# Per-seller cart targets (machine-readable) written by the scrape run and
# consumed by `python -m src.add_to_cart`, which runs as a separate step.
CART_TARGETS_FILE = Path(os.getenv("CART_TARGETS_FILE", ROOT_DIR / "cart_targets.json"))

# Lists a seller's matching inventory with add-to-cart buttons right in the
# results (confirmed live), so the cart-add step can add several items per
# seller from one page instead of visiting each listing individually.
SELLER_SEARCH_URL = "https://www.tcgplayer.com/search/one-piece-card-game/product"
