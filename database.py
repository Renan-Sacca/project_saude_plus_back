from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
import os

ECHO = os.getenv("SQLALCHEMY_ECHO", "0") == "1"

engine = create_engine(
    Config.DATABASE_URL,
    echo=ECHO,
    pool_pre_ping=True,
    future=True
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
