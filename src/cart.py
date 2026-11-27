"""Adds a seller's qualifying listings to the cart by loading each product
page filtered to just that seller (/product/{id}?seller={code}), foil, Near
Mint - one page load per product, no pagination.
"""
from __future__ import annotations

import logging
import re

from playwright.sync_api import Page

from src import config
from src.scraper import parse_price

logger = logging.getLogger(__name__)


def _seller_code(seller_url: str) -> str:
    return seller_url.rstrip("/").rsplit("/", 1)[-1]


def _product_url(product_id: str, seller_code: str) -> str:
    return (
        f"https://www.tcgplayer.com/product/{product_id}"
        f"?seller={seller_code}&Printing=Foil&Condition=Near+Mint&Language=English"
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


CART_BADGE_SELECTOR = ".mp-header__content__cart-count__chip"


def _read_cart_count(page: Page) -> int:
    el = page.query_selector(CART_BADGE_SELECTOR)
    text = el.inner_text().strip() if el else ""
    return int(text) if text.isdigit() else 0


def _wait_for_cart_count(page: Page, expected: int) -> bool:
    """Waits for the header cart badge to reach `expected`, confirming the
    add-to-cart click actually landed before moving on to the next click.

    A fixed sleep isn't enough here: firing add-to-cart clicks back-to-back
    races the async requests that update the cart, and later ones can
    silently clobber earlier ones (confirmed live - 9 rapid clicks left only
    1 product in the real cart). Waiting for the badge to actually reach the
    expected count is a real confirmation instead of a guess.
    """
    try:
        page.wait_for_function(
            """(expected) => {
                const el = document.querySelector('.mp-header__content__cart-count__chip');
                return el && el.textContent.trim() === String(expected);
            }""",
            arg=expected,
            timeout=8000,
        )
        return True
    except Exception:
        return False


def _clear_seller_filter(page: Page) -> None:
    # ?seller= persists as a sticky SellerFilter cookie (confirmed live); left
    # in the shared profile, it would limit every later product page to one seller.
    page.context.clear_cookies(name="SellerFilter")


def _add_product(page: Page, product_id: str, seller_code: str, seller_name: str, cart_count: int) -> int | None:
    """Adds this seller's listing of `product_id` to the cart. Returns the
    updated cart count, or None if no qualifying listing was added."""
    page.goto(_product_url(product_id, seller_code), wait_until="domcontentloaded")
    try:
        page.wait_for_selector(".listing-item", timeout=10000)
    except Exception:
        return None  # seller no longer has a matching listing

    for row in page.query_selector_all(".listing-item"):
        seller_link = row.query_selector(".seller-info__name")
        if not seller_link or not (seller_link.get_attribute("href") or "").rstrip("/").endswith(seller_code):
            continue

        price_el = row.query_selector(".listing-item__listing-data__info__price")
        price = parse_price(price_el.inner_text()) if price_el else None
        if price is None or price > config.MAX_PRICE:
            continue

        add_button = row.query_selector("button[data-testid^='add-to-cart']")
        if not add_button:
            continue

        quantity = _select_max_quantity(page, row)
        add_button.click()
        expected_count = cart_count + quantity
        if _wait_for_cart_count(page, expected_count):
            cart_count = expected_count
        else:
            logger.warning(
                "Cart badge didn't confirm product %s (expected %d) - may not have been added",
                product_id, expected_count,
            )
            cart_count = _read_cart_count(page)
        logger.info("Added to cart: %dx product %s from %s @ $%.2f", quantity, product_id, seller_name, price)
        return cart_count

    return None


def add_seller_targets(page: Page, seller: dict) -> None:
    """Adds every wanted product_id in `seller` to the cart, loading each
    product page filtered to that seller."""
    seller_name = seller["seller_name"]
    seller_code = _seller_code(seller["seller_url"])
    wanted = list(dict.fromkeys(seller["product_ids"]))
    added: set[str] = set()
    cart_count = _read_cart_count(page)

    try:
        for product_id in wanted:
            try:
                new_count = _add_product(page, product_id, seller_code, seller_name, cart_count)
            except Exception:
                logger.exception("Failed to add product %s from %s", product_id, seller_name)
                continue
            if new_count is not None:
                cart_count = new_count
                added.add(product_id)
    finally:
        _clear_seller_filter(page)

    missing = set(wanted) - added
    if missing:
        logger.warning(
            "%s: %d/%d targets not added (sold out, price changed, or page layout mismatch): %s",
            seller_name, len(missing), len(wanted), ", ".join(sorted(missing)),
        )


def log_cart_summary(page: Page) -> None:
    """Navigates to the real cart page and logs what's actually in it, so a
    run's success can be confirmed without relying solely on click logs."""
    page.goto("https://www.tcgplayer.com/cart", wait_until="networkidle")
    try:
        page.wait_for_selector("text=Shopping Cart", timeout=10000)
    except Exception:
        pass
    text = page.evaluate("() => document.body.innerText")
    if "Your cart is empty" in text:
        logger.warning("Cart check: cart is EMPTY")
        return
    match = re.search(r"Items\n(\d+)", text)
    logger.info("Cart check: %s item(s) in cart", match.group(1) if match else "unknown number of")

