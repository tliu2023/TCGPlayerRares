"""Accumulates qualifying listings per seller across every rare in a run,
then decides which sellers' orders are worth adding to the cart."""
import logging

from src import config
from src.models import Listing, SellerAggregate

logger = logging.getLogger(__name__)


def _cents_per_rare(aggregate: SellerAggregate) -> float:
    return (aggregate.total / aggregate.total_quantity) if aggregate.total_quantity else float("inf")


class SellerAggregator:
    """Tracks a running per-seller total as rares are scraped one at a time.

    Call add_listings() once per rare's scraped listings. After every rare has
    been processed, call qualifying_targets() to get the per-seller cart
    targets for every seller whose running total exceeded
    MIN_SELLER_ORDER_TOTAL.
    """

    def __init__(self) -> None:
        self._sellers: dict[str, SellerAggregate] = {}

    def add_listings(self, listings: list[Listing]) -> None:
        cheap_listings = [listing for listing in listings if listing.price <= config.MAX_PRICE]
        for listing in cheap_listings:
            aggregate = self._sellers.setdefault(listing.seller_name, SellerAggregate(listing.seller_name))
            aggregate.seller_url = aggregate.seller_url or listing.seller_url
            aggregate.total += listing.price * listing.quantity_available
            aggregate.total_quantity += listing.quantity_available
            aggregate.listings.append(listing)
        logger.info("%d/%d listings were under $%.2f", len(cheap_listings), len(listings), config.MAX_PRICE)

    def _qualifying_aggregates(self) -> list[SellerAggregate]:
        """Sellers whose running total exceeds MIN_SELLER_ORDER_TOTAL,
        ordered cheapest cents/rare first so the best deals are prioritized
        if a cart-add run gets cut short partway through."""
        qualifying = []
        for aggregate in self._sellers.values():
            if aggregate.total > config.MIN_SELLER_ORDER_TOTAL:
                qualifying.append(aggregate)
            else:
                logger.debug(
                    "Skipping seller '%s': order total $%.2f does not exceed minimum $%.2f",
                    aggregate.seller_name, aggregate.total, config.MIN_SELLER_ORDER_TOTAL,
                )
        qualifying.sort(key=_cents_per_rare)
        return qualifying

    def qualifying_targets(self) -> list[dict]:
        """Returns one dict per qualifying seller - seller_name, seller_url,
        and the distinct product IDs to buy from them - for the cart-add
        phase to look up on that seller's own search-results page instead of
        visiting each listing individually."""
        targets = []
        for aggregate in self._qualifying_aggregates():
            product_ids = list(dict.fromkeys(listing.product_id for listing in aggregate.listings))
            targets.append({
                "seller_name": aggregate.seller_name,
                "seller_url": aggregate.seller_url,
                "product_ids": product_ids,
            })

        total_listings = sum(len(t["product_ids"]) for t in targets)
        logger.info(
            "%d/%d sellers qualify (order total > $%.2f), %d distinct products to add to cart",
            len(targets), len(self._sellers), config.MIN_SELLER_ORDER_TOTAL, total_listings,
        )
        return targets

    def summary(self) -> list[str]:
        """One line per seller whose running total exceeds
        MIN_SELLER_ORDER_TOTAL: total $, total rares, the average price per
        rare in cents (rounded to the nearest 0.01 cent), and the seller's
        storefront URL - ordered cheapest cents/rare first to match the
        cart-add priority order."""
        lines = []
        for aggregate in self._qualifying_aggregates():
            cents_per_rare = (aggregate.total / aggregate.total_quantity) * 100 if aggregate.total_quantity else 0.0
            lines.append(
                f"{aggregate.seller_name}: ${aggregate.total:.2f} total, "
                f"{aggregate.total_quantity} rares, {cents_per_rare:.2f} cents/rare, {aggregate.seller_url}"
            )
        return lines

