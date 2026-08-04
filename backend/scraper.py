"""
MindEase — Therapist Scraper
Scrapes Practo for therapists matching the user's condition and city.
Falls back to a curated static list if scraping is blocked.

CONDITION → SPECIALTY MAPPING:
  anxiety  → Anxiety Disorders, CBT, Stress Management
  adhd     → ADHD, Attention Deficit, Child & Adolescent Psychiatry
  stress   → Stress Management, Work-Life Balance, Burnout
  sleep    → Sleep Disorders, Insomnia, CBT for Insomnia
"""

import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup

# Condition → Practo search query mapping
CONDITION_QUERIES = {
    "anxiety": "anxiety therapist",
    "adhd":    "ADHD psychologist",
    "stress":  "stress counsellor",
    "sleep":   "sleep disorder psychologist",
}

CONDITION_TAGS = {
    "anxiety": ["Anxiety", "CBT", "Panic Disorder", "OCD"],
    "adhd":    ["ADHD", "Attention Deficit", "Executive Function"],
    "stress":  ["Stress", "Burnout", "Work-Life Balance"],
    "sleep":   ["Insomnia", "Sleep Disorders", "CBT-I"],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def scrape_practo(city: str, condition: str) -> list[dict]:
    """
    Scrape Practo search results for therapists.
    Returns list of therapist dicts.
    """
    query   = CONDITION_QUERIES.get(condition, "therapist")
    city_q  = city.lower().replace(" ", "-")
    url     = f"https://www.practo.com/{city_q}/therapist?specialization={query.replace(' ', '%20')}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        therapists = []
        cards = soup.select("div[data-qa-id='doctor_card']")[:8]

        for card in cards:
            try:
                name_el       = card.select_one("[data-qa-id='doctor_name']")
                rating_el     = card.select_one("[data-qa-id='doctor_rating']")
                specialty_el  = card.select_one("[data-qa-id='doctor_specialization']")
                exp_el        = card.select_one("[data-qa-id='doctor_experience']")
                fee_el        = card.select_one("[data-qa-id='doctor_fee']")
                locality_el   = card.select_one("[data-qa-id='practice_locality']")

                name     = name_el.get_text(strip=True)     if name_el     else "Unknown"
                rating   = rating_el.get_text(strip=True)   if rating_el   else "N/A"
                fee      = fee_el.get_text(strip=True)       if fee_el      else "Contact for fee"
                locality = locality_el.get_text(strip=True) if locality_el else city

                # Only include highly-rated (4.5+)
                try:
                    rating_float = float(rating.replace("(", "").replace(")", "").split()[0])
                    if rating_float < 4.5:
                        continue
                except (ValueError, IndexError):
                    pass

                therapists.append({
                    "name":       name,
                    "specialty":  specialty_el.get_text(strip=True) if specialty_el else "Therapist",
                    "rating":     rating,
                    "experience": exp_el.get_text(strip=True) if exp_el else "",
                    "fee":        fee,
                    "location":   f"{locality}, {city}",
                    "tags":       CONDITION_TAGS.get(condition, []),
                    "source":     "practo",
                })
            except Exception:
                continue

        return therapists[:5]

    except Exception as e:
        print(f"Scraper error: {e}")
        return []


def get_fallback_therapists(city: str, condition: str) -> list[dict]:
    """
    Static fallback list when scraping is blocked.
    Shows realistic data for demo purposes.
    """
    base = [
        {
            "name":       "Dr. Priya Sharma",
            "specialty":  "Clinical Psychologist",
            "rating":     "4.9",
            "experience": "12 years",
            "fee":        "₹800/session",
            "location":   f"{city}",
            "phone":      "+91-9XXXXXXXXX",
            "tags":       CONDITION_TAGS.get(condition, []),
            "source":     "fallback",
            "lat":        None,
            "lng":        None,
        },
        {
            "name":       "Dr. Rohit Agarwal",
            "specialty":  "Psychiatrist",
            "rating":     "4.7",
            "experience": "8 years",
            "fee":        "₹1,200/session",
            "location":   f"{city}",
            "phone":      "+91-9XXXXXXXXX",
            "tags":       CONDITION_TAGS.get(condition, []),
            "source":     "fallback",
            "lat":        None,
            "lng":        None,
        },
        {
            "name":       "Ms. Neha Kapoor",
            "specialty":  "Counselling Psychologist",
            "rating":     "4.8",
            "experience": "6 years",
            "fee":        "₹600/session",
            "location":   f"{city}",
            "phone":      "+91-9XXXXXXXXX",
            "tags":       CONDITION_TAGS.get(condition, []),
            "source":     "fallback",
            "lat":        None,
            "lng":        None,
        },
    ]
    return base


def find_therapists(city: str, condition: str) -> list[dict]:
    """
    Main entry point.
    Tries scraping first, falls back to static list.
    Called by POST /api/v1/therapist/search
    """
    results = scrape_practo(city, condition)
    if not results:
        results = get_fallback_therapists(city, condition)
    return results
