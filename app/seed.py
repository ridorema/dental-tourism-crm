# app/seed.py
from werkzeug.security import generate_password_hash

def seed_if_empty(db, Clinic, User):
    # if at least one clinic exists, do nothing
    if db.session.query(Clinic).first():
        return

    clinic = Clinic(
        name="Tirana Smile",
        slug="tirana-smile",
        country="Albania",
        timezone="Europe/Tirane",
        default_currency="EUR",
        default_language="it",
    )
    db.session.add(clinic)
    db.session.flush()  # get clinic.id without full commit

    admin = User(
        clinic_id=clinic.id,
        email="admin@demo.com",
        first_name="Admin",
        last_name="Demo",
        role="admin",
        password_hash=generate_password_hash("Admin12345!"),
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()
