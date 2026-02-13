from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email

from app.extensions import db
from app.models import Clinic, LoginAttempt, User
from app.security import rate_limiter, request_ip_hash
from app.services.activity_service import log_activity


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    clinic_slug = StringField("Workspace", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


def _auth_limited():
    key = f"auth:{request_ip_hash()}"
    return rate_limiter.is_limited(
        key=key,
        limit=current_app.config["AUTH_RATE_LIMIT_COUNT"],
        window_seconds=current_app.config["AUTH_RATE_LIMIT_WINDOW_SECONDS"],
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        if _auth_limited():
            flash("Too many login attempts. Try again later.", "danger")
            return render_template("auth/login.html", form=form)

        clinic_slug = form.clinic_slug.data.strip().lower()
        email = form.email.data.strip().lower()

        clinic = Clinic.query.filter_by(slug=clinic_slug).first()
        user = None
        if clinic:
            user = User.query.filter_by(clinic_id=clinic.id, email=email).first()

        success = bool(user and user.check_password(form.password.data) and user.is_active_user)

        db.session.add(
            LoginAttempt(
                clinic_id=clinic.id if clinic else None,
                email=email,
                ip_hash=request_ip_hash(),
                user_agent=request.headers.get("User-Agent", "")[:255],
                success=success,
            )
        )

        if success:
            user.last_login_at = datetime.utcnow()
            login_user(user)
            db.session.add(
                log_activity(
                    clinic_id=user.clinic_id,
                    user_id=user.id,
                    action="auth.login.success",
                    details="User logged in",
                )
            )
            db.session.commit()
            return redirect(request.args.get("next") or url_for("dashboard.index"))

        db.session.add(
            log_activity(
                clinic_id=clinic.id if clinic else None,
                action="auth.login.failed",
                details=f"Failed login for {email}",
            )
        )
        db.session.commit()
        flash("Invalid credentials or disabled user", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(
        log_activity(
            clinic_id=current_user.clinic_id,
            user_id=current_user.id,
            action="auth.logout",
            details="User logged out",
        )
    )
    db.session.commit()
    logout_user()
    flash("Logged out", "success")
    return redirect(url_for("auth.login"))
