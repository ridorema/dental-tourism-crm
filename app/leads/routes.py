from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from sqlalchemy import or_
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.authz import permission_required
from app.extensions import db

from app.models import ActivityLog, Lead
from app.services.activity_service import log_activity
from app.services.conversion_service import create_conversion_event_for_lead
from app.services.lead_import_service import map_row_to_lead_kwargs, parse_uploaded_leads
from app.services.lead_service import convert_lead_to_patient
from app.services.whatsapp_service import render_whatsapp_template
from app.tenancy import TenantGuard


leads_bp = Blueprint("leads", __name__, url_prefix="/leads")

STATUS_CHOICES = [
    ("new", "New"),
    ("contacted", "Contacted"),
    ("qualified", "Qualified"),
    ("quoted", "Quoted"),
    ("accepted", "Quote Accepted"),
    ("completed", "Completed"),
    ("lost", "Lost"),
]


class LeadForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired()])
    last_name = StringField("Last name", validators=[DataRequired()])
    email = StringField("Email", validators=[Optional()])
    phone = StringField("Phone", validators=[Optional()])
    source = StringField("Source", validators=[DataRequired()])
    status = SelectField("Status", choices=STATUS_CHOICES, validators=[DataRequired()])
    language = StringField("Language", validators=[DataRequired()])
    country = StringField("Country", validators=[DataRequired()])
    next_action_date = DateField("Next action date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save lead")


class NoteForm(FlaskForm):
    details = TextAreaField("New note", validators=[DataRequired()])
    submit = SubmitField("Add Note")


class FollowUpForm(FlaskForm):
    next_action_date = DateField("Next action date", validators=[DataRequired()])
    submit = SubmitField("Set Follow-Up")


class StatusForm(FlaskForm):
    status = SelectField("Status", choices=STATUS_CHOICES, validators=[DataRequired()])
    submit = SubmitField("Update Status")


class ImportLeadsForm(FlaskForm):
    file = FileField("CSV or XLSX", validators=[FileRequired()])
    submit = SubmitField("Import Leads")


@leads_bp.route("/")
@login_required
@permission_required("leads.manage")
def list_leads():
    query = TenantGuard.scoped_query(Lead)

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Lead.first_name.ilike(like), Lead.last_name.ilike(like), Lead.email.ilike(like), Lead.phone.ilike(like)))
    if status:
        query = query.filter(Lead.status == status)

    leads = query.order_by(Lead.created_at.desc()).all()
    return render_template("leads/list.html", leads=leads, q=q, status=status)


@leads_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("leads.manage")
def create_lead():
    form = LeadForm()
    if form.validate_on_submit():
        lead = Lead(
            clinic_id=current_user.clinic_id,
            assigned_agent_id=current_user.id if current_user.role in {"admin", "agent"} else None,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            source=form.source.data,
            status=form.status.data,
            stage_key=form.status.data,
            language=form.language.data,
            country=form.country.data,
            next_action_date=form.next_action_date.data,
            notes=form.notes.data,
        )
        db.session.add(lead)
        db.session.flush()

        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="lead.created", details=f"Lead {lead.first_name} {lead.last_name} created"))
        db.session.commit()
        flash("Lead created", "success")
        return redirect(url_for("leads.lead_detail", lead_id=lead.id))

    return render_template("leads/new.html", form=form)


@leads_bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("leads.manage")
def import_leads():
    form = ImportLeadsForm()
    if form.validate_on_submit():
        try:
            rows = parse_uploaded_leads(form.file.data)
        except Exception as exc:
            flash(str(exc), "danger")
            return redirect(url_for("leads.import_leads"))

        count = 0
        for row in rows:
            db.session.add(Lead(clinic_id=current_user.clinic_id, assigned_agent_id=current_user.id, **map_row_to_lead_kwargs(row)))
            count += 1

        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="lead.import", details=f"Imported {count} leads"))
        db.session.commit()
        flash(f"Imported {count} leads", "success")
        return redirect(url_for("leads.list_leads"))

    return render_template("leads/import.html", form=form)


@leads_bp.route("/follow-ups")
@login_required
@permission_required("leads.manage")
def follow_ups():
    today = date.today()
    due_leads = TenantGuard.scoped_query(Lead).filter(Lead.next_action_date.isnot(None), Lead.next_action_date <= today, Lead.status.notin_(["lost", "completed"])).order_by(Lead.next_action_date.asc()).all()
    upcoming_leads = TenantGuard.scoped_query(Lead).filter(Lead.next_action_date.isnot(None), Lead.next_action_date > today, Lead.status.notin_(["lost", "completed"])).order_by(Lead.next_action_date.asc()).all()
    return render_template("leads/follow_ups.html", due_leads=due_leads, upcoming_leads=upcoming_leads, today=today)


@leads_bp.route("/<int:lead_id>", methods=["GET", "POST"])
@login_required
@permission_required("leads.manage")
def lead_detail(lead_id):
    lead = TenantGuard.get_or_404(Lead, lead_id)

    note_form = NoteForm(prefix="note")
    follow_form = FollowUpForm(prefix="follow")
    status_form = StatusForm(prefix="status")
    if request.method == "GET":
        status_form.status.data = lead.status

    if note_form.submit.data and note_form.validate_on_submit():
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="lead.note", details=note_form.details.data))
        db.session.commit()
        flash("Note added", "success")
        return redirect(url_for("leads.lead_detail", lead_id=lead.id))

    if follow_form.submit.data and follow_form.validate_on_submit():
        lead.next_action_date = follow_form.next_action_date.data
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="lead.followup", details=f"Follow-up set to {lead.next_action_date}"))
        db.session.commit()
        flash("Follow-up updated", "success")
        return redirect(url_for("leads.lead_detail", lead_id=lead.id))

    if status_form.submit.data and status_form.validate_on_submit():
        lead.status = status_form.status.data
        lead.stage_key = lead.status
        if lead.status in {"accepted", "completed"}:
            conversion_name = "Quote Accepted" if lead.status == "accepted" else "Completed"
            create_conversion_event_for_lead(lead, conversion_name=conversion_name)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="lead.status", details=f"Status changed to {lead.status}"))
        db.session.commit()
        flash("Status updated", "success")
        return redirect(url_for("leads.lead_detail", lead_id=lead.id))

    activities = (
        TenantGuard.scoped_query(ActivityLog)
        .filter(ActivityLog.lead_id == lead.id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )

    ctx = {
        "first_name": lead.first_name,
        "clinic_name": current_user.clinic.name,
        "quote_total": "-",
        "currency": current_user.clinic.default_currency,
        "appointment_date": lead.next_action_date.isoformat() if lead.next_action_date else "da confermare",
        "appointment_time": "10:00",
    }
    whatsapp_templates = {
        "new lead": render_whatsapp_template("new", ctx),
        "follow-up": render_whatsapp_template("contacted", ctx),
        "quote sent": render_whatsapp_template("quoted", ctx),
        "appointment reminder": render_whatsapp_template("appointment_reminder", ctx),
    }

    return render_template("leads/detail.html", lead=lead, activities=activities, note_form=note_form, follow_up_form=follow_form, status_form=status_form, whatsapp_templates=whatsapp_templates)


@leads_bp.route("/<int:lead_id>/convert", methods=["POST"])
@login_required
@permission_required("patients.manage")
def convert(lead_id):
    lead = TenantGuard.get_or_404(Lead, lead_id)
    patient = convert_lead_to_patient(lead, current_user)
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, patient_id=patient.id, action="lead.convert", details="Lead converted"))
    db.session.commit()
    flash("Lead converted to patient", "success")
    return redirect(url_for("patients.patient_detail", patient_id=patient.id))


@leads_bp.route("/<int:lead_id>/delete", methods=["POST"])
@login_required
@permission_required("leads.manage")
def delete_lead(lead_id):
    lead = TenantGuard.get_or_404(Lead, lead_id)
    lead.deleted_at = datetime.utcnow()
    lead.deleted_by = current_user.id
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="lead.soft_delete", details="Lead deleted"))
    db.session.commit()
    flash("Lead archived", "success")
    return redirect(url_for("leads.list_leads"))
