"""Configuración centralizada y logging estructurado de Py2Java Edu."""

import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

_log_level_name = (os.environ.get("LOG_LEVEL") or "INFO").strip().upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logging.Formatter.converter = time.gmtime
logger = logging.getLogger("py2java")
logger.setLevel(_log_level)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
is_production = (
    is_vercel
    or os.environ.get("FLASK_ENV", "").strip().lower() == "production"
    or os.environ.get("APP_ENV", "").strip().lower() == "production"
    or os.environ.get("ENV", "").strip().lower() == "production"
)

_initial_db_url = os.environ.get("DATABASE_URL") or ""
is_postgres = bool(
    _initial_db_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg2://"))
)


def configure_app(app, config_overrides=None):
    """Configura secretos, cookies, base de datos y opciones del motor SQLAlchemy."""
    global is_vercel, is_production, is_postgres

    is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    is_production = (
        is_vercel
        or os.environ.get("FLASK_ENV", "").strip().lower() == "production"
        or os.environ.get("APP_ENV", "").strip().lower() == "production"
        or os.environ.get("ENV", "").strip().lower() == "production"
    )

    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if config_overrides and config_overrides.get("SECRET_KEY"):
        secret = str(config_overrides["SECRET_KEY"]).strip()

    if is_production:
        if not secret or len(secret) < 32:
            raise RuntimeError(
                "Configuración insegura: la variable de entorno SECRET_KEY es obligatoria en producción "
                "y debe tener al menos 32 caracteres."
            )
    elif not secret:
        secret = os.urandom(32).hex()
        logger.warning(
            "SECRET_KEY no configurada en desarrollo local. Usando clave temporal aleatoria."
        )
    elif len(secret) < 32:
        logger.warning(
            "SECRET_KEY tiene menos de 32 caracteres. Usa una clave de al menos 32 caracteres en producción."
        )

    app.secret_key = secret
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = is_production
    app.config["IS_VERCEL"] = is_vercel
    app.config["IS_PRODUCTION"] = is_production

    database_url = os.environ.get("DATABASE_URL")
    if config_overrides and "SQLALCHEMY_DATABASE_URI" in config_overrides:
        database_url = config_overrides["SQLALCHEMY_DATABASE_URI"]

    is_postgres = bool(
        database_url
        and database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg2://"))
    )

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        if (
            is_postgres
            and "sslmode=" not in database_url
            and "localhost" not in database_url
            and "127.0.0.1" not in database_url
        ):
            separator = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{separator}sslmode=require"
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

        if is_vercel:
            from sqlalchemy.pool import NullPool

            engine_options = {
                "pool_pre_ping": True,
                "poolclass": NullPool,
            }
            if is_postgres:
                engine_options["connect_args"] = {"connect_timeout": 10}
        elif is_postgres:
            engine_options = {
                "pool_pre_ping": True,
                "pool_size": 2,
                "max_overflow": 3,
                "pool_recycle": 280,
                "connect_args": {"connect_timeout": 10},
            }
        else:
            engine_options = {"pool_pre_ping": True}
    else:
        if is_vercel:
            sqlite_path = "/tmp/database_v2.sqlite"
        else:
            sqlite_path = os.path.join(PROJECT_ROOT, "database_v2.sqlite")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + sqlite_path
        engine_options = {"pool_pre_ping": True}

    app.config["IS_POSTGRES"] = is_postgres
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
    app.config.setdefault(
        "RATELIMIT_STORAGE_URI",
        os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    )

    if config_overrides:
        app.config.update(config_overrides)
