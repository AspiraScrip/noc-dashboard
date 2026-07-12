import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para acessar o painel."
login_manager.login_message_category = "warning"

_monitor_started = False


def create_app(config_name=None):
    global _monitor_started

    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    from config import config_by_name
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth import auth_bp
    from app.routes import main_bp
    from app.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        _ensure_default_admin()

        if not _monitor_started and not app.config.get("TESTING"):
            from app.monitor import start_monitor
            start_monitor(app)
            _monitor_started = True

    return app


def _ensure_default_admin():
    from app.models import User
    if User.query.count() == 0:
        admin = User(username="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
