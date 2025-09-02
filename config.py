import os
from dotenv import load_dotenv

# Carrega .env assim que a config é importada
load_dotenv()

def _build_db_url_from_parts() -> str | None:
    user = os.getenv("DB_USER")
    pwd  = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    db   = os.getenv("DB_NAME")
    if all([user, pwd, host, db]):
        return f"mysql+mysqlconnector://{user}:{pwd}@{host}/{db}?charset=utf8mb4"
    return None

class Config:
    # Segredo / sessão
    APP_SECRET = os.getenv("APP_SECRET") or os.getenv("SECRET_KEY", "dev-secret")

    # URLs (padronizado em 127.0.0.1 para DEV)
    BASE_URL  = os.getenv("BASE_URL", "http://127.0.0.1:5000")
    FRONT_URL = os.getenv("FRONT_URL", "http://127.0.0.1:5173")
    FRONT_LOGIN_REDIRECT_PATH = os.getenv("FRONT_LOGIN_REDIRECT_PATH", "/auth/callback")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

    # Banco de dados
    DATABASE_URL = os.getenv("DATABASE_URL") or _build_db_url_from_parts() or "sqlite:///./dev.db"

    # Cookies de sessão (DEV http)
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE   = False

    # ---- E-mail (usado pelos endpoints de forgot/reset) ----
    MAIL_SERVER   = os.getenv("MAIL_SERVER", "smtp.googlemail.com")
    MAIL_PORT     = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS  = str(os.getenv("MAIL_USE_TLS", "True")).lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")            # ex.: seuemail@gmail.com
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")            # senha de app do Gmail
    MAIL_FROM     = os.getenv("MAIL_FROM", MAIL_USERNAME) # remetente (default = username)
