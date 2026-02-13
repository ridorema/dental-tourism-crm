from datetime import datetime
from decimal import Decimal

from app.extensions import db
from app.models import ConversionEvent


def create_conversion_event_for_lead(lead, conversion_name, value=None, currency="EUR"):
    existing = (
        ConversionEvent.query.filter_by(
            clinic_id=lead.clinic_id,
            lead_id=lead.id,
            conversion_name=conversion_name,
        )
        .order_by(ConversionEvent.created_at.desc())
        .first()
    )
    if existing:
        return existing

    event = ConversionEvent(
        clinic_id=lead.clinic_id,
        lead_id=lead.id,
        gclid=lead.gclid,
        conversion_name=conversion_name,
        conversion_time=datetime.utcnow(),
        conversion_value=Decimal(str(value or 0)),
        currency=currency,
    )
    db.session.add(event)
    return event
