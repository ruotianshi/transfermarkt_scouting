import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime, timedelta

CACHE_PATH = os.path.join(os.path.dirname(__file__), "../cache/teams_cache.json")
CACHE_TTL_HOURS = 24

LEAGUES = {
    "Premier League": {"url": "https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1", "country": "England"},
    "Championship":   {"url": "https://www.transfermarkt.co.uk/championship/startseite/wettbewerb/GB2",   "country": "England"},
    "League One":     {"url": "https://www.transfermarkt.co.uk/league-one/startseite/wettbewerb/GB3",     "country": "England"},
    "League Two":     {"url": "https://www.transfermarkt.co.uk/league-two/startseite/wettbewerb/GB4",     "country": "England"},
    "La Liga":        {"url": "https://www.transfermarkt.co.uk/laliga/startseite/wettbewerb/ES1",         "country": "Spain"},
    "Bundesliga":     {"url": "https://www.transfermarkt.co.uk/bundesliga/startseite/wettbewerb/L1",      "country": "Germany"},
    "Serie A":        {"url": "https://www.transfermarkt.co.uk/serie-a/startseite/wettbewerb/IT1",        "country": "Italy"},
    "Ligue 1":        {"url": "https://www.transfermarkt.co.uk/ligue-1/startseite/wettbewerb/FR1",        "country": "France"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(data: dict):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cache_fresh(cache: dict, league: str) -> bool:
    if league not in cache:
        return False
    ts = cache[league].get("fetched_at")
    if not ts:
        return False
    fetched = datetime.fromisoformat(ts)
    return datetime.now() - fetched < timedelta(hours=CACHE_TTL_HOURS)


def get_league_names() -> list:
    return list(LEAGUES.keys())


def get_teams(league: str, force_refresh: bool = False) -> dict:
    """
    Returns {team_name: {"kader_url": ..., "crest_url": ...}} for the league.
    Uses local JSON cache unless stale or force_refresh=True.
    """
    cache = _load_cache()
    if not force_refresh and _cache_fresh(cache, league):
        return cache[league]["teams"]

    league_url = LEAGUES[league]["url"]
    teams = _fetch_teams_from_page(league_url)

    cache[league] = {
        "teams": teams,
        "fetched_at": datetime.now().isoformat(),
    }
    _save_cache(cache)
    return teams


def _fetch_teams_from_page(league_url: str) -> dict:
    """Scrape the league page for team names, kader URLs and crest URLs."""
    try:
        resp = requests.get(league_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        teams = {}
        table = soup.find("table", class_="items")
        if not table:
            return teams

        for row in table.find_all("tr", class_=["odd", "even"]):
            name_td = row.find("td", class_="hauptlink")
            if not name_td:
                continue
            a = name_td.find("a", href=True)
            if not a:
                continue

            team_name = a.get_text(strip=True)
            href = a["href"]
            # Convert /startseite/ path to /kader/ with season param
            kader_href = href.replace("/startseite/", "/kader/") + "/saison_id/2025/plus/1"
            kader_url = "https://www.transfermarkt.co.uk" + kader_href

            crest_url = ""
            img = row.find("img", class_="tiny_wappen")
            if img:
                crest_url = img.get("src") or img.get("data-src", "")

            teams[team_name] = {
                "kader_url": kader_url,
                "crest_url": crest_url,
            }

        return teams

    except Exception as e:
        print(f"[leagues] Error fetching {league_url}: {e}")
        return {}
