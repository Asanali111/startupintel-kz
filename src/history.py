"""
Stateful memory — load / save the duplicate-prevention database.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.config import HISTORY_FILE, DATA_DIR

logger = logging.getLogger(__name__)

# Astana timezone (UTC+5)
TZ_ASTANA = timezone(timedelta(hours=5))


def _ensure_data_dir() -> None:
    """Create `data/` directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_history() -> dict:
    """
    Load ``history.json`` and return parsed dict.
    Returns a fresh skeleton if the file is missing or corrupted.
    """
    _ensure_data_dir()
    if not HISTORY_FILE.exists():
        logger.info("history.json not found — starting fresh.")
        return {"scraped_urls": [], "last_run": None}

    try:
        raw = HISTORY_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        # Guarantee required keys exist
        data.setdefault("scraped_urls", [])
        data.setdefault("last_run", None)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupted history.json, resetting. Error: %s", exc)
        return {"scraped_urls": [], "last_run": None}


def save_history(history: dict) -> None:
    """
    Persist *history* back to ``data/history.json``.
    Updates ``last_run`` timestamp automatically.
    """
    _ensure_data_dir()
    history["last_run"] = datetime.now(TZ_ASTANA).isoformat()
    HISTORY_FILE.write_text(
        json.dumps(history, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("history.json saved (%d URLs tracked).", len(history["scraped_urls"]))


def is_seen(url: str, history: dict) -> bool:
    """Return True if *url* was already processed."""
    return url in history["scraped_urls"]


def mark_seen(urls: list[str], history: dict) -> None:
    """Add a batch of *urls* to the seen-set (de-duplicated)."""
    existing = set(history["scraped_urls"])
    existing.update(urls)
    history["scraped_urls"] = sorted(existing)
