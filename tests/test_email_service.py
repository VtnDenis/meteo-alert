from __future__ import annotations

from src.email_service import EmailContent, build_resend_payload


def test_build_resend_payload() -> None:
    content = EmailContent(subject="s", text="t", html="<p>h</p>")
    payload = build_resend_payload("from@example.com", "to@example.com", content)

    assert payload["from"] == "from@example.com"
    assert payload["to"] == ["to@example.com"]
    assert payload["subject"] == "s"
    assert payload["text"] == "t"
    assert payload["html"] == "<p>h</p>"
