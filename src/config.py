"""
Central configuration — reads environment variables and defines constants.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"

# ── API Keys (injected via .env or GitHub Secrets) ───────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Scraper Targets (documentation; actual registration is in main.py) ───────
TARGETS = {
    # Telegram channels
    "the_tech_kz":        "https://t.me/s/the_tech_kz",
    "digitalkazakhstan":  "https://t.me/s/digitalkazakhstan",
    "astanahub":          "https://t.me/s/astanahub",
    "forbeskazakhstan":   "https://t.me/s/forbeskazakhstan",
    "therundownai":       "https://t.me/s/therundownai",
    "tldrtech":           "https://t.me/s/tldrtech",
    # HTML scrapers
    "digitalbusiness":    "https://digitalbusiness.kz",
    "er10":               "https://er10.kz",
    "opentools":          "https://opentools.ai/news",
    # RSS feeds
    "astanatimes":        "https://astanatimes.com/feed/",
    "producthunt":        "https://www.producthunt.com/feed",
    "openai_blog":        "https://openai.com/blog/rss.xml",
    "hf_blog":            "https://huggingface.co/blog/feed.xml",
    # Free APIs
    "hackernews":         "https://hacker-news.firebaseio.com/v0",
}

# ── LLM Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash-latest"
CONTENT_TRUNCATE_CHARS = 800       # Max chars per article sent to LLM


# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_SEND_DELAY = 1.0          # Seconds between messages (rate-limit)
