import json

import pytest
from fastapi.testclient import TestClient

from api import index as api


@pytest.fixture(scope="module")
def client():
    with TestClient(api.app) as c:   # lifespan: builds the chatbot on sample data
        yield c


def collect(ws, message):
    ws.send_text(json.dumps({"message": message}))
    events = []
    while True:
        ev = json.loads(ws.receive_text())
        events.append(ev)
        if ev["type"] in ("bot_complete", "error"):
            return events


def test_health_reports_ready_and_offline(client):
    body = client.get("/health").json()
    assert body["status"] == "healthy" and body["chatbot_ready"] and body["offline_demo"]


def test_index_and_static_served(client):
    assert "Flu Akademi" in client.get("/").text
    assert client.get("/static/styles.css").status_code == 200


def test_websocket_streams_a_full_answer(client):
    with client.websocket_connect("/ws/chat") as ws:
        types = [e["type"] for e in collect(ws, "Tarım devrimi insanlığı nasıl etkiledi?")]
    assert types[0] == "bot_thinking" and types[1] == "bot_start"
    assert types.count("bot_chunk") >= 1 and types[-1] == "bot_complete"


def test_streamed_chunks_add_up_to_the_final_answer(client):
    with client.websocket_connect("/ws/chat") as ws:
        events = collect(ws, "Neolitik Devrim nedir?")
    chunks = "".join(e["content"] for e in events if e["type"] == "bot_chunk")
    assert chunks == events[-1]["content"]


def test_invalid_json_is_rejected_without_closing(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("not json")
        assert json.loads(ws.receive_text())["type"] == "error"
        assert collect(ws, "Neolitik Devrim nedir?")[-1]["type"] == "bot_complete"


def test_too_long_message_rejected(client):
    with client.websocket_connect("/ws/chat") as ws:
        ev = collect(ws, "a" * (api.MAX_MESSAGE_CHARS + 1))
    assert ev[-1]["type"] == "error" and "uzun" in ev[-1]["content"]


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(api, "RATE_LIMIT_MESSAGES", 2)
    with client.websocket_connect("/ws/chat") as ws:
        results = [collect(ws, "Neolitik Devrim nedir?")[-1]["type"] for _ in range(3)]
    assert results == ["bot_complete", "bot_complete", "error"]


def test_generation_errors_do_not_leak_details(client, monkeypatch):
    def broken(_):
        raise RuntimeError("secret internal detail")
        yield  # pragma: no cover

    monkeypatch.setattr(api.chatbot, "ask_question_agentic_stream", broken)
    with client.websocket_connect("/ws/chat") as ws:
        ev = collect(ws, "Neolitik Devrim nedir?")[-1]
    assert ev["type"] == "error" and "secret" not in ev["content"]
