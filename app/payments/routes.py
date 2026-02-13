from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional

from app.authz import permission_required
from app.extensions import db
from app.models import Payment, Quote
from app.services.activity_service import log_activity
from app.tenancy import TenantGuard


payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


class PaymentForm(FlaskForm):
    quote_id = SelectField("Quote", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Amount", validators=[DataRequired()])
    currency = SelectField("Currency", choices=[("EUR", "EUR"), ("USD", "USD")], validators=[DataRequired()])
    method = SelectField("Method", choices=[("bank_transfer", "Bank transfer"), ("cash", "Cash"), ("card", "Card")], validators=[DataRequired()])
    due_date = DateField("Due date", validators=[Optional()])
    submit = SubmitField("Record payment")


@payments_bp.route("/")
@login_required
@permission_required("payments.manage")
def list_payments():
    payments = TenantGuard.scoped_query(Payment).order_by(Payment.created_at.desc()).all()
    outstanding = TenantGuard.scoped_query(Payment).filter(Payment.status == "pending").with_entities(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar()
    return render_template("payments/list.html", payments=payments, outstanding=outstanding)


@payments_bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("payments.manage")
def create_payment():
    form = PaymentForm()
    quotes = TenantGuard.scoped_query(Quote).filter(Quote.status.in_(["sent", "accepted"]))
    form.quote_id.choices = [(quote.id, f"#{quote.id} {quote.total} {quote.currency}") for quote in quotes]

    if form.validate_on_submit():
        quote = TenantGuard.get_or_404(Quote, form.quote_id.data)
        payment = Payment(
            clinic_id=current_user.clinic_id,
            quote_id=quote.id,
            patient_id=quote.patient_id,
            amount=form.amount.data,
            currency=form.currency.data,
            method=form.method.data,
            status="pending",
            due_date=form.due_date.data,
        )
        db.session.add(payment)
        db.session.flush()
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=quote.lead_id, quote_id=quote.id, payment_id=payment.id, action="payment.recorded", details=f"Payment {payment.id} recorded"))
        db.session.commit()
        flash("Payment recorded", "success")
        return redirect(url_for("payments.list_payments"))

    return render_template("payments/new.html", form=form)


@payments_bp.route("/<int:payment_id>/mark-paid", methods=["POST"])
@login_required
@permission_required("payments.manage")
def mark_paid(payment_id):
    payment = TenantGuard.get_or_404(Payment, payment_id)
    payment.status = "paid"
    payment.paid_at = datetime.utcnow()

    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=None, quote_id=payment.quote_id, payment_id=payment.id, action="payment.paid", details=f"Payment {payment.id} marked paid"))
    db.session.commit()

    flash("Payment marked as paid", "success")
    return redirect(url_for("payments.list_payments"))
