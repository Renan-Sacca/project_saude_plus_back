import time
import requests
import jwt
from urllib.parse import urlencode
from flask import Blueprint, request, jsonify, redirect, session
from sqlalchemy import select

from config import Config
from database import SessionLocal
from models import User

AUTH_URI  = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

calendar_bp = Blueprint("calendar", __name__)

@calendar_bp.get("/calendar/status")
def calendar_status():
    email = session.get("email")
    if not email:
        return jsonify({"connected": False, "reason": "not_logged"})
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        return jsonify({"connected": bool(u and u.google_refresh_token)})

@calendar_bp.get("/auth/google/calendar")
def google_calendar_connect():
    if not session.get("email"):
        return redirect(Config.FRONT_URL)
    redirect_uri = f"{Config.BASE_URL}/oauth2/callback/calendar"
    params = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": "calendar",
    }
    return redirect(f"{AUTH_URI}?{urlencode(params)}")

@calendar_bp.get("/oauth2/callback/calendar")
def oauth_calendar_callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "código ausente"}), 400

    redirect_uri = f"{Config.BASE_URL}/oauth2/callback/calendar"
    data = {
        "code": code,
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    tok = requests.post(TOKEN_URI, data=data, timeout=20).json()
    access_token  = tok.get("access_token")
    refresh_token = tok.get("refresh_token")
    expires_in    = int(tok.get("expires_in", 3600))

    email = session.get("email")
    if not email and tok.get("id_token"):
        claims = jwt.decode(tok["id_token"], options={"verify_signature": False})
        email = (claims.get("email") or "").lower()
    if not email:
        return jsonify({"error": "sem sessão/email para salvar tokens", "raw": tok}), 400

    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            u = User(email=email)
            db.add(u)
        u.google_access_token  = access_token
        u.google_token_expiry  = int(time.time()) + expires_in
        if refresh_token:
            u.google_refresh_token = refresh_token
        db.commit()

    return redirect(f"{Config.FRONT_URL}/calendar")

def _get_access_token_or_refresh(u: User) -> str:
    now = int(time.time())
    if not u.google_refresh_token:
        raise RuntimeError("Calendar não conectado para este usuário.")
    if not u.google_access_token or now >= int(u.google_token_expiry or 0) - 60:
        data = {
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "refresh_token": u.google_refresh_token,
            "grant_type": "refresh_token",
        }
        tok = requests.post(TOKEN_URI, data=data, timeout=20).json()
        if "access_token" not in tok:
            raise RuntimeError(f"Falha ao renovar token: {tok}")
        u.google_access_token = tok["access_token"]
        u.google_token_expiry = now + int(tok.get("expires_in", 3600))
    return u.google_access_token

@calendar_bp.post("/calendar/events")
def create_event():
    email = session.get("email")
    if not email:
        return jsonify({"error": "não autenticado"}), 401

    body = request.get_json(force=True)
    summary = body.get("summary") or "Novo evento"
    description = body.get("description")
    start = body.get("start")
    end   = body.get("end")
    tz    = body.get("timeZone") or "America/Sao_Paulo"
    create_meet = bool(body.get("createMeet"))

    if not start or not end:
        return jsonify({"error": "start e end são obrigatórios"}), 400

    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start, "timeZone": tz},
        "end":   {"dateTime": end,   "timeZone": tz},
    }
    params = {}
    if create_meet:
        event["conferenceData"] = {"createRequest": {"requestId": f"meet-{int(time.time())}"}}
        params["conferenceDataVersion"] = 1

    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            return jsonify({"error": "usuário não encontrado"}), 404
        try:
            at = _get_access_token_or_refresh(u)
            db.add(u); db.commit()
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    r = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json"},
        params=params,
        json=event,
        timeout=20
    )
    try:
        data = r.json()
    except Exception:
        return (r.text, r.status_code, {"Content-Type": "application/json"})
    return jsonify(data), r.status_code
