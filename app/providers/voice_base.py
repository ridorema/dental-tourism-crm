class VoiceProviderBase:
    def initiate_call(self, *, clinic_id, from_number, to_number, lead_id=None, patient_id=None):
        raise NotImplementedError

    def handle_webhook_call_events(self, payload):
        raise NotImplementedError
