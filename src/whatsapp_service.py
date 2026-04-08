from __future__ import annotations

from dataclasses import dataclass

import requests

_GRAPH_BASE_URL = "https://graph.facebook.com"


@dataclass(frozen=True, slots=True)
class WhatsAppTemplateContent:
    body_parameters: tuple[str, ...]


def build_whatsapp_template_payload(
    recipient_phone_number: str,
    template_name: str,
    template_language: str,
    content: WhatsAppTemplateContent,
    idempotency_key: str,
) -> dict[str, object]:
    template: dict[str, object] = {
        "name": template_name,
        "language": {"code": template_language},
    }
    if content.body_parameters:
        template["components"] = [
            {
                "type": "body",
                "parameters": [
                    {
                        "type": "text",
                        "text": value,
                    }
                    for value in content.body_parameters
                ],
            }
        ]

    payload: dict[str, object] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone_number,
        "type": "template",
        "template": template,
    }
    if idempotency_key:
        payload["biz_opaque_callback_data"] = idempotency_key
    return payload


class MetaWhatsAppService:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        recipient_phone_number: str,
        template_name: str,
        template_language: str,
        graph_api_version: str = "v25.0",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._access_token = access_token
        self._recipient_phone_number = recipient_phone_number
        self._template_name = template_name
        self._template_language = template_language
        self._timeout_seconds = timeout_seconds
        self._send_message_url = f"{_GRAPH_BASE_URL}/{graph_api_version}/{phone_number_id}/messages"

    def send(self, content: WhatsAppTemplateContent, idempotency_key: str) -> str:
        payload = build_whatsapp_template_payload(
            recipient_phone_number=self._recipient_phone_number,
            template_name=self._template_name,
            template_language=self._template_language,
            content=content,
            idempotency_key=idempotency_key,
        )
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self._send_message_url,
            json=payload,
            headers=headers,
            timeout=self._timeout_seconds,
        )
        if response.status_code >= 400:
            message = _extract_error_message(response)
            raise RuntimeError(f"WhatsApp send failed: HTTP {response.status_code} - {message}")

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("WhatsApp response is not valid JSON.") from exc

        message_id = _extract_message_id(data)
        if message_id is None:
            raise RuntimeError("WhatsApp response did not include a message id.")
        return message_id


def _extract_message_id(body: object) -> str | None:
    if not isinstance(body, dict):
        return None

    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return None

    first_message = messages[0]
    if not isinstance(first_message, dict):
        return None

    message_id = first_message.get("id")
    if isinstance(message_id, str) and message_id:
        return message_id
    return None


def _extract_error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:300]

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = _extract_non_blank_string(error, "message")
            code = error.get("code")
            subcode = error.get("error_subcode")
            fbtrace_id = _extract_non_blank_string(error, "fbtrace_id")

            details: list[str] = []
            if message:
                details.append(message)
            if isinstance(code, int):
                details.append(f"code={code}")
            if isinstance(subcode, int):
                details.append(f"subcode={subcode}")
            if fbtrace_id:
                details.append(f"fbtrace_id={fbtrace_id}")
            if details:
                return " | ".join(details)

        message = _extract_non_blank_string(body, "message")
        if message:
            return message

    return str(body)[:300]


def _extract_non_blank_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None
