from fastapi.testclient import TestClient

from src.api.app import app
from src.templates.config import reset_template_cache


def test_health(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "matchmaking")
    reset_template_cache()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_template_route(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    reset_template_cache()
    client = TestClient(app)

    response = client.get("/api/config/template")

    assert response.status_code == 200
    assert response.json()["template"]["template"]["id"] == "education"


def test_chat_uses_template_fallback(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    reset_template_cache()
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"question": "hello", "accountId": "u1", "profile": {"student_grade": "Grade 8"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == "education"
    assert payload["next_field"]["key"] == "subject"
    assert "subject" in payload["response"].lower()


def test_chat_asks_contact_after_required_fields(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    reset_template_cache()
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={
            "question": "I want a trial class",
            "accountId": "contact-after-required-user",
            "profile": {"student_grade": "Grade 8", "subject": "Math"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_field"]["key"] == "phone"
    assert "phone" in payload["response"].lower()


def test_chat_uses_template_faq(monkeypatch):
    monkeypatch.setenv("ACTIVE_TEMPLATE", "education")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    reset_template_cache()
    client = TestClient(app)

    response = client.post(
        "/api/chat",
        json={"question": "How much is the tuition?", "accountId": "faq-user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Course pricing depends" in payload["response"]
    assert payload["next_field"]["key"] == "student_grade"
