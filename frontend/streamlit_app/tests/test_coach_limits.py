from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import requests
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
from utils import gemini_client as gc  # noqa: E402


@pytest.fixture
def coach_http(monkeypatch):
    transport = SimpleNamespace(
        requests=[], text="Reply", status=200, reject_primary=False
    )

    def send(self, request, **kwargs):
        assert request.url.host == "generativelanguage.googleapis.com"
        transport.requests.append(json.loads(request.content))
        status = (
            404
            if transport.reject_primary and "gemini-2.5-flash:" in request.url.path
            else transport.status
        )
        payload = (
            {
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": transport.text}]}}
                ]
            }
            if status == 200
            else {"error": {"code": status, "message": "Simulated failure"}}
        )
        return httpx.Response(status, request=request, json=payload)

    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected external HTTP request")

    monkeypatch.setattr(httpx.Client, "send", send)
    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setenv("GEMINI_MODEL", gc.DEFAULT_MODEL)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    return transport


@pytest.fixture
def coach_app(coach_http):
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=10)
    app.secrets["GEMINI_API_KEY"] = "test-key"
    app.secrets["GEMINI_MODEL"] = gc.DEFAULT_MODEL
    app.run().switch_page("pages/6_AI_Coach.py").run()
    assert not app.exception, [item.message for item in app.exception]
    assert len(app.chat_input) == 1
    return app


# A client bypassing the UI must not spend a request on an oversized prompt.
@pytest.mark.parametrize(
    "prompt", ["x" * 4001, " " + "x" * 3999 + " "], ids=["oversized", "padded"]
)
def test_client_rejects_oversized_input_before_http(coach_http, prompt):
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        with pytest.raises(gc.GeminiClientError, match="4000"):
            client.send_message(prompt)
    finally:
        client.close()
    assert coach_http.requests == []


# The character cap must accept exactly 4000 characters, including Unicode.
@pytest.mark.parametrize(
    "prompt", ["x" * 4000, chr(0x1F3AF) * 4000], ids=["ascii", "unicode"]
)
def test_client_accepts_input_at_character_limit_without_changing_it(
    coach_http, prompt
):
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message(prompt) == "Reply"
    finally:
        client.close()
    assert len(coach_http.requests) == 1
    assert coach_http.requests[0]["contents"] == [
        {"role": "user", "parts": [{"text": prompt}]}
    ]


# A missing widget cap would let users enter more text than the client accepts.
def test_chat_widget_caps_input_and_accepts_the_exact_limit(coach_app, coach_http):
    assert coach_app.chat_input[0].proto.max_chars == 4000
    prompt = "x" * 4000
    coach_app.chat_input[0].set_value(prompt).run()
    assert not coach_app.exception
    assert not coach_app.error
    assert [
        message.content for message in coach_app.session_state.coach_messages[1:]
    ] == [
        prompt,
        "Reply",
    ]
    assert len(coach_http.requests) == 1


# Neither a forged widget submission nor a queued starter may bypass the UI cap.
@pytest.mark.parametrize("source", ["typed", "pending"])
def test_ui_rejects_oversized_input_without_retaining_a_turn(
    coach_app, coach_http, source
):
    greeting = list(coach_app.session_state.coach_messages)
    if source == "typed":
        coach_app.chat_input[0].set_value("x" * 4001).run()
    else:
        coach_app.session_state.coach_pending_prompt = "x" * 4001
        coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == greeting
    assert coach_http.requests == []
    assert "coach_pending_prompt" not in coach_app.session_state
    assert len(coach_app.error) == 1
    assert "4000" in coach_app.error[0].value
    coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == greeting
    assert coach_http.requests == []


def exchanges(count):
    messages = []
    for number in range(1, count + 1):
        messages.extend(
            [
                gc.ChatMessage("user", f"Question {number}"),
                gc.ChatMessage("assistant", f"Answer {number}"),
            ]
        )
    return messages


# Taking the last 20 messages discards half the approved 20 exchanges.
@pytest.mark.parametrize("greeting", [[], [gc.ChatMessage("assistant", "Greeting")]])
def test_client_sends_twenty_complete_exchanges_without_mutating_history(
    coach_http, greeting
):
    history = greeting + exchanges(21)
    original = list(history)
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message("Question 22", history=history) == "Reply"
    finally:
        client.close()
    assert history == original
    contents = coach_http.requests[0]["contents"]
    assert len(contents) == 41 + len(greeting)
    assert [item["role"] for item in contents] == (
        (["model"] if greeting else []) + ["user", "model"] * 20 + ["user"]
    )
    assert contents[len(greeting)]["parts"][0]["text"] == "Question 2"
    assert contents[-2]["parts"][0]["text"] == "Answer 21"
    assert contents[-1]["parts"][0]["text"] == "Question 22"


# Session retention and rendered messages must be capped on reruns and success.
def test_ui_trims_old_complete_pairs_before_rendering_and_after_success(
    coach_app, coach_http
):
    greeting = gc.ChatMessage("assistant", "Greeting")
    coach_app.session_state.coach_messages = [greeting] + exchanges(21)
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_app.session_state.coach_messages) == 41
    assert len(coach_app.chat_message) == 41
    assert coach_app.session_state.coach_messages[0] == greeting
    assert coach_app.chat_message[1].markdown[0].value == "Question 2"
    assert coach_http.requests == []

    coach_app.chat_input[0].set_value("Question 22").run()
    assert not coach_app.exception
    assert not coach_app.error
    assert len(coach_app.session_state.coach_messages) == 41
    assert len(coach_app.chat_message) == 41
    assert coach_app.session_state.coach_messages[1].content == "Question 3"
    assert [
        message.content for message in coach_app.session_state.coach_messages[-2:]
    ] == [
        "Question 22",
        "Reply",
    ]
    assert len(coach_http.requests[0]["contents"]) == 42
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_app.chat_message) == 41
    assert coach_app.chat_message[1].markdown[0].value == "Question 3"
    assert len(coach_http.requests) == 1


# Trimming must not leave a failed user turn or remove a completed answer.
@pytest.mark.parametrize("failure", ["authentication", "request", "empty_reply"])
def test_failed_pending_turn_is_removed_and_next_success_remains_bounded(
    coach_app, coach_http, failure
):
    original = [gc.ChatMessage("assistant", "Greeting")] + exchanges(20)
    coach_app.session_state.coach_messages = list(original)
    coach_http.status = {"authentication": 401, "request": 400}.get(failure, 200)
    coach_http.text = "" if failure == "empty_reply" else "Reply"
    coach_app.session_state.coach_pending_prompt = "Failed question"
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_app.error) == 1
    assert coach_app.session_state.coach_messages == original
    assert "coach_pending_prompt" not in coach_app.session_state
    assert len(coach_http.requests) == 1
    coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == original
    assert len(coach_http.requests) == 1

    coach_http.status = 200
    coach_http.text = "Recovered reply"
    coach_app.chat_input[0].set_value("Recovered question").run()
    assert not coach_app.exception
    assert not coach_app.error
    assert len(coach_app.session_state.coach_messages) == 41
    assert coach_app.session_state.coach_messages[1].content == "Question 2"
    assert [
        message.content for message in coach_app.session_state.coach_messages[-2:]
    ] == [
        "Recovered question",
        "Recovered reply",
    ]


# Reset must also clear a queued turn so it cannot be sent after the rerun.
def test_reset_clears_retained_conversation_and_pending_prompt(coach_app, coach_http):
    greeting = list(coach_app.session_state.coach_messages)
    coach_app.session_state.coach_messages = greeting + exchanges(20)
    coach_app.session_state.coach_pending_prompt = "Queued question"
    coach_app.button[0].click().run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == greeting
    assert "coach_pending_prompt" not in coach_app.session_state
    assert len(coach_app.chat_message) == 1
    assert coach_http.requests == []


# The bounded rerun must preserve fallback feedback without resending the prompt.
def test_bounded_rerun_keeps_fallback_caption_without_another_request(
    coach_app, coach_http
):
    coach_app.session_state.coach_messages = [
        gc.ChatMessage("assistant", "Greeting")
    ] + exchanges(20)
    coach_http.reject_primary = True
    coach_app.chat_input[0].set_value("Question 21").run()
    assert not coach_app.exception
    assert not coach_app.error
    assert len(coach_app.chat_message) == 41
    assert len(coach_http.requests) == 2
    assert any("gemini-2.5-flash-lite" in item.value for item in coach_app.caption)
    assert "coach_pending_prompt" not in coach_app.session_state
    assert "coach_fallback_model" not in coach_app.session_state
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_http.requests) == 2
    assert not any("gemini-2.5-flash-lite" in item.value for item in coach_app.caption)


def large_history():
    return [
        gc.ChatMessage("assistant", "Greeting"),
        gc.ChatMessage("user", "Old question"),
        gc.ChatMessage("assistant", "O" * 60000),
        gc.ChatMessage("user", chr(0x1F3AF) * 1000),
        gc.ChatMessage("assistant", "R" * 60000),
        gc.ChatMessage("user", "New question"),
        gc.ChatMessage("assistant", "N" * 9000),
    ]


# Counting characters instead of UTF-8 bytes would retain all three pairs.
def test_client_byte_budget_trims_old_pairs_and_keeps_unicode_intact(coach_http):
    history = large_history()
    original = list(history)
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message("Next question", history=history) == "Reply"
    finally:
        client.close()
    assert history == original
    contents = coach_http.requests[0]["contents"]
    assert len(contents) == 6
    assert [item["role"] for item in contents] == [
        "model",
        "user",
        "model",
        "user",
        "model",
        "user",
    ]
    assert contents[1]["parts"][0]["text"] == chr(0x1F3AF) * 1000
    assert contents[2]["parts"][0]["text"] == "R" * 60000
    assert contents[3]["parts"][0]["text"] == "New question"
    assert contents[4]["parts"][0]["text"] == "N" * 9000


# The same budget must apply to retained state before rendering, even on reruns.
def test_ui_byte_budget_trims_old_pairs_before_rendering(coach_app, coach_http):
    coach_app.session_state.coach_messages = large_history()
    coach_app.run()
    assert not coach_app.exception
    retained = coach_app.session_state.coach_messages
    assert len(retained) == 5
    assert [message.role for message in retained] == [
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert retained[0].content == "Greeting"
    assert retained[1].content == chr(0x1F3AF) * 1000
    assert retained[2].content == "R" * 60000
    assert retained[3].content == "New question"
    assert retained[4].content == "N" * 9000
    assert sum(len(message.content.encode("utf-8")) for message in retained) <= 131072
    assert len(coach_app.chat_message) == 5
    assert coach_app.chat_message[1].markdown[0].value == chr(0x1F3AF) * 1000
    assert coach_http.requests == []
    coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == retained
    assert coach_http.requests == []


# The outbound budget includes the new input, with an inclusive byte boundary.
@pytest.mark.parametrize("answer_bytes", [131069, 131070], ids=["exact", "over"])
def test_client_byte_budget_includes_pending_input(coach_http, answer_bytes):
    history = [
        gc.ChatMessage("assistant", "G"),
        gc.ChatMessage("user", "Q"),
        gc.ChatMessage("assistant", "A" * answer_bytes),
    ]
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message("N", history=history) == "Reply"
    finally:
        client.close()
    contents = coach_http.requests[0]["contents"]
    assert len(contents) == (4 if answer_bytes == 131069 else 2)
    assert contents[0]["parts"][0]["text"] == "G"
    assert contents[-1]["parts"][0]["text"] == "N"
    if answer_bytes == 131069:
        assert contents[1]["parts"][0]["text"] == "Q"
        assert contents[2]["parts"][0]["text"] == "A" * 131069


# A retained history at exactly 128 KiB fits; one byte more drops the whole pair.
@pytest.mark.parametrize("answer_bytes", [131070, 131071], ids=["exact", "over"])
def test_ui_byte_budget_has_an_inclusive_boundary(coach_app, answer_bytes):
    greeting = gc.ChatMessage("assistant", "G")
    history = [
        greeting,
        gc.ChatMessage("user", "Q"),
        gc.ChatMessage("assistant", "A" * answer_bytes),
    ]
    coach_app.session_state.coach_messages = list(history)
    coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == (
        history if answer_bytes == 131070 else [greeting]
    )
    assert len(coach_app.chat_message) == (3 if answer_bytes == 131070 else 1)


# A failed pending turn must still be the last item removed after byte trimming.
def test_ui_byte_budget_preserves_failed_pending_cleanup(coach_app, coach_http):
    greeting = gc.ChatMessage("assistant", "G")
    coach_app.session_state.coach_messages = [
        greeting,
        gc.ChatMessage("user", "old"),
        gc.ChatMessage("assistant", "A" * 131067),
    ]
    coach_http.status = 401
    coach_app.session_state.coach_pending_prompt = "pending"
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_app.error) == 1
    assert coach_app.session_state.coach_messages == [greeting]
    assert "coach_pending_prompt" not in coach_app.session_state
    assert coach_http.requests[0]["contents"] == [
        {"role": "model", "parts": [{"text": "G"}]},
        {"role": "user", "parts": [{"text": "pending"}]},
    ]
    coach_app.run()
    assert not coach_app.exception
    assert coach_app.session_state.coach_messages == [greeting]
    assert len(coach_http.requests) == 1


# A single oversized reply must never leave its user message retained alone.
def test_ui_byte_budget_drops_an_oversized_reply_as_a_complete_pair(
    coach_app, coach_http
):
    greeting = list(coach_app.session_state.coach_messages)
    coach_app.session_state.coach_messages = greeting + exchanges(1)
    coach_http.text = "R" * 131073
    coach_app.chat_input[0].set_value("Question 2").run()
    assert not coach_app.exception
    assert not coach_app.error
    assert coach_app.session_state.coach_messages == greeting
    assert len(coach_app.chat_message) == 1
    coach_app.run()
    assert not coach_app.exception
    assert len(coach_app.chat_message) == 1
    assert len(coach_http.requests) == 1


# An oversized optional greeting must not force valid exchanges out of history.
def test_client_byte_budget_drops_oversized_greeting_but_keeps_the_exchange(coach_http):
    history = [
        gc.ChatMessage("assistant", "G" * 131073),
        gc.ChatMessage("user", "Q"),
        gc.ChatMessage("assistant", "A"),
    ]
    client = gc.GeminiCoachClient("test instruction", api_key="test-key")
    try:
        assert client.send_message("N", history=history) == "Reply"
    finally:
        client.close()
    assert coach_http.requests[0]["contents"] == [
        {"role": "user", "parts": [{"text": "Q"}]},
        {"role": "model", "parts": [{"text": "A"}]},
        {"role": "user", "parts": [{"text": "N"}]},
    ]
