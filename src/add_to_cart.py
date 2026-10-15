"""Entry point (step 2 of 2): reads cart_targets.json (written by
`python -m src.main`) and adds each seller's qualifying listings to the
cart, via their seller-scoped search-results page (see cart.py). Builds a
guest cart - run headed (HEADLESS=false) and log in manually afterward,
while the browser stays open, to carry the cart over to your account.
"""
import json
import logging

from playwright.sync_api import sync_playwright

from src import cart, config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    if not config.CART_TARGETS_FILE.exists():
        logger.error("%s not found - run `python -m src.main` first", config.CART_TARGETS_FILE)
        return

    sellers = json.loads(config.CART_TARGETS_FILE.read_text())
    if not sellers:
        logger.info("No qualifying sellers in %s", config.CART_TARGETS_FILE)
        return

    config.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        launch_kwargs = {}
        if config.HEADLESS:
            launch_kwargs["user_agent"] = config.HEADLESS_USER_AGENT
            launch_kwargs["viewport"] = config.HEADLESS_VIEWPORT
        context = playwright.chromium.launch_persistent_context(
            str(config.BROWSER_PROFILE_DIR), headless=config.HEADLESS, **launch_kwargs
        )
        page = context.new_page()

        for seller in sellers:
            cart.add_seller_targets(page, seller)

        if config.HEADLESS:
            context.close()
        else:
            input("Done adding to cart. Log in (or review/checkout) in the browser window, "
                  "then press Enter here to close it...")
            context.close()


if __name__ == "__main__":
    main()
