from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SoftDeleteMixin:
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class Clinic(TimestampMixin, db.Model):
    __tablename__ = "clinics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    logo_url = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(80), nullable=False, default="Albania")
    timezone = db.Column(db.String(60), nullable=False, default="Europe/Tirane")
    default_currency = db.Column(db.String(8), nullable=False, default="EUR")
    default_language = db.Column(db.String(12), nullable=False, default="it")
    languages_json = db.Column(db.JSON, nullable=False, default=list)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    clinic = db.relationship("Clinic")

    __table_args__ = (
        db.UniqueConstraint("clinic_id", "email", name="uq_user_clinic_email"),
        db.CheckConstraint("role IN ('admin', 'agent', 'doctor', 'finance')", name="ck_user_role"),
    )

    @property
    def is_active(self):
        return self.is_active_user

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class PipelineStage(TimestampMixin, db.Model):
    __tablename__ = "pipeline_stages"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    stage_key = db.Column(db.String(40), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_default = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("clinic_id", "stage_key", name="uq_pipeline_stage_key"),
    )


class AssignmentRule(TimestampMixin, db.Model):
    __tablename__ = "assignment_rules"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    mode = db.Column(db.String(20), nullable=False, default="round_robin")
    config_json = db.Column(db.JSON, nullable=False, default=dict)


class Lead(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(40), nullable=True)

    source = db.Column(db.String(80), nullable=False, default="website_form")
    status = db.Column(db.String(30), nullable=False, default="new", index=True)
    stage_key = db.Column(db.String(40), nullable=False, default="new")

    language = db.Column(db.String(20), nullable=False, default="it")
    country = db.Column(db.String(80), nullable=False, default="Italy")
    notes = db.Column(db.Text, nullable=True)
    next_action_date = db.Column(db.Date, nullable=True, index=True)
    converted_to_patient = db.Column(db.Boolean, nullable=False, default=False)

    landing_page_url = db.Column(db.String(500), nullable=True)
    referrer_url = db.Column(db.String(500), nullable=True)
    utm_source = db.Column(db.String(120), nullable=True)
    utm_medium = db.Column(db.String(120), nullable=True)
    utm_campaign = db.Column(db.String(120), nullable=True)
    utm_term = db.Column(db.String(120), nullable=True)
    utm_content = db.Column(db.String(120), nullable=True)
    gclid = db.Column(db.String(255), nullable=True, index=True)
    fbclid = db.Column(db.String(255), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    ip_hash = db.Column(db.String(128), nullable=True)

    patient = db.relationship("Patient", back_populates="lead", uselist=False)

    __table_args__ = (
        db.Index("ix_lead_clinic_status", "clinic_id", "status"),
        db.Index("ix_lead_clinic_created", "clinic_id", "created_at"),
    )


class Patient(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, unique=True)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    country = db.Column(db.String(80), nullable=False, default="Italy")
    language = db.Column(db.String(20), nullable=False, default="it")
    clinical_notes = db.Column(db.Text, nullable=True)

    lead = db.relationship("Lead", back_populates="patient")


class TreatmentPlan(TimestampMixin, db.Model):
    __tablename__ = "treatment_plans"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    items = db.Column(db.JSON, nullable=False, default=list)
    estimated_days = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    quotes = db.relationship("Quote", backref="treatment_plan")


class Quote(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "quotes"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    treatment_plan_id = db.Column(db.Integer, db.ForeignKey("treatment_plans.id"), nullable=True)
    currency = db.Column(db.String(3), nullable=False, default="EUR")
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    pdf_url = db.Column(db.String(255), nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_quote_clinic_status", "clinic_id", "status"),
    )


class Invoice(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id"), nullable=True, index=True)
    invoice_number = db.Column(db.String(60), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="EUR")
    status = db.Column(db.String(20), nullable=False, default="issued", index=True)
    issued_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="EUR")
    method = db.Column(db.String(30), nullable=False, default="bank_transfer")
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    due_date = db.Column(db.Date, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    quote = db.relationship("Quote", backref="payments")


class Appointment(TimestampMixin, db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    appointment_type = db.Column(db.String(20), nullable=False, default="in_person")
    scheduled_at = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text, nullable=True)


class Conversation(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    channel = db.Column(db.String(20), nullable=False, default="whatsapp")
    external_id = db.Column(db.String(255), nullable=True, index=True)
    last_message_at = db.Column(db.DateTime, nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="open")


class Message(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True)
    direction = db.Column(db.String(20), nullable=False)
    body = db.Column(db.Text, nullable=False)
    template_name = db.Column(db.String(80), nullable=True)
    provider_message_id = db.Column(db.String(255), nullable=True, index=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    error_code = db.Column(db.String(60), nullable=True)
    error_message = db.Column(db.String(300), nullable=True)

    conversation = db.relationship("Conversation")


class Call(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "calls"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    direction = db.Column(db.String(20), nullable=False)
    from_number = db.Column(db.String(40), nullable=False)
    to_number = db.Column(db.String(40), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True, index=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ringing", index=True)
    recording_url = db.Column(db.String(255), nullable=True)
    provider_call_id = db.Column(db.String(255), nullable=True, index=True)


class CallDisposition(TimestampMixin, db.Model):
    __tablename__ = "call_dispositions"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    call_id = db.Column(db.Integer, db.ForeignKey("calls.id"), nullable=False, index=True)
    outcome = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    followup_at = db.Column(db.DateTime, nullable=True)


class PhoneNumber(TimestampMixin, db.Model):
    __tablename__ = "phone_numbers"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    e164 = db.Column(db.String(40), nullable=False)
    label = db.Column(db.String(80), nullable=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)


class ProviderCredential(TimestampMixin, db.Model):
    __tablename__ = "provider_credentials"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    provider_type = db.Column(db.String(40), nullable=False)
    encrypted_json = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)


class WebhookEvent(TimestampMixin, db.Model):
    __tablename__ = "webhook_events"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=True, index=True)
    provider = db.Column(db.String(40), nullable=False, index=True)
    raw_json = db.Column(db.JSON, nullable=False)
    signature_ok = db.Column(db.Boolean, nullable=False, default=False)
    processed_at = db.Column(db.DateTime, nullable=True)


class ContactIdentity(TimestampMixin, db.Model):
    __tablename__ = "contact_identities"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    phone_e164 = db.Column(db.String(40), nullable=True)
    whatsapp_e164 = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(20), nullable=True)


class LeadPayload(TimestampMixin, db.Model):
    __tablename__ = "lead_payloads"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=True, index=True)
    provider = db.Column(db.String(40), nullable=False)
    payload_json = db.Column(db.JSON, nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)


class ConversionEvent(TimestampMixin, db.Model):
    __tablename__ = "conversion_events"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False, index=True)
    gclid = db.Column(db.String(255), nullable=True, index=True)
    conversion_name = db.Column(db.String(100), nullable=False)
    conversion_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    conversion_value = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    currency = db.Column(db.String(8), nullable=False, default="EUR")


class ConsentEvent(TimestampMixin, db.Model):
    __tablename__ = "consent_events"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=False, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    consent_type = db.Column(db.String(80), nullable=False)
    granted = db.Column(db.Boolean, nullable=False, default=True)


class ActivityLog(TimestampMixin, db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quotes.id"), nullable=True, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True, index=True)
    action = db.Column(db.String(120), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)


class LoginAttempt(TimestampMixin, db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey("clinics.id"), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=False)
    ip_hash = db.Column(db.String(128), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=False)
