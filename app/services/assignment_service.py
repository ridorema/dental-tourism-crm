from app.extensions import db
from app.models import AssignmentRule, Lead, User


def assign_next_lead_for_clinic(clinic_id):
    rule = AssignmentRule.query.filter_by(clinic_id=clinic_id).order_by(AssignmentRule.created_at.desc()).first()
    mode = rule.mode if rule else "round_robin"

    lead = (
        Lead.query.filter_by(clinic_id=clinic_id, assigned_agent_id=None)
        .filter(Lead.status == "new", Lead.deleted_at.is_(None))
        .order_by(Lead.created_at.asc())
        .first()
    )
    if not lead:
        return None

    agents = User.query.filter_by(clinic_id=clinic_id, role="agent", is_active_user=True).order_by(User.id.asc()).all()
    if not agents:
        return None

    if mode == "manual":
        return lead

    idx = lead.id % len(agents)
    lead.assigned_agent_id = agents[idx].id
    db.session.add(lead)
    return lead
