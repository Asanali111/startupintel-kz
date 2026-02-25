"""
Scraper for digitalbusiness.kz — main news feed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scrapers.base import Article, BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class DigitalBusinessScraper(BaseScraper):
    SOURCE_NAME = "digitalbusiness.kz"
    TARGET_URL = "https://digitalbusiness.kz"

    async def _scrape_page(self, page: Page) -> list[Article]:
        articles: list[Article] = []

        # Wait for feed items to render
        await page.wait_for_selector("article, .post-item, .news-item", timeout=15_000)

        # Strategy: grab all visible article link blocks from the main feed.
        # Typical pattern:  <a href="/slug"> ... <h2>Title</h2> ... <p>snippet</p> ... </a>
        # We try several common selectors and merge results.
        link_elements = await page.query_selector_all(
            "article a[href], .post-item a[href], .news-item a[href]"
        )

        seen_hrefs: set[str] = set()

        for el in link_elements:
            href = await el.get_attribute("href")
            if not href or href in seen_hrefs:
                continue

            # Normalise relative URLs
            if href.startswith("/"):
                href = f"https://digitalbusiness.kz{href}"

            # Skip external links / non-article hrefs
            if "digitalbusiness.kz" not in href:
                continue

            seen_hrefs.add(href)

            # Extract title: prefer nested heading, fall back to link text
            title_el = await el.query_selector("h1, h2, h3, h4, .title")
            title = (await title_el.inner_text()).strip() if title_el else ""
            if not title:
                title = (await el.inner_text()).strip()[:120]
            if not title:
                continue

            # Extract snippet / body preview
            snippet_el = await el.query_selector("p, .excerpt, .description")
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

            articles.append(
                Article(
                    source=self.SOURCE_NAME,
                    url=href,
                    title=title,
                    raw_content=f"{title}. {snippet}",
                )
            )

        logger.info("[%s] Parsed %d article links.", self.SOURCE_NAME, len(articles))
        return articles
