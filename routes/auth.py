import jwt
import requests
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from flask import Blueprint, request, jsonify, redirect, session
from sqlalchemy import select

from config import Config
from database import SessionLocal
from models import User
from services.security import hash_pwd, check_pwd

AUTH_URI  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Serializer para tokens de reset (24h por padrão no verify)
RESET_SALT = "password-reset"
serializer = URLSafeTimedSerializer(Config.APP_SECRET, salt=RESET_SALT)

auth_bp = Blueprint("auth", __name__)

# -------------------- Helpers de e-mail --------------------
def _send_email(to_email: str, subject: str, html: str):
    """
    Envia e-mail via SMTP (Gmail/app password). Usa as variáveis:
    MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD
    """
    host = (Config.__dict__.get("MAIL_SERVER") or "smtp.googlemail.com")
    port = int(Config.__dict__.get("MAIL_PORT") or 587)
    use_tls = str(Config.__dict__.get("MAIL_USE_TLS", True)).lower() in ("1", "true", "yes")
    username = Config.__dict__.get("MAIL_USERNAME")
    password = Config.__dict__.get("MAIL_PASSWORD")

    if not username or not password:
        # Evita quebrar fluxo se não configurado — apenas loga
        print("[WARN] MAIL_USERNAME/MAIL_PASSWORD não configurados; e-mail não enviado.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_email
    msg.set_content("Seu cliente não suporta HTML.\n\n" + html, charset="utf-8")
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.send_message(msg)

# -------------------- Auth local --------------------
@auth_bp.post("/auth/register")
def auth_register():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    pwd   = data.get("password") or ""
    if not email or not pwd:
        return jsonify({"error": "email e senha são obrigatórios"}), 400

    with SessionLocal() as db:
        if db.scalars(select(User).where(User.email == email)).first():
            return jsonify({"error": "email já cadastrado"}), 409
        u = User(email=email, password_hash=hash_pwd(pwd))
        db.add(u)
        db.commit()
    session["email"] = email
    return jsonify({"ok": True, "email": email})

@auth_bp.post("/auth/login")
def auth_login():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    pwd   = data.get("password") or ""
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u or not check_pwd(pwd, u.password_hash):
            return jsonify({"error": "credenciais inválidas"}), 401
    session["email"] = email
    return jsonify({"ok": True, "email": email})

@auth_bp.post("/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True})

@auth_bp.get("/me")
def me():
    return jsonify({"email": session.get("email")})

# -------------------- Forgot / Reset password --------------------
@auth_bp.post("/auth/forgot-password")
def forgot_password():
    data = request.get_json(force=True)
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email é obrigatório"}), 400

    # Não revelar se usuário existe ou não
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()

    # Gera token sempre (mesmo se não existe, para não expor informação)
    token = serializer.dumps({"email": email})
    reset_link = f"{Config.FRONT_URL}/reset-password/{token}"

    # Se existir usuário, envia o e-mail; se não, “no-op”
    if u:
        html = f"""
        <h2>Recuperação de senha - Saúde Plus</h2>
        <p>Você solicitou a redefinição de senha.</p>
        <p>Clique no link abaixo para criar uma nova senha (válido por 24 horas):</p>
        <p><a href="{reset_link}" target="_blank">{reset_link}</a></p>
        <p>Se você não solicitou, ignore este e-mail.</p>
        """
        try:
            _send_email(email, "Recuperação de Senha - Saúde Plus", html)
        except Exception as e:
            # Não quebre a UX; apenas logue
            print("[MAIL ERROR]", e)

    # Resposta genérica
    return jsonify({"ok": True})

@auth_bp.post("/auth/reset-password")
def reset_password():
    data = request.get_json(force=True)
    token = data.get("token")
    new_pwd = data.get("password")
    if not token or not new_pwd:
        return jsonify({"error": "token e password são obrigatórios"}), 400

    try:
        payload = serializer.loads(token, max_age=60*60*24)  # 24h
        email = (payload.get("email") or "").lower()
    except SignatureExpired:
        return jsonify({"error": "token expirado"}), 400
    except BadSignature:
        return jsonify({"error": "token inválido"}), 400

    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            return jsonify({"error": "usuário não encontrado"}), 404
        u.password_hash = hash_pwd(new_pwd)
        db.commit()

    return jsonify({"ok": True})

# -------------------- Google Login (sem calendar aqui) --------------------
def _google_login_redirect(redirect_uri: str):
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "include_granted_scopes": "true",
        "state": "login"
    }
    return redirect(f"{AUTH_URI}?{urlencode(params)}")

def _exchange_code_for_tokens(redirect_uri: str):
    code = request.args.get("code")
    if not code:
        return None, (jsonify({"error": "código ausente"}), 400)
    data = {
        "code": code,
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    tok = requests.post(TOKEN_URI, data=data, timeout=20).json()
    if "id_token" not in tok:
        return None, (jsonify({"error": "id_token não recebido", "raw": tok}), 400)
    return tok, None

def _finish_login_with_id_token(id_token: str):
    # Em produção, valide a assinatura!
    claims = jwt.decode(id_token, options={"verify_signature": False})
    email = (claims.get("email") or "").lower()
    sub   = claims.get("sub")
    if not email:
        return jsonify({"error": "email não encontrado no id_token"}), 400

    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            u = db.scalars(select(User).where(User.google_sub == sub)).first()
        if u:
            u.google_sub = sub
        else:
            u = User(email=email, google_sub=sub)
            db.add(u)
        db.commit()

    session["email"] = email
    return redirect(f"{Config.FRONT_URL}{Config.FRONT_LOGIN_REDIRECT_PATH}")

@auth_bp.get("/auth/google/login")
def google_login():
    redirect_uri = f"{Config.BASE_URL}/oauth2/callback/login"
    return _google_login_redirect(redirect_uri)

@auth_bp.get("/oauth2/callback/login")
def oauth_login_callback():
    redirect_uri = f"{Config.BASE_URL}/oauth2/callback/login"
    tok, err = _exchange_code_for_tokens(redirect_uri)
    if err:
        return err
    return _finish_login_with_id_token(tok["id_token"])
