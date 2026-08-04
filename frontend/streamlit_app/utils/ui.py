from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Apply the custom dark theme used throughout the demo."""
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
        }
        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .stApp {
            background:
                radial-gradient(
                    circle at top left,
                    rgba(240, 79, 95, 0.16),
                    transparent 24%,
                ),
                radial-gradient(
                    circle at 85% 10%,
                    rgba(77, 173, 255, 0.16),
                    transparent 28%,
                ),
                linear-gradient(135deg, #03050a 0%, #0b1119 45%, #070b12 100%);
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3.2rem;
            max-width: 1320px;
        }
        h1, h2, h3, h4 {
            letter-spacing: -0.02em;
            color: #f4f7fb;
        }
        p, li, .stTextInput, .stTextArea, .stSelectbox {
            color: #b8c1cc;
        }
        .hero-card {
            padding: 1.5rem 1.65rem;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            background: linear-gradient(
                135deg,
                rgba(255,255,255,0.06),
                rgba(255,255,255,0.03)
            );
            box-shadow: 0 22px 60px rgba(0, 0, 0, 0.32);
            backdrop-filter: blur(16px);
            position: relative;
            overflow: hidden;
        }
        .hero-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(
                90deg,
                rgba(240, 79, 95, 0.18),
                transparent 35%,
                rgba(77, 173, 255, 0.16)
            );
            pointer-events: none;
        }
        .metric-card {
            padding: 1rem 1.1rem;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
            margin-bottom: 0.75rem;
        }
        .pill {
            display: inline-block;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            font-size: 0.9rem;
            margin-right: 0.45rem;
            margin-bottom: 0.45rem;
            background: rgba(255,255,255,0.08);
            color: #e5ecf4;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .nav-card {
            padding: 0.85rem 0.9rem;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(
                135deg,
                rgba(255,255,255,0.06),
                rgba(255,255,255,0.03)
            );
            margin-bottom: 0.7rem;
        }
        [data-testid="stSidebar"] {
            background: rgba(3, 7, 11, 0.96);
            border-right: 1px solid rgba(255,255,255,0.08);
        }
        [data-testid="stSidebarNav"] {
            background: transparent;
        }
        [data-testid="stMetricValue"] {
            color: #78c2ff;
            font-weight: 700;
        }
        .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(240,79,95,0.35);
            background: linear-gradient(135deg, #f04f5f, #ff6d6d);
            color: white;
            padding: 0.55rem 1rem;
            font-weight: 600;
        }
        .stButton > button:hover {
            border-color: rgba(255,255,255,0.25);
            box-shadow: 0 10px 24px rgba(240,79,95,0.28);
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 12px !important;
            color: #f4f7fb !important;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render a polished sidebar navigation for the demo pages."""
    with st.sidebar:
        st.markdown(
            "<div class='nav-card'><div style='font-size:1rem; font-weight:700;'>"
            "VALORANT AI COACH</div><div style='color:#8b949e; "
            "font-size:0.85rem;'>Professional demo • Streamlit</div></div>",
            unsafe_allow_html=True,
        )
        st.page_link("pages/1_Home.py", label="Home", icon="🏠")
        st.page_link("pages/2_Player_Search.py", label="Player Search", icon="🎯")
        st.page_link("pages/3_Architecture.py", label="Architecture", icon="🏗️")
        st.page_link("pages/4_Roadmap.py", label="Roadmap", icon="🗺️")
        st.page_link("pages/5_API_Docs.py", label="API Docs", icon="📚")
        st.markdown("---")
        st.markdown(
            "<div class='nav-card'><div style='font-size:0.9rem; font-weight:700;'>"
            "API bridge</div><div style='color:#8b949e; font-size:0.82rem;'>"
            "The UI consumes FastAPI endpoints only.</div></div>",
            unsafe_allow_html=True,
        )


def render_page_header(
    title: str,
    subtitle: str,
    eyebrow: str = "PRODUCT DEMO",
) -> None:
    """Render a consistent hero header for the presentation pages."""
    st.markdown(
        f"<div class='hero-card'><div class='pill'>{eyebrow}</div>"
        f"<h1 style='margin:0.25rem 0 0.4rem;'>{title}</h1>"
        f"<p style='margin:0; color:#a7b2bf; line-height:1.6;'>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, description: str | None = None) -> None:
    """Render a compact metric card inside the SaaS-style layout."""
    description_html = (
        f"<div style='color:#8b949e; margin-top:0.35rem;'>{description}</div>"
        if description
        else ""
    )
    st.markdown(
        f"<div class='metric-card'><div style='font-size:0.8rem; "
        f"text-transform:uppercase; letter-spacing:.12em; color:#8b949e;'>{title}</div>"
        f"<div style='font-size:1.4rem; font-weight:700; color:#f4f7fb; "
        f"margin-top:0.25rem;'>{value}</div>{description_html}</div>",
        unsafe_allow_html=True,
    )
