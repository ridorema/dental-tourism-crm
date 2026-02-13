from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, send_from_directory, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.authz import permission_required
from app.extensions import db
from app.models import Lead, Patient, Quote, TreatmentPlan
from app.services.activity_service import log_activity
from app.services.conversion_service import create_conversion_event_for_lead
from app.services.email_service import send_quote_email_stub
from app.services.pdf_service import generate_quote_pdf
from app.services.quote_service import calculate_quote_total
from app.tenancy import TenantGuard


quotes_bp = Blueprint("quotes", __name__, url_prefix="/quotes")


class QuoteForm(FlaskForm):
    lead_id = SelectField("Lead", coerce=int, validators=[DataRequired()])
    currency = SelectField("Currency", choices=[("EUR", "EUR"), ("USD", "USD")], validators=[DataRequired()])
    item_label = StringField("Item", validators=[DataRequired()])
    quantity = DecimalField("Quantity", default=1, validators=[DataRequired()])
    unit_price = DecimalField("Unit price", validators=[DataRequired()])
    notes = TextAreaField("Plan notes", validators=[Optional()])
    submit = SubmitField("Create quote")


@quotes_bp.route("/")
@login_required
@permission_required("quotes.manage")
def list_quotes():
    quotes = TenantGuard.scoped_query(Quote).order_by(Quote.created_at.desc()).all()
    return render_template("quotes/list.html", quotes=quotes)


@quotes_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("quotes.manage")
def create_quote():
    form = QuoteForm()
    leads = TenantGuard.scoped_query(Lead).filter(Lead.status.in_(["new", "contacted", "qualified", "quoted", "accepted"])).all()
    form.lead_id.choices = [(lead.id, f"#{lead.id} {lead.first_name} {lead.last_name}") for lead in leads]

    if form.validate_on_submit():
        lead = TenantGuard.get_or_404(Lead, form.lead_id.data)
        patient = TenantGuard.scoped_query(Patient).filter(Patient.lead_id == lead.id).first()

        items = [{"label": form.item_label.data, "quantity": float(form.quantity.data), "unit_price": float(form.unit_price.data)}]
        treatment_plan = TreatmentPlan(clinic_id=current_user.clinic_id, lead_id=lead.id, patient_id=patient.id if patient else None, items=items, notes=form.notes.data)
        db.session.add(treatment_plan)
        db.session.flush()

        quote = Quote(
            clinic_id=current_user.clinic_id,
            lead_id=lead.id,
            patient_id=patient.id if patient else None,
            treatment_plan_id=treatment_plan.id,
            currency=form.currency.data,
            total=calculate_quote_total(items),
            status="draft",
        )
        db.session.add(quote)
        lead.status = "quoted"
        lead.stage_key = "quoted"

        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, quote_id=quote.id, action="quote.created", details=f"Quote {quote.id} created"))
        db.session.commit()

        flash("Quote created", "success")
        return redirect(url_for("quotes.list_quotes"))

    return render_template("quotes/new.html", form=form)


@quotes_bp.route("/<int:quote_id>/send", methods=["POST"])
@login_required
@permission_required("quotes.manage")
def send_quote(quote_id):
    quote = TenantGuard.get_or_404(Quote, quote_id)
    lead = TenantGuard.scoped_query(Lead).filter(Lead.id == quote.lead_id).first()

    if not quote.pdf_url:
        quote.pdf_url = generate_quote_pdf(quote=quote, lead=lead, clinic=current_user.clinic)

    quote.status = "sent"
    quote.sent_at = datetime.utcnow()
    email_result = send_quote_email_stub(quote=quote, recipient_email=lead.email if lead else "")

    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=quote.lead_id, quote_id=quote.id, action="quote.sent", details=f"email_stub={email_result['sent']} recipient={email_result['recipient']}"))
    db.session.commit()

    flash("Quote sent (stub)", "success")
    return redirect(url_for("quotes.list_quotes"))


@quotes_bp.route("/<int:quote_id>/pdf")
@login_required
@permission_required("quotes.manage")
def download_quote_pdf(quote_id):
    quote = TenantGuard.get_or_404(Quote, quote_id)
    lead = TenantGuard.scoped_query(Lead).filter(Lead.id == quote.lead_id).first()
    if not quote.pdf_url:
        quote.pdf_url = generate_quote_pdf(quote=quote, lead=lead, clinic=current_user.clinic)
        db.session.commit()

    pdf_path = Path(quote.pdf_url)
    return send_from_directory(Path(current_app.root_path) / pdf_path.parent, pdf_path.name, as_attachment=True)


@quotes_bp.route("/<int:quote_id>/accept", methods=["POST"])
@login_required
@permission_required("quotes.manage")
def accept_quote(quote_id):
    quote = TenantGuard.get_or_404(Quote, quote_id)
    quote.status = "accepted"
    quote.accepted_at = datetime.utcnow()

    lead = TenantGuard.scoped_query(Lead).filter(Lead.id == quote.lead_id).first()
    if lead:
        lead.status = "accepted"
        lead.stage_key = "accepted"
        create_conversion_event_for_lead(lead, conversion_name="Quote Accepted", value=quote.total, currency=quote.currency)

    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=quote.lead_id, quote_id=quote.id, action="quote.accepted", details="Quote accepted"))
    db.session.commit()
    flash("Quote accepted", "success")
    return redirect(url_for("quotes.list_quotes"))
