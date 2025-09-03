from flask import Blueprint, request, jsonify
from sqlalchemy import select, or_
from database import SessionLocal
from models import Professional, Specialty

prof_public_bp = Blueprint("prof_public", __name__)

@prof_public_bp.get("/specialties")
def get_specialties():
    profession = request.args.get("profession")
    with SessionLocal() as db:
        stmt = select(Specialty)
        if profession in ("psychology", "nutrition"):
            stmt = stmt.where(Specialty.profession == profession)
        items = db.scalars(stmt.order_by(Specialty.name.asc())).all()
        return jsonify([{
            "id": s.id, "profession": s.profession, "name": s.name, "slug": s.slug
        } for s in items])

@prof_public_bp.get("/professionals")
def list_professionals():
    profession = request.args.get("profession")
    city = request.args.get("city")
    modality = request.args.get("modality")
    price_min = request.args.get("price_min", type=int)
    price_max = request.args.get("price_max", type=int)
    term = request.args.get("q")

    with SessionLocal() as db:
        stmt = select(Professional).where(Professional.is_active == True)  # noqa: E712
        if profession in ("psychology", "nutrition"):
            stmt = stmt.where(Professional.profession == profession)
        if city:
            stmt = stmt.where(Professional.city.ilike(f"%{city}%"))
        if modality in ("online", "presencial"):
            stmt = stmt.where(Professional.modalities.like(f"%{modality}%"))
        if price_min is not None:
            stmt = stmt.where(Professional.price_cents >= price_min)
        if price_max is not None:
            stmt = stmt.where(Professional.price_cents <= price_max)
        if term:
            like = f"%{term}%"
            stmt = stmt.where(or_(Professional.full_name.ilike(like), Professional.bio.ilike(like)))

        # ordena pelo preço (crescente) como padrão
        stmt = stmt.order_by(Professional.price_cents.asc())
        items = db.scalars(stmt).all()

        def to_dict(p: Professional):
            return {
                "id": p.id,
                "full_name": p.full_name,
                "profession": p.profession,
                "register_code": p.register_code,
                "city": p.city,
                "state": p.state,
                "avatar_url": p.avatar_url,
                "whatsapp": p.whatsapp,
                "price_cents": p.price_cents,
                "session_minutes": p.session_minutes,
                "modalities": p.modalities.split(",") if p.modalities else [],
                "rating": float(p.rating) if p.rating is not None else None
            }

        return jsonify({"items": [to_dict(p) for p in items]})

@prof_public_bp.get("/professionals/<int:pid>")
def get_professional(pid: int):
    with SessionLocal() as db:
        p = db.get(Professional, pid)
        if not p:
            return jsonify({"error": "not_found"}), 404
        return jsonify({
            "id": p.id,
            "full_name": p.full_name,
            "profession": p.profession,
            "register_code": p.register_code,
            "city": p.city,
            "state": p.state,
            "bio": p.bio,
            "avatar_url": p.avatar_url,
            "whatsapp": p.whatsapp,
            "price_cents": p.price_cents,
            "session_minutes": p.session_minutes,
            "modalities": p.modalities.split(",") if p.modalities else [],
            "rating": float(p.rating) if p.rating is not None else None
        })
