from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from app.extensions import db
from app.models import Call, Clinic, Conversation, Lead, LeadPayload, Message, WebhookEvent
from app.providers.factory import get_voice_provider, get_whatsapp_provider
from app.security import rate_limiter, request_ip_hash
from app.services.activity_service import log_activity
from app.services.lead_import_service import map_row_to_lead_kwargs


api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _api_limited(prefix):
    key = f"{prefix}:{request_ip_hash()}"
    return rate_limiter.is_limited(
        key=key,
        limit=current_app.config["API_RATE_LIMIT_COUNT"],
        window_seconds=current_app.config["API_RATE_LIMIT_WINDOW_SECONDS"],
    )


def _captcha_valid(payload):
    if not current_app.config.get("ENABLE_CAPTCHA"):
        return True
    token = payload.get("captcha_token")
    return bool(token)


@api_bp.route("/leads", methods=["POST"])
def create_api_lead():
    if _api_limited("lead_api"):
        return jsonify({"error": "Rate limit exceeded"}), 429

    configured_key = current_app.config.get("LEAD_API_KEY")
    request_key = request.headers.get("X-API-Key", "")
    if configured_key and request_key != configured_key:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or request.form.to_dict()

    if payload.get("company_website"):
        return jsonify({"error": "spam detected"}), 400
    if not _captcha_valid(payload):
        return jsonify({"error": "captcha failed"}), 400

    clinic_slug = (payload.get("clinic_slug") or "").strip().lower()
    clinic = Clinic.query.filter_by(slug=clinic_slug).first()
    if not clinic:
        return jsonify({"error": "Invalid clinic_slug"}), 404

    lead_kwargs = map_row_to_lead_kwargs(payload)
    lead_kwargs.update(
        {
            "source": "website_form",
            "landing_page_url": payload.get("landing_page_url"),
            "referrer_url": payload.get("referrer_url"),
            "user_agent": request.headers.get("User-Agent", "")[:300],
            "ip_hash": request_ip_hash(),
        }
    )

    lead = Lead(clinic_id=clinic.id, assigned_agent_id=None, **lead_kwargs)
    db.session.add(lead)
    db.session.flush()
    db.session.add(log_activity(clinic_id=clinic.id, lead_id=lead.id, action="lead.api.created", details="Lead captured via website form API"))
    db.session.commit()

    return jsonify({"lead_id": lead.id}), 201


@api_bp.route("/webhooks/meta-leads", methods=["POST"])
def meta_leads_webhook():
    payload = request.get_json(silent=True) or {}
    clinic_slug = payload.get("clinic_slug", "")
    clinic = Clinic.query.filter_by(slug=clinic_slug).first() if clinic_slug else None

    db.session.add(WebhookEvent(clinic_id=clinic.id if clinic else None, provider="meta_leads", raw_json=payload, signature_ok=True, processed_at=datetime.utcnow()))
    db.session.flush()

    lead_payload = LeadPayload(clinic_id=clinic.id if clinic else None, provider="meta_leads", payload_json=payload)
    db.session.add(lead_payload)

    if clinic:
        mapped = {
            "first_name": payload.get("first_name") or payload.get("full_name", "Meta"),
            "last_name": payload.get("last_name") or "Lead",
            "email": payload.get("email"),
            "phone": payload.get("phone"),
            "source": "meta_lead_ads",
            "status": "new",
            "stage_key": "new",
            "language": payload.get("language") or clinic.default_language,
            "country": payload.get("country") or "Italy",
            "utm_source": payload.get("utm_source") or "meta",
            "utm_medium": payload.get("utm_medium") or "paid_social",
            "utm_campaign": payload.get("utm_campaign"),
            "fbclid": payload.get("fbclid"),
            "user_agent": request.headers.get("User-Agent", "")[:300],
            "ip_hash": request_ip_hash(),
        }
        lead = Lead(clinic_id=clinic.id, **mapped)
        db.session.add(lead)
        db.session.flush()
        lead_payload.lead_id = lead.id

    db.session.commit()
    return jsonify({"ok": True}), 200


@api_bp.route("/webhooks/whatsapp", methods=["POST"])
def whatsapp_webhook():
    payload = request.get_json(silent=True) or {}
    clinic_slug = payload.get("clinic_slug", "")
    clinic = Clinic.query.filter_by(slug=clinic_slug).first() if clinic_slug else None

    db.session.add(WebhookEvent(clinic_id=clinic.id if clinic else None, provider="whatsapp", raw_json=payload, signature_ok=False, processed_at=datetime.utcnow()))

    if clinic:
        parsed = get_whatsapp_provider().parse_webhook(payload)
        conversation = Conversation.query.filter_by(clinic_id=clinic.id, external_id=parsed.get("external_conversation_id")).first()
        if not conversation:
            conversation = Conversation(clinic_id=clinic.id, channel="whatsapp", external_id=parsed.get("external_conversation_id"), status="open")
            db.session.add(conversation)
            db.session.flush()

        message = Message(
            clinic_id=clinic.id,
            conversation_id=conversation.id,
            direction="inbound",
            body=parsed.get("body", ""),
            provider_message_id=payload.get("provider_message_id"),
        )
        conversation.last_message_at = datetime.utcnow()
        db.session.add(message)

    db.session.commit()
    return jsonify({"ok": True}), 200


@api_bp.route("/webhooks/voice", methods=["POST"])
def voice_webhook():
    payload = request.get_json(silent=True) or request.form.to_dict()
    clinic_slug = payload.get("clinic_slug", "")
    clinic = Clinic.query.filter_by(slug=clinic_slug).first() if clinic_slug else None

    db.session.add(WebhookEvent(clinic_id=clinic.id if clinic else None, provider="voice", raw_json=payload, signature_ok=False, processed_at=datetime.utcnow()))

    if clinic:
        parsed = get_voice_provider().handle_webhook_call_events(payload)
        call = Call.query.filter_by(clinic_id=clinic.id, provider_call_id=parsed.get("provider_call_id")).first()
        if call:
            call.status = parsed.get("status", call.status)
            call.recording_url = parsed.get("recording_url") or call.recording_url
            if parsed.get("duration_seconds"):
                call.duration_seconds = int(parsed.get("duration_seconds"))
            if call.status in {"completed", "failed", "no_answer"}:
                call.ended_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"ok": True}), 200


@api_bp.route("/voice/token", methods=["GET"])
def voice_token_placeholder():
    return jsonify({"token": "stub-token", "provider": current_app.config.get("VOICE_PROVIDER", "stub")})
