from __future__ import annotations

from html import escape

import streamlit as st


def apply_global_styles() -> None:
    """Shared presentation tokens for player data and coaching."""
    st.markdown(
        """
        <style>
        :root { color-scheme: dark; }
        *, *::before, *::after { box-sizing: border-box; }
        html, body, [class*="css"] {
            font-family: ui-sans-serif, system-ui, -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .stApp { background: #111214; }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1120px;
        }
        h1, h2, h3, h4 {
            letter-spacing: 0;
            color: #f4f7fb;
            overflow-wrap: anywhere;
        }
        h1 { font-size: 2rem; line-height: 1.25; }
        p, li { color: #b8c1cc; line-height: 1.6; }
        .page-header { margin-bottom: 1.5rem; }
        .page-header h1 {
            margin: 0 0 0.5rem;
            font-size: 2rem;
            line-height: 1.25;
        }
        .page-header p { margin: 0; }
        .hero-card, .metric-card, .nav-card {
            padding: 1rem;
            border: 1px solid #8b949e;
            border-radius: 6px;
            background: #1d1f20;
            margin-bottom: 1rem;
            min-width: 0;
            overflow-wrap: anywhere;
        }
        .pill {
            display: inline-block;
            font-size: 0.875rem;
            color: #b8c1cc;
            margin: 0 1rem 0.5rem 0;
        }
        [data-testid="stSidebar"] {
            background: #1d1f20;
            border-right: 1px solid #8b949e;
        }
        [data-testid="stMetricValue"] { color: #78c2ff; }
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            border-radius: 6px;
            min-height: 44px;
        }
        button[kind="primary"], button[kind="primaryFormSubmit"],
        button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
            background: #bd263f;
            border-color: #bd263f;
            color: #ffffff;
        }
        button:focus-visible, input:focus-visible, a:focus-visible {
            outline: 2px solid #f04f5f;
            outline-offset: 3px;
        }
        .stTextInput input, .stTextArea textarea {
            max-width: 100%;
            border: 1px solid #8b949e;
            border-radius: 6px;
            color: #f4f7fb;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #8b949e;
        }
        @media (max-width: 480px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Single navigation surface, collapsed automatically on narrow screens."""
    with st.sidebar:
        st.markdown("### Valorant AI Coach")
        st.page_link(
            "pages/2_Player_Search.py", label="Player search", icon=":material/search:"
        )
        st.page_link("pages/6_AI_Coach.py", label="AI coach", icon=":material/forum:")
        st.divider()
        st.page_link("pages/1_Home.py", label="Overview", icon=":material/home:")
        st.page_link(
            "pages/3_Architecture.py",
            label="Architecture",
            icon=":material/account_tree:",
        )
        st.page_link("pages/4_Roadmap.py", label="Roadmap", icon=":material/route:")
        st.page_link("pages/5_API_Docs.py", label="API docs", icon=":material/code:")


def apply_chat_styles() -> None:
    """Chat styling uses the same surface, border and typography tokens."""
    st.markdown(
        """
        <style>
        [data-testid="stChatMessage"] {
            border-radius: 6px;
            border: 1px solid #8b949e;
            background: #1d1f20;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] li { color: #b8c1cc; line-height: 1.6; }
        [data-testid="stChatMessage"] strong { color: #f4f7fb; }
        [data-testid="stChatMessage"] code {
            background: #111214;
            color: #78c2ff;
            border-radius: 4px;
            padding: 0.125rem 0.25rem;
        }
        [data-testid="stChatInput"] {
            border-radius: 6px;
            border: 1px solid #8b949e;
            background: #1d1f20;
        }
        [data-testid="stChatInput"] textarea { color: #f4f7fb; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, eyebrow: str = "") -> None:
    """Unframed header above the primary workspace."""
    eyebrow_html = f"<p>{escape(eyebrow)}</p>" if eyebrow else ""
    st.markdown(
        f"<header class='page-header'>{eyebrow_html}"
        f"<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></header>",
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, description: str | None = None) -> None:
    """Render a framed individual data item."""
    description_html = f"<p>{escape(description)}</p>" if description else ""
    st.markdown(
        f"<div class='metric-card'><div>{escape(title)}</div>"
        f"<strong>{escape(value)}</strong>{description_html}</div>",
        unsafe_allow_html=True,
    )
