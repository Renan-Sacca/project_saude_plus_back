from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Enum, Boolean, ForeignKey, Numeric, SmallInteger
from datetime import datetime

# ===============================
# Seu código existente (mantido)
# ===============================

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str]           = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None]    = mapped_column(String(255), unique=False, nullable=True)
    google_access_token: Mapped[str | None]  = mapped_column(String(2048), nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    google_token_expiry: Mapped[int | None]  = mapped_column(Integer, nullable=True)

# ==========================================
# Novas tabelas (acrescentadas ao seu modelo)
# ==========================================

class Specialty(Base):
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Mantemos as verticais que você quer: psicologia e nutrição
    profession: Mapped[str] = mapped_column(
        Enum("psychology", "nutrition", name="spec_profession"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)


class Professional(Base):
    __tablename__ = "professionals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Se o profissional também tiver login no sistema, podemos ligar ao users.id
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    profession: Mapped[str] = mapped_column(
        Enum("psychology", "nutrition", name="profession"),
        nullable=False
    )
    register_code: Mapped[str | None] = mapped_column(String(40), nullable=True)  # CRP/CRN/etc
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=50)
    # "online", "presencial" ou "online,presencial"
    modalities: Mapped[str] = mapped_column(String(40), nullable=False, default="online")
    rating: Mapped[Numeric | None] = mapped_column(Numeric(3, 2), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # relacionamentos
    specialties: Mapped[list["ProfessionalSpecialty"]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )
    locations: Mapped[list["Location"]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )
    availability: Mapped[list["Availability"]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )


class ProfessionalSpecialty(Base):
    __tablename__ = "professional_specialties"
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"), primary_key=True)

    professional: Mapped["Professional"] = relationship(back_populates="specialties")
    specialty: Mapped["Specialty"] = relationship()


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)

    address: Mapped[str] = mapped_column(String(200), nullable=False)
    lat: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)
    lng: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    professional: Mapped["Professional"] = relationship(back_populates="locations")


class Availability(Base):
    __tablename__ = "availability"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)

    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Dom .. 6=Sáb
    start_time: Mapped[str] = mapped_column(String(8), nullable=False)  # "HH:MM:SS"
    end_time: Mapped[str] = mapped_column(String(8), nullable=False)

    professional: Mapped["Professional"] = relationship(back_populates="availability")


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "confirmed", "cancelled", name="appt_status"),
        nullable=False,
        default="pending"
    )
    google_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    professional: Mapped["Professional"] = relationship(back_populates="appointments")
    user: Mapped["User"] = relationship()
