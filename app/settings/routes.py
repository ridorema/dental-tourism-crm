import csv
from io import StringIO

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional

from app.authz import permission_required
from app.extensions import db
from app.models import ActivityLog, Clinic, ConsentEvent, Lead, Patient, PipelineStage, ProviderCredential
from app.security import hash_value
from app.services.activity_service import log_activity
from app.tenancy import TenantGuard


settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


class ClinicProfileForm(FlaskForm):
    name = StringField("Clinic name", validators=[DataRequired()])
    logo_url = StringField("Logo URL", validators=[Optional()])
    default_currency = StringField("Default currency", validators=[DataRequired()])
    timezone = StringField("Timezone", validators=[DataRequired()])
    default_language = StringField("Default language", validators=[DataRequired()])
    submit = SubmitField("Save Profile")


class PipelineForm(FlaskForm):
    name = StringField("Stage name", validators=[DataRequired()])
    stage_key = StringField("Stage key", validators=[DataRequired()])
    submit = SubmitField("Add Stage")


class IntegrationCredentialForm(FlaskForm):
    provider_type = SelectField("Provider", choices=[("meta_whatsapp", "Meta WhatsApp"), ("twilio_voice", "Twilio Voice"), ("google_ads", "Google Ads")], validators=[DataRequired()])
    encrypted_json = StringField("Credential JSON (encrypted placeholder)", validators=[DataRequired()])
    active = BooleanField("Active")
    submit = SubmitField("Save Credential")


@settings_bp.route("/clinic", methods=["GET", "POST"])
@login_required
@permission_required("settings.manage")
def clinic_profile():
    clinic = Clinic.query.get_or_404(current_user.clinic_id)
    form = ClinicProfileForm(obj=clinic)
    if form.validate_on_submit():
        clinic.name = form.name.data
        clinic.logo_url = form.logo_url.data
        clinic.default_currency = form.default_currency.data
        clinic.timezone = form.timezone.data
        clinic.default_language = form.default_language.data
        db.session.add(log_activity(clinic_id=clinic.id, user_id=current_user.id, action="settings.clinic.updated", details="Clinic profile updated"))
        db.session.commit()
        flash("Clinic profile updated", "success")
        return redirect(url_for("settings.clinic_profile"))

    return render_template("settings/clinic.html", form=form, clinic=clinic)


@settings_bp.route("/pipeline", methods=["GET", "POST"])
@login_required
@permission_required("settings.manage")
def pipeline_settings():
    form = PipelineForm()
    if form.validate_on_submit():
        stage = PipelineStage(clinic_id=current_user.clinic_id, name=form.name.data, stage_key=form.stage_key.data.strip().lower(), sort_order=PipelineStage.query.filter_by(clinic_id=current_user.clinic_id).count() + 1)
        db.session.add(stage)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="settings.pipeline.stage_added", details=stage.stage_key))
        db.session.commit()
        flash("Pipeline stage added", "success")
        return redirect(url_for("settings.pipeline_settings"))

    stages = TenantGuard.scoped_query(PipelineStage, include_deleted=True).order_by(PipelineStage.sort_order.asc()).all()
    return render_template("settings/pipeline.html", form=form, stages=stages)


@settings_bp.route("/integrations", methods=["GET", "POST"])
@login_required
@permission_required("integrations.manage")
def integrations_settings():
    form = IntegrationCredentialForm()
    if form.validate_on_submit():
        cred = ProviderCredential(clinic_id=current_user.clinic_id, provider_type=form.provider_type.data, encrypted_json=form.encrypted_json.data, active=form.active.data)
        db.session.add(cred)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="settings.integration.saved", details=cred.provider_type))
        db.session.commit()
        flash("Credential saved", "success")
        return redirect(url_for("settings.integrations_settings"))

    creds = TenantGuard.scoped_query(ProviderCredential, include_deleted=True).order_by(ProviderCredential.created_at.desc()).all()
    webhook_base = request.url_root.rstrip("/") + "/api/v1/webhooks"
    return render_template("settings/integrations.html", form=form, creds=creds, webhook_base=webhook_base)


@settings_bp.route("/gdpr/export/<int:patient_id>")
@login_required
@permission_required("gdpr.manage")
def gdpr_export(patient_id):
    patient = TenantGuard.get_or_404(Patient, patient_id)
    lead = TenantGuard.scoped_query(Lead).filter(Lead.id == patient.lead_id).first()

    rows = [{
        "patient_id": patient.id,
        "name": f"{patient.first_name} {patient.last_name}",
        "email": patient.email,
        "phone": patient.phone,
        "country": patient.country,
        "language": patient.language,
        "clinical_notes": patient.clinical_notes,
        "lead_source": lead.source if lead else None,
        "lead_status": lead.status if lead else None,
    }]

    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, patient_id=patient.id, action="gdpr.export", details="Patient data exported"))
    db.session.commit()

    return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=patient_{patient.id}_export.csv"})


@settings_bp.route("/gdpr/anonymize/<int:patient_id>", methods=["POST"])
@login_required
@permission_required("gdpr.manage")
def gdpr_anonymize(patient_id):
    patient = TenantGuard.get_or_404(Patient, patient_id)
    patient.first_name = "Anonymized"
    patient.last_name = f"Patient-{patient.id}"
    patient.email = None
    patient.phone = None
    patient.clinical_notes = None

    db.session.add(ConsentEvent(clinic_id=current_user.clinic_id, patient_id=patient.id, consent_type="gdpr_anonymize", granted=False))
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, patient_id=patient.id, action="gdpr.anonymize", details="Patient anonymized"))
    db.session.commit()
    flash("Patient anonymized", "success")
    return redirect(url_for("patients.patient_detail", patient_id=patient.id))


@settings_bp.route("/audit")
@login_required
@permission_required("settings.manage")
def audit_log():
    logs = TenantGuard.scoped_query(ActivityLog, include_deleted=True).order_by(ActivityLog.created_at.desc()).limit(300).all()
    return render_template("settings/audit.html", logs=logs)
