"""
Generic Telegram channel scraper — works for any public channel.

Uses the ``/s/<channel>`` web-preview endpoint so no API credentials
are needed.

Key selectors (Telegram widget DOM):
  • Message bubble:  ``.tgme_widget_message``
  • Post text:       ``.tgme_widget_message_text``
  • Post link attr:  ``data-post``  → value like ``channel_name/1234``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scrapers.base import Article, BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

TELEGRAM_BASE = "https://t.me"


class TelegramChannelScraper(BaseScraper):
    """
    Scrape the latest posts from any public Telegram channel.

    Usage::

        scraper = TelegramChannelScraper("the_tech_kz", seen_urls)
    """

    def __init__(self, channel: str, seen_urls: set[str]) -> None:
        super().__init__(seen_urls)
        self._channel = channel
        self.SOURCE_NAME = f"tg/{channel}"
        self.TARGET_URL = f"{TELEGRAM_BASE}/s/{channel}"

    async def _scrape_page(self, page: Page) -> list[Article]:
        articles: list[Article] = []

        # Wait for Telegram widget messages to render
        await page.wait_for_selector(".tgme_widget_message", timeout=20_000)

        messages = await page.query_selector_all(".tgme_widget_message")

        for msg in messages:
            # ── Extract post identifier ──────────────────────────────────
            data_post = await msg.get_attribute("data-post")
            if not data_post:
                continue

            post_url = f"{TELEGRAM_BASE}/{data_post}"

            # ── Extract message text ─────────────────────────────────────
            text_el = await msg.query_selector(".tgme_widget_message_text")
            if not text_el:
                continue

            full_text = (await text_el.inner_text()).strip()
            if not full_text:
                continue

            # Use the first line (or first 120 chars) as the title
            first_line = full_text.split("\n")[0].strip()
            title = first_line[:120] if first_line else full_text[:120]

            # ── Date (best-effort) ───────────────────────────────────────
            date_el = await msg.query_selector(
                "time.datetime, .tgme_widget_message_date time"
            )
            published = ""
            if date_el:
                published = (
                    await date_el.get_attribute("datetime")
                    or (await date_el.inner_text()).strip()
                )

            articles.append(
                Article(
                    source=self.SOURCE_NAME,
                    url=post_url,
                    title=title,
                    raw_content=full_text,
                    published_at=published,
                )
            )

        logger.info("[%s] Parsed %d messages.", self.SOURCE_NAME, len(articles))
        return articles
