from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.authz import permission_required
from app.extensions import db
from app.models import User
from app.services.activity_service import log_activity
from app.tenancy import TenantGuard


users_bp = Blueprint("users", __name__, url_prefix="/users")


class UserCreateForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = SelectField("Role", choices=[("admin", "admin"), ("agent", "agent"), ("doctor", "doctor"), ("finance", "finance")], validators=[DataRequired()])
    password = PasswordField("Initial password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Create User")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Reset Password")


@users_bp.route("/", methods=["GET", "POST"])
@login_required
@permission_required("users.manage")
def list_users():
    form = UserCreateForm(prefix="create")
    if form.validate_on_submit() and form.submit.data:
        existing = TenantGuard.scoped_query(User, include_deleted=True).filter(User.email == form.email.data.strip().lower()).first()
        if existing:
            flash("User with this email already exists in this clinic.", "danger")
            return redirect(url_for("users.list_users"))

        user = User(
            clinic_id=current_user.clinic_id,
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            is_active_user=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="users.create", details=f"Created user {user.email}"))
        db.session.commit()
        flash("User created", "success")
        return redirect(url_for("users.list_users"))

    users = TenantGuard.scoped_query(User, include_deleted=True).order_by(User.created_at.desc()).all()
    return render_template("users/list.html", users=users, form=form)


@users_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
@permission_required("users.manage")
def toggle_user(user_id):
    user = TenantGuard.get_or_404(User, user_id, include_deleted=True)
    if user.id == current_user.id:
        flash("You cannot disable your own account.", "danger")
        return redirect(url_for("users.list_users"))

    user.is_active_user = not user.is_active_user
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="users.toggle", details=f"User {user.email} active={user.is_active_user}"))
    db.session.commit()
    flash("User status updated", "success")
    return redirect(url_for("users.list_users"))


@users_bp.route("/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@permission_required("users.manage")
def reset_password(user_id):
    user = TenantGuard.get_or_404(User, user_id, include_deleted=True)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="users.reset_password", details=f"Reset password for {user.email}"))
        db.session.commit()
        flash("Password reset", "success")
        return redirect(url_for("users.list_users"))

    return render_template("users/reset_password.html", form=form, target_user=user)


@users_bp.route("/<int:user_id>/role", methods=["POST"])
@login_required
@permission_required("users.manage")
def update_role(user_id):
    user = TenantGuard.get_or_404(User, user_id, include_deleted=True)
    new_role = request.form.get("role", "").strip()
    if new_role not in {"admin", "agent", "doctor", "finance"}:
        flash("Invalid role", "danger")
        return redirect(url_for("users.list_users"))

    user.role = new_role
    db.session.add(log_activity(clinic_id=current_user.clinic_id, user_id=current_user.id, action="users.role_update", details=f"Role updated for {user.email} -> {new_role}"))
    db.session.commit()
    flash("Role updated", "success")
    return redirect(url_for("users.list_users"))
