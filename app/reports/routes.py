from collections import defaultdict

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.authz import permission_required
from app.models import Lead, Payment
from app.tenancy import TenantGuard


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@login_required
@permission_required("reports.view")
def index():
    leads_by_source = (
        TenantGuard.scoped_query(Lead)
        .with_entities(Lead.source, func.count(Lead.id))
        .group_by(Lead.source)
        .order_by(func.count(Lead.id).desc())
        .all()
    )

    total_leads = TenantGuard.scoped_query(Lead).count()
    won_leads = TenantGuard.scoped_query(Lead).filter(Lead.status.in_(["accepted", "completed"])).count()
    conversion_rate = round((won_leads / total_leads) * 100, 2) if total_leads else 0

    paid_payments = TenantGuard.scoped_query(Payment).filter(Payment.status == "paid", Payment.paid_at.isnot(None)).all()
    revenue_map = defaultdict(float)
    for payment in paid_payments:
        revenue_map[payment.paid_at.strftime("%Y-%m")] += float(payment.amount)

    monthly_revenue = sorted(revenue_map.items(), key=lambda x: x[0], reverse=True)

    return render_template("reports/index.html", leads_by_source=leads_by_source, total_leads=total_leads, won_leads=won_leads, conversion_rate=conversion_rate, monthly_revenue=monthly_revenue)
