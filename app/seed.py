from werkzeug.security import generate_password_hash
from sqlalchemy import inspect

def seed_if_empty(db, Clinic, User):
    # If tables aren't created yet, do nothing (migrations will create them first)
    try:
        inspector = inspect(db.engine)
        if "clinics" not in inspector.get_table_names():
            return
    except Exception:
        return

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
    db.session.flush()

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