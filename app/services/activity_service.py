from app.models import ActivityLog


def log_activity(clinic_id, action, user_id=None, lead_id=None, patient_id=None, quote_id=None, payment_id=None, details=None):
    return ActivityLog(
        clinic_id=clinic_id,
        action=action,
        user_id=user_id,
        lead_id=lead_id,
        patient_id=patient_id,
        quote_id=quote_id,
        payment_id=payment_id,
        details=details,
    )
