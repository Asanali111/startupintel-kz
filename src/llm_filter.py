"""
The Brain — Gemini 1.5 Flash article analyser.

Processes articles in small batches (to stay within the context window)
and returns an LLM-generated summary for every article.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import google.generativeai as genai

from src.config import (
    CONTENT_TRUNCATE_CHARS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)

if TYPE_CHECKING:
    from src.scrapers.base import Article

logger = logging.getLogger(__name__)

# ── Tuning ───────────────────────────────────────────────────────────────────
BATCH_SIZE = 25          # articles per LLM call
DELAY_BETWEEN_BATCHES = 2  # seconds — avoid rate-limiting

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert startup ecosystem analyst summarising articles \
for an 11th-grade NIS student (Physics/Math FMN) in Kazakhstan who is \
passionate about ENTREPRENEURSHIP and building startups.
Analyse each article in the batch and provide a concise summary.

For every article, write a clear 1-sentence summary explaining why it \
might matter to a student entrepreneur in Kazakhstan.

Respond EXCLUSIVELY with a JSON array matching this schema:
[
  {
    "id": "article_id",
    "summary": "1-sentence summary of why this matters for a student entrepreneur."
  }
]
"""


# ── Internal ─────────────────────────────────────────────────────────────────

async def _analyse_single_batch(
    model: genai.GenerativeModel,
    batch: list[Article],
    batch_num: int,
) -> list[dict]:
    """Send one batch of articles to Gemini and return parsed results."""
    batch_text = ""
    for idx, article in enumerate(batch):
        snippet = article.raw_content[:CONTENT_TRUNCATE_CHARS]
        batch_text += (
            f"\n--- Article {idx} ---\n"
            f"ID: {article.id}\n"
            f"Title: {article.title}\n"
            f"Content:\n{snippet}\n"
        )

    prompt_payload = (
        f"{SYSTEM_PROMPT}\n\nHere are the articles to evaluate:\n{batch_text}"
    )

    try:
        response = await model.generate_content_async(
            contents=prompt_payload,
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:
        logger.error("Batch %d — Gemini API call failed: %s", batch_num, exc)
        return []

    try:
        evaluated: list[dict] = json.loads(response.text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Batch %d — Failed to parse Gemini JSON: %s", batch_num, exc)
        logger.debug("Raw response text: %s", response.text)
        return []

    logger.info("Batch %d — analysed %d articles.", batch_num, len(evaluated))
    return evaluated


# ── Public API ───────────────────────────────────────────────────────────────

async def analyse_articles_batch(
    articles: list[Article],
) -> list[dict]:
    """
    Process articles in batches of ``BATCH_SIZE`` to stay within Gemini's
    context window.  Returns a combined list of ``{"id", "summary"}`` dicts.
    """
    if not articles:
        logger.info("No articles to analyse — skipping LLM call.")
        return []

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Cannot analyse articles.")
        return []

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    # Split into batches
    batches = [
        articles[i : i + BATCH_SIZE]
        for i in range(0, len(articles), BATCH_SIZE)
    ]
    logger.info(
        "Processing %d articles in %d batch(es) of up to %d…",
        len(articles), len(batches), BATCH_SIZE,
    )

    all_results: list[dict] = []

    for batch_num, batch in enumerate(batches, start=1):
        results = await _analyse_single_batch(model, batch, batch_num)
        all_results.extend(results)
        # Rate-limit between batches (skip delay after last batch)
        if batch_num < len(batches):
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    logger.info(
        "LLM analysis complete — %d/%d articles summarised.",
        len(all_results), len(articles),
    )
    return all_results
