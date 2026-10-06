from __future__ import annotations

import logging
import sys
from contextlib import closing, suppress
from html import escape
from pathlib import Path

# Guarantees `utils` stays importable even when this module is loaded before the
# Streamlit entrypoint has registered the app directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from utils.api_client import APIClientError, get_api_client  # noqa: E402
from utils.avatar import external_avatar_url  # noqa: E402
from utils.coach_persona import (  # noqa: E402
    COACH_TAGLINE,
    build_system_prompt,
    get_starter_prompts,
    get_welcome_message,
)
from utils.config import get_api_base_url  # noqa: E402
from utils.gemini_client import (  # noqa: E402
    MAX_INPUT_CHARS,
    MSG_INPUT_TOO_LONG,
    MSG_MISSING_KEY,
    MSG_UNEXPECTED,
    ROLE_ASSISTANT,
    ROLE_USER,
    ChatMessage,
    GeminiClientError,
    GeminiConfigurationError,
    get_gemini_client,
    get_model_chain,
    get_model_name,
    is_configured,
    trim_chat_history,
)
from utils.ui import (  # noqa: E402
    apply_chat_styles,
    apply_global_styles,
    render_page_header,
    render_sidebar,
)

logger = logging.getLogger(__name__)


def render_home_page() -> None:
    """Render the landing experience for the university demo."""
    st.set_page_config(
        page_title="Valorant AI Coach",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="auto",
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
        initial_sidebar_state="auto",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Valorant AI Coach",
        "Player search",
        eyebrow="",
    )

    with st.form("player_search"):
        name_col, tag_col = st.columns([2, 1])
        with name_col:
            game_name = st.text_input("Game name", value="TestPlayer")
        with tag_col:
            tag_line = st.text_input("Tag line", value="NA1")
        submitted = st.form_submit_button(
            "Search player", type="primary", icon=":material/search:"
        )

    if submitted:
        game_name = game_name.strip()
        tag_line = tag_line.strip()
        if not game_name or not tag_line:
            st.warning("Please provide both a game name and a tag line.")
            return

        result = {
            "game_name": game_name,
            "tag_line": tag_line,
            "profile": None,
            "rank": None,
            "matches_payload": None,
            "error": None,
        }
        client = get_api_client()
        with st.spinner("Querying the backend API..."):
            try:
                result["profile"] = client.get_player_profile(game_name, tag_line)
            except APIClientError as exc:
                result["error"] = str(exc)
            else:
                with suppress(APIClientError):
                    result["rank"] = client.get_player_rank(game_name, tag_line)
                with suppress(APIClientError):
                    result["matches_payload"] = client.get_player_matches(
                        game_name, tag_line
                    )
        st.session_state["player_search_result"] = result

    result = st.session_state.get("player_search_result")
    if result is None:
        return
    if result["error"] is not None:
        st.error(result["error"])
        st.info(
            "Ensure the FastAPI backend is running at the configured "
            "URL before using the demo."
        )
        return

    profile = result["profile"]
    rank = result["rank"]
    matches_payload = result["matches_payload"]
    if rank is not None and matches_payload is not None:
        st.success("Player data retrieved successfully.")
    else:
        st.success("Player profile retrieved successfully.")
    profile_col, rank_col = st.columns([1.5, 0.8], vertical_alignment="top")
    with profile_col:
        st.markdown("### Profile")
        card_content = "<div class='hero-card'>"
        avatar_url = external_avatar_url(profile.get("avatar_url"))
        if avatar_url:
            st.image(avatar_url, width=120)
        else:
            st.markdown(
                "<div style='width:120px;height:120px;border-radius:16px;"
                "background:#161b22;border:1px dashed #30363d;"
                "display:flex;align-items:center;justify-content:center;"
                "color:#8b949e;'>Avatar placeholder</div>",
                unsafe_allow_html=True,
            )
        card_content += (
            f"<h3>{escape(str(profile.get('game_name', result['game_name'])))}#"
            f"{escape(str(profile.get('tag_line', result['tag_line'])))}</h3>"
        )
        card_content += (
            f"<p><strong>Level:</strong> "
            f"{escape(str(profile.get('account_level', 'Unknown')))}</p>"
        )
        card_content += (
            f"<p><strong>Region:</strong> "
            f"{escape(str(profile.get('region', 'Unknown')))}</p>"
        )
        card_content += (
            "<p><strong>Provider strategy:</strong> " "Tracker → Henrik → Riot</p>"
        )
        card_content += "</div>"
        st.markdown(card_content, unsafe_allow_html=True)

    with rank_col:
        st.markdown("### Rank")
        if rank is None:
            st.warning("Rank is currently unavailable. Please try again.")
        else:
            points = rank.get("points")
            points_label = escape(str(points)) if points is not None else "—"
            st.markdown(
                f"<div class='metric-card'><h4>"
                f"{escape(str(rank.get('tier_name', 'Unranked')))}</h4>"
                f"<p style='color:#8b949e;'>Rank name: "
                f"{escape(str(rank.get('rank_name') or 'Not available'))}</p>"
                f"<p style='color:#8b949e;'>Points: {points_label}</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("Recent matches")
    if matches_payload is None:
        st.warning("Recent matches are currently unavailable. Please try again.")
    else:
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
        initial_sidebar_state="auto",
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
        "SOLID: services and providers follow a maintainable, testable " "structure.",
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
        initial_sidebar_state="auto",
    )
    apply_global_styles()
    render_sidebar()

    render_page_header(
        "Roadmap",
        "A clear product roadmap that communicates progress from backend "
        "foundations to future AI-driven coaching features.",
        eyebrow="PRODUCT ROADMAP",
    )

    milestones = [
        (
            "Provider API and player lookup",
            "Integrated; live credentials pending",
            "2026-10-12",
        ),
        ("Persistence and refresh policy", "Not implemented", "2026-10-23"),
        ("Grounded personalized coaching", "Not implemented", "2026-11-06"),
        ("Authentication, jobs and agent memory", "Not implemented", "2026-11-13"),
        ("OCR and tactical timeline", "Not implemented", "2026-11-20"),
        ("Production release candidate", "Not deployed", "2026-11-30"),
        ("Final delivery", "Planned", "2026-12-10"),
    ]
    st.dataframe(
        pd.DataFrame(milestones, columns=["Milestone", "Status", "Target"]),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Target dates are planning checkpoints, not delivery guarantees.")


def render_api_docs_page() -> None:
    """Render API documentation references and endpoint summary."""
    st.set_page_config(
        page_title="API Docs • Valorant AI Coach",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="auto",
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
    base_url = get_api_base_url()
    with col_a:
        st.link_button("Swagger UI", f"{base_url}/docs")
    with col_b:
        st.link_button("ReDoc", f"{base_url}/redoc")
    with col_c:
        st.link_button(
            "GitHub repository", "https://github.com/Siname22/ValorantAICoach"
        )

    st.markdown("---")
    st.subheader("Available endpoints")
    endpoints = [
        ("GET /players/{game}/{tag}", "Player profile and enriched identity"),
        ("GET /players/{game}/{tag}/rank", "Competitive rank information"),
        ("GET /players/{game}/{tag}/matches", "Recent match history"),
        ("GET /players/{game}/{tag}/stats", "Tracker lifetime statistics"),
        ("GET /players/{game}/{tag}/overview", "Identity and available optional data"),
        ("GET /matches/{match_id}", "Riot match details"),
        ("GET /health/live", "Application liveness"),
    ]
    for endpoint, description in endpoints:
        st.markdown(
            f"<div class='metric-card'><strong>{endpoint}</strong>"
            f"<br>{description}</div>",
            unsafe_allow_html=True,
        )


def _render_coach_setup_notice() -> None:
    """Explain how to enable the chatbot when no API key is configured."""
    st.warning(
        f"{MSG_MISSING_KEY} "
        "El resto de la aplicación sigue funcionando con normalidad sin ella.",
        icon="🔑",
    )
    st.markdown(
        "<div class='metric-card'>"
        "<strong>Enable the assistant in three steps</strong>"
        "<ol style='margin:0.5rem 0 0; padding-left:1.2rem; color:#a7b2bf;'>"
        "<li>Create a free API key in Google AI Studio.</li>"
        "<li>Add <code>GEMINI_API_KEY</code> to <code>.streamlit/secrets.toml</code> "
        "locally, or to the app secrets in Streamlit Community Cloud.</li>"
        "<li>Reload this page.</li></ol></div>",
        unsafe_allow_html=True,
    )
    with st.expander("secrets.toml template"):
        st.code(
            'GEMINI_API_KEY = "your_key_here"\n' 'GEMINI_MODEL = "gemini-2.5-flash"',
            language="toml",
        )
    st.link_button("Open Google AI Studio", "https://aistudio.google.com/apikey")
    st.caption("Full walkthrough: docs/chatbot_installation.md in the repository.")


def _render_coach_messages(
    messages: list[ChatMessage], fallback_model: str | None = None
) -> None:
    for index, message in enumerate(messages):
        avatar = "🤖" if message.role == ROLE_ASSISTANT else "🎯"
        with st.chat_message(message.role, avatar=avatar):
            st.markdown(message.content)
            if fallback_model and index == len(messages) - 1:
                st.caption(f"Respondido por el modelo de respaldo: {fallback_model}")


def render_ai_coach_page() -> None:
    """Render the Gemini-powered coaching assistant."""
    st.set_page_config(
        page_title="AI Coach • Valorant AI Coach",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="auto",
    )
    apply_global_styles()
    apply_chat_styles()
    render_sidebar()

    render_page_header(
        "AI Coach assistant",
        COACH_TAGLINE,
        eyebrow="AI ASSISTANT",
    )

    if not is_configured():
        st.markdown("")
        _render_coach_setup_notice()
        return

    if "coach_messages" not in st.session_state:
        st.session_state.coach_messages = [
            ChatMessage(role=ROLE_ASSISTANT, content=get_welcome_message())
        ]
    st.session_state.coach_messages = trim_chat_history(st.session_state.coach_messages)

    header_cols = st.columns([2.4, 0.8, 0.8], vertical_alignment="center")
    with header_cols[0]:
        fallback_count = max(len(get_model_chain()) - 1, 0)
        st.markdown(
            f"<div class='pill'>Google AI Studio</div>"
            f"<div class='pill'>{get_model_name()}</div>"
            f"<div class='pill'>+{fallback_count} modelos de respaldo</div>"
            f"<div class='pill'>Silver → Platinum focus</div>",
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        turns = sum(
            1
            for message in st.session_state.coach_messages
            if message.role == ROLE_USER
        )
        st.markdown(
            f"<div class='metric-card' style='margin:0;'>"
            f"<div style='font-size:0.72rem; text-transform:uppercase; "
            f"letter-spacing:.12em; color:#8b949e;'>Questions</div>"
            f"<div style='font-size:1.25rem; font-weight:700; color:#f4f7fb;'>"
            f"{turns}</div></div>",
            unsafe_allow_html=True,
        )
    with header_cols[2]:
        if st.button("Reset chat", use_container_width=True):
            st.session_state.coach_messages = [
                ChatMessage(role=ROLE_ASSISTANT, content=get_welcome_message())
            ]
            st.session_state.pop("coach_pending_prompt", None)
            st.rerun()

    st.markdown("")

    if len(st.session_state.coach_messages) == 1:
        st.caption("Suggested questions")
        starter_cols = st.columns(2)
        for index, starter in enumerate(get_starter_prompts()):
            with starter_cols[index % 2]:
                if st.button(starter, key=f"starter_{index}", use_container_width=True):
                    st.session_state.coach_pending_prompt = starter
                    st.rerun()

    typed_prompt = st.chat_input(
        "Ask your Valorant coach anything…", max_chars=MAX_INPUT_CHARS
    )
    prompt = st.session_state.pop("coach_pending_prompt", None) or typed_prompt

    if prompt and len(prompt) > MAX_INPUT_CHARS:
        _render_coach_messages(st.session_state.coach_messages)
        st.error(MSG_INPUT_TOO_LONG, icon="⚠️")
        return

    if prompt:
        st.session_state.coach_messages.append(
            ChatMessage(role=ROLE_USER, content=prompt)
        )
        st.session_state.coach_messages = trim_chat_history(
            st.session_state.coach_messages
        )
    _render_coach_messages(
        st.session_state.coach_messages,
        fallback_model=st.session_state.pop("coach_fallback_model", None),
    )
    if not prompt:
        return

    # The history excludes the turn just appended: the SDK receives it as the
    # message being sent, not as part of the previous conversation.
    history = st.session_state.coach_messages[:-1]
    with st.chat_message(ROLE_ASSISTANT, avatar="🤖"):
        with st.spinner("Analysing the situation…"):
            try:
                with closing(get_gemini_client(build_system_prompt())) as client:
                    reply = client.send_message(prompt, history=history)
            except GeminiConfigurationError as exc:
                st.error(str(exc), icon="🔑")
                st.session_state.coach_messages.pop()
                return
            except GeminiClientError as exc:
                st.error(str(exc), icon="⚠️")
                st.session_state.coach_messages.pop()
                return
            except Exception as exc:  # noqa: BLE001 - last line of defence
                # The client classifies known failures; keep unforeseen bugs
                # from rendering a traceback in a public deployment.
                logger.error(
                    "Unhandled failure while contacting the coach: %s",
                    type(exc).__name__,
                )
                st.error(MSG_UNEXPECTED, icon="⚠️")
                st.session_state.coach_messages.pop()
                return
        st.markdown(reply)
        # Surfaced only when fallback leaves the configured model.
        if client.active_model != client.model:
            st.caption(f"Respondido por el modelo de respaldo: {client.active_model}")

    response_message = ChatMessage(role=ROLE_ASSISTANT, content=reply)
    st.session_state.coach_messages.append(response_message)
    retained = trim_chat_history(st.session_state.coach_messages)
    trimmed = len(retained) < len(st.session_state.coach_messages)
    st.session_state.coach_messages = retained
    if trimmed:
        if (
            client.active_model != client.model
            and retained
            and retained[-1] is response_message
        ):
            st.session_state.coach_fallback_model = client.active_model
        st.rerun()
