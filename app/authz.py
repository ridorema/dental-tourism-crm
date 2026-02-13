from functools import wraps

from flask import abort
from flask_login import current_user

ROLE_PERMISSIONS = {
    "admin": {
        "users.manage",
        "settings.manage",
        "integrations.manage",
        "communications.use",
        "leads.manage",
        "patients.manage",
        "quotes.manage",
        "appointments.manage",
        "payments.manage",
        "reports.view",
        "gdpr.manage",
    },
    "agent": {
        "communications.use",
        "leads.manage",
        "patients.manage",
        "quotes.manage",
        "appointments.manage",
        "reports.view",
    },
    "doctor": {
        "patients.assigned",
        "appointments.manage",
        "clinical_notes.manage",
        "communications.use",
    },
    "finance": {
        "payments.manage",
        "reports.view",
        "invoices.manage",
        "communications.use",
    },
}


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def permission_required(*permissions):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            allowed = ROLE_PERMISSIONS.get(current_user.role, set())
            if not set(permissions).issubset(allowed):
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
