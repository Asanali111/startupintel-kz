"""
Shared Article dataclass and abstract async base scraper.
"""

from __future__ import annotations

import abc
import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Browser, Page

logger = logging.getLogger(__name__)


# ── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class Article:
    """Internal representation of a single piece of content."""
    source: str         # e.g. 'digitalbusiness.kz'
    url: str            # unique article/post permalink
    title: str          # headline
    raw_content: str    # body text for LLM evaluation
    published_at: str = ""  # ISO-8601 or relative date string

    # Derived — computed once on creation
    id: str = field(init=False)

    def __post_init__(self) -> None:
        self.id = hashlib.sha256(self.url.encode()).hexdigest()[:16]


# ── Base Scraper ─────────────────────────────────────────────────────────────

class BaseScraper(abc.ABC):
    """
    Async interface every source scraper must implement.
    Subclasses override ``_scrape_page`` while the base handles
    browser lifecycle and history filtering.
    """

    SOURCE_NAME: str = "unknown"
    TARGET_URL: str = ""

    def __init__(self, seen_urls: set[str]) -> None:
        self._seen_urls = seen_urls

    # ── Public API ───────────────────────────────────────────────────────

    async def run(self, browser: Browser) -> list[Article]:
        """
        Open a page, scrape articles, and filter out already-seen URLs.
        Returns only *new* articles.
        """
        page: Page = await browser.new_page()
        try:
            logger.info("[%s] Navigating to %s", self.SOURCE_NAME, self.TARGET_URL)
            await page.goto(self.TARGET_URL, wait_until="domcontentloaded", timeout=30_000)
            raw_articles = await self._scrape_page(page)
        except Exception as exc:
            logger.error("[%s] Scraping failed: %s", self.SOURCE_NAME, exc)
            return []
        finally:
            await page.close()

        # De-duplicate against history
        new_articles = [a for a in raw_articles if a.url not in self._seen_urls]
        logger.info(
            "[%s] Found %d articles (%d new).",
            self.SOURCE_NAME,
            len(raw_articles),
            len(new_articles),
        )
        return new_articles

    # ── Template method ──────────────────────────────────────────────────

    @abc.abstractmethod
    async def _scrape_page(self, page: Page) -> list[Article]:
        """Subclasses extract Article objects from the loaded page."""
        ...
