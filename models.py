from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer

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
