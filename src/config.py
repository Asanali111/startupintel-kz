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

# ── Scraper Targets ─────────────────────────────────────────────────────────
TARGETS = {
    "digitalbusiness": "https://digitalbusiness.kz",
    "er10": "https://er10.kz",
    "the_tech_kz": "https://t.me/s/the_tech_kz",
}

# ── LLM Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash-latest"
CONTENT_TRUNCATE_CHARS = 800       # Max chars per article sent to LLM
RELEVANCE_THRESHOLD = 7            # Minimum score to pass filter

# ── Telegram ────────────────────────────────────────────────────────────────
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_SEND_DELAY = 1.0          # Seconds between messages (rate-limit)
