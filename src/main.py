"""
StartupIntel_KZ — main orchestrator.

Pipeline:  Load History → Run Scrapers (gather) → Filter (LLM) → Notify → Save History
"""

from __future__ import annotations

import asyncio
import logging
import sys

from playwright.async_api import async_playwright

from src.history import load_history, mark_seen, save_history
from src.llm_filter import filter_articles_batch
from src.scrapers.base import Article
from src.scrapers.digitalbusiness import DigitalBusinessScraper
from src.scrapers.er10 import Er10Scraper
from src.scrapers.the_tech_kz import TheTechKZScraper
from src.telegram_notifier import notify_telegram

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
    scrapers = [
        DigitalBusinessScraper(seen_urls),
        Er10Scraper(seen_urls),
        TheTechKZScraper(seen_urls),
    ]

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

    if not all_new_articles:
        logger.info("Nothing new — exiting early.")
        save_history(history)
        return

    # 3. Filter via LLM ──────────────────────────────────────────────────
    approved = await filter_articles_batch(all_new_articles)

    # Build a lookup so the notifier can resolve article metadata by ID
    articles_by_id: dict[str, Article] = {a.id: a for a in all_new_articles}

    # 4. Notify via Telegram ─────────────────────────────────────────────
    sent_count = await notify_telegram(approved, articles_by_id)
    logger.info("Telegram: %d messages delivered.", sent_count)

    # 5. Save History (mark ALL scraped URLs, not just approved ones) ────
    new_urls = [a.url for a in all_new_articles]
    mark_seen(new_urls, history)
    save_history(history)

    logger.info(
        "═══ Pipeline complete — %d scraped, %d approved, %d sent ═══",
        len(all_new_articles),
        len(approved),
        sent_count,
    )


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Sync wrapper for the async pipeline (convenience for CLI / GH Actions)."""
    asyncio.run(pipeline())


if __name__ == "__main__":
    main()
