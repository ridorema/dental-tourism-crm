import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parent

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = database_url or f"sqlite:///{BASE_DIR / 'app.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    PER_PAGE = int(os.getenv("PER_PAGE", "20"))

    LEAD_API_KEY = os.getenv("LEAD_API_KEY", "change-this-key")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    AUTH_RATE_LIMIT_COUNT = int(os.getenv("AUTH_RATE_LIMIT_COUNT", "10"))
    AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
    API_RATE_LIMIT_COUNT = int(os.getenv("API_RATE_LIMIT_COUNT", "30"))
    API_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "60"))

    DATA_HASH_SALT = os.getenv("DATA_HASH_SALT", "dev-hash-salt")

    ENABLE_CAPTCHA = os.getenv("ENABLE_CAPTCHA", "0") == "1"
    CAPTCHA_PROVIDER = os.getenv("CAPTCHA_PROVIDER", "turnstile")
    CAPTCHA_SECRET = os.getenv("CAPTCHA_SECRET", "")

    WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "stub")
    VOICE_PROVIDER = os.getenv("VOICE_PROVIDER", "stub")
