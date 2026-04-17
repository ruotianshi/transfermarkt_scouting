"""
Report generator.
  - render_html()  →  HTML string (used for Streamlit preview)
  - render_pdf()   →  PDF bytes  (used for st.download_button)
"""

import os
import io
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from .formation import formation_svg_base64

TEMPLATE_DIR = os.path.dirname(__file__)


def _df_to_records(df) -> list:
    """Convert a DataFrame to a list of SimpleNamespace-like dicts for Jinja2."""
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    # Convert NaT / NaN to empty string for clean rendering
    cleaned = []
    for r in records:
        cleaned.append({
            k: ("" if (v != v or str(v) == "NaT") else v)
            for k, v in r.items()
        })
    return [_DictObj(r) for r in cleaned]


class _DictObj:
    """Allows attribute access on a dict (row.Name instead of row['Name'])."""
    def __init__(self, d: dict):
        self.__dict__.update(d)


def render_html(
    owner_club: str,
    home_team: str,
    away_team: str,
    league: str,
    match_date: str,
    home_formation: str,
    away_formation: str,
    home_l5g: list,      # e.g. ['w','w','d','l','w']
    away_l5g: list,
    home_crest_url: str,
    away_crest_url: str,
    home_summer_df,
    home_loan_df,
    away_summer_df,
    away_loan_df,
    home_poi: str = "",
    away_poi: str = "",
    league_logo_url: str = "",
    home_league: str = "",
    away_league: str = "",
    note: str = "",
) -> str:
    """Render the Jinja2 template and return an HTML string."""

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)
    tpl = env.get_template("template.html")

    context = dict(
        owner_club        = owner_club,
        home_team         = home_team,
        away_team         = away_team,
        league            = league,
        home_league       = home_league or league,
        away_league       = away_league or league,
        match_date        = match_date,
        home_formation    = home_formation,
        away_formation    = away_formation,
        home_formation_svg= formation_svg_base64(home_formation),
        away_formation_svg= formation_svg_base64(away_formation),
        home_l5g          = home_l5g,
        away_l5g          = away_l5g,
        home_crest_url    = home_crest_url,
        away_crest_url    = away_crest_url,
        home_summer       = _df_to_records(home_summer_df),
        home_loans        = _df_to_records(home_loan_df),
        away_summer       = _df_to_records(away_summer_df),
        away_loans        = _df_to_records(away_loan_df),
        home_poi          = home_poi,
        away_poi          = away_poi,
        league_logo_url   = league_logo_url,
        note              = note,
        generated_at      = datetime.now().strftime("%d %b %Y %H:%M"),
    )

    return tpl.render(**context)


def render_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError:
        raise ImportError(
            "WeasyPrint is not installed. Run: pip install weasyprint"
        )
