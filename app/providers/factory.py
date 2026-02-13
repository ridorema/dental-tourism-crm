from flask import current_app

from app.providers.voice_stub import StubVoiceProvider
from app.providers.voice_twilio import TwilioVoiceProvider
from app.providers.whatsapp_meta import MetaWhatsAppProvider
from app.providers.whatsapp_stub import StubWhatsAppProvider


def get_whatsapp_provider():
    provider = current_app.config.get("WHATSAPP_PROVIDER", "stub")
    if provider == "meta":
        return MetaWhatsAppProvider()
    return StubWhatsAppProvider()


def get_voice_provider():
    provider = current_app.config.get("VOICE_PROVIDER", "stub")
    if provider == "twilio":
        return TwilioVoiceProvider()
    return StubVoiceProvider()
