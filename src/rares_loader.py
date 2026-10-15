"""Loads the rares.txt watchlist into RareCard objects."""
import logging
from pathlib import Path

from src.models import RareCard

logger = logging.getLogger(__name__)


def load_rares(rares_file: Path) -> list[RareCard]:
    if not rares_file.exists():
        raise FileNotFoundError(f"Rares list not found: {rares_file}")

    rares: list[RareCard] = []
    for raw_line in rares_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("http://") or line.startswith("https://"):
            rares.append(RareCard(name=line, url=line))
        else:
            rares.append(RareCard(name=line, url=None))

    logger.info("Loaded %d rares from %s", len(rares), rares_file)
    return rares
