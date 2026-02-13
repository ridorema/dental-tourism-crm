from datetime import datetime

from app.providers.whatsapp_base import WhatsAppProviderBase


class StubWhatsAppProvider(WhatsAppProviderBase):
    def send_text(self, *, clinic_id, to_number, body, conversation_external_id=None):
        return {
            "provider_message_id": f"stub-msg-{int(datetime.utcnow().timestamp())}",
            "status": "queued",
            "to_number": to_number,
            "body": body,
        }

    def send_template(self, *, clinic_id, to_number, template_name, context):
        rendered = template_name + " | " + ", ".join(f"{k}={v}" for k, v in context.items())
        return self.send_text(clinic_id=clinic_id, to_number=to_number, body=rendered)

    def parse_webhook(self, payload):
        return {
            "event_type": "message",
            "external_conversation_id": payload.get("conversation_id", "stub-conv"),
            "from_number": payload.get("from_number"),
            "body": payload.get("body", ""),
        }
