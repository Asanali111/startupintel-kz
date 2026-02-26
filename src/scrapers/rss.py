"""
RSS / Atom feed scraper — lightweight, no browser needed.

Uses ``feedparser`` + ``aiohttp`` to pull and parse standard feeds.
"""

from __future__ import annotations

import logging

import aiohttp
import feedparser

from src.scrapers.base import Article, BaseHTTPScraper

logger = logging.getLogger(__name__)


class RSSFeedScraper(BaseHTTPScraper):
    """
    Fetch and parse an RSS or Atom feed.

    Usage::

        scraper = RSSFeedScraper(
            source_name="astanatimes",
            feed_url="https://astanatimes.com/feed/",
            seen_urls=seen_urls,
        )
    """

    def __init__(
        self, source_name: str, feed_url: str, seen_urls: set[str]
    ) -> None:
        super().__init__(seen_urls)
        self.SOURCE_NAME = source_name
        self._feed_url = feed_url

    async def _fetch_articles(self) -> list[Article]:
        logger.info("[%s] Fetching RSS feed: %s", self.SOURCE_NAME, self._feed_url)

        async with aiohttp.ClientSession() as session:
            async with session.get(self._feed_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                raw = await resp.text()

        feed = feedparser.parse(raw)
        articles: list[Article] = []

        for entry in feed.entries:
            link = entry.get("link", "")
            title = entry.get("title", "").strip()
            if not link or not title:
                continue

            # Build body from summary / content
            summary = entry.get("summary", "")
            content_blocks = entry.get("content", [])
            body = ""
            if content_blocks:
                body = content_blocks[0].get("value", "")
            if not body:
                body = summary

            # Strip HTML tags (rough but sufficient for LLM input)
            import re
            body = re.sub(r"<[^>]+>", " ", body).strip()

            published = entry.get("published", entry.get("updated", ""))

            articles.append(
                Article(
                    source=self.SOURCE_NAME,
                    url=link,
                    title=title,
                    raw_content=f"{title}. {body}" if body else title,
                    published_at=published,
                )
            )

        logger.info("[%s] Parsed %d RSS entries.", self.SOURCE_NAME, len(articles))
        return articles
