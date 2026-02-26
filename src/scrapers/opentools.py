"""
Scraper for opentools.ai/news — HTML page (no RSS available).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scrapers.base import Article, BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class OpenToolsScraper(BaseScraper):
    SOURCE_NAME = "opentools.ai"
    TARGET_URL = "https://opentools.ai/news"

    async def _scrape_page(self, page: Page) -> list[Article]:
        articles: list[Article] = []

        # Wait for news items to load
        await page.wait_for_selector("a[href*='/news/']", timeout=20_000)

        link_elements = await page.query_selector_all("a[href*='/news/']")

        seen_hrefs: set[str] = set()

        for el in link_elements:
            href = await el.get_attribute("href")
            if not href or href in seen_hrefs:
                continue

            # Normalise relative URLs
            if href.startswith("/"):
                href = f"https://opentools.ai{href}"

            # Skip non-article links (e.g. /news itself, /news/feed)
            if href.rstrip("/") == "https://opentools.ai/news":
                continue

            seen_hrefs.add(href)

            # Extract title from the link text or nested heading
            title_el = await el.query_selector("h1, h2, h3, h4, .title, span")
            title = ""
            if title_el:
                title = (await title_el.inner_text()).strip()
            if not title:
                title = (await el.inner_text()).strip()[:150]
            if not title:
                continue

            # Extract snippet if available
            snippet = ""
            parent = await el.evaluate_handle("el => el.closest('article, div, li')")
            if parent:
                snippet_el = await parent.as_element().query_selector(
                    "p, .description, .excerpt, .summary"
                )
                if snippet_el:
                    snippet = (await snippet_el.inner_text()).strip()

            articles.append(
                Article(
                    source=self.SOURCE_NAME,
                    url=href,
                    title=title,
                    raw_content=f"{title}. {snippet}" if snippet else title,
                )
            )

        logger.info("[%s] Parsed %d article links.", self.SOURCE_NAME, len(articles))
        return articles
