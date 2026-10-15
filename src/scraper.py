"""Scrapes TCGPlayer product pages for current seller listings.

Listing data (price, condition, seller, quantity) is read from the DOM/text
via Playwright selectors rather than screenshots - this is cheaper to compute
and more reliable than visually parsing a rendered page.

Selectors for the listing row, price, condition, seller name, quantity, and
add-to-cart button were verified live against an OP16 product page on
2026-10-15. The photo/comment-listing detector is still a TODO placeholder -
no listing with a photo/comment turned up on the pages checked so far.
"""
import logging
import re
from urllib.parse import urlencode, urljoin, urlparse, parse_qs, urlunparse

from playwright.sync_api import BrowserContext, Page

from src import config
from src.models import Listing, RareCard

logger = logging.getLogger(__name__)


def configure_listing_display(context: BrowserContext) -> None:
    """Sets TCGPlayer's listings-per-page/sort preference, which the site
    reads from a cookie rather than a URL param. Call this once per context,
    before scraping any product pages."""
    context.add_cookies([{
        "name": "product-display-settings",
        "value": f"sort=price+shipping&size={config.LISTINGS_PER_PAGE}",
        "domain": ".tcgplayer.com",
        "path": "/",
    }])


def resolve_url(page: Page, rare: RareCard) -> str:
    """Returns rare.url if set, otherwise searches TCGPlayer by name and
    returns the first matching product URL."""
    if rare.url:
        return rare.url

    page.goto(config.TCGPLAYER_SEARCH_URL, wait_until="domcontentloaded")
    page.fill("input[type='search']", rare.name)  # TODO: verify search input selector
    page.keyboard.press("Enter")
    page.wait_for_selector(".search-result")  # TODO: verify result card selector

    first_result = page.query_selector(".search-result a")
    if not first_result:
        raise RuntimeError(f"No TCGPlayer search results found for '{rare.name}'")

    url = first_result.get_attribute("href")
    if not url:
        raise RuntimeError(f"Search result for '{rare.name}' had no href")
    return url if url.startswith("http") else f"https://www.tcgplayer.com{url}"


def get_listings(page: Page, rare: RareCard) -> list[Listing]:
    """Navigates to the card's product page and extracts every seller listing,
    paging through the listings table (?page=2, ?page=3, ...) until a page
    comes back with no rows, or a listing's price exceeds MAX_PRICE.

    Listings are sorted price-ascending by default (TCGPlayer's "Price +
    Shipping: Lowest First"), so as soon as one listing is too expensive we
    stop reading rows/pages for this rare entirely and move on to the next
    rare - everything after it would only be pricier.
    """
    base_url = resolve_url(page, rare)
    product_id = extract_product_id(base_url)
    listings: list[Listing] = []
    page_number = 1

    while True:
        page.goto(_with_page_number(base_url, page_number), wait_until="domcontentloaded")
        page.wait_for_selector(".listing-item")
        rows = page.query_selector_all(".listing-item")
        if not rows:
            break

        hit_max_price = False
        for row in rows:
            if _has_picture_or_description(row):
                continue

            seller_el = row.query_selector(".seller-info__name")
            price_el = row.query_selector(".listing-item__listing-data__info__price")
            qty_el = row.query_selector(".add-to-cart__available")
            condition_el = row.query_selector(".listing-item__condition")

            if not (seller_el and price_el):
                continue

            price = parse_price(price_el.inner_text())
            if price > config.MAX_PRICE:
                # Listings are price-ascending, so every row/page after this is pricier too.
                hit_max_price = True
                break

            seller_href = seller_el.get_attribute("href") or ""
            quantity = _parse_quantity(qty_el.inner_text()) if qty_el else 1
            listings.append(
                Listing(
                    card_name=rare.name,
                    product_id=product_id,
                    seller_name=seller_el.inner_text().strip(),
                    seller_url=urljoin("https://www.tcgplayer.com", seller_href),
                    price=price,
                    quantity_available=quantity,
                    condition=condition_el.inner_text().strip() if condition_el else "Unknown",
                )
            )

        if hit_max_price:
            break
        page_number += 1

    logger.info("Found %d listings for %s across %d page(s)", len(listings), rare.name, page_number)
    return listings


def extract_product_id(url: str) -> str:
    """Pulls the numeric product ID out of a TCGPlayer product URL, e.g.
    ".../product/696013/..." -> "696013"."""
    match = re.search(r"/product/(\d+)", url)
    if not match:
        raise ValueError(f"Could not find a product ID in URL: {url}")
    return match.group(1)



def _with_page_number(url: str, page_number: int) -> str:
    """Returns url with its "page" query param set to page_number."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_number)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def _has_picture_or_description(row) -> bool:
    """Skip listings with seller-added photos or a comment/description -
    these are typically hand-priced and shouldn't be treated as bulk-cheap."""
    # TODO: verify these selectors - no photo/comment listings have turned up
    # on the live pages checked so far, so this is still unverified.
    return bool(
        row.query_selector(".listing-item__listing-photo")
        or row.query_selector(".listing-item__comments")
    )


def parse_price(text: str) -> float:
    return float(text.replace("$", "").replace(",", "").strip())


def _parse_quantity(text: str) -> int:
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0
