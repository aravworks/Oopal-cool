"""
MindEase — Therapist Finder via Google News + Gemini analysis

Practo and JustDial both run active anti-bot protection (DataDome-style
cryptographic challenges, TLS-fingerprint blocking) that blocks both plain
requests and real headless-browser automation — confirmed by direct testing,
not assumption. Scraping Google Search/Maps results directly is against
Google's ToS and gets blocked even harder.

Instead: search Google News' public RSS feed (a documented, non-adversarial
endpoint — no anti-bot circumvention involved) for real news coverage naming
real therapists/psychologists (awards, recognition, feature articles), then
ask Gemini to identify which articles actually name a specific professional
and how relevant they are to the user's condition — extracting ONLY what's
stated in the article, never fabricating contact details, fees, or ratings.
The city is geocoded via OpenStreetMap's Nominatim for an approximate map
pin (not the therapist's exact clinic address, which we don't have).

If no real, named therapist turns up in recent news for a city, this
returns an empty list — no fake fallback profiles. Coverage will be patchy
for smaller cities/conditions; that's an honest limitation, not a bug.
"""

import re
import json
import html
import random
import urllib.parse
import xml.etree.ElementTree as ET

import requests
import google.generativeai as genai
from gemini_system_prompt import generate_with_fallback, GEMINI_CALL_TIMEOUT

NEWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
NOMINATIM_UA = "MindEase-CollegeProject/1.0 (non-commercial demo; contact via GitHub)"

CONDITION_QUERIES = {
    "anxiety": "anxiety therapist",
    "adhd":    "ADHD psychologist",
    "stress":  "stress counsellor",
    "sleep":   "sleep therapist",
}


def _fetch_news_items(query: str, limit: int = 12) -> list[dict]:
    """Query Google News' public RSS search feed. Returns real article metadata."""
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    resp = requests.get(url, headers={"User-Agent": NEWS_UA}, timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    items = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        desc_raw = html.unescape(item.findtext("description") or "")
        # RSS description is usually '<a href="...">TITLE</a>&nbsp;&nbsp;<font ...>SOURCE</font>'
        m = re.search(r">([^<]+)</a>\s*(.*)$", desc_raw)
        source = re.sub(r"<[^>]+>", "", m.group(2)).strip() if m else ""
        if title:
            items.append({"title": title, "link": link, "source": source, "pub_date": pub_date})
    return items


def _geocode_city(city: str) -> dict | None:
    """Approximate city-level coordinates via OpenStreetMap's Nominatim — not
    the therapist's exact address, which we have no reliable source for."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": city, "country": "India", "format": "json", "limit": 1},
            headers={"User-Agent": NOMINATIM_UA},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
    except Exception:
        return None


def find_therapists(city: str, condition: str) -> list[dict]:
    """
    Main entry point. Called by POST /api/v1/therapist/search.
    Returns real, named therapists found in real news coverage, each with
    an approximate city-level map pin. Empty list if nothing genuine found —
    no fabricated profiles.
    """
    keyword = CONDITION_QUERIES.get(condition, "therapist")
    queries = [
        f'"{city}" {keyword} recognition award',
        f'"{city}" psychologist felicitated OR honoured OR awarded',
    ]

    seen_links = set()
    items = []
    for q in queries:
        try:
            for it in _fetch_news_items(q):
                if it["link"] and it["link"] not in seen_links:
                    seen_links.add(it["link"])
                    items.append(it)
        except Exception as e:
            print(f"[scraper] news fetch failed for query '{q}': {e}")

    if not items:
        return []

    numbered = "\n".join(
        f"{i+1}. TITLE: {it['title']}\n   SOURCE: {it['source']}\n   DATE: {it['pub_date']}"
        for i, it in enumerate(items)
    )

    prompt = f"""You are screening real news headlines to find therapists, psychologists,
psychiatrists, or counsellors who could help someone dealing with {condition},
based in or near {city}.

For each numbered item, decide if it names a SPECIFIC real person or named
clinic/wellness-center (not a generic mental-health-awareness piece with no
professional named). If it does, extract ONLY what the title/source actually
states — never invent a phone number, address, fee, or rating that isn't there.

Return a JSON array (max 5 items, most relevant to {condition} first). Each object:
{{
  "name": "the person's name, or clinic/center name if no individual is named",
  "specialty_note": "short phrase from the headline on why they're notable",
  "relevance_to_condition": "one short sentence on why this fits someone with {condition}",
  "item_number": <the numbered item this came from, integer>
}}

If none of the items name a real therapist/psychologist/clinic, return [].
JSON only, no markdown.

Items:
{numbered}
"""

    try:
        resp = generate_with_fallback(
            lambda name: genai.GenerativeModel(name).generate_content(
                prompt, request_options={"timeout": GEMINI_CALL_TIMEOUT}
            )
        )
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        matches = json.loads(raw)
    except Exception as e:
        print(f"[scraper] Gemini analysis failed: {e}")
        matches = []

    if not matches:
        return []

    geo = _geocode_city(city)
    results = []
    for m in matches[:5]:
        idx = (m.get("item_number") or 0) - 1
        source_item = items[idx] if 0 <= idx < len(items) else {}
        lat = lng = None
        if geo:
            # Small jitter so multiple pins in one city don't stack exactly —
            # this is an approximate area pin, not a precise clinic address.
            lat = geo["lat"] + random.uniform(-0.01, 0.01)
            lng = geo["lng"] + random.uniform(-0.01, 0.01)
        results.append({
            "name":        m.get("name", "").strip() or "Unnamed in article",
            "specialty":   m.get("specialty_note", "").strip(),
            "relevance":   m.get("relevance_to_condition", "").strip(),
            "source":      source_item.get("source", ""),
            "article_url": source_item.get("link"),
            "location":    city,
            "lat":         lat,
            "lng":         lng,
        })
    return results
