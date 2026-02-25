"""
The Brain — Gemini 1.5 Flash relevance filter.

Batches all new articles into a single LLM call and returns only
those scoring ≥ RELEVANCE_THRESHOLD.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import google.generativeai as genai

from src.config import (
    CONTENT_TRUNCATE_CHARS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    RELEVANCE_THRESHOLD,
)

if TYPE_CHECKING:
    from src.scrapers.base import Article

logger = logging.getLogger(__name__)

# ── System Prompt (verbatim from PLAN.md) ────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert Chief Solutions Architect determining article relevance \
for an 11th-grade NIS student (Physics/Math FMN) in Astana.
Evaluate each article in the batch and score it from 0 to 10 based on relevance.

ACCEPT (Score 7-10): Hard Tech, AI Algorithms, Hardware/Engineering/Robotics, \
Hackathons, Student Grants/Olympiads.
REJECT (Score 0-6): Generic crypto pumps, pure marketing fluff, banking news, \
general lifestyle.

Respond EXCLUSIVELY with a JSON array matching this schema:
[
  {
    "id": "article_id",
    "score": 8,
    "summary": "1-sentence highly concise summary of why this matters for a STEM student."
  }
]
"""


# ── Public API ───────────────────────────────────────────────────────────────

async def filter_articles_batch(
    articles: list[Article],
) -> list[dict]:
    """
    Send a batched payload of newly scraped articles to Gemini 1.5 Flash.

    Returns a list of dicts ``{"id", "score", "summary"}`` for articles
    that scored ≥ ``RELEVANCE_THRESHOLD``.
    """
    if not articles:
        logger.info("No articles to filter — skipping LLM call.")
        return []

    # ── Configure SDK ────────────────────────────────────────────────────
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. Cannot filter articles.")
        return []

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    # ── Build batched prompt ─────────────────────────────────────────────
    batch_text = ""
    for idx, article in enumerate(articles):
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

    # ── Call Gemini (async) ──────────────────────────────────────────────
    logger.info("Sending %d articles to %s for scoring…", len(articles), GEMINI_MODEL)

    try:
        response = await model.generate_content_async(
            contents=prompt_payload,
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        return []

    # ── Parse response ───────────────────────────────────────────────────
    try:
        evaluated: list[dict] = json.loads(response.text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse Gemini JSON response: %s", exc)
        logger.debug("Raw response text: %s", response.text)
        return []

    # ── Filter by threshold ──────────────────────────────────────────────
    approved = [
        item for item in evaluated
        if isinstance(item, dict) and item.get("score", 0) >= RELEVANCE_THRESHOLD
    ]

    logger.info(
        "LLM scored %d articles → %d approved (threshold=%d).",
        len(evaluated),
        len(approved),
        RELEVANCE_THRESHOLD,
    )
    return approved
