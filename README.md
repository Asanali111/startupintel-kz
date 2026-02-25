# StartupIntel_KZ

A serverless, zero-cost intelligence agent that tracks the Kazakhstan startup & tech ecosystem.

## Architecture

- **Input**: Playwright headless scrapers for `digitalbusiness.kz`, `er10.kz`, and `t.me/s/the_tech_kz`
- **Filter**: Gemini 1.5 Flash scores articles (0-10) for relevance to a Physics/Math student
- **Output**: Telegram Bot delivers curated digest

## Setup

1. Copy `.env.example` → `.env` and fill in your keys.
2. `pip install -r requirements.txt && playwright install chromium`
3. `python src/main.py`

## Infrastructure

Runs daily at 09:00 Astana time via GitHub Actions. State is persisted in `data/history.json`.
