"""
Transfermarkt Scout Platform
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import io

from scraper import get_league_names, get_teams, scrape_team
from report import render_html, render_pdf, FORMATIONS

# ─────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scout Platform",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Custom CSS  (minimal — keep Streamlit's own theme)
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Tighten metric cards */
  [data-testid="metric-container"] { padding: 10px 14px !important; }
  /* Tighten sidebar padding */
  section[data-testid="stSidebar"] > div { padding-top: 1rem; }
  /* Download button full width */
  .stDownloadButton > button { width: 100%; }
  /* Table header */
  .team-header {
    background: #0f2557;
    color: white;
    padding: 6px 10px;
    border-radius: 4px 4px 0 0;
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 0;
  }
</style>
""", unsafe_allow_html=True)

FORMATION_LIST = list(FORMATIONS.keys())
L5G_OPTIONS    = ["W", "D", "L"]
OWNER_CLUB_DEFAULT = "Gillingham"


# ─────────────────────────────────────────────────────────────────
# Session-state helpers
# ─────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "home_data":      None,
        "away_data":      None,
        "home_team_name": "",
        "away_team_name": "",
        "fetched":        False,
        "report_html":    None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚽ Scout Platform")
    st.divider()

    # ── Owner club ──
    owner_club = st.text_input("Your club name", value=OWNER_CLUB_DEFAULT)
    st.divider()

    # ── Match setup ──
    st.subheader("Match setup")

    all_leagues = get_league_names()

    # ── Home team ──
    st.caption("Home team")
    home_league = st.selectbox("Home league", all_leagues, key="home_league_sel")
    with st.spinner("Loading home team list…"):
        home_teams_dict = get_teams(home_league)
    home_team_names = sorted(home_teams_dict.keys())
    if not home_team_names:
        st.warning("Could not load home teams — check your connection.")
        st.stop()
    col_h_ref = st.columns([4, 1])
    with col_h_ref[1]:
        if st.button("↻", key="ref_home", help="Refresh home team list"):
            home_teams_dict = get_teams(home_league, force_refresh=True)
            st.rerun()
    home_team = st.selectbox("Home team", home_team_names, key="home_select")

    st.divider()

    # ── Away team ──
    st.caption("Away team")
    away_league = st.selectbox("Away league", all_leagues, key="away_league_sel")
    with st.spinner("Loading away team list…"):
        away_teams_dict = get_teams(away_league)
    away_team_names = sorted(away_teams_dict.keys())
    if not away_team_names:
        st.warning("Could not load away teams — check your connection.")
        st.stop()
    col_a_ref = st.columns([4, 1])
    with col_a_ref[1]:
        if st.button("↻", key="ref_away", help="Refresh away team list"):
            away_teams_dict = get_teams(away_league, force_refresh=True)
            st.rerun()
    away_team = st.selectbox("Away team", away_team_names, key="away_select")

    st.divider()

    # ── Competition name (shown on report) ──
    COMMON_COMPETITIONS = [
        "Premier League", "Championship", "League One", "League Two",
        "La Liga", "Bundesliga", "Serie A", "Ligue 1",
        "Champions League", "Europa League", "Conference League",
        "FA Cup", "Carabao Cup", "EFL Trophy", "Custom…",
    ]
    comp_choice = st.selectbox("Competition (report)", COMMON_COMPETITIONS, key="comp_sel")
    if comp_choice == "Custom…":
        competition = st.text_input("Competition name", placeholder="e.g. Friendly", key="comp_custom")
    else:
        competition = comp_choice

    match_date = st.date_input("Match date")
    st.divider()

    # ── Home team settings ──
    st.subheader(f"🏠 {home_team}")

    home_formation = st.selectbox("Formation", FORMATION_LIST, key="home_form")

    st.caption("Last 5 games  (oldest → newest)")
    home_l5g = []
    cols_h = st.columns(5)
    for i, col in enumerate(cols_h):
        with col:
            val = st.selectbox(f"G{i+1}", L5G_OPTIONS, key=f"hl5g_{i}")
            home_l5g.append(val.lower())

    home_poi = st.text_area("Player(s) of interest", height=70, key="home_poi",
                             placeholder="e.g. Michael Cheek — top scorer…")
    st.divider()

    # ── Away team settings ──
    st.subheader(f"✈️ {away_team}")

    away_formation = st.selectbox("Formation", FORMATION_LIST, key="away_form")

    st.caption("Last 5 games  (oldest → newest)")
    away_l5g = []
    cols_a = st.columns(5)
    for i, col in enumerate(cols_a):
        with col:
            val = st.selectbox(f"G{i+1}", L5G_OPTIONS, key=f"al5g_{i}")
            away_l5g.append(val.lower())

    away_poi = st.text_area("Player(s) of interest", height=70, key="away_poi",
                             placeholder="e.g. Jake Eastwood — key GK…")
    st.divider()

    # ── Note ──
    st.subheader("📝 Note")
    report_note = st.text_area(
        "Note (shown at bottom of report)",
        height=90,
        key="report_note",
        placeholder="e.g. Key tactical observation, referee info, travel notes…",
    )
    st.divider()

    # ── Fetch button ──
    fetch_clicked = st.button("🔍 Fetch data", use_container_width=True, type="primary")

    if fetch_clicked:
        home_url = home_teams_dict[home_team]["kader_url"]
        away_url = away_teams_dict[away_team]["kader_url"]

        with st.spinner(f"Fetching {home_team}…"):
            home_data = scrape_team(home_url)

        with st.spinner(f"Fetching {away_team}…"):
            away_data = scrape_team(away_url)

        st.session_state["home_data"]      = home_data
        st.session_state["away_data"]      = away_data
        st.session_state["home_team_name"] = home_team
        st.session_state["away_team_name"] = away_team
        st.session_state["fetched"]        = True
        st.session_state["report_html"]    = None  # reset on new fetch
        st.rerun()


# ─────────────────────────────────────────────────────────────────
# Main area
# ─────────────────────────────────────────────────────────────────

# ── Banner ──────────────────────────────────────────────────────
def _l5g_html(results: list) -> str:
    colors = {"w": "#22c55e", "d": "#f59e0b", "l": "#ef4444"}
    dots = "".join(
        f'<span style="display:inline-block;width:14px;height:14px;'
        f'border-radius:50%;background:{colors.get(r,"#888")};margin-right:3px"></span>'
        for r in results
    )
    return dots


st.markdown(f"""
<div style="
  background:linear-gradient(135deg,#0f2557 0%,#1a3a6b 100%);
  border:1px solid #2a4a8a;
  border-radius:8px;
  padding:14px 20px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin-bottom:16px;
">
  <div style="text-align:left">
    <div style="color:white;font-size:16px;font-weight:700">{home_team}</div>
    <div style="color:#aabbd0;font-size:11px">{home_formation}</div>
    <div style="margin-top:5px">{_l5g_html(home_l5g)}</div>
  </div>
  <div style="text-align:center">
    <div style="color:white;font-size:22px;font-weight:700">V</div>
    <div style="color:#d0d8e8;font-size:12px;margin-top:4px">{match_date.strftime("%d %b %Y")}</div>
    <div style="color:#8899bb;font-size:10px;margin-top:2px">{competition}</div>
  </div>
  <div style="text-align:right">
    <div style="color:white;font-size:16px;font-weight:700">{away_team}</div>
    <div style="color:#aabbd0;font-size:11px">{away_formation}</div>
    <div style="margin-top:5px;direction:rtl">{_l5g_html(away_l5g)}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Guard: no data yet ───────────────────────────────────────────
if not st.session_state["fetched"]:
    st.info("👈 Select both teams in the sidebar and click **Fetch data** to begin.")
    st.stop()

home_data = st.session_state["home_data"]
away_data = st.session_state["away_data"]

# Error handling
if home_data["error"]:
    st.error(f"Error fetching {home_team}: {home_data['error']}")
if away_data["error"]:
    st.error(f"Error fetching {away_team}: {away_data['error']}")

if home_data["full_df"].empty and away_data["full_df"].empty:
    st.stop()

# ── Metric cards ────────────────────────────────────────────────
def _avg_age(df) -> str:
    if df.empty or "Age" not in df.columns:
        return "—"
    ages = pd.to_numeric(df["Age"], errors="coerce").dropna()
    return f"{ages.mean():.1f}" if not ages.empty else "—"

mc = st.columns(8)
home_full   = home_data["full_df"]
home_summer = home_data["summer_df"]
home_loans  = home_data["loan_df"]
away_full   = away_data["full_df"]
away_summer = away_data["summer_df"]
away_loans  = away_data["loan_df"]

with mc[0]: st.metric("🏠 Squad",       len(home_full))
with mc[1]: st.metric("📋 Out contract", len(home_summer))
with mc[2]: st.metric("🔄 On loan",     len(home_loans))
with mc[3]: st.metric("📅 Avg age",     _avg_age(home_full))
with mc[4]: st.metric("✈️ Squad",        len(away_full))
with mc[5]: st.metric("📋 Out contract", len(away_summer))
with mc[6]: st.metric("🔄 On loan",     len(away_loans))
with mc[7]: st.metric("📅 Avg age",     _avg_age(away_full))

st.divider()

# ── Tabs ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Squad overview",
    "📅 Contract watch",
    "🔄 Loan players",
    "📄 Pre scout report",
])


# ─── Helper: interactive dataframe with AgGrid (or fallback) ────
def _show_table(df: pd.DataFrame, key: str, height: int = 300):
    if df.empty:
        st.info("No data available.")
        return
    st.dataframe(df, use_container_width=True, height=height, key=key)


def _download_row(df: pd.DataFrame, label: str):
    """Render CSV and XLSX download buttons side by side."""
    if df.empty:
        return
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(f"⬇ CSV", csv_bytes, f"{label}.csv", "text/csv", key=f"{label}_csv")
    with c2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False)
        st.download_button(f"⬇ XLSX", buf.getvalue(), f"{label}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"{label}_xlsx")


# ─── TAB 1: Squad overview ──────────────────────────────────────
with tab1:
    col_h, col_a = st.columns(2)

    with col_h:
        st.markdown(f"#### 🏠 {home_team} — Full squad")
        _show_table(home_full, key="home_full_grid")
        _download_row(home_full, f"home_{home_team}_squad")

    with col_a:
        st.markdown(f"#### ✈️ {away_team} — Full squad")
        _show_table(away_full, key="away_full_grid")
        _download_row(away_full, f"away_{away_team}_squad")


# ─── TAB 2: Contract watch ──────────────────────────────────────
with tab2:
    col_h, col_a = st.columns(2)

    with col_h:
        st.markdown(f"#### 🏠 {home_team} — Out of contract (summer 2026)")
        _show_table(home_summer, key="home_summer_grid")
        _download_row(home_summer, f"home_{home_team}_out_of_contract")

    with col_a:
        st.markdown(f"#### ✈️ {away_team} — Out of contract (summer 2026)")
        _show_table(away_summer, key="away_summer_grid")
        _download_row(away_summer, f"away_{away_team}_out_of_contract")


# ─── TAB 3: Loan players ────────────────────────────────────────
with tab3:
    col_h, col_a = st.columns(2)

    with col_h:
        st.markdown(f"#### 🏠 {home_team} — On loan")
        _show_table(home_loans, key="home_loan_grid")
        _download_row(home_loans, f"home_{home_team}_loans")

    with col_a:
        st.markdown(f"#### ✈️ {away_team} — On loan")
        _show_table(away_loans, key="away_loan_grid")
        _download_row(away_loans, f"away_{away_team}_loans")


# ─── TAB 4: Pre scout report ────────────────────────────────────
with tab4:
    st.markdown("#### Pre Scout Report preview")
    st.caption(
        "The report is generated from the data fetched above. "
        "Formation, Last 5 Games and Players of Interest are set in the sidebar."
    )

    # Build / rebuild HTML
    if st.button("🔄 Generate / refresh report", type="primary"):
        html = render_html(
            owner_club       = owner_club,
            home_team        = home_team,
            away_team        = away_team,
            league           = competition,
            match_date       = match_date.strftime("%d-%m-%Y"),
            home_formation   = home_formation,
            away_formation   = away_formation,
            home_l5g         = home_l5g,
            away_l5g         = away_l5g,
            home_crest_url   = home_data.get("crest_url", ""),
            away_crest_url   = away_data.get("crest_url", ""),
            home_summer_df   = home_summer,
            home_loan_df     = home_loans,
            away_summer_df   = away_summer,
            away_loan_df     = away_loans,
            home_poi         = home_poi,
            away_poi         = away_poi,
            home_league      = home_league,
            away_league      = away_league,
            note             = report_note,
        )
        st.session_state["report_html"] = html

    # Preview
    if st.session_state["report_html"]:
        html = st.session_state["report_html"]

        # Inline preview (scaled down)
        st.components.v1.html(html, height=900, scrolling=True)

        st.divider()
        c1, c2 = st.columns([1, 4])

        with c1:
            # HTML download
            st.download_button(
                "⬇ Download HTML",
                html.encode("utf-8"),
                file_name=f"scout_report_{home_team}_v_{away_team}.html",
                mime="text/html",
                use_container_width=True,
            )

        with c2:
            # PDF download
            if st.button("📄 Generate PDF", use_container_width=False):
                with st.spinner("Generating PDF…"):
                    try:
                        pdf_bytes = render_pdf(html)
                        st.download_button(
                            "⬇ Download PDF",
                            pdf_bytes,
                            file_name=f"scout_report_{home_team}_v_{away_team}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except ImportError as e:
                        st.error(str(e))
    else:
        st.info("Click **Generate / refresh report** to build the preview.")
