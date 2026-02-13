from datetime import datetime

from app.providers.voice_base import VoiceProviderBase


class StubVoiceProvider(VoiceProviderBase):
    def initiate_call(self, *, clinic_id, from_number, to_number, lead_id=None, patient_id=None):
        now = datetime.utcnow()
        return {
            "provider_call_id": f"stub-call-{int(now.timestamp())}",
            "status": "ringing",
            "started_at": now,
            "from_number": from_number,
            "to_number": to_number,
        }

    def handle_webhook_call_events(self, payload):
        return {
            "provider_call_id": payload.get("provider_call_id"),
            "status": payload.get("status", "completed"),
            "recording_url": payload.get("recording_url"),
            "duration_seconds": payload.get("duration_seconds"),
        }
