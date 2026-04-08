from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from src.alert_logic import (
    MIN_PRECIPITATION_THRESHOLD_MM,
    SlotName,
    build_idempotency_key,
    is_rainy,
    resolve_slot,
    slot_hours_utc,
    slot_label_fr,
)
from src.config import AppConfig
from src.email_service import EmailContent, ResendEmailService
from src.open_meteo_client import ForecastPoint, OpenMeteoClient
from src.whatsapp_service import MetaWhatsAppService, WhatsAppTemplateContent


@dataclass(frozen=True, slots=True)
class RunResult:
    status: str
    detail: str
    slot: SlotName | None
    sent_email_id: str | None
    sent_whatsapp_message_id: str | None
    rainy_hours_local: tuple[str, ...]


def run_monitoring(config: AppConfig, now_utc: datetime | None = None) -> RunResult:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware.")

    timezone_info = ZoneInfo(config.timezone_name)
    now_local = now.astimezone(timezone_info)

    if now_local.date() > config.target_date:
        return RunResult(
            status="skip_out_of_target_date",
            detail="Current local date is after TARGET_DATE.",
            slot=None,
            sent_email_id=None,
            sent_whatsapp_message_id=None,
            rainy_hours_local=(),
        )

    slot = resolve_slot(now_local=now_local, target_date=config.target_date)
    if slot is None:
        return RunResult(
            status="skip_out_of_target_slot",
            detail="Current local hour is outside morning/afternoon slots.",
            slot=None,
            sent_email_id=None,
            sent_whatsapp_message_id=None,
            rainy_hours_local=(),
        )

    hours_utc = slot_hours_utc(config.target_date, slot, timezone_info)

    meteo_client = OpenMeteoClient(config)
    forecast_points = meteo_client.fetch_slot_precipitations(
        slot_hours_utc=hours_utc,
        lat=config.target_lat,
        lon=config.target_lon,
    )

    rainy_points = [
        point
        for point in forecast_points
        if is_rainy([point.precipitation_mm], threshold_mm=MIN_PRECIPITATION_THRESHOLD_MM)
    ]
    if not rainy_points:
        return RunResult(
            status="skip_no_rain",
            detail="No rainy hour detected in the current slot.",
            slot=slot,
            sent_email_id=None,
            sent_whatsapp_message_id=None,
            rainy_hours_local=(),
        )

    email_content = _build_email_content(
        slot=slot,
        target_date=config.target_date.isoformat(),
        rainy_points=rainy_points,
        timezone_info=timezone_info,
    )
    whatsapp_content = _build_whatsapp_template_content(
        slot=slot,
        target_date=config.target_date.isoformat(),
        rainy_points=rainy_points,
        timezone_info=timezone_info,
    )
    idempotency_key = build_idempotency_key(target_date=config.target_date, slot=slot)
    rainy_hours_local = tuple(_format_local_hour(point, timezone_info) for point in rainy_points)

    whatsapp_service = MetaWhatsAppService(
        access_token=config.whatsapp_access_token,
        phone_number_id=config.whatsapp_phone_number_id,
        recipient_phone_number=config.whatsapp_recipient_number,
        template_name=config.whatsapp_template_name,
        template_language=config.whatsapp_template_language,
        graph_api_version=config.whatsapp_graph_api_version,
        timeout_seconds=config.whatsapp_timeout_seconds,
    )

    try:
        whatsapp_message_id = whatsapp_service.send(content=whatsapp_content, idempotency_key=idempotency_key)
        return RunResult(
            status="sent",
            detail=f"Rain detected in {len(rainy_points)} hour(s); WhatsApp alert sent.",
            slot=slot,
            sent_email_id=None,
            sent_whatsapp_message_id=whatsapp_message_id,
            rainy_hours_local=rainy_hours_local,
        )
    except RuntimeError as whatsapp_error:
        email_service = ResendEmailService(
            api_key=config.resend_api_key,
            from_email=config.resend_from,
            to_email=config.resend_to,
        )
        email_id = email_service.send(content=email_content, idempotency_key=idempotency_key)
        return RunResult(
            status="sent",
            detail=(
                f"Rain detected in {len(rainy_points)} hour(s); "
                f"WhatsApp failed, fallback email sent ({whatsapp_error})."
            ),
            slot=slot,
            sent_email_id=email_id,
            sent_whatsapp_message_id=None,
            rainy_hours_local=rainy_hours_local,
        )


def run_result_to_dict(result: RunResult) -> dict[str, object]:
    return {
        "status": result.status,
        "detail": result.detail,
        "slot": result.slot.value if result.slot is not None else None,
        "sent_email_id": result.sent_email_id,
        "sent_whatsapp_message_id": result.sent_whatsapp_message_id,
        "rainy_hours_local": list(result.rainy_hours_local),
    }


def _build_whatsapp_template_content(
    slot: SlotName,
    target_date: str,
    rainy_points: list[ForecastPoint],
    timezone_info: ZoneInfo,
) -> WhatsAppTemplateContent:
    rainy_points_sorted = sorted(rainy_points, key=lambda item: item.forecast_time_utc)
    report = "; ".join(
        f"{point.forecast_time_utc.astimezone(timezone_info).strftime('%H:%M')} : {point.precipitation_mm:.2f} mm"
        for point in rainy_points_sorted
    )
    return WhatsAppTemplateContent(
        body_parameters=(
            target_date,
            slot_label_fr(slot),
            report,
        )
    )


def _build_email_content(
    slot: SlotName,
    target_date: str,
    rainy_points: list[ForecastPoint],
    timezone_info: ZoneInfo,
) -> EmailContent:
    rainy_points_sorted = sorted(rainy_points, key=lambda item: item.forecast_time_utc)

    lines_text = [
        f"Alerte pluie pour Saint-Chamond ({target_date}, {slot_label_fr(slot)}).",
        "Heures pluvieuses détectées:",
    ]
    lines_html = [
        f"<p><strong>Alerte pluie</strong> pour Saint-Chamond ({target_date}, {slot_label_fr(slot)}).</p>",
        "<p>Heures pluvieuses détectées :</p>",
        "<ul>",
    ]

    for point in rainy_points_sorted:
        local_dt = point.forecast_time_utc.astimezone(timezone_info)
        line = f"- {local_dt.strftime('%H:%M')} : {point.precipitation_mm:.2f} mm"
        lines_text.append(line)
        lines_html.append(f"<li>{local_dt.strftime('%H:%M')} : {point.precipitation_mm:.2f} mm</li>")

    lines_html.append("</ul>")

    subject = f"[Alerte pluie] Saint-Chamond - {target_date} ({slot_label_fr(slot)})"
    return EmailContent(
        subject=subject,
        text="\n".join(lines_text),
        html="\n".join(lines_html),
    )


def _format_local_hour(point: ForecastPoint, timezone_info: ZoneInfo) -> str:
    return point.forecast_time_utc.astimezone(timezone_info).strftime("%H:%M")
