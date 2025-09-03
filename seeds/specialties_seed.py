# seed_all.py
"""
Seed completo para:
- specialties
- professionals
- professional_specialties (vínculos)
- locations
- availability
- appointments (alguns exemplos)
Idempotente (não duplica se rodar de novo).

Como rodar:
    python seed_all.py
"""

from datetime import datetime, timedelta, time
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import SessionLocal, engine
from models import Base, Specialty, Professional, ProfessionalSpecialty, Location, Availability, Appointment

# ---------- CONFIG DO SEED ----------

PSY_SPECIALTIES = [
    ("Psicanálise", "psicanalise"),
    ("TCC", "tcc"),
    ("Ansiedade", "ansiedade"),
    ("Depressão", "depressao"),
]

NUT_SPECIALTIES = [
    ("Emagrecimento", "emagrecimento"),
    ("Esportiva", "esportiva"),
    ("Clínica", "clinica"),
    ("Vegana", "vegana"),
]

PROFESSIONALS = [
    # Psicologia
    {
        "full_name": "Dra. Ana Pereira",
        "profession": "psychology",
        "register_code": "CRP 06/123456",
        "city": "São Paulo",
        "state": "SP",
        "bio": "Psicóloga com 10+ anos de experiência em Psicanálise e TCC.",
        "avatar_url": None,
        "whatsapp": "+5511999990001",
        "price_cents": 8000,
        "session_minutes": 50,
        "modalities": "online,presencial",
        "rating": 4.8,
        "is_active": True,
        # Slugs das especialidades para vincular
        "specialties": ["psicanalise", "tcc", "ansiedade"],
        # Endereços (opcional)
        "locations": [
            {"address": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP", "lat": None, "lng": None, "is_primary": True}
        ],
        # Disponibilidade semanal (0=Dom..6=Sáb)
        "availability": [
            {"weekday": 1, "start": "09:00:00", "end": "12:00:00"},
            {"weekday": 3, "start": "14:00:00", "end": "18:00:00"},
        ],
    },
    # Psicologia
    {
        "full_name": "Dr. Bruno Costa",
        "profession": "psychology",
        "register_code": "CRP 07/654321",
        "city": "Rio de Janeiro",
        "state": "RJ",
        "bio": "Atuação em ansiedade e depressão com abordagem integrativa.",
        "avatar_url": None,
        "whatsapp": "+5521999990002",
        "price_cents": 6000,
        "session_minutes": 50,
        "modalities": "online",
        "rating": 4.6,
        "is_active": True,
        "specialties": ["ansiedade", "depressao"],
        "locations": [],
        "availability": [
            {"weekday": 2, "start": "10:00:00", "end": "12:00:00"},
            {"weekday": 4, "start": "15:00:00", "end": "17:00:00"},
        ],
    },
    # Nutrição
    {
        "full_name": "Nutri. Camila Souza",
        "profession": "nutrition",
        "register_code": "CRN 03/888888",
        "city": "Curitiba",
        "state": "PR",
        "bio": "Nutricionista clínica e esportiva, foco em emagrecimento saudável.",
        "avatar_url": None,
        "whatsapp": "+5541999990003",
        "price_cents": 7000,
        "session_minutes": 60,
        "modalities": "online,presencial",
        "rating": 4.7,
        "is_active": True,
        "specialties": ["emagrecimento", "esportiva", "clinica"],
        "locations": [
            {"address": "Rua XV de Novembro, 500 - Centro, Curitiba - PR", "lat": None, "lng": None, "is_primary": True}
        ],
        "availability": [
            {"weekday": 1, "start": "09:00:00", "end": "11:30:00"},
            {"weekday": 5, "start": "13:30:00", "end": "16:30:00"},
        ],
    },
]

# Alguns agendamentos de exemplo (opcional)
# Os horários são gerados para amanhã conforme a availability do profissional (se existir).
CREATE_SAMPLE_APPOINTMENTS = True


# ---------- FUNÇÕES AUXILIARES ----------

def ensure_tables():
    """Cria as tabelas definidas em models.py, sem dropar as existentes."""
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)

def get_specialty_by_slug(db, slug: str) -> Specialty | None:
    return db.scalars(select(Specialty).where(Specialty.slug == slug)).first()

def get_professional_by_name(db, name: str) -> Professional | None:
    return db.scalars(select(Professional).where(Professional.full_name == name)).first()

def upsert_specialty(db, profession: str, name: str, slug: str) -> Specialty:
    s = get_specialty_by_slug(db, slug)
    if s:
        # Atualiza nome/profissão caso tenha mudado
        s.name = name
        s.profession = profession
        db.flush()
        return s
    s = Specialty(profession=profession, name=name, slug=slug)
    db.add(s)
    db.flush()
    return s

def upsert_professional(db, data: dict) -> Professional:
    p = get_professional_by_name(db, data["full_name"])
    if p:
        # Atualiza campos básicos se já existir
        p.profession       = data["profession"]
        p.register_code    = data.get("register_code")
        p.city             = data.get("city")
        p.state            = data.get("state")
        p.bio              = data.get("bio")
        p.avatar_url       = data.get("avatar_url")
        p.whatsapp         = data.get("whatsapp")
        p.price_cents      = data.get("price_cents", 0)
        p.session_minutes  = data.get("session_minutes", 50)
        p.modalities       = data.get("modalities", "online")
        p.rating           = data.get("rating")
        p.is_active        = data.get("is_active", True)
        db.flush()
        return p

    p = Professional(
        full_name=data["full_name"],
        profession=data["profession"],
        register_code=data.get("register_code"),
        city=data.get("city"),
        state=data.get("state"),
        bio=data.get("bio"),
        avatar_url=data.get("avatar_url"),
        whatsapp=data.get("whatsapp"),
        price_cents=data.get("price_cents", 0),
        session_minutes=data.get("session_minutes", 50),
        modalities=data.get("modalities", "online"),
        rating=data.get("rating"),
        is_active=data.get("is_active", True),
        user_id=data.get("user_id"),
    )
    db.add(p)
    db.flush()
    return p

def ensure_professional_specialties(db, professional_id: int, specialty_slugs: list[str]):
    # Carrega todas existentes para comparar
    existing = {
        s.specialty_id
        for s in db.scalars(
            select(ProfessionalSpecialty).where(ProfessionalSpecialty.professional_id == professional_id)
        ).all()
    }
    # Conjunto alvo
    target_ids = set()
    for slug in specialty_slugs or []:
        spec = get_specialty_by_slug(db, slug)
        if spec:
            target_ids.add(spec.id)

    # Inserir os que faltam
    for sid in target_ids - existing:
        db.add(ProfessionalSpecialty(professional_id=professional_id, specialty_id=sid))

    # Remover os que sobraram
    for sid in existing - target_ids:
        ps = db.scalars(
            select(ProfessionalSpecialty).where(
                ProfessionalSpecialty.professional_id == professional_id,
                ProfessionalSpecialty.specialty_id == sid
            )
        ).first()
        if ps:
            db.delete(ps)

def ensure_locations(db, professional_id: int, locations: list[dict]):
    # Estratégia idempotente simples: se o profissional não tiver localização, cria as informadas;
    # se já tiver, não mexe (para não apagar nada manual).
    has_any = db.scalars(select(Location).where(Location.professional_id == professional_id)).first()
    if has_any:
        return
    for loc in locations or []:
        db.add(Location(
            professional_id=professional_id,
            address=loc["address"],
            lat=loc.get("lat"),
            lng=loc.get("lng"),
            is_primary=bool(loc.get("is_primary", True))
        ))

def ensure_availability(db, professional_id: int, availability: list[dict]):
    # Mesma estratégia: só cria se não existir nenhuma (para não sobrescrever mudanças manuais)
    has_any = db.scalars(select(Availability).where(Availability.professional_id == professional_id)).first()
    if has_any:
        return
    for av in availability or []:
        db.add(Availability(
            professional_id=professional_id,
            weekday=int(av["weekday"]),
            start_time=av["start"],
            end_time=av["end"]
        ))

def create_sample_appointments(db, professional: Professional, days_ahead: int = 1):
    """Cria 1 ou 2 agendamentos de exemplo para amanhã, se houver availability."""
    av = db.scalars(select(Availability).where(Availability.professional_id == professional.id)).all()
    if not av:
        return

    # pega a primeira janela da semana e agenda "amanhã" dentro dela
    tomorrow = (datetime.now().date() + timedelta(days=days_ahead))
    # vamos só marcar 2 horários dentro da primeira janela, se couber
    first = av[0]
    start_hh, start_mm, _ = map(int, first.start_time.split(":"))
    end_hh, end_mm, _ = map(int, first.end_time.split(":"))

    # slot 1
    s1 = datetime.combine(tomorrow, time(hour=start_hh, minute=start_mm))
    e1 = s1 + timedelta(minutes=professional.session_minutes)
    if s1.time() < time(hour=end_hh, minute=end_mm):
        db.add(Appointment(
            professional_id=professional.id,
            user_id=1,  # se tiver um usuário 1; se não, apenas não cria ou ajuste aqui
            starts_at=s1,
            ends_at=e1,
            price_cents=professional.price_cents,
            status="confirmed"
        ))

    # slot 2 (se couber)
    s2 = e1 + timedelta(minutes=10)
    e2 = s2 + timedelta(minutes=professional.session_minutes)
    if e2.time() <= time(hour=end_hh, minute=end_mm):
        db.add(Appointment(
            professional_id=professional.id,
            user_id=1,
            starts_at=s2,
            ends_at=e2,
            price_cents=professional.price_cents,
            status="confirmed"
        ))

# ---------- EXECUÇÃO DO SEED ----------

def main():
    # Garante que as tabelas existem (não derruba nada)
    ensure_tables()

    with SessionLocal() as db:
        # 1) Specialties (upsert por slug)
        for name, slug in PSY_SPECIALTIES:
            upsert_specialty(db, "psychology", name, slug)
        for name, slug in NUT_SPECIALTIES:
            upsert_specialty(db, "nutrition", name, slug)
        db.commit()

        # 2) Professionals + vinculações + locais + availability
        for pdata in PROFESSIONALS:
            p = upsert_professional(db, pdata)
            db.commit()

            ensure_professional_specialties(db, p.id, pdata.get("specialties", []))
            ensure_locations(db, p.id, pdata.get("locations", []))
            ensure_availability(db, p.id, pdata.get("availability", []))
            db.commit()

            # 3) Appointments de exemplo (opcional)
            if CREATE_SAMPLE_APPOINTMENTS:
                try:
                    create_sample_appointments(db, p)
                    db.commit()
                except IntegrityError:
                    db.rollback()

    print("Seed concluído com sucesso.")

if __name__ == "__main__":
    main()
