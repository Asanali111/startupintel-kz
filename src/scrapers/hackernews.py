"""
HackerNews scraper — uses the free Firebase REST API.

Endpoint docs: https://github.com/HackerNews/API
No authentication required.
"""

from __future__ import annotations

import logging

import aiohttp

from src.scrapers.base import Article, BaseHTTPScraper

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
MAX_STORIES = 15  # cap to avoid overwhelming the digest


class HackerNewsScraper(BaseHTTPScraper):
    """Fetch the current top stories from HackerNews."""

    SOURCE_NAME = "hackernews"

    async def _fetch_articles(self) -> list[Article]:
        logger.info("[%s] Fetching top stories…", self.SOURCE_NAME)
        articles: list[Article] = []

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 1. Get IDs of top stories
            async with session.get(f"{HN_API}/topstories.json") as resp:
                story_ids: list[int] = await resp.json()

            # 2. Fetch details for the first MAX_STORIES
            for sid in story_ids[:MAX_STORIES]:
                try:
                    async with session.get(f"{HN_API}/item/{sid}.json") as resp:
                        item = await resp.json()
                except Exception:
                    continue

                if not item or item.get("type") != "story":
                    continue

                title = item.get("title", "")
                url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                text = item.get("text", "")  # self-posts have text

                if not title:
                    continue

                articles.append(
                    Article(
                        source=self.SOURCE_NAME,
                        url=url,
                        title=title,
                        raw_content=f"{title}. {text}" if text else title,
                    )
                )

        logger.info("[%s] Fetched %d stories.", self.SOURCE_NAME, len(articles))
        return articles
