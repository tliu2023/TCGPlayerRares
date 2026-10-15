"""Adds a seller's qualifying listings to the cart via their own TCGPlayer
search-results page, filtered to just that seller (?seller={code}), foil,
Rare, Near Mint One Piece cards. Each page of results (confirmed live) has
up to 10 rows with an add-to-cart button right there, so one seller can
usually be handled in a couple of page loads instead of visiting every
listing individually.
"""
import logging
import re

from playwright.sync_api import Page

from src import config
from src.scraper import parse_price

logger = logging.getLogger(__name__)


def _seller_code(seller_url: str) -> str:
    return seller_url.rstrip("/").rsplit("/", 1)[-1]


def _search_url(seller_code: str, page_number: int) -> str:
    return (
        f"{config.SELLER_SEARCH_URL}?productLineName=one-piece-card-game&seller={seller_code}"
        f"&view=list&Printing=Foil&page={page_number}&RarityName=Rare&Condition=Near+Mint"
    )


def _select_max_quantity(page: Page, row) -> int:
    """Clicks the row's quantity <select> to a count matching real stock,
    e.g. "of 3" -> options 1/2/3), then selects the highest value.

    Confirmed live: without first clicking the select, it only ever has a
    single "1" option (regardless of real availability) and the add-to-cart
    button silently does nothing - the click has to land after the select
    has been interacted with at least once.
    """
    select_el = row.query_selector("select")
    if not select_el:
        return 1

    select_el.click()
    page.wait_for_timeout(300)  # let the real option list render

    values = [opt.get_attribute("value") for opt in select_el.query_selector_all("option")]
    quantities = [int(v) for v in values if v and v.isdigit()]
    max_quantity = max(quantities) if quantities else 1
    select_el.select_option(str(max_quantity))
    return max_quantity


def add_seller_targets(page: Page, seller: dict) -> None:
    """Adds every wanted product_id in `seller` to the cart, paging through
    that seller's filtered search results until all targets are found or
    there are no more pages."""
    seller_name = seller["seller_name"]
    seller_code = _seller_code(seller["seller_url"])
    wanted = set(seller["product_ids"])
    added: set[str] = set()
    page_number = 1

    while wanted - added:
        page.goto(_search_url(seller_code, page_number), wait_until="domcontentloaded")
        try:
            page.wait_for_selector(".search-result", timeout=10000)
        except Exception:
            break  # no (more) results for this seller
        rows = page.query_selector_all(".search-result")
        if not rows:
            break

        for row in rows:
            link = row.query_selector("a[href*='/product/']")
            match = re.search(r"/product/(\d+)", link.get_attribute("href") or "") if link else None
            product_id = match.group(1) if match else None
            if not product_id or product_id not in wanted or product_id in added:
                continue

            price_el = row.query_selector(".inventory__price")
            price = parse_price(price_el.inner_text()) if price_el else None
            if price is None or price > config.MAX_PRICE:
                continue

            add_button = row.query_selector("button[data-testid^='add-to-cart']")
            if not add_button:
                continue

            try:
                quantity = _select_max_quantity(page, row)
                add_button.click()
                added.add(product_id)
                logger.info(
                    "Added to cart: %dx product %s from %s @ $%.2f", quantity, product_id, seller_name, price,
                )
            except Exception:
                logger.exception("Failed to add product %s from %s", product_id, seller_name)

        page_number += 1

    missing = wanted - added
    if missing:
        logger.warning(
            "%s: %d/%d targets not added (sold out, price changed, or page layout mismatch): %s",
            seller_name, len(missing), len(wanted), ", ".join(sorted(missing)),
        )

