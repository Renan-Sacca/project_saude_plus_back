# routes/profile.py
from flask import Blueprint, jsonify, request, session
from sqlalchemy import select
from database import SessionLocal
from models import User, Professional

profile_bp = Blueprint("profile", __name__)

@profile_bp.get("/api/me")
def me():
    email = session.get("email")
    if not email:
        return jsonify({"error": "not_authenticated"}), 401
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            return jsonify({"error": "not_found"}), 404
        # checar se é profissional (tem Professional vinculado por user_id)
        pro = db.scalars(select(Professional).where(Professional.user_id == u.id)).first()
        return jsonify({
            "email": u.email,
            "name": u.name or "",
            "phone": u.phone or "",
            "is_professional": bool(pro),
            "professional_id": pro.id if pro else None
        })

@profile_bp.put("/api/me")
def update_me():
    email = session.get("email")
    if not email:
        return jsonify({"error": "not_authenticated"}), 401
    data = request.get_json(force=True)
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == email)).first()
        if not u:
            return jsonify({"error": "not_found"}), 404
        # Campos básicos pro "user comum"
        if "name" in data:  u.name = data["name"] or None
        if "phone" in data: u.phone = data["phone"] or None
        db.commit()
        return jsonify({"ok": True})
