import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import time
import random

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.transfermarkt.co.uk/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

SUMMER_START = datetime(2026, 5, 1)
SUMMER_END   = datetime(2026, 8, 31)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scrape_team(kader_url: str) -> dict:
    """
    Scrape a Transfermarkt kader page.

    Returns:
        {
            "full_df":   DataFrame  – all players,
            "summer_df": DataFrame  – out-of-contract players (summer 2026),
            "loan_df":   DataFrame  – on-loan players,
            "team_name": str,
            "crest_url": str,
            "error":     str | None,
        }
    """
    empty = _empty_result()
    try:
        full_df, crest_url, team_name = _scrape_kader(kader_url)
        if full_df.empty:
            empty["error"] = "No players found on kader page."
            return empty

        # Fetch and merge playing-time data
        minutes_url = _kader_to_minutes_url(kader_url)
        time.sleep(random.uniform(2, 4))
        minutes_df = _scrape_minutes(minutes_url)

        if not minutes_df.empty:
            full_df = full_df.drop(columns=["MinutePlayed"], errors="ignore")
            full_df = pd.merge(full_df, minutes_df, on="Name", how="left")
            full_df["MinutePlayed"] = full_df["MinutePlayed"].fillna(0).astype(int)
        else:
            full_df["MinutePlayed"] = 0

        # Re-order columns
        col_order = ["Name", "Position", "MinutePlayed", "Age", "Contract_Date", "Contract_Type"]
        full_df = full_df[[c for c in col_order if c in full_df.columns]]

        # ---- Loan players ----
        loan_mask = full_df["Contract_Type"].str.contains("On loan", case=False, na=False)
        loan_df = full_df[loan_mask].copy()
        if not loan_df.empty:
            loan_df["From"] = loan_df["Contract_Type"].apply(_extract_from_club)
            loan_df = loan_df[["Name", "Position", "From", "MinutePlayed", "Age", "Contract_Date"]]
        else:
            loan_df = pd.DataFrame(columns=["Name", "Position", "From", "MinutePlayed", "Age", "Contract_Date"])

        # ---- Summer 2026 expiries (excluding loans) ----
        if not full_df.empty:
            summer_mask = (
                (full_df["Contract_Date"] >= SUMMER_START) &
                (full_df["Contract_Date"] <= SUMMER_END)
            )
            summer_df = full_df[summer_mask & ~loan_mask].copy().reset_index(drop=True)
        else:
            summer_df = pd.DataFrame(columns=full_df.columns)

        return {
            "full_df":   full_df,
            "summer_df": summer_df,
            "loan_df":   loan_df,
            "team_name": team_name,
            "crest_url": crest_url,
            "error":     None,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        empty["error"] = str(e)
        return empty


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_result() -> dict:
    cols_full  = ["Name", "Position", "MinutePlayed", "Age", "Contract_Date", "Contract_Type"]
    cols_loan  = ["Name", "Position", "From", "MinutePlayed", "Age", "Contract_Date"]
    return {
        "full_df":   pd.DataFrame(columns=cols_full),
        "summer_df": pd.DataFrame(columns=cols_full),
        "loan_df":   pd.DataFrame(columns=cols_loan),
        "team_name": "",
        "crest_url": "",
        "error":     None,
    }


def _kader_to_minutes_url(kader_url: str) -> str:
    team_match = re.search(r"transfermarkt\.co\.uk/([^/]+)/kader/", kader_url)
    id_match   = re.search(r"/verein/(\d+)", kader_url)
    if team_match and id_match:
        return (
            f"https://www.transfermarkt.co.uk/"
            f"{team_match.group(1)}/leistungsdaten/verein/{id_match.group(1)}"
        )
    raise ValueError(f"Cannot parse kader URL: {kader_url}")


def _scrape_kader(kader_url: str):
    """Returns (full_df, crest_url, team_name)."""
    resp = requests.get(kader_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    # ---- Team name ----
    team_name = ""
    h1 = soup.find("h1", class_="data-header__headline-wrapper")
    if h1:
        team_name = h1.get_text(strip=True)
    if not team_name:
        m = re.search(r"transfermarkt\.co\.uk/([^/]+)/kader/", kader_url)
        team_name = m.group(1).replace("-", " ").title() if m else ""

    # ---- Crest URL ----
    crest_url = ""
    crest_img = soup.find("img", class_="data-header__profile-image")
    if crest_img:
        crest_url = crest_img.get("src") or crest_img.get("data-src", "")

    # ---- Player rows ----
    # Transfermarkt uses main rows (odd/even) plus sub-rows (no class).
    # We identify player rows by the presence of td.posrela.
    data = {k: [] for k in ["Name", "Position", "MinutePlayed", "Age", "Contract_Date", "Contract_Type"]}

    for row in soup.select("table.items tbody tr"):
        pos_td = row.find("td", class_="posrela")
        if not pos_td:
            continue  # skip header rows, sub-rows, spacers

        # ---- Name ----
        # New TM structure: player link has href matching /profil/spieler/, no special class
        name_a = pos_td.find("a", href=re.compile(r"/profil/spieler/\d+"))
        if not name_a:
            continue
        name = name_a.get_text(strip=True)
        if not name:
            continue
        data["Name"].append(name)

        # ---- Position ----
        # Sits in the last <tr> of the inline-table inside posrela
        pos = ""
        inline_table = pos_td.find("table", class_="inline-table")
        if inline_table:
            trs = inline_table.find_all("tr")
            if len(trs) >= 2:
                pos = trs[-1].get_text(strip=True)
        if not pos:
            pos = pos_td.get_text(" ", strip=True)
        data["Position"].append(pos)

        # ---- Age (extract from DOB cell "dd/mm/YYYY (age)") ----
        zentriert_tds = row.find_all("td", class_="zentriert")
        age = None
        for td in zentriert_tds:
            txt = td.get_text(strip=True)
            m = re.search(r'\((\d{1,2})\)', txt)
            if m:
                candidate = int(m.group(1))
                if 14 <= candidate <= 55:
                    age = candidate
                    break
        data["Age"].append(age)

        # Minutes played placeholder (filled later)
        data["MinutePlayed"].append(0)

        # ---- Contract date ----
        # Second-to-last zentriert td (last is the previous-club logo td or market value);
        # scan right-to-left for a date-like text dd/mm/YYYY
        contract_date = None
        for td in reversed(zentriert_tds):
            txt = td.get_text(strip=True)
            if re.match(r"\d{2}/\d{2}/\d{4}", txt):
                contract_date = txt
                break
        data["Contract_Date"].append(contract_date)

        # ---- Contract type (loan info) ----
        contract_type = ""
        loan_span = row.find("span", class_="wechsel-kader-wappen")
        if loan_span and loan_span.a:
            contract_type = loan_span.a.get("title", "")
        if not contract_type:
            loan_link = row.find("a", class_="hide-for-small")
            if loan_link:
                contract_type = loan_link.get("title", "")
        data["Contract_Type"].append(contract_type)

    full_df = pd.DataFrame(data).dropna(subset=["Name"]).reset_index(drop=True)

    # Parse contract dates (format: dd/mm/YYYY)
    full_df["Contract_Date"] = pd.to_datetime(
        full_df["Contract_Date"], format="%d/%m/%Y", errors="coerce"
    )

    return full_df, crest_url, team_name


def _scrape_minutes(minutes_url: str) -> pd.DataFrame:
    """Returns DataFrame with columns [Name, MinutePlayed]."""
    try:
        resp = requests.get(minutes_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        players, minutes_list, seen = [], [], set()

        for row in soup.select("table.items tbody tr"):
            name_elem = row.find("a", title=True, href=re.compile(r"/profil/spieler/"))
            if not name_elem:
                name_td = row.find("td", class_="hauptlink")
                name_elem = name_td.find("a") if name_td else None
            if not name_elem:
                continue

            player_name = name_elem.get_text(strip=True)
            if player_name in seen:
                continue

            mins = 0
            for td in row.find_all("td"):
                if "rechts" in td.get("class", []):
                    txt = td.get_text(strip=True)
                    if txt and txt.replace("'", "").replace(".", "").isdigit():
                        mins = int(txt.replace("'", "").replace(".", ""))
                        break

            players.append(player_name)
            minutes_list.append(mins)
            seen.add(player_name)

        return pd.DataFrame({"Name": players, "MinutePlayed": minutes_list})

    except Exception as e:
        print(f"[team] Error fetching minutes from {minutes_url}: {e}")
        return pd.DataFrame(columns=["Name", "MinutePlayed"])


def _extract_from_club(contract_type: str) -> str:
    if pd.isna(contract_type):
        return ""
    m = re.search(r"from\s+(.+?)\s+until", contract_type, re.IGNORECASE)
    return m.group(1).strip() if m else ""
