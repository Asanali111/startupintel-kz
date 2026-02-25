# How StartupIntel_KZ Works

## Is It Free?

**Yes, 100% free.** Here's why:

| Component | Service | Cost |
|-----------|---------|------|
| **Server** | GitHub Actions | Free (2,000 min/month for public repos) |
| **AI Brain** | Gemini 1.5 Flash | Free tier (15 requests/min, 1M tokens/day) |
| **Notifications** | Telegram Bot API | Free forever |
| **Database** | `history.json` in the repo | Free (it's just a file) |
| **Browser** | Playwright on GitHub's servers | Free (part of Actions) |

Your pipeline runs ~1 min 20s per day = **~40 minutes/month** out of the 2,000 free minutes.

---

## Where Does It Search?

The bot scrapes **3 Kazakhstan tech news sources** every morning:

### 1. digitalbusiness.kz
- 🇰🇿 Government digital economy & IT portal
- Topics: tech policy, digitalization, IT industry news
- What it grabs: article titles, links, and text snippets from the main feed

### 2. er10.kz
- 🇰🇿 Business & innovation news outlet
- Topics: startups, investments, entrepreneurship, tech initiatives
- What it grabs: article containers with titles, descriptions, and dates

### 3. t.me/s/the_tech_kz (Telegram Channel)
- 🇰🇿 Popular Kazakh tech Telegram channel
- Topics: AI, hardware, hackathons, grants, startup ecosystem
- What it grabs: message text from the public web view (no Telegram API needed)

---

## How It Works (Step by Step)

```
Every day at 09:00 Astana time, GitHub wakes up and runs this pipeline:
```

### Step 1: Load Memory
The bot reads `data/history.json` — a list of every article URL it has already seen. This prevents you from getting the same news twice.

### Step 2: Scrape (The Eyes)
A headless Chromium browser (Playwright) opens all 3 websites simultaneously and extracts:
- **Title** of each article/post
- **URL** (the link)
- **Text content** (body/snippet)

Any URL already in `history.json` is immediately discarded.

### Step 3: AI Filter (The Brain)
All new articles are batched into **one single request** to Google Gemini 1.5 Flash. The AI reads every article and scores it from **0 to 10** based on this logic:

| Score | Meaning | Example |
|-------|---------|---------|
| **8–10** | Highly relevant | "NIS students win robotics olympiad", "New AI grant for Kazakh youth" |
| **7** | Relevant | "Astana Hub launches hardware accelerator" |
| **4–6** | Meh | "Kaspi launches new banking feature" |
| **0–3** | Irrelevant | "Crypto pump alert", "Celebrity marketing deal" |

**Only articles scoring 7 or above pass through.**

The AI is specifically tuned for a **Physics/Math NIS student** — it prioritizes:
- ✅ Deep Tech, AI algorithms, robotics, hardware engineering
- ✅ Hackathons, student grants, olympiads
- ❌ Crypto spam, marketing fluff, banking news

### Step 4: Notify (The Mouth)
Approved articles are sent to your Telegram as messages formatted like:

```
[8] NIS Students Win National Robotics Olympiad
Teams from Astana and Almaty competed in autonomous drone challenges.
https://digitalbusiness.kz/article/...
```

### Step 5: Save Memory
All scraped URLs (even rejected ones) are saved to `history.json` and committed back to the repo. Tomorrow's run will skip them.

---

## Architecture Diagram

```
  ┌─────────────────────────────────────────────────────┐
  │              GitHub Actions (09:00 daily)            │
  │                                                     │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
  │  │ digital  │  │  er10.kz │  │  t.me/s/         │  │
  │  │business  │  │          │  │  the_tech_kz     │  │
  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
  │       │              │                 │            │
  │       └──────────────┼─────────────────┘            │
  │                      ▼                              │
  │           ┌─────────────────────┐                   │
  │           │   New Articles?     │                   │
  │           │  (check history)    │                   │
  │           └─────────┬───────────┘                   │
  │                     ▼                               │
  │           ┌─────────────────────┐                   │
  │           │   Gemini 1.5 Flash  │                   │
  │           │   Score 0-10        │                   │
  │           └─────────┬───────────┘                   │
  │                     ▼                               │
  │           ┌─────────────────────┐                   │
  │           │   Score ≥ 7?        │──── No ──→ Skip   │
  │           └─────────┬───────────┘                   │
  │                Yes  ▼                               │
  │           ┌─────────────────────┐                   │
  │           │   Telegram Bot      │ ──→ 📱 Your Phone │
  │           └─────────────────────┘                   │
  │                     ▼                               │
  │           ┌─────────────────────┐                   │
  │           │   Save history.json │                   │
  │           └─────────────────────┘                   │
  └─────────────────────────────────────────────────────┘
```

---

## File Map

| File | Role |
|------|------|
| `src/main.py` | Orchestrator — runs the whole pipeline |
| `src/config.py` | Reads API keys and defines constants |
| `src/history.py` | Loads/saves the duplicate-prevention database |
| `src/llm_filter.py` | Sends articles to Gemini, filters by score |
| `src/telegram_notifier.py` | Sends approved articles to your Telegram |
| `src/scrapers/base.py` | Shared Article format + base scraper class |
| `src/scrapers/digitalbusiness.py` | Scrapes digitalbusiness.kz |
| `src/scrapers/er10.py` | Scrapes er10.kz |
| `src/scrapers/the_tech_kz.py` | Scrapes Telegram channel web view |
| `data/history.json` | Memory — list of already-seen URLs |
| `.github/workflows/daily_scraper.yml` | Cron job that triggers everything |
