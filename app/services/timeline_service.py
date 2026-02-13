from app.models import ActivityLog, Appointment, Call, Conversation, Message, Payment
from app.tenancy import clinic_query


def build_contact_timeline(lead_id=None, patient_id=None):
    events = []

    if lead_id:
        for item in clinic_query(ActivityLog).filter(ActivityLog.lead_id == lead_id).all():
            events.append((item.created_at, "activity", item.action, item.details or ""))

        for item in (
            clinic_query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Conversation.lead_id == lead_id)
            .all()
        ):
            events.append((item.created_at, "message", item.direction, item.body))

        for item in clinic_query(Call).filter(Call.lead_id == lead_id).all():
            events.append((item.created_at, "call", item.status, f"{item.from_number} -> {item.to_number}"))

    if patient_id:
        for item in clinic_query(Appointment).filter(Appointment.patient_id == patient_id).all():
            events.append((item.created_at, "appointment", item.appointment_type, str(item.scheduled_at)))

        for item in clinic_query(Payment).filter(Payment.patient_id == patient_id).all():
            events.append((item.created_at, "payment", item.status, f"{item.amount} {item.currency}"))

    events.sort(key=lambda x: x[0], reverse=True)
    return events
