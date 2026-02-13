from app.extensions import db
from app.models import Patient


def convert_lead_to_patient(lead, actor):
    if lead.converted_to_patient and lead.patient:
        return lead.patient

    patient = Patient(
        clinic_id=lead.clinic_id,
        lead=lead,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        phone=lead.phone,
        country=lead.country,
        language=lead.language,
    )
    lead.converted_to_patient = True
    if lead.status == "new":
        lead.status = "qualified"
        lead.stage_key = "qualified"

    db.session.add(patient)
    db.session.flush()
    return patient
