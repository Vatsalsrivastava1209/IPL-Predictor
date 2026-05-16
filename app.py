from pathlib import Path
from os import environ

import pandas as pd
import streamlit as st

from src.data_loader import FIXTURES_FILE, OVERRIDES_FILE, STATE_FILE, load_fixtures, load_overrides, load_state
from src.lineage import collect_snapshot_metadata, data_snapshot_hash
from src.observability import log_event, new_session_id
from src.simulator import compare_what_if, run_monte_carlo


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "rf_model.pkl"

st.set_page_config(page_title="IPL 2026 Champion Predictor", layout="wide")


def format_pct(value):
    return f"{value:.1f}%"


if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()
    log_event("session_started", session_id=st.session_state.session_id)


@st.cache_data(show_spinner=False)
def cached_simulation(n_simulations, snapshot_hash):
    return run_monte_carlo(n_simulations=n_simulations, persist=True)


@st.cache_data(show_spinner=False)
def cached_what_if(match_no, n_simulations, snapshot_hash):
    base, team1_case, team2_case = compare_what_if(match_no, n_simulations=n_simulations, persist=True)
    return base.probabilities, team1_case.probabilities, team2_case.probabilities


def probability_table(df):
    view = df.copy()
    for col in ["top4_pct", "top2_pct", "final_pct", "champion_pct"]:
        view[col] = view[col].round(1)
    st.dataframe(
        view,
        hide_index=True,
        use_container_width=True,
        column_config={
            "team": "Team",
            "top4_pct": st.column_config.ProgressColumn("Top 4", min_value=0, max_value=100, format="%.1f%%"),
            "top2_pct": st.column_config.ProgressColumn("Top 2", min_value=0, max_value=100, format="%.1f%%"),
            "final_pct": st.column_config.ProgressColumn("Final", min_value=0, max_value=100, format="%.1f%%"),
            "champion_pct": st.column_config.ProgressColumn("Champion", min_value=0, max_value=100, format="%.1f%%"),
            "elo": st.column_config.NumberColumn("Elo", format="%.0f"),
        },
    )


def render_downloads(probabilities, x_summary):
    csv = probabilities.to_csv(index=False).encode("utf-8")
    col1, col2 = st.columns([1, 2])
    with col1:
        downloaded = st.download_button("Download odds CSV", csv, "ipl_2026_probabilities.csv", "text/csv")
        if downloaded:
            log_event("odds_csv_downloaded", session_id=st.session_state.session_id)
    with col2:
        st.text_area("X-ready summary", x_summary, height=86)
        log_event("x_summary_viewed", session_id=st.session_state.session_id)


st.title("IPL 2026 Champion Predictor")
st.caption("Monte Carlo playoff and title odds powered by manual 2026 data, recent form, Elo ratings, and explainable assumptions.")

with st.sidebar:
    st.header("Simulation")
    n_simulations = st.slider("Monte Carlo seasons", 1_000, 20_000, 10_000, step=1_000)
    st.caption("10,000 is the default for stable public screenshots.")
    st.divider()
    st.header("Live data")
    st.success("CSV snapshot mode")
    st.caption("Daily API refresh should run in GitHub Actions. The app reads the latest committed CSV snapshot.")
    if environ.get("CRICAPI_KEY"):
        st.caption("A Streamlit secret is present, but writes should still happen through the scheduled workflow.")
    st.divider()
    st.header("Data source")
    st.write(f"State: `{STATE_FILE.name}`")
    st.write(f"Fixtures: `{FIXTURES_FILE.name}`")
    st.write(f"Overrides: `{OVERRIDES_FILE.name}`")
    if st.button("Clear cache and rerun"):
        st.cache_data.clear()
        st.rerun()

try:
    snapshot_hash = data_snapshot_hash()
    snapshot_metadata = collect_snapshot_metadata()
    state = load_state()
    fixtures = load_fixtures()
    overrides = load_overrides()
    simulation = cached_simulation(n_simulations, snapshot_hash)
except Exception as exc:
    log_event("data_load_failed", session_id=st.session_state.session_id, error_type=type(exc).__name__)
    st.error(f"Dashboard data could not be loaded: {exc}")
    st.stop()

probabilities = simulation.probabilities
leader = probabilities.iloc[0]
scheduled = fixtures[fixtures["status"] == "scheduled"]

tab_overview, tab_playoff, tab_champion, tab_what_if, tab_baseline, tab_method = st.tabs(
    ["Overview", "Playoff Race", "Champion Odds", "What-if Simulator", "Historical Baseline", "Methodology"]
)

with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Most likely champion", leader["team"])
    col2.metric("Title odds", format_pct(leader["champion_pct"]))
    col3.metric("Top 4 odds", format_pct(leader["top4_pct"]))
    col4.metric("Remaining fixtures", len(scheduled))
    st.caption(f"Snapshot hash: `{simulation.data_snapshot_hash}` | Runtime: `{simulation.runtime_ms:.0f} ms`")

    st.subheader("Probability Table")
    probability_table(probabilities)
    render_downloads(probabilities, simulation.x_summary)

    st.subheader("Current Manual Points Table")
    st.dataframe(state, hide_index=True, use_container_width=True)

with tab_playoff:
    st.subheader("Top 4 Race")
    chart_df = probabilities.set_index("team")[["top4_pct", "top2_pct"]].sort_values("top4_pct")
    st.bar_chart(chart_df)

    st.subheader("Remaining Fixtures")
    st.dataframe(
        scheduled[["match_no", "date", "team1", "team2", "venue", "city"]],
        hide_index=True,
        use_container_width=True,
    )

with tab_champion:
    st.subheader("Champion Odds")
    champion_df = probabilities.set_index("team")[["champion_pct", "final_pct"]].sort_values("champion_pct")
    st.bar_chart(champion_df)

    st.subheader("Team Ratings")
    rating_rows = []
    for team, rating in simulation.ratings.items():
        rating_rows.append(
            {
                "team": team,
                "elo": rating.elo,
                "batting_index": rating.batting_index,
                "bowling_index": rating.bowling_index,
                "form_index": rating.form_index,
                "nrr": rating.nrr,
            }
        )
    st.dataframe(pd.DataFrame(rating_rows).sort_values("elo", ascending=False), hide_index=True, use_container_width=True)

with tab_what_if:
    st.subheader("Lock One Upcoming Result")
    if scheduled.empty:
        st.info("No scheduled fixtures are left in the manual fixture file.")
    else:
        options = {
            f"Match {int(row.match_no)}: {row.team1} vs {row.team2}": int(row.match_no)
            for row in scheduled.itertuples()
        }
        label = st.selectbox("Choose a fixture", list(options))
        match_no = options[label]
        selected = fixtures.loc[fixtures["match_no"] == match_no].iloc[0]
        log_event(
            "what_if_fixture_selected",
            session_id=st.session_state.session_id,
            data_snapshot_hash=snapshot_hash,
            selected_match_no=match_no,
        )

        with st.spinner("Running what-if simulations..."):
            base_df, team1_df, team2_df = cached_what_if(match_no, max(1_000, n_simulations // 2), snapshot_hash)

        winner_choice = st.radio("Locked winner view", [selected["team1"], selected["team2"]], horizontal=True)
        log_event(
            "what_if_winner_selected",
            session_id=st.session_state.session_id,
            data_snapshot_hash=snapshot_hash,
            selected_match_no=match_no,
            locked_winner=winner_choice,
        )
        scenario_df = team1_df if winner_choice == selected["team1"] else team2_df
        merged = base_df[["team", "champion_pct", "top4_pct"]].merge(
            scenario_df[["team", "champion_pct", "top4_pct"]],
            on="team",
            suffixes=("_base", "_scenario"),
        )
        merged["champion_delta"] = merged["champion_pct_scenario"] - merged["champion_pct_base"]
        merged["top4_delta"] = merged["top4_pct_scenario"] - merged["top4_pct_base"]
        movers = merged.sort_values("champion_delta", ascending=False)

        st.write(f"If **{winner_choice}** win match {match_no}:")
        st.dataframe(
            movers[["team", "champion_pct_base", "champion_pct_scenario", "champion_delta", "top4_delta"]].round(2),
            hide_index=True,
            use_container_width=True,
        )
        st.subheader("Biggest Title Odds Movers")
        st.bar_chart(movers.set_index("team")["champion_delta"])

with tab_baseline:
    st.subheader("Historical Baseline")
    st.info(
        "The old Random Forest model is kept only as a historical baseline. "
        "It is not used for the main IPL 2026 odds because random historical splits did not generalize well to newer seasons."
    )
    if MODEL_PATH.exists():
        st.success(f"Legacy model artifact found: `{MODEL_PATH.name}`")
    else:
        st.warning("No legacy model artifact found. The dashboard still works from CSV data.")

with tab_method:
    st.subheader("How to Read This")
    st.write(
        "These are probabilities, not guarantees. The simulator runs the remaining IPL season thousands of times, "
        "then counts how often each team reaches the top 4, top 2, final, and title."
    )
    st.write(
        "Old IPL data is used only as a background Elo prior. Current season state, recent completed fixtures, NRR, "
        "manual strength overrides, and the remaining schedule carry the public-facing prediction."
    )
    st.write(
        "Manual CSVs are intentional: they make the dashboard transparent and stable for demos. Update the files, clear "
        "the Streamlit cache, and rerun the simulation."
    )

    st.subheader("Manual Strength Overrides")
    st.dataframe(overrides, hide_index=True, use_container_width=True)

    st.subheader("Data Lineage")
    st.dataframe(pd.DataFrame(snapshot_metadata), hide_index=True, use_container_width=True)
    log_event("methodology_tab_rendered", session_id=st.session_state.session_id, data_snapshot_hash=snapshot_hash)
