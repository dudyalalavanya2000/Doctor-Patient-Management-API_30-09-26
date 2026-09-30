import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


# =========================
# Database Configuration
# =========================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./doctor_patient.db"
)


# =========================
# Database Engine
# =========================

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_foreign_keys(
        dbapi_connection,
        connection_record
    ):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine = create_engine(DATABASE_URL)


# =========================
# Session Configuration
# =========================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =========================
# Base Model
# =========================

Base = declarative_base()


# =========================
# Database Dependency
# =========================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()