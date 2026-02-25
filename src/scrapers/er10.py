"""
Scraper for er10.kz — innovation / tech news feed.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scrapers.base import Article, BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class Er10Scraper(BaseScraper):
    SOURCE_NAME = "er10.kz"
    TARGET_URL = "https://er10.kz"

    async def _scrape_page(self, page: Page) -> list[Article]:
        articles: list[Article] = []

        # Wait for the page feed to load
        await page.wait_for_selector(
            "article, .post, .news-card, .item, a[href*='/news/']",
            timeout=15_000,
        )

        # Gather all article-like containers
        containers = await page.query_selector_all(
            "article, .post, .news-card, .item"
        )

        seen_hrefs: set[str] = set()

        for container in containers:
            # Find the primary link inside each container
            link_el = await container.query_selector("a[href]")
            if not link_el:
                continue

            href = await link_el.get_attribute("href")
            if not href or href in seen_hrefs:
                continue

            # Normalise relative URLs
            if href.startswith("/"):
                href = f"https://er10.kz{href}"

            if "er10.kz" not in href:
                continue

            seen_hrefs.add(href)

            # Title
            title_el = await container.query_selector("h1, h2, h3, h4, .title, .headline")
            title = (await title_el.inner_text()).strip() if title_el else ""
            if not title:
                title = (await link_el.inner_text()).strip()[:120]
            if not title:
                continue

            # Snippet / description
            snippet_el = await container.query_selector("p, .excerpt, .desc, .summary")
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

            # Date (best-effort)
            date_el = await container.query_selector("time, .date, .published")
            published = ""
            if date_el:
                published = (
                    await date_el.get_attribute("datetime")
                    or (await date_el.inner_text()).strip()
                )

            articles.append(
                Article(
                    source=self.SOURCE_NAME,
                    url=href,
                    title=title,
                    raw_content=f"{title}. {snippet}",
                    published_at=published,
                )
            )

        logger.info("[%s] Parsed %d article links.", self.SOURCE_NAME, len(articles))
        return articles
