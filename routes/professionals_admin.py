from flask import Blueprint, request, jsonify, abort, session
from sqlalchemy import select, delete
from database import SessionLocal
from models import Professional, ProfessionalSpecialty, Availability, Location

prof_admin_bp = Blueprint("prof_admin", __name__, url_prefix="/admin")

def is_admin() -> bool:
    # MVP: exige estar logado. Troque por regra real de admin depois.
    return bool(session.get("email"))

@prof_admin_bp.post("/professionals")
def create_professional():
    if not is_admin():
        abort(403)
    data = request.get_json(force=True)
    with SessionLocal() as db:
        p = Professional(
            full_name=data["full_name"],
            profession=data["profession"],
            register_code=data.get("register_code"),
            city=data.get("city"),
            state=data.get("state"),
            bio=data.get("bio"),
            avatar_url=data.get("avatar_url"),
            whatsapp=data.get("whatsapp"),
            price_cents=int(data.get("price_cents", 0)),
            session_minutes=int(data.get("session_minutes", 50)),
            modalities=",".join(data.get("modalities", ["online"])),
            rating=data.get("rating"),
            is_active=bool(data.get("is_active", True)),
            user_id=data.get("user_id")
        )
        db.add(p)
        db.commit()
        # vincular especialidades (opcional)
        for sid in data.get("specialty_ids", []) or []:
            db.add(ProfessionalSpecialty(professional_id=p.id, specialty_id=int(sid)))
        db.commit()
        return jsonify({"id": p.id}), 201

@prof_admin_bp.put("/professionals/<int:pid>")
def update_professional(pid: int):
    if not is_admin():
        abort(403)
    data = request.get_json(force=True)
    with SessionLocal() as db:
        p = db.get(Professional, pid)
        if not p:
            return jsonify({"error": "not_found"}), 404
        for field in ["full_name","profession","register_code","city","state","bio",
                      "avatar_url","whatsapp","price_cents","session_minutes","rating","is_active","user_id"]:
            if field in data:
                setattr(p, field, data[field])
        if "modalities" in data:
            p.modalities = ",".join(data["modalities"])
        db.commit()

        if "specialty_ids" in data:
            db.execute(
                delete(ProfessionalSpecialty).where(ProfessionalSpecialty.professional_id == p.id)
            )
            for sid in data["specialty_ids"] or []:
                db.add(ProfessionalSpecialty(professional_id=p.id, specialty_id=int(sid)))
            db.commit()
        return jsonify({"ok": True})

@prof_admin_bp.delete("/professionals/<int:pid>")
def delete_professional(pid: int):
    if not is_admin():
        abort(403)
    with SessionLocal() as db:
        p = db.get(Professional, pid)
        if not p:
            return jsonify({"error": "not_found"}), 404
        db.delete(p)
        db.commit()
        return jsonify({"ok": True})

@prof_admin_bp.post("/professionals/<int:pid>/availability")
def add_availability(pid: int):
    if not is_admin():
        abort(403)
    data = request.get_json(force=True)
    with SessionLocal() as db:
        av = Availability(
            professional_id=pid,
            weekday=int(data["weekday"]),
            start_time=data["start_time"],
            end_time=data["end_time"]
        )
        db.add(av)
        db.commit()
        return jsonify({"id": av.id}), 201

@prof_admin_bp.post("/professionals/<int:pid>/locations")
def add_location(pid: int):
    if not is_admin():
        abort(403)
    data = request.get_json(force=True)
    with SessionLocal() as db:
        loc = Location(
            professional_id=pid,
            address=data["address"],
            lat=data.get("lat"),
            lng=data.get("lng"),
            is_primary=bool(data.get("is_primary", True))
        )
        db.add(loc)
        db.commit()
        return jsonify({"id": loc.id}), 201
