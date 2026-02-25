"""
Scraper for t.me/s/the_tech_kz — Telegram public web-view DOM.

The ``/s/`` path exposes messages as static HTML widgets, avoiding
the need for Telegram API credentials.

Key selectors (Telegram widget DOM):
  • Message bubble:  ``.tgme_widget_message``
  • Post text:       ``.tgme_widget_message_text``
  • Post link attr:  ``data-post``  → value like ``the_tech_kz/1234``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.scrapers.base import Article, BaseScraper

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

TELEGRAM_BASE = "https://t.me"


class TheTechKZScraper(BaseScraper):
    SOURCE_NAME = "the_tech_kz"
    TARGET_URL = "https://t.me/s/the_tech_kz"

    async def _scrape_page(self, page: Page) -> list[Article]:
        articles: list[Article] = []

        # Wait for Telegram widget messages to render
        await page.wait_for_selector(".tgme_widget_message", timeout=20_000)

        # Grab all message bubbles
        messages = await page.query_selector_all(".tgme_widget_message")

        for msg in messages:
            # ── Extract post identifier ──────────────────────────────────
            data_post = await msg.get_attribute("data-post")
            if not data_post:
                continue

            # Build canonical URL  →  https://t.me/the_tech_kz/1234
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
            date_el = await msg.query_selector("time.datetime, .tgme_widget_message_date time")
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
