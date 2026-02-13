from app.providers.voice_base import VoiceProviderBase


class TwilioVoiceProvider(VoiceProviderBase):
    def initiate_call(self, *, clinic_id, from_number, to_number, lead_id=None, patient_id=None):
        raise NotImplementedError("Twilio live calling not wired yet; use stub mode.")

    def handle_webhook_call_events(self, payload):
        return {
            "provider_call_id": payload.get("CallSid"),
            "status": payload.get("CallStatus", "completed"),
            "recording_url": payload.get("RecordingUrl"),
            "duration_seconds": payload.get("CallDuration"),
        }
