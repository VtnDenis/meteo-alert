from __future__ import annotations

import pytest

from src.whatsapp_service import (
    MetaWhatsAppService,
    WhatsAppTemplateContent,
    build_whatsapp_template_payload,
)


class _DummyResponse:
    def __init__(self, status_code: int, body: object, text: str = "") -> None:
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self) -> object:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def test_build_whatsapp_template_payload() -> None:
    payload = build_whatsapp_template_payload(
        recipient_phone_number="+33624018317",
        template_name="meteo_alerte_pluie_resume_v1",
        template_language="fr_FR",
        content=WhatsAppTemplateContent(body_parameters=("2026-04-11", "matin", "08:00 : 0.70 mm")),
        idempotency_key="meteo-alert/2026-04-11/morning",
    )

    assert payload["messaging_product"] == "whatsapp"
    assert payload["recipient_type"] == "individual"
    assert payload["to"] == "+33624018317"
    assert payload["type"] == "template"
    assert payload["biz_opaque_callback_data"] == "meteo-alert/2026-04-11/morning"

    template = payload["template"]
    assert isinstance(template, dict)
    assert template["name"] == "meteo_alerte_pluie_resume_v1"
    assert template["language"] == {"code": "fr_FR"}


def test_send_returns_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MetaWhatsAppService(
        access_token="token_123",
        phone_number_id="1906385232743451",
        recipient_phone_number="+33624018317",
        template_name="meteo_alerte_pluie_resume_v1",
        template_language="fr_FR",
        graph_api_version="v25.0",
    )

    def _fake_post(url: str, json: object, headers: object, timeout: float) -> _DummyResponse:
        assert url == "https://graph.facebook.com/v25.0/1906385232743451/messages"
        assert timeout == 20.0
        assert isinstance(headers, dict)
        assert headers["Authorization"] == "Bearer token_123"
        assert headers["Content-Type"] == "application/json"
        assert isinstance(json, dict)
        return _DummyResponse(
            status_code=200,
            body={
                "messaging_product": "whatsapp",
                "messages": [{"id": "wamid.HBgLM..."}],
            },
        )

    monkeypatch.setattr("src.whatsapp_service.requests.post", _fake_post)

    message_id = service.send(
        content=WhatsAppTemplateContent(body_parameters=("2026-04-11", "matin", "08:00 : 0.70 mm")),
        idempotency_key="meteo-alert/2026-04-11/morning",
    )

    assert message_id == "wamid.HBgLM..."


def test_send_raises_when_graph_api_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MetaWhatsAppService(
        access_token="token_123",
        phone_number_id="1906385232743451",
        recipient_phone_number="+33624018317",
        template_name="meteo_alerte_pluie_resume_v1",
        template_language="fr_FR",
    )

    def _fake_post(url: str, json: object, headers: object, timeout: float) -> _DummyResponse:
        return _DummyResponse(
            status_code=400,
            body={
                "error": {
                    "message": "Unsupported post request",
                    "code": 100,
                    "fbtrace_id": "ABCD123",
                }
            },
        )

    monkeypatch.setattr("src.whatsapp_service.requests.post", _fake_post)

    with pytest.raises(RuntimeError, match="WhatsApp send failed"):
        service.send(
            content=WhatsAppTemplateContent(body_parameters=("2026-04-11", "matin", "08:00 : 0.70 mm")),
            idempotency_key="meteo-alert/2026-04-11/morning",
        )


def test_send_raises_when_message_id_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MetaWhatsAppService(
        access_token="token_123",
        phone_number_id="1906385232743451",
        recipient_phone_number="+33624018317",
        template_name="meteo_alerte_pluie_resume_v1",
        template_language="fr_FR",
    )

    def _fake_post(url: str, json: object, headers: object, timeout: float) -> _DummyResponse:
        return _DummyResponse(status_code=200, body={"messaging_product": "whatsapp"})

    monkeypatch.setattr("src.whatsapp_service.requests.post", _fake_post)

    with pytest.raises(RuntimeError, match="did not include a message id"):
        service.send(
            content=WhatsAppTemplateContent(body_parameters=("2026-04-11", "matin", "08:00 : 0.70 mm")),
            idempotency_key="meteo-alert/2026-04-11/morning",
        )
