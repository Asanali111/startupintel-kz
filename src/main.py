"""
StartupIntel_KZ — main orchestrator.

Pipeline:  Load History → Run Scrapers (gather) → Analyse (LLM) → Notify → Save History
"""

from __future__ import annotations

import asyncio
import logging
import sys

from playwright.async_api import async_playwright

from src.history import load_history, mark_seen, save_history
from src.llm_filter import analyse_articles_batch
from src.scrapers.base import Article
from src.scrapers.digitalbusiness import DigitalBusinessScraper
from src.scrapers.er10 import Er10Scraper
from src.scrapers.hackernews import HackerNewsScraper
from src.scrapers.opentools import OpenToolsScraper
from src.scrapers.rss import RSSFeedScraper
from src.scrapers.telegram import TelegramChannelScraper
from src.telegram_notifier import notify_telegram, send_status_report

# ── Telegram Channels ────────────────────────────────────────────────────────
TELEGRAM_CHANNELS = [
    "the_tech_kz",
    "digitalkazakhstan",
    "astanahub",
    "forbeskazakhstan",
    "therundownai",
    "tldrtech",
]

# ── RSS Feeds ────────────────────────────────────────────────────────────────
RSS_FEEDS = {
    "astanatimes":   "https://astanatimes.com/feed/",
    "producthunt":   "https://www.producthunt.com/feed",
    "openai_blog":   "https://openai.com/blog/rss.xml",
    "hf_blog":       "https://huggingface.co/blog/feed.xml",
}


# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("startupintel")


# ── Pipeline ─────────────────────────────────────────────────────────────────

async def pipeline() -> None:
    """Execute the full scrape → filter → notify pipeline."""

    # 1. Load History ─────────────────────────────────────────────────────
    logger.info("═══ StartupIntel_KZ — pipeline start ═══")
    history = load_history()
    seen_urls: set[str] = set(history.get("scraped_urls", []))
    logger.info("Loaded history: %d previously seen URLs.", len(seen_urls))

    # 2. Run Scrapers (gather) ────────────────────────────────────────────
    # Build scraper instances from the registries
    scrapers = []
    # Telegram channels
    for channel in TELEGRAM_CHANNELS:
        scrapers.append(TelegramChannelScraper(channel, seen_urls))
    # RSS feeds
    for name, url in RSS_FEEDS.items():
        scrapers.append(RSSFeedScraper(name, url, seen_urls))
    # HTML scrapers (Playwright-based)
    scrapers.append(DigitalBusinessScraper(seen_urls))
    scrapers.append(Er10Scraper(seen_urls))
    scrapers.append(OpenToolsScraper(seen_urls))
    # API scrapers (HTTP-based)
    scrapers.append(HackerNewsScraper(seen_urls))

    all_new_articles: list[Article] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            # Run all scrapers concurrently
            results: list[list[Article]] = await asyncio.gather(
                *(scraper.run(browser) for scraper in scrapers),
                return_exceptions=False,
            )
            for batch in results:
                all_new_articles.extend(batch)
        finally:
            await browser.close()

    logger.info("Scrapers returned %d new articles total.", len(all_new_articles))

    # 3. Analyse via LLM ─────────────────────────────────────────────────
    analysed: list[dict] = []
    sent_count = 0

    if all_new_articles:
        analysed = await analyse_articles_batch(all_new_articles)

        # Build a lookup so the notifier can resolve article metadata by ID
        articles_by_id: dict[str, Article] = {a.id: a for a in all_new_articles}

        # 4. Notify via Telegram ─────────────────────────────────────────
        sent_count = await notify_telegram(analysed, articles_by_id)
        logger.info("Telegram: %d messages delivered.", sent_count)

    # 5. Always send a status report ─────────────────────────────────────
    await send_status_report(
        total_scraped=len(all_new_articles),
        total_analysed=len(analysed),
        total_sent=sent_count,
    )

    # 6. Save History (mark ALL scraped URLs, not just approved ones) ────
    if all_new_articles:
        new_urls = [a.url for a in all_new_articles]
        mark_seen(new_urls, history)
    save_history(history)

    logger.info(
        "═══ Pipeline complete — %d scraped, %d analysed, %d sent ═══",
        len(all_new_articles),
        len(analysed),
        sent_count,
    )


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Sync wrapper for the async pipeline (convenience for CLI / GH Actions)."""
    asyncio.run(pipeline())


if __name__ == "__main__":
    main()
