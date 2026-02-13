from app.providers.whatsapp_base import WhatsAppProviderBase


class MetaWhatsAppProvider(WhatsAppProviderBase):
    def send_text(self, *, clinic_id, to_number, body, conversation_external_id=None):
        raise NotImplementedError("Meta WhatsApp API not wired yet; use stub mode.")

    def send_template(self, *, clinic_id, to_number, template_name, context):
        raise NotImplementedError("Meta WhatsApp API not wired yet; use stub mode.")

    def parse_webhook(self, payload):
        # Placeholder for signature verification and event normalization.
        return {
            "event_type": "message",
            "external_conversation_id": payload.get("entry", [{}])[0].get("id"),
            "from_number": None,
            "body": "",
        }
