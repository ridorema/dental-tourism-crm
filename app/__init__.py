from flask import Flask

from .api.routes import api_bp
from .auth.routes import auth_bp
from .communications.routes import communications_bp
from .dashboard.routes import dashboard_bp
from .extensions import db, login_manager, migrate
from .integrations.routes import integrations_bp
from .leads.routes import leads_bp
from .models import User
from .patients.routes import patients_bp
from .payments.routes import payments_bp
from .quotes.routes import quotes_bp
from .reports.routes import reports_bp
from .settings.routes import settings_bp
from .users.routes import users_bp


def create_app(config_object="app.config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .cli import register_cli
    register_cli(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(quotes_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(communications_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    # ✅ Auto-seed only if empty
    with app.app_context():
        from .models import Clinic, User
        from .seed import seed_if_empty
        seed_if_empty(db, Clinic, User)

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))