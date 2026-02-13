from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.authz import permission_required
from app.extensions import db
from app.models import ActivityLog, Call, CallDisposition, Conversation, Lead, Message
from app.providers.factory import get_voice_provider, get_whatsapp_provider
from app.services.activity_service import log_activity
from app.services.assignment_service import assign_next_lead_for_clinic
from app.tenancy import TenantGuard


communications_bp = Blueprint("communications", __name__, url_prefix="/communications")


class MessageForm(FlaskForm):
    body = TextAreaField("Message", validators=[DataRequired()])
    submit = SubmitField("Send")


class CallForm(FlaskForm):
    to_number = StringField("Phone", validators=[DataRequired()])
    submit = SubmitField("Call")


class DispositionForm(FlaskForm):
    outcome = SelectField("Outcome", choices=[("answered", "Answered"), ("no_answer", "No answer"), ("busy", "Busy"), ("wrong_number", "Wrong number")], validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Optional()])
    followup_at = DateTimeLocalField("Follow-up", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Save Disposition")


@communications_bp.route("/inbox")
@login_required
@permission_required("communications.use")
def inbox():
    conversations = TenantGuard.scoped_query(Conversation).order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc()).all()
    return render_template("communications/inbox.html", conversations=conversations)


@communications_bp.route("/thread/<int:conversation_id>", methods=["GET", "POST"])
@login_required
@permission_required("communications.use")
def thread(conversation_id):
    conversation = TenantGuard.get_or_404(Conversation, conversation_id)
    message_form = MessageForm(prefix="msg")
    call_form = CallForm(prefix="call")

    if message_form.submit.data and message_form.validate_on_submit():
        provider = get_whatsapp_provider()
        to_number = request.form.get("to_number", "")
        provider_result = provider.send_text(clinic_id=current_user.clinic_id, to_number=to_number, body=message_form.body.data, conversation_external_id=conversation.external_id)

        msg = Message(
            clinic_id=current_user.clinic_id,
            conversation_id=conversation.id,
            direction="outbound",
            body=message_form.body.data,
            provider_message_id=provider_result.get("provider_message_id"),
        )
        conversation.last_message_at = datetime.utcnow()
        db.session.add(msg)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=conversation.lead_id, patient_id=conversation.patient_id, action="message.sent", details=message_form.body.data[:200]))
        db.session.commit()
        flash("Message sent", "success")
        return redirect(url_for("communications.thread", conversation_id=conversation.id))

    if call_form.submit.data and call_form.validate_on_submit():
        provider = get_voice_provider()
        from_number = "+355690000001"
        result = provider.initiate_call(clinic_id=current_user.clinic_id, from_number=from_number, to_number=call_form.to_number.data, lead_id=conversation.lead_id, patient_id=conversation.patient_id)

        call = Call(
            clinic_id=current_user.clinic_id,
            lead_id=conversation.lead_id,
            patient_id=conversation.patient_id,
            direction="outbound",
            from_number=result["from_number"],
            to_number=result["to_number"],
            started_at=result.get("started_at"),
            status=result.get("status", "ringing"),
            provider_call_id=result.get("provider_call_id"),
        )
        db.session.add(call)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=conversation.lead_id, patient_id=conversation.patient_id, action="call.started", details=f"to={call.to_number}"))
        db.session.commit()
        flash("Call started in stub mode", "success")
        return redirect(url_for("communications.thread", conversation_id=conversation.id))

    messages = TenantGuard.scoped_query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    calls = TenantGuard.scoped_query(Call).filter(Call.lead_id == conversation.lead_id).order_by(Call.created_at.desc()).all()
    disposition_form = DispositionForm(prefix="disp")

    return render_template("communications/thread.html", conversation=conversation, messages=messages, calls=calls, message_form=message_form, call_form=call_form, disposition_form=disposition_form)


@communications_bp.route("/calls/<int:call_id>/disposition", methods=["POST"])
@login_required
@permission_required("communications.use")
def save_disposition(call_id):
    call = TenantGuard.get_or_404(Call, call_id)
    form = DispositionForm(prefix="disp")
    if form.validate_on_submit():
        disposition = CallDisposition(
            clinic_id=current_user.clinic_id,
            call_id=call.id,
            outcome=form.outcome.data,
            notes=form.notes.data,
            followup_at=form.followup_at.data,
        )
        db.session.add(disposition)

        if call.lead_id and form.followup_at.data:
            lead = TenantGuard.scoped_query(Lead).filter(Lead.id == call.lead_id).first()
            if lead:
                lead.next_action_date = form.followup_at.data.date()

        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=call.lead_id, patient_id=call.patient_id, action="call.disposition", details=form.outcome.data))
        db.session.commit()
        flash("Disposition saved", "success")

    return redirect(request.referrer or url_for("communications.inbox"))


@communications_bp.route("/queue")
@login_required
@permission_required("communications.use")
def queue():
    new_leads = TenantGuard.scoped_query(Lead).filter(Lead.status == "new").order_by(Lead.created_at.asc()).all()
    followups = TenantGuard.scoped_query(Lead).filter(Lead.next_action_date.isnot(None), Lead.next_action_date <= datetime.utcnow().date(), Lead.status.notin_(["lost", "completed"])).order_by(Lead.next_action_date.asc()).all()
    missed_calls = TenantGuard.scoped_query(Call).filter(Call.status.in_(["failed", "missed", "no_answer"]))
    missed_calls = missed_calls.order_by(Call.created_at.desc()).limit(50).all()

    return render_template("communications/queue.html", new_leads=new_leads, followups=followups, missed_calls=missed_calls)


@communications_bp.route("/queue/assign-next", methods=["POST"])
@login_required
@permission_required("communications.use")
def assign_next():
    lead = assign_next_lead_for_clinic(current_user.clinic_id)
    if not lead:
        flash("No unassigned new lead available", "warning")
        return redirect(url_for("communications.queue"))

    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, lead_id=lead.id, action="queue.assign_next", details=f"Assigned lead to agent {lead.assigned_agent_id}"))
    db.session.commit()
    flash(f"Lead #{lead.id} assigned to agent {lead.assigned_agent_id}", "success")
    return redirect(url_for("communications.queue"))


@communications_bp.route("/timeline/lead/<int:lead_id>")
@login_required
@permission_required("communications.use")
def lead_timeline(lead_id):
    page = request.args.get("page", 1, type=int)
    per_page = 25

    lead = TenantGuard.get_or_404(Lead, lead_id)
    events = []

    messages = (
        TenantGuard.scoped_query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.lead_id == lead.id)
        .all()
    )
    for msg in messages:
        events.append({"at": msg.created_at, "type": "message", "title": msg.direction, "body": msg.body})

    calls = TenantGuard.scoped_query(Call).filter(Call.lead_id == lead.id).all()
    for call in calls:
        events.append({"at": call.created_at, "type": "call", "title": call.status, "body": f"{call.from_number} -> {call.to_number}"})

    logs = TenantGuard.scoped_query(ActivityLog).filter(ActivityLog.lead_id == lead.id).all()
    for item in logs:
        events.append({"at": item.created_at, "type": "activity", "title": item.action, "body": item.details or ""})

    events.sort(key=lambda x: x["at"], reverse=True)
    start = (page - 1) * per_page
    end = start + per_page
    paged = events[start:end]
    has_next = end < len(events)

    return render_template("communications/timeline.html", lead=lead, events=paged, page=page, has_next=has_next)


@communications_bp.route("/softphone")
@login_required
@permission_required("communications.use")
def softphone_panel():
    return render_template("communications/softphone.html")
