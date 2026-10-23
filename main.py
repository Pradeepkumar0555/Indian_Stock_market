"""
Daily Market Morning Digest — Fresh News Pipeline
===================================================
Fetches RSS headlines → filters by freshness (24h) → deduplicates
→ sends actionable digest via Telegram.

Environment Variables Required:
    TELEGRAM_BOT_TOKEN  — Telegram Bot API token
    TELEGRAM_CHAT_ID    — Target chat/channel ID
"""

import os
import time
import calendar
from datetime import datetime, timezone

import requests
import feedparser
from dotenv import load_dotenv

from prompts import AI_SYSTEM_PROMPT  # noqa: F401  (available for LLM integration)

# ── Load .env file ──
load_dotenv()

# ─────────────────────────── Configuration ───────────────────────────


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FEEDS = [
    # ── Indian Markets & Economy ──
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://www.moneycontrol.com/rss/economy.xml",
    # ── Global Macro, Commodities & Forex ──
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords=markets&sort=date",
]

# ─────────────────────────── Core Logic ──────────────────────────────


def _entry_timestamp(entry) -> float | None:
    """
    Extract a UTC timestamp from an RSS entry.

    Uses `published_parsed` or `updated_parsed` (struct_time in UTC via
    feedparser) and converts with `calendar.timegm` (UTC-safe) instead of
    `time.mktime` (local-tz dependent) to avoid timezone drift.
    """
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return calendar.timegm(parsed)  # UTC struct_time → UTC epoch
    return None


def fetch_fresh_news(limit: int = 12, max_age_hours: int = 24) -> list[tuple[str, str]]:
    """
    Aggregate headlines from all RSS feeds with strict freshness filtering.

    Parameters
    ----------
    limit : int
        Maximum number of headlines to return.
    max_age_hours : int
        Articles older than this many hours are discarded.

    Returns
    -------
    list[tuple[str, str]]
        List of (title, link) tuples for fresh articles.
    """
    news_items: list[tuple[str, str]] = []
    seen_titles: set[str] = set()

    now_utc = time.time()
    cutoff = now_utc - (max_age_hours * 3600)

    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            print(f"[WARN] Feed parse error ({url}): {exc}")
            continue

        for entry in feed.entries:
            # ── 1. Freshness gate: drop anything older than cutoff ──
            entry_ts = _entry_timestamp(entry)
            if entry_ts is not None and entry_ts < cutoff:
                continue  # Purana article — skip

            # ── 2. Deduplicate by normalised title ──
            raw_title = entry.get("title", "").strip()
            normalised = " ".join(raw_title.split()).lower()
            if not normalised or normalised in seen_titles:
                continue
            seen_titles.add(normalised)

            link = entry.get("link", "")
            news_items.append((raw_title, link))

            if len(news_items) >= limit:
                break

        if len(news_items) >= limit:
            break

    return news_items[:limit]


# ──────────────────────── Telegram Delivery ──────────────────────────


def _escape_markdownv2(text: str) -> str:
    """Escape special characters required by Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


def send_telegram_alert(items: list[tuple[str, str]]) -> None:
    """
    Format and send the digest to Telegram via the Bot API.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("[ERROR] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return

    if not items:
        print("[INFO] No fresh news found in the configured time window.")
        return

    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    # ── Build message ──
    lines = [
        f"📊 *Daily Market Morning Digest \\({_escape_markdownv2(today_str)}\\)*",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for idx, (title, link) in enumerate(items, start=1):
        safe_title = _escape_markdownv2(title)
        if link:
            safe_link = link.replace(")", "\\)")
            lines.append(f"{idx}\\. [{safe_title}]({safe_link})")
        else:
            lines.append(f"{idx}\\. {safe_title}")
        lines.append("")  # blank line between items

    message = "\n".join(lines)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }

    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            print("[OK] Fresh morning news delivered!")
        else:
            print(f"[ERROR] Telegram API error ({res.status_code}): {res.text}")
    except requests.RequestException as exc:
        print(f"[ERROR] Network error: {exc}")


# ──────────────────────────── Entry Point ────────────────────────────

if __name__ == "__main__":
    # 20-hour window ensures subah 8 AM run pe kal dopahar se aaj tak ki news aaye
    articles = fetch_fresh_news(limit=12, max_age_hours=20)
    print(f"[INFO] Found {len(articles)} fresh article(s).")
    send_telegram_alert(articles)
