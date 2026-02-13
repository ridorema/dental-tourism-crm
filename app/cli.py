from datetime import datetime, timedelta

import click

from app.extensions import db
from app.models import Call, Clinic, Conversation, Lead, Message, Payment, PipelineStage, Quote, User


ROLES = ["admin", "agent", "doctor", "finance"]


def _create_user(clinic_id, role, email_prefix):
    user = User(
        clinic_id=clinic_id,
        full_name=f"{role.title()} User",
        email=f"{email_prefix}+{role}@example.com",
        role=role,
        is_active_user=True,
    )
    user.set_password(f"{role}12345")
    return user


@click.command("seed-demo-data")
def seed_demo_data():
    if Clinic.query.filter_by(slug="tirana-smile").first():
        click.echo("Demo data already exists.")
        return

    clinics = [
        Clinic(name="Tirana Smile Clinic", slug="tirana-smile", default_currency="EUR", timezone="Europe/Tirane", default_language="it", languages_json=["it", "en"]),
        Clinic(name="Durres Dental Hub", slug="durres-dental", default_currency="EUR", timezone="Europe/Tirane", default_language="en", languages_json=["en", "it", "de"]),
    ]
    db.session.add_all(clinics)
    db.session.flush()

    for clinic in clinics:
        for idx, role in enumerate(ROLES, start=1):
            db.session.add(_create_user(clinic.id, role, clinic.slug))

        db.session.add_all(
            [
                PipelineStage(clinic_id=clinic.id, name="New", stage_key="new", sort_order=1, is_default=True),
                PipelineStage(clinic_id=clinic.id, name="Contacted", stage_key="contacted", sort_order=2),
                PipelineStage(clinic_id=clinic.id, name="Qualified", stage_key="qualified", sort_order=3),
                PipelineStage(clinic_id=clinic.id, name="Quoted", stage_key="quoted", sort_order=4),
                PipelineStage(clinic_id=clinic.id, name="Accepted", stage_key="accepted", sort_order=5),
                PipelineStage(clinic_id=clinic.id, name="Completed", stage_key="completed", sort_order=6),
            ]
        )

    db.session.flush()

    tirana_admin = User.query.filter_by(email="tirana-smile+admin@example.com").first()
    tirana_agent = User.query.filter_by(email="tirana-smile+agent@example.com").first()

    lead = Lead(
        clinic_id=clinics[0].id,
        assigned_agent_id=tirana_agent.id,
        first_name="Marco",
        last_name="Rossi",
        email="marco.rossi@example.it",
        phone="+39 333 123 4567",
        source="google_ads",
        status="quoted",
        stage_key="quoted",
        language="it",
        country="Italy",
        notes="Interested in implants",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="implants_it",
        gclid="demo-gclid-123",
        landing_page_url="https://clinic.example/implants",
        referrer_url="https://google.com",
        user_agent="seed",
        ip_hash="seed-hash",
        next_action_date=datetime.utcnow().date() + timedelta(days=1),
    )
    db.session.add(lead)
    db.session.flush()

    quote = Quote(
        clinic_id=clinics[0].id,
        lead_id=lead.id,
        currency="EUR",
        total=4500,
        status="sent",
        sent_at=datetime.utcnow() - timedelta(days=2),
    )
    db.session.add(quote)
    db.session.flush()

    payment = Payment(
        clinic_id=clinics[0].id,
        quote_id=quote.id,
        amount=1000,
        currency="EUR",
        method="bank_transfer",
        status="pending",
        due_date=datetime.utcnow().date() + timedelta(days=5),
    )
    db.session.add(payment)

    conversation = Conversation(
        clinic_id=clinics[0].id,
        lead_id=lead.id,
        channel="whatsapp",
        external_id="stub-conv-1",
        last_message_at=datetime.utcnow() - timedelta(hours=2),
        status="open",
    )
    db.session.add(conversation)
    db.session.flush()

    db.session.add_all(
        [
            Message(clinic_id=clinics[0].id, conversation_id=conversation.id, direction="inbound", body="Ciao, vorrei informazioni"),
            Message(clinic_id=clinics[0].id, conversation_id=conversation.id, direction="outbound", body="Ciao Marco, ti invio il preventivo oggi"),
            Call(
                clinic_id=clinics[0].id,
                lead_id=lead.id,
                direction="outbound",
                from_number="+355690000001",
                to_number=lead.phone,
                started_at=datetime.utcnow() - timedelta(hours=3),
                ended_at=datetime.utcnow() - timedelta(hours=3, minutes=-4),
                duration_seconds=240,
                status="completed",
                provider_call_id="stub-call-seed-1",
            ),
        ]
    )

    # second clinic isolation sample
    db.session.add(
        Lead(
            clinic_id=clinics[1].id,
            first_name="Anna",
            last_name="Muller",
            source="website_form",
            status="new",
            stage_key="new",
            language="de",
            country="Germany",
            notes="Asks for all-on-4 package",
        )
    )

    db.session.commit()

    click.echo("Seeded 2 clinics with users, attribution leads, conversation and call stubs.")
    click.echo("Login example: clinic=tirana-smile email=tirana-smile+admin@example.com password=admin12345")



def register_cli(app):
    app.cli.add_command(seed_demo_data)
