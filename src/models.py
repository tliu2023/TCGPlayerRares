"""Data models shared across the scraper, filter, and cart modules."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RareCard:
    """A single entry from rares.txt."""
    name: str
    url: str | None  # None when only a name was provided; scraper resolves it via search.


@dataclass(frozen=True)
class Listing:
    """A single seller's listing for a given card."""
    card_name: str
    product_id: str  # TCGPlayer product ID, used to match this card on the seller's search-results page.
    seller_name: str
    seller_url: str  # Seller's storefront URL, e.g. https://www.tcgplayer.com/sellers/{name}/{code}
    price: float
    quantity_available: int
    condition: str


@dataclass
class SellerAggregate:
    """Running total for one seller, accumulated across every rare scraped this run."""
    seller_name: str
    seller_url: str = ""
    total: float = 0.0
    total_quantity: int = 0
    listings: list[Listing] = field(default_factory=list)
