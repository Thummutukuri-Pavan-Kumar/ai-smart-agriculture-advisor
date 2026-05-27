# backend/db.py
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sagri-db")

# Read DB env vars
DB_USER = os.getenv("MYSQL_USER")
DB_PASS = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DB")

# Optional: control SQLAlchemy echo for debugging (default False)
DB_ECHO = os.getenv("DB_ECHO", "False").lower() in ("1", "true", "yes")

# Build DATABASE_URL and engine
if DB_USER and DB_PASS and DB_HOST and DB_NAME:
    # Option A: mysql+mysqlconnector (if you use mysql-connector-python)
    # DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Option B (safer/popular): pymysql (install with pip install pymysql)
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    logger.info("Using MySQL database at %s:%s/%s", DB_HOST, DB_PORT, DB_NAME)
    engine = create_engine(DATABASE_URL, echo=DB_ECHO, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base = declarative_base()
else:
    # fallback sqlite for fast local development
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sqlite_dir = os.path.join(project_dir, "data")
    os.makedirs(sqlite_dir, exist_ok=True)
    sqlite_path = os.path.join(sqlite_dir, "agri_advisor_dev.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    logger.info("Using SQLite fallback DB at %s", sqlite_path)
    # For SQLite we must set check_same_thread=False
    engine = create_engine(DATABASE_URL, echo=DB_ECHO, future=True, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base = declarative_base()

# Export symbols
__all__ = ["engine", "SessionLocal", "Base", "DATABASE_URL"]
