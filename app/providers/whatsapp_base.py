class WhatsAppProviderBase:
    def send_text(self, *, clinic_id, to_number, body, conversation_external_id=None):
        raise NotImplementedError

    def send_template(self, *, clinic_id, to_number, template_name, context):
        raise NotImplementedError

    def parse_webhook(self, payload):
        raise NotImplementedError
