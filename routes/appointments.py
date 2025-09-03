from datetime import datetime
from flask import Blueprint, request, jsonify, abort, session
from sqlalchemy import select
from database import SessionLocal
from models import Appointment, Professional, User
# Reaproveita sua função de refresh de access_token
from routes.calendar import _get_access_token_or_refresh

appointments_bp = Blueprint("appointments", __name__, url_prefix="/")

@appointments_bp.post("/appointments")
def create_appointment():
    email = session.get("email")
    if not email:
        return jsonify({"error": "não autenticado"}), 401

    body = request.get_json(force=True)
    prof_id = int(body["professional_id"])
    starts_at = datetime.fromisoformat(body["starts_at"])
    ends_at = datetime.fromisoformat(body["ends_at"])

    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            return jsonify({"error": "usuário não encontrado"}), 404

        p = db.get(Professional, prof_id)
        if not p or not p.is_active:
            return jsonify({"error": "profissional indisponível"}), 404

        appt = Appointment(
            professional_id=p.id,
            user_id=u.id,
            starts_at=starts_at,
            ends_at=ends_at,
            price_cents=p.price_cents,
            status="confirmed"
        )
        db.add(appt)
        db.commit()

        # Tenta criar evento no Calendar se o usuário estiver conectado
        if u.google_refresh_token:
            try:
                at = _get_access_token_or_refresh(u)  # atualiza access token se necessário
                db.add(u); db.commit()
                event = {
                    "summary": f"Sessão com {p.full_name}",
                    "start": {"dateTime": starts_at.isoformat(), "timeZone": "America/Sao_Paulo"},
                    "end":   {"dateTime": ends_at.isoformat(),   "timeZone": "America/Sao_Paulo"},
                }
                import requests
                r = requests.post(
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    headers={"Authorization": f"Bearer {at}", "Content-Type": "application/json"},
                    json=event,
                    timeout=20
                )
                data = r.json()
                if r.ok and data.get("id"):
                    appt.google_event_id = data["id"]
                    db.commit()
            except Exception as e:
                # Não quebra o fluxo de agendamento
                print("[Calendar] Falhou ao criar evento:", e)

        return jsonify({"id": appt.id})
