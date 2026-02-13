from datetime import date, datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from app.models import Call, Lead, Message, Payment, Quote
from app.tenancy import TenantGuard


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    start_of_month = date.today().replace(day=1)

    new_leads_7d = TenantGuard.scoped_query(Lead).filter(Lead.created_at >= seven_days_ago).count()
    active_leads = TenantGuard.scoped_query(Lead).filter(Lead.status.in_(["new", "contacted", "qualified", "quoted", "accepted"])).count()
    quotes_sent = TenantGuard.scoped_query(Quote).filter(Quote.status == "sent").count()
    due_followups = TenantGuard.scoped_query(Lead).filter(Lead.next_action_date.isnot(None), Lead.next_action_date <= date.today(), Lead.status.notin_(["lost", "completed"])).count()

    revenue_this_month = TenantGuard.scoped_query(Payment).filter(Payment.status == "paid", Payment.paid_at >= start_of_month).with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    outstanding_balance = TenantGuard.scoped_query(Payment).filter(Payment.status == "pending").with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    calls_today = TenantGuard.scoped_query(Call).filter(Call.created_at >= today_start).count()
    answered_calls = TenantGuard.scoped_query(Call).filter(Call.created_at >= today_start, Call.status == "completed").count()
    answer_rate = round((answered_calls / calls_today) * 100, 2) if calls_today else 0
    avg_duration = TenantGuard.scoped_query(Call).filter(Call.created_at >= today_start, Call.duration_seconds.isnot(None)).with_entities(func.coalesce(func.avg(Call.duration_seconds), 0)).scalar()

    messages_today = TenantGuard.scoped_query(Message).filter(Message.created_at >= today_start, Message.direction == "outbound").count()

    funnel = {
        "new": TenantGuard.scoped_query(Lead).filter(Lead.status == "new").count(),
        "quoted": TenantGuard.scoped_query(Lead).filter(Lead.status == "quoted").count(),
        "accepted": TenantGuard.scoped_query(Lead).filter(Lead.status == "accepted").count(),
        "completed": TenantGuard.scoped_query(Lead).filter(Lead.status == "completed").count(),
    }

    return render_template(
        "dashboard/index.html",
        kpis={
            "new_leads_7d": new_leads_7d,
            "active_leads": active_leads,
            "quotes_sent": quotes_sent,
            "due_followups": due_followups,
            "revenue_this_month": revenue_this_month,
            "outstanding_balance": outstanding_balance,
            "calls_today": calls_today,
            "answer_rate": answer_rate,
            "avg_duration": round(float(avg_duration), 2) if avg_duration else 0,
            "messages_today": messages_today,
            "funnel": funnel,
            "currency": current_user.clinic.default_currency,
            "clinic": current_user.clinic,
        },
    )
