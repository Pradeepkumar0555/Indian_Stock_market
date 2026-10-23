# Indian Stock Market — Daily Morning Digest Bot

Automated pipeline that fetches fresh financial news from Indian & global RSS feeds, filters out stale articles, and delivers a clean morning brief to Telegram.

## Features

- **Strict 24h Freshness Filter** — Articles older than the configured window are discarded at the Python level using UTC-safe timestamp comparison.
- **AI System Prompt** — Ready-to-use institutional-grade prompt for Gemini/Groq/OpenAI summarization (see `prompts.py`).
- **Deduplication** — Normalised title matching prevents repeated headlines.
- **Telegram MarkdownV2** — Properly escaped rich formatting with clickable links.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# 3. Run
python main.py
```

## File Structure

| File | Purpose |
|---|---|
| `main.py` | RSS fetching, freshness filtering, Telegram delivery |
| `prompts.py` | AI system prompt for LLM-based summarization |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
