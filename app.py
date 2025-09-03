from flask import Flask
from flask_cors import CORS
from config import Config
from routes.auth import auth_bp
from routes.calendar import calendar_bp
from routes.health import health_bp

# NOVOS blueprints
from routes.professionals_public import prof_public_bp
from routes.professionals_admin import prof_admin_bp
from routes.appointments import appointments_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = Config.APP_SECRET

    # CORS com credenciais
    CORS(app, origins=[Config.FRONT_URL], supports_credentials=True)

    # Cookies de sessão (DEV http)
    app.config.update(
        SESSION_COOKIE_NAME="saude_session",
        SESSION_COOKIE_SAMESITE=Config.SESSION_COOKIE_SAMESITE,
        SESSION_COOKIE_SECURE=Config.SESSION_COOKIE_SECURE,
        SESSION_COOKIE_DOMAIN=None,  # host-only
    )

    # Blueprints existentes
    app.register_blueprint(auth_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(health_bp)

    # Blueprints novos
    app.register_blueprint(prof_public_bp)
    app.register_blueprint(prof_admin_bp)
    app.register_blueprint(appointments_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
