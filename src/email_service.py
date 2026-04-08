from __future__ import annotations

from dataclasses import dataclass

import requests

_RESEND_SEND_EMAIL_URL = "https://api.resend.com/emails"


@dataclass(frozen=True, slots=True)
class EmailContent:
    subject: str
    text: str
    html: str


def build_resend_payload(from_email: str, to_email: str, content: EmailContent) -> dict[str, object]:
    return {
        "from": from_email,
        "to": [to_email],
        "subject": content.subject,
        "text": content.text,
        "html": content.html,
    }


class ResendEmailService:
    def __init__(self, api_key: str, from_email: str, to_email: str, timeout_seconds: float = 20.0) -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._to_email = to_email
        self._timeout_seconds = timeout_seconds

    def send(self, content: EmailContent, idempotency_key: str) -> str:
        payload = build_resend_payload(
            from_email=self._from_email,
            to_email=self._to_email,
            content=content,
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

        response = requests.post(
            _RESEND_SEND_EMAIL_URL,
            json=payload,
            headers=headers,
            timeout=self._timeout_seconds,
        )
        if response.status_code >= 400:
            message = _extract_error_message(response)
            raise RuntimeError(f"Resend send failed: HTTP {response.status_code} - {message}")

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Resend response is not valid JSON.") from exc

        email_id = data.get("id")
        if not isinstance(email_id, str) or not email_id:
            raise RuntimeError("Resend response did not include an email id.")
        return email_id


def _extract_error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:300]

    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str) and message:
            return message

        name = body.get("name")
        if isinstance(name, str) and name:
            return name

    return str(body)[:300]
