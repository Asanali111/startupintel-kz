"""
The Mouth — Telegram Bot notification sender.

Formats approved articles and pushes them to the configured chat
via the Telegram Bot API (plain ``aiohttp`` requests, no SDK).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp

from src.config import TELEGRAM_API_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_SEND_DELAY

if TYPE_CHECKING:
    from src.scrapers.base import Article

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_message(article: Article, summary: str) -> str:
    """
    Build the Telegram message string.

    Format:  Title
             Summary
             URL
    """
    return (
        f"{article.title}\n"
        f"{summary}\n"
        f"{article.url}"
    )


# ── Public API ───────────────────────────────────────────────────────────────

async def notify_telegram(
    approved: list[dict],
    articles_by_id: dict[str, Article],
) -> int:
    """
    Send one Telegram message per approved article.

    Parameters
    ----------
    approved
        List of dicts from the LLM filter: ``{"id", "score", "summary"}``.
    articles_by_id
        Lookup table ``{article.id: Article}`` so we can attach URLs/titles.

    Returns
    -------
    int
        Number of messages successfully sent.
    """
    if not approved:
        logger.info("Nothing to send — approved list is empty.")
        return 0

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set.")
        return 0

    send_url = f"{TELEGRAM_API_URL}/sendMessage"
    sent = 0

    async with aiohttp.ClientSession() as session:
        for item in approved:
            article_id: str = item.get("id", "")
            article = articles_by_id.get(article_id)

            if article is None:
                logger.warning("No article found for id=%s — skipping.", article_id)
                continue

            text = _format_message(
                article,
                summary=item.get("summary", ""),
            )

            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": False,
            }

            try:
                async with session.post(send_url, json=payload) as resp:
                    if resp.status == 200:
                        sent += 1
                        logger.info("Sent message for [%s] %s", article.source, article.title)
                    else:
                        body = await resp.text()
                        logger.error(
                            "Telegram API error %d: %s", resp.status, body
                        )
            except aiohttp.ClientError as exc:
                logger.error("Network error sending to Telegram: %s", exc)

            # Rate-limit: wait between messages to avoid Telegram throttling
            await asyncio.sleep(TELEGRAM_SEND_DELAY)

    logger.info("Telegram delivery complete: %d/%d sent.", sent, len(approved))
    return sent


async def send_status_report(
    total_scraped: int,
    total_analysed: int,
    total_sent: int,
) -> None:
    """
    Always send a summary message so the user knows the bot ran,
    even if zero articles were found.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set.")
        return

    if total_scraped == 0:
        status = "😴 No new articles found today."
    else:
        status = (
            f"✅ Scanned {total_scraped} article(s), "
            f"analysed {total_analysed}, sent {total_sent} to Telegram."
        )

    text = f"📊 StartupIntel_KZ — Daily Report\n\n{status}"

    send_url = f"{TELEGRAM_API_URL}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(send_url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
            }) as resp:
                if resp.status == 200:
                    logger.info("Status report sent to Telegram.")
                else:
                    body = await resp.text()
                    logger.error("Telegram status report error %d: %s", resp.status, body)
        except aiohttp.ClientError as exc:
            logger.error("Network error sending status report: %s", exc)

