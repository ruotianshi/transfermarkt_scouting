# Transfermarkt Scout Platform

A Streamlit dashboard for scouting data from Transfermarkt — contract watch,
loan players, and automated Pre Scout Reports.

## Setup

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# WeasyPrint on macOS also needs:
# brew install pango

# WeasyPrint on Ubuntu/Debian also needs:
# sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0

# 3. Run the app
streamlit run app.py
```

## Project structure

```
scout_platform/
├── app.py                      ← Streamlit entry point
├── requirements.txt
├── scraper/
│   ├── __init__.py
│   ├── leagues.py              ← League → team URL mapping + cache
│   └── team.py                 ← Transfermarkt kader page scraper
├── report/
│   ├── __init__.py
│   ├── generator.py            ← Jinja2 render + WeasyPrint PDF export
│   ├── formation.py            ← SVG formation diagram generator
│   └── template.html           ← Report HTML/CSS template
├── assets/
│   └── league_logos/           ← (optional) local league logo images
└── cache/
    └── teams_cache.json        ← Auto-generated team URL cache (24h TTL)
```

## Features

| Module | Description |
|---|---|
| **Squad overview** | Full squad table for both teams |
| **Contract watch** | Players out of contract summer 2026 |
| **Loan players** | Active loan players + parent clubs |
| **Pre scout report** | Printable two-column report (HTML + PDF) |

## Notes

- Data is cached at the league level for 24 hours to reduce scraping load.
- Per-team data (kader + playing time) is cached in `st.session_state` for
  the duration of the browser session — click **Fetch data** again to refresh.
- WeasyPrint requires system-level Pango library for PDF export.
  If unavailable, the HTML download still works and can be printed from any browser.
- `streamlit-aggrid` is optional — the app falls back to `st.dataframe` if not installed.
