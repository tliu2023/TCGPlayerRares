"""Logs into TCGPlayer so cart additions are tied to the account.

Credentials come from TCGPLAYER_USERNAME/TCGPLAYER_PASSWORD env vars and are
never logged. The login page is protected by hCaptcha (confirmed live), so
an automated headless login can still get silently challenged/blocked - if
that happens, fall back to running once with HEADLESS=false and logging in
by hand. The session persists in BROWSER_PROFILE_DIR for every run after
that, so this is normally a one-time step.
"""
import logging

from playwright.sync_api import Page

from src import config

logger = logging.getLogger(__name__)

# Only rendered in the header when no one is signed in (confirmed live).
_SIGNED_OUT_SELECTOR = "a[data-aid='header-sign-in']"


def is_logged_in(page: Page) -> bool:
    # Logged-out visits to /account redirect to /login, which has no header
    # at all - so the sign-in-link absence check alone gives a false
    # positive there. Check the URL first (confirmed live).
    if "/login" in page.url:
        return False
    return page.query_selector(_SIGNED_OUT_SELECTOR) is None


def ensure_logged_in(page: Page) -> bool:
    """Returns True if a logged-in session is active by the time this
    returns, whether it already was or login just succeeded."""
    page.goto(config.TCGPLAYER_ACCOUNT_URL, wait_until="domcontentloaded")
    if is_logged_in(page):
        logger.info("Already logged in to TCGPlayer")
        return True

    if not (config.TCGPLAYER_USERNAME and config.TCGPLAYER_PASSWORD):
        logger.warning(
            "Not logged in to TCGPlayer and TCGPLAYER_USERNAME/TCGPLAYER_PASSWORD "
            "are not set. Run once with HEADLESS=false and log in manually - the "
            "session persists in BROWSER_PROFILE_DIR for future runs."
        )
        return False

    page.goto(config.TCGPLAYER_LOGIN_URL, wait_until="domcontentloaded")
    page.fill("input[data-testid='sign-in-email']", config.TCGPLAYER_USERNAME)
    page.fill("input[data-testid='sign-in-password']", config.TCGPLAYER_PASSWORD)
    page.click("button[data-testid='sign-in-submit']")
    page.wait_for_timeout(3000)  # let a redirect (or hCaptcha challenge) settle

    page.goto(config.TCGPLAYER_ACCOUNT_URL, wait_until="domcontentloaded")
    if is_logged_in(page):
        logger.info("Logged in to TCGPlayer as %s", config.TCGPLAYER_USERNAME)
        return True

    logger.warning(
        "Automated login did not complete - TCGPlayer's login page is "
        "hCaptcha-protected and may have challenged the headless browser. "
        "Run once with HEADLESS=false to log in and solve the captcha "
        "manually; the session persists in BROWSER_PROFILE_DIR afterward."
    )
    return False
