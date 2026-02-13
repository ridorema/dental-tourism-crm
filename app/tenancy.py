from functools import wraps

from flask import abort
from flask_login import current_user


class TenantGuard:
    @staticmethod
    def require_user_clinic(clinic_id):
        if not current_user.is_authenticated:
            abort(401)
        if clinic_id != current_user.clinic_id:
            abort(404)

    @staticmethod
    def scoped_query(model, include_deleted=False):
        if not current_user.is_authenticated:
            abort(401)
        query = model.query.filter(model.clinic_id == current_user.clinic_id)
        if hasattr(model, "deleted_at") and not include_deleted:
            query = query.filter(model.deleted_at.is_(None))
        return query

    @staticmethod
    def get_or_404(model, object_id, include_deleted=False):
        obj = TenantGuard.scoped_query(model, include_deleted=include_deleted).filter(model.id == object_id).first()
        if obj is None:
            abort(404)
        return obj


def clinic_query(model, include_deleted=False):
    return TenantGuard.scoped_query(model, include_deleted=include_deleted)


def require_clinic_object(obj):
    if obj is None:
        abort(404)
    TenantGuard.require_user_clinic(obj.clinic_id)
    if hasattr(obj, "deleted_at") and obj.deleted_at is not None:
        abort(404)
    return obj


def scoped_route(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return view_func(*args, **kwargs)

    return wrapped
