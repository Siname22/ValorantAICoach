from __future__ import annotations

import sys
from pathlib import Path

# Guarantees `utils` stays importable even when this module is loaded before the
# Streamlit entrypoint has registered the app directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from utils.api_client import APIClientError, get_api_client  # noqa: E402
from utils.ui import (  # noqa: E402
    apply_global_styles,
    render_metric_card,
    render_page_header,
    render_sidebar,
)


def render_home_page() -> None:
    """Render the landing experience for the university demo."""
    st.set_page_config(
        page_title="Valorant AI Coach",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Valorant AI Coach",
        "A polished Streamlit experience for presenting the FastAPI backend "
        "as a professional product demo for recruiters and stakeholders.",
        eyebrow="PRODUCT DEMO",
    )

    st.markdown("")
    col_a, col_b = st.columns([1.4, 0.8], vertical_alignment="center")
    with col_a:
        st.markdown(
            "The backend architecture is already in place, and this interface "
            "turns it into a clean, premium presentation layer for live demos."
        )
        st.markdown(
            "<div class='pill'>FastAPI</div>"
            "<div class='pill'>Clean Architecture</div>"
            "<div class='pill'>Provider Fallback</div>"
            "<div class='pill'>REST API</div>"
            "<div class='pill'>Streamlit UI</div>",
            unsafe_allow_html=True,
        )
        if st.button("Search a player", type="primary"):
            st.switch_page("pages/2_Player_Search.py")
    with col_b:
        st.markdown(
            "<div class='hero-card'>"
            "<h4 style='margin-top:0;'>Experience highlights</h4>"
            "<ul><li>Backend remains untouched</li>"
            "<li>Frontend is fully HTTP-based</li>"
            "<li>Designed for presentation and deployment</li></ul>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("Implemented technologies")
    tech_cols = st.columns(4)
    tech_items = [
        ("Python", "Backend orchestration and data models"),
        ("FastAPI", "Public REST endpoints"),
        ("Streamlit", "Interactive presentation UI"),
        ("Plotly", "Roadmap visualization"),
    ]
    for column, (name, description) in zip(tech_cols, tech_items, strict=False):
        with column:
            st.markdown(
                f"<div class='metric-card'><h4>{name}</h4>"
                f"<p style='color:#8b949e; margin:0;'>{description}</p></div>",
                unsafe_allow_html=True,
            )


def render_player_search_page() -> None:
    """Render the interactive player search experience."""
    st.set_page_config(
        page_title="Player Search • Valorant AI Coach",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Player search",
        "Enter a player identity to fetch the profile, rank and recent matches "
        "from the existing REST API in a polished product interface.",
        eyebrow="LIVE DATA",
    )

    st.markdown("")
    left_col, right_col = st.columns([1.25, 0.75], vertical_alignment="top")

    with left_col, st.container():
        st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
        with st.form("player_search"):
            game_name = st.text_input("Game Name", value="TestPlayer")
            tag_line = st.text_input("Tag", value="NA1")
            submitted = st.form_submit_button("Analyze", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        render_metric_card(
            "Status",
            "HTTP-ready",
            "The UI calls the REST API directly and keeps the backend untouched.",
        )
        render_metric_card(
            "Data sources",
            "Tracker → Henrik → Riot",
            "Fallback strategy preserved from the backend layer.",
        )
        render_metric_card(
            "Presentation mode",
            "SaaS-style",
            "Optimized for demos, talks and recruiter walkthroughs.",
        )

    if submitted:
        if not game_name or not tag_line:
            st.warning("Please provide both a game name and a tag line.")
            return

        client = get_api_client()
        with st.spinner("Querying the backend API..."):
            try:
                profile = client.get_player_profile(game_name, tag_line)
                rank = client.get_player_rank(game_name, tag_line)
                matches_payload = client.get_player_matches(game_name, tag_line)
            except APIClientError as exc:
                st.error(str(exc))
                st.info(
                    "Ensure the FastAPI backend is running at the configured "
                    "URL before using the demo."
                )
                return

        st.success("Player data retrieved successfully.")
        profile_col, rank_col = st.columns([1.5, 0.8], vertical_alignment="top")
        with profile_col:
            st.markdown("### Profile")
            card_content = "<div class='hero-card'>"
            if profile.get("avatar_url"):
                st.image(profile["avatar_url"], width=120)
            else:
                st.markdown(
                    "<div style='width:120px;height:120px;border-radius:16px;"
                    "background:#161b22;border:1px dashed #30363d;"
                    "display:flex;align-items:center;justify-content:center;"
                    "color:#8b949e;'>Avatar placeholder</div>",
                    unsafe_allow_html=True,
                )
            card_content += (
                f"<h3>{profile.get('game_name', game_name)}#"
                f"{profile.get('tag_line', tag_line)}</h3>"
            )
            card_content += (
                f"<p><strong>Level:</strong> "
                f"{profile.get('account_level', 'Unknown')}</p>"
            )
            card_content += (
                f"<p><strong>Region:</strong> {profile.get('region', 'Unknown')}</p>"
            )
            card_content += (
                "<p><strong>Provider strategy:</strong> "
                "Tracker → Henrik → Riot</p>"
            )
            card_content += "</div>"
            st.markdown(card_content, unsafe_allow_html=True)

        with rank_col:
            st.markdown("### Rank")
            st.markdown(
                f"<div class='metric-card'><h4>{rank.get('tier_name', 'Unranked')}</h4>"
                f"<p style='color:#8b949e;'>Rank name: "
                f"{rank.get('rank_name') or 'Not available'}</p>"
                f"<p style='color:#8b949e;'>Points: "
                f"{rank.get('points') or '—'}</p></div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.subheader("Recent matches")
        matches = matches_payload.get("matches", [])
        if matches:
            frame = pd.DataFrame(matches)
            display_frame = frame[
                [
                    "map_name",
                    "mode",
                    "result",
                    "kills",
                    "deaths",
                    "assists",
                    "agent_name",
                ]
            ].copy()
            st.dataframe(display_frame, use_container_width=True, hide_index=True)
        else:
            st.info("No matches were returned for this player.")


def render_architecture_page() -> None:
    """Render an architectural overview of the system."""
    st.set_page_config(
        page_title="Architecture • Valorant AI Coach",
        page_icon="🧱",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Architecture",
        "A clean layered system where the UI stays independent from the service "
        "logic and communicates over HTTP.",
        eyebrow="SYSTEM DESIGN",
    )

    layers = [
        "Streamlit",
        "FastAPI",
        "PlayerService",
        "Provider SDK",
        "Riot",
        "Henrik",
        "Tracker",
    ]
    for index, layer in enumerate(layers):
        if index == len(layers) - 1:
            st.markdown(
                f"<div class='metric-card'><strong>{layer}</strong></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='metric-card'><strong>{layer}</strong><br>↓</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("Key ideas")
    bullets = [
        "Fallback automático: the backend tries Tracker, then Henrik, then Riot.",
        "Normalización: provider-specific data is converted into a unified "
        "domain model.",
        "Clean Architecture: business logic remains isolated from the transport "
        "layer.",
        "SOLID: services and providers follow a maintainable, testable "
        "structure.",
        "Dependency Injection: providers are wired at runtime through the "
        "application container.",
    ]
    for bullet in bullets:
        st.markdown(f"- {bullet}")


def render_roadmap_page() -> None:
    """Render a visual roadmap focused on the project milestones."""
    st.set_page_config(
        page_title="Roadmap • Valorant AI Coach",
        page_icon="🛣️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Roadmap",
        "A clear product roadmap that communicates progress from backend "
        "foundations to future AI-driven coaching features.",
        eyebrow="PRODUCT ROADMAP",
    )

    items = [
        ("Backend", 100),
        ("REST API", 100),
        ("Providers", 95),
        ("OCR", 35),
        ("Computer Vision", 25),
        ("LLM Coach", 20),
        ("Match Analyzer", 30),
        ("AI Recommendations", 15),
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=[name for name, _ in items],
                y=[value for _, value in items],
                marker_color="#f04f5f",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=330,
    )
    st.plotly_chart(fig, use_container_width=True)

    for name, progress in items:
        st.markdown(
            f"<div class='metric-card'><strong>{name}</strong>"
            f"<br>{'█' * int(progress / 10)} {progress}%</div>",
            unsafe_allow_html=True,
        )


def render_api_docs_page() -> None:
    """Render API documentation references and endpoint summary."""
    st.set_page_config(
        page_title="API Docs • Valorant AI Coach",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "API docs",
        "Open the backend references directly from the UI to present the "
        "interface alongside the API surface.",
        eyebrow="DOCS",
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.link_button("Swagger UI", "http://127.0.0.1:8000/docs")
    with col_b:
        st.link_button("ReDoc", "http://127.0.0.1:8000/redoc")
    with col_c:
        st.link_button("GitHub repository", "https://github.com/Siname22/ValorantAICoach")

    st.markdown("---")
    st.subheader("Available endpoints")
    endpoints = [
        ("GET /players/{game}/{tag}", "Player profile and enriched identity"),
        ("GET /players/{game}/{tag}/rank", "Competitive rank information"),
        ("GET /players/{game}/{tag}/matches", "Recent match history"),
    ]
    for endpoint, description in endpoints:
        st.markdown(
            f"<div class='metric-card'><strong>{endpoint}</strong>"
            f"<br>{description}</div>",
            unsafe_allow_html=True,
        )
