"""Entry point (step 1 of 2): scrape each tracked rare, aggregate per-seller
totals, and write seller_summary.txt (human-readable) and cart_targets.json
(consumed by `python -m src.add_to_cart`, which actually adds things to the
cart). Scraping is read-only, so this step doesn't need to be logged in.
"""
import json
import logging

from playwright.sync_api import sync_playwright

from src import config, scraper
from src.filters import SellerAggregator
from src.rares_loader import load_rares

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    rares = load_rares(config.RARES_FILE)
    config.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        launch_kwargs = {}
        if config.HEADLESS:
            launch_kwargs["user_agent"] = config.HEADLESS_USER_AGENT
            launch_kwargs["viewport"] = config.HEADLESS_VIEWPORT
        context = playwright.chromium.launch_persistent_context(
            str(config.BROWSER_PROFILE_DIR), headless=config.HEADLESS, **launch_kwargs
        )
        scraper.configure_listing_display(context)
        page = context.new_page()

        # Running per-seller totals, built up one rare at a time.
        aggregator = SellerAggregator()
        for rare in rares:
            try:
                listings = scraper.get_listings(page, rare)
                aggregator.add_listings(listings)
            except Exception:
                logger.exception("Failed to scrape '%s', skipping", rare.name)
            page.wait_for_timeout(int(config.REQUEST_DELAY_SECONDS * 1000))

        context.close()

    # Only now, after every rare has been scraped, do we know each seller's
    # final total - so the summary and cart targets are written here.
    summary_lines = aggregator.summary()
    for line in summary_lines:
        logger.info(line)
    config.SELLER_SUMMARY_FILE.write_text("\n".join(summary_lines) + "\n" if summary_lines else "")

    targets = aggregator.qualifying_targets()
    config.CART_TARGETS_FILE.write_text(json.dumps(targets, indent=2))
    if not targets:
        logger.info("No sellers reached MIN_SELLER_ORDER_TOTAL")



if __name__ == "__main__":
    main()
