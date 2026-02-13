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

    # Keep seed compatible with both legacy and current User schemas.
    user_kwargs = {
        "clinic_id": clinic.id,
        "email": "admin@demo.com",
        "role": "admin",
        "password_hash": generate_password_hash("Admin12345!"),
    }

    if hasattr(User, "full_name"):
        user_kwargs["full_name"] = "Admin Demo"
    else:
        user_kwargs["first_name"] = "Admin"
        user_kwargs["last_name"] = "Demo"

    if hasattr(User, "is_active_user"):
        user_kwargs["is_active_user"] = True
    elif hasattr(User, "is_active"):
        user_kwargs["is_active"] = True

    admin = User(**user_kwargs)
    db.session.add(admin)
    db.session.commit()
