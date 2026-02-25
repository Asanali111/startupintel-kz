# Implementation Plan: StartupIntel_KZ

> [!NOTE]
> This architectural plan outlines a serverless, zero-cost intelligence agent designed to track the Kazakhstan tech/startup ecosystem. The pipeline collects data with Playwright, curates relevance with Gemini Flash, delivers digests via Telegram, and maintains state via Git commits.

## 1. Directory Structure

```text
StartupIntel_KZ/
├── .github/
│   └── workflows/
│       └── daily_scraper.yml       # GitHub Actions cron job
├── data/
│   └── history.json                # State DB to prevent duplicates
├── src/
│   ├── __init__.py
│   ├── main.py                     # Entry point (async pipeline)
│   ├── config.py                   # Env vars & constants
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base.py                 # Scraper interface/base class
│   │   ├── digitalbusiness.py      # Target 1 scraper
│   │   ├── er10.py                 # Target 2 scraper
│   │   └── the_tech_kz.py          # Target 3 scraper (t.me/s/...)
│   ├── llm_filter.py               # Gemini LLM logic + systemic prompt
│   └── telegram_notifier.py        # Telegram Bot API client
├── requirements.txt            
├── .env.example
├── .gitignore
└── README.md
```

## 2. Data Schemas

### Database Schema (`data/history.json`)
A simple document to represent previously seen or processed articles to prevent duplicate notifications.
```json
{
  "scraped_urls": [
    "https://digitalbusiness.kz/2023-10-15/...",
    "https://er10.kz/article/...",
    "https://t.me/s/the_tech_kz/1204"
  ],
  "last_run": "2024-03-01T09:00:00+05:00"
}
```

### Internal Data Object (`Article`)
Use a `dataclass` or `Pydantic` model to enforce types across the pipeline.
```python
from dataclasses import dataclass

@dataclass
class Article:
    id: str             # Unique identifier (e.g., URL hash or specific source ID)
    source: str         # Origin (e.g., 'digitalbusiness.kz')
    url: str            # Unique article/post link
    title: str          # Article title or Telegram header
    raw_content: str    # Raw text to be evaluated by Gemini
    published_at: str   # ISO format or relative
```

## 3. Pseudo-Code for the "Smart Filter" Layer
To minimize API calls, we batch articles into a single prompt for Gemini 1.5 Flash using Structured Outputs (`JSON` mode).

```python
import google.generativeai as genai
import json

# The Brain Layer Prompt
SYSTEM_PROMPT = """
You are an expert Chief Solutions Architect determining article relevance for an 11th-grade NIS student (Physics/Math FMN) in Astana. 
Evaluate each article in the batch and score it from 0 to 10 based on relevance.

ACCEPT (Score 7-10): Hard Tech, AI Algorithms, Hardware/Engineering/Robotics, Hackathons, Student Grants/Olympiads.
REJECT (Score 0-6): Generic crypto pumps, pure marketing fluff, banking news, general lifestyle.

Respond EXCLUSIVELY with a JSON array matching this schema:
[
  {
    "id": "article_id",
    "score": 8,
    "summary": "1-sentence highly concise summary of why this matters for a STEM student."
  }
]
"""

async def filter_articles_batch(articles: list[Article]) -> list[dict]:
    """Sends a batched payload of newly scraped articles to Gemini."""
    if not articles:
        return []

    # Construct the batched prompt payload
    batch_text = ""
    for idx, article in enumerate(articles):
        # Truncate content to save tokens
        content_snippet = article.raw_content[:800]
        batch_text += f"\n--- Article {idx} ---\nID: {article.id}\nTitle: {article.title}\nContent:\n{content_snippet}\n"
    
    # Initialize Gemini 1.5 Flash (Async)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt_payload = f"{SYSTEM_PROMPT}\n\nHere are the articles to evaluate:\n{batch_text}"
    
    # Generate structured JSON output
    response = await model.generate_content_async(
        contents=prompt_payload,
        generation_config={"response_mime_type": "application/json"}
    )
    
    # Parse the LLM's JSON decision
    evaluated_batch = json.loads(response.text)
    
    # Filter only actionable, high-quality news
    approved_articles = [item for item in evaluated_batch if item.get("score", 0) >= 7]
    return approved_articles
```

## 4. Step-by-Step Implementation Guide (Opus Handoff)

- [ ] **Step 1: Project Initialization**
  - Create the exact directory tree mapping defined above.
  - Create `requirements.txt` containing: `playwright`, `google-generativeai`, `aiohttp`, `pydantic`.

- [ ] **Step 2: Stateful Memory (`history.json`)**
  - Implement read/write functions for `data/history.json`.
  - Ensure missing files/directories are handled gracefully.

- [ ] **Step 3: Playwright Scrapers (Input Layer)**
  - Implement async Playwright in headless mode in `scrapers/base.py`.
  - **DigitalBusiness**: Target main feed container -> extract `<a>` elements for titles and hrefs -> fetch text.
  - **Er10**: Target innovation feed -> extract titles/links/snippets.
  - **The Tech KZ**: Target `https://t.me/s/the_tech_kz` -> Extract `.tgme_widget_message_text` and `data-post` identifiers for links. 
  - *Crucial Check*: Immediately discard any URL already present in `history.json` before sending to the LLM.

- [ ] **Step 4: LLM Brain Verification (Filter Layer)**
  - Implement the batching pseudo-code in `llm_filter.py`.
  - Read `GEMINI_API_KEY` from environment variables.
  - Integrate approvals with the original `Article` dataclass URLs/Titles.

- [ ] **Step 5: Telegram Notification (Output Layer)**
  - Implement `telegram_notifier.py` using simple `aiohttp` requests to `https://api.telegram.org/bot{TOKEN}/sendMessage`.
  - Loop over approved articles and format strings exactly as: `[{score}] {title}\n{summary}\n{url}`
  - Handle rate limiting if multiple messages are sent per session by adding `asyncio.sleep(1)` buffers.

- [ ] **Step 6: Orchestration (`main.py`)**
  - Define `async def main():`
  - Await Scraping `results = await asyncio.gather(*scrapers)`.
  - Await Filtering `approved = await filter_articles_batch(results)`.
  - Await Notifying `await notify_telegram(approved)`.
  - Save new URLs sequentially to `history.json`.

- [ ] **Step 7: GitHub Actions Automation (Infrastructure)**
  - Generate the `.github/workflows/daily_scraper.yml` file.
  - Ensure the trigger is `schedule: - cron: "0 4 * * *"` (Exactly 09:00 AM Astana time, UTC+5).
  - Define build steps: Checkout repo -> Setup Python 3.12 -> Install dependencies -> `playwright install chromium` -> Run `python src/main.py`.
  - Provide environment variables injected via GitHub Secrets: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
  - **Final Step**: Commit the updated `history.json` back to the GitHub tree using `stefanzweifel/git-auto-commit-action@v5`.

> [!IMPORTANT]
> This plan guarantees strict cost controls ($0/month) while using the latest reliable Async Python 3.12 syntax. Ensure the prompt logic restricts token lengths by truncating article content to `<1000` chars before batching.
