import csv
import hashlib
import hmac
import html
from io import StringIO
import json
import math
import os
import random
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

import click
import requests as http_requests
from flask import (Flask, Response, flash, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from sqlalchemy import func, or_
from werkzeug.security import check_password_hash, generate_password_hash

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import socket
import ssl

from content_loader import (LESSON_ALIASES, get_lesson, get_lesson_title, get_reference,
                            load_ui_strings, load_quiz, load_all_quizzes,
                            load_examples_catalog, get_example_by_id,
                            load_practice_problems, get_practice_problem,
                            get_evaluation_for_section, load_all_evaluations)
from models import (AuditLog, Classroom, ExerciseAttempt, LessonProgress, User, QuizResult,
                    PracticeSubmission, DailyStreak, SectionEvaluation,
                    PasswordResetCode, db)
from search_index import search_lessons
from translator import translate

app = Flask(__name__)
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
is_production = (
    is_vercel
    or os.environ.get("FLASK_ENV", "").strip().lower() == "production"
    or os.environ.get("APP_ENV", "").strip().lower() == "production"
    or os.environ.get("ENV", "").strip().lower() == "production"
)

_secret = (os.environ.get("SECRET_KEY") or "").strip()
if is_production:
    if not _secret or len(_secret) < 32:
        raise RuntimeError(
            "Configuración insegura: la variable de entorno SECRET_KEY es obligatoria en producción "
            "y debe tener al menos 32 caracteres."
        )
elif not _secret:
    _secret = os.urandom(32).hex()
    print("[AVISO] SECRET_KEY no configurada en desarrollo local. Usando clave temporal aleatoria.", flush=True)
elif len(_secret) < 32:
    print("[AVISO] SECRET_KEY tiene menos de 32 caracteres. Usa una clave de al menos 32 caracteres en producción.", flush=True)

app.secret_key = _secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = is_production

TEACHER_SECRET_CODE = os.environ.get("TEACHER_SECRET_CODE", "")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
MIN_PASSWORD_LENGTH = 8
MAX_RESET_FAILED_ATTEMPTS = 5
_DUMMY_PASSWORD_HASH = generate_password_hash("py2java-dummy-timing-guard")


def _is_valid_username(username):
    return bool(username and USERNAME_RE.fullmatch(username))


def _is_valid_email(email):
    return bool(email and len(email) <= 120 and EMAIL_RE.fullmatch(email))


def _is_safe_redirect_url(target):
    """Permite únicamente rutas internas relativas o del mismo host HTTP(S), bloqueando open redirects."""
    if not target or not isinstance(target, str):
        return False
    cleaned = target.strip()
    if not cleaned or "\\" in cleaned or any(ord(c) < 32 for c in cleaned):
        return False
    parsed = urlparse(cleaned)
    if parsed.scheme or parsed.netloc:
        return parsed.scheme in ("http", "https") and parsed.netloc == request.host
    return cleaned.startswith("/") and not cleaned.startswith("//")


def _get_safe_next_url(raw_target, default=None, exclude_paths=()):
    if not _is_safe_redirect_url(raw_target):
        return default
    cleaned = raw_target.strip()
    if exclude_paths and urlparse(cleaned).path in exclude_paths:
        return default
    return cleaned


def _get_client_ip():
    """Obtiene la IP del cliente para rate-limiting."""
    if is_vercel:
        vercel_ip = (request.headers.get("X-Vercel-Forwarded-For") or "").strip()
        if vercel_ip:
            return vercel_ip.split(",")[0].strip()
        forwarded_for = (request.headers.get("X-Forwarded-For") or "").strip()
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return get_remote_address() or "unknown"


def _login_rate_limit_key():
    """Clave de rate-limiting por (IP, username) para frenar fuerza bruta sin bloquear cuentas globalmente."""
    username = (request.form.get("username") or "").strip().lower()[:80]
    return f"{_get_client_ip()}:{username}"


limiter = Limiter(
    key_func=_get_client_ip,
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)

# Database Configuration
database_url = os.environ.get("DATABASE_URL")

is_postgres = bool(database_url and database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg2://")))
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if is_postgres and "sslmode=" not in database_url and "localhost" not in database_url and "127.0.0.1" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    if is_vercel:
        # Serverless: use NullPool so each invocation opens/closes its own connection
        # This prevents accumulating idle connections that exhaust Postgres pool limits
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
    # On Vercel serverless, working directory is read-only (/var/task), write SQLite to /tmp
    if is_vercel:
        sqlite_path = "/tmp/database_v2.sqlite"
    else:
        sqlite_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "database_v2.sqlite"
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + sqlite_path
    engine_options = {"pool_pre_ping": True}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        print(f"[ERROR in load_user]: {e}", flush=True)
        db.session.rollback()
        return None


_db_initialized = False


def _bootstrap_initial_superadmin():
    """Crea un Super Admin inicial desde variables de entorno SOLO si aún no existe ninguno."""
    existing_sa = User.query.filter_by(role="superadmin").first()
    if existing_sa:
        return

    sa_username = (os.environ.get("SUPERADMIN_USERNAME") or "").strip()
    sa_email = (os.environ.get("SUPERADMIN_EMAIL") or "").strip().lower()
    sa_password = os.environ.get("SUPERADMIN_PASSWORD") or ""

    if not (sa_username or sa_email or sa_password):
        print(
            "[INFO] No existe ninguna cuenta Super Admin. Ejecuta 'flask create-superadmin' "
            "o define SUPERADMIN_USERNAME, SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD.",
            flush=True,
        )
        return

    if not (sa_username and sa_email and sa_password):
        print(
            "[WARNING] Variables de bootstrap de Super Admin incompletas. "
            "Se requieren SUPERADMIN_USERNAME, SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD.",
            flush=True,
        )
        return

    if not _is_valid_username(sa_username):
        print("[WARNING] SUPERADMIN_USERNAME inválido (debe tener 3-30 caracteres: letras, números, _ o -).", flush=True)
        return

    if not _is_valid_email(sa_email):
        print("[WARNING] SUPERADMIN_EMAIL no tiene un formato de correo válido.", flush=True)
        return

    if len(sa_password) < MIN_PASSWORD_LENGTH:
        print(f"[WARNING] SUPERADMIN_PASSWORD debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.", flush=True)
        return

    collision = User.query.filter(
        or_(
            func.lower(User.username) == sa_username.lower(),
            func.lower(User.email) == sa_email.lower(),
        )
    ).first()
    if collision:
        print(
            "[WARNING] No se creó Super Admin desde variables de entorno porque el usuario o correo ya existe.",
            flush=True,
        )
        return

    superadmin_user = User(
        username=sa_username,
        email=sa_email,
        password_hash=generate_password_hash(sa_password),
        role="superadmin",
        is_suspended=False,
    )
    db.session.add(superadmin_user)
    db.session.commit()
    print(f"[INFO] Cuenta Super Admin inicial '{sa_username}' creada desde variables de entorno.", flush=True)


def init_db():
    global _db_initialized
    with app.app_context():
        try:
            db.create_all()
            # Migración automática idempotente: asegura columnas nuevas sin perder datos
            if is_postgres:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text(
                            "ALTER TABLE users "
                            "ADD COLUMN IF NOT EXISTS email VARCHAR(120), "
                            "ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0, "
                            "ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP, "
                            "ADD COLUMN IF NOT EXISTS section_id INTEGER REFERENCES classrooms(id), "
                            "ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE NOT NULL, "
                            "ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMP, "
                            "ADD COLUMN IF NOT EXISTS suspended_reason TEXT, "
                            "ADD COLUMN IF NOT EXISTS suspended_by INTEGER REFERENCES users(id)"
                        ))
                except Exception as mig_err:
                    print(f"[WARNING] Migración Postgres users: {mig_err}", flush=True)
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text(
                            "ALTER TABLE password_reset_codes "
                            "ADD COLUMN IF NOT EXISTS failed_attempts INTEGER DEFAULT 0 NOT NULL"
                        ))
                except Exception as mig_err:
                    print(f"[WARNING] Migración Postgres password_reset_codes: {mig_err}", flush=True)
            else:
                for col_def in [
                    "email VARCHAR(120)",
                    "failed_login_attempts INTEGER DEFAULT 0",
                    "locked_until TIMESTAMP",
                    "section_id INTEGER REFERENCES classrooms(id)",
                    "is_suspended BOOLEAN DEFAULT 0",
                    "suspended_at TIMESTAMP",
                    "suspended_reason TEXT",
                    "suspended_by INTEGER REFERENCES users(id)",
                ]:
                    try:
                        with db.engine.begin() as conn:
                            conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col_def}"))
                    except Exception:
                        pass
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text("UPDATE users SET is_suspended = 0 WHERE is_suspended IS NULL"))
                except Exception:
                    pass
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text("ALTER TABLE password_reset_codes ADD COLUMN failed_attempts INTEGER DEFAULT 0"))
                except Exception:
                    pass
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text("UPDATE password_reset_codes SET failed_attempts = 0 WHERE failed_attempts IS NULL"))
                except Exception:
                    pass

            try:
                _bootstrap_initial_superadmin()
            except Exception as sa_err:
                print(f"[WARNING] No se pudo verificar Super Admin inicial: {sa_err}", flush=True)
                try:
                    db.session.rollback()
                except Exception:
                    pass
            _db_initialized = True
            print("[INFO] db.create_all() y migraciones ejecutadas con éxito.", flush=True)
        except Exception as e:
            print(f"[WARNING] db.create_all falló durante el inicio: {e}", flush=True)


@app.cli.command("create-superadmin")
@click.option("--username", prompt="Usuario Super Admin", help="Usuario (3-30 caracteres: letras, números, _ o -).")
@click.option("--email", prompt="Correo electrónico", help="Correo electrónico válido.")
@click.option(
    "--password",
    prompt="Contraseña",
    hide_input=True,
    confirmation_prompt="Confirmar contraseña",
    help="Contraseña (mínimo 8 caracteres).",
)
def create_superadmin_command(username, email, password):
    """Crea una cuenta Super Admin de forma segura desde la CLI."""
    if not _db_initialized:
        init_db()

    clean_username = (username or "").strip()
    clean_email = (email or "").strip().lower()

    if not _is_valid_username(clean_username):
        raise click.ClickException(
            "El nombre de usuario debe tener entre 3 y 30 caracteres (solo letras, números, '-' o '_')."
        )
    if not _is_valid_email(clean_email):
        raise click.ClickException("Debes proporcionar un correo electrónico válido.")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise click.ClickException(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")

    if User.query.filter(func.lower(User.username) == clean_username.lower()).first():
        raise click.ClickException(f"El nombre de usuario '{clean_username}' ya existe.")
    if User.query.filter(func.lower(User.email) == clean_email.lower()).first():
        raise click.ClickException(f"El correo '{clean_email}' ya está registrado.")

    new_sa = User(
        username=clean_username,
        email=clean_email,
        password_hash=generate_password_hash(password),
        role="superadmin",
        is_suspended=False,
    )
    db.session.add(new_sa)
    db.session.commit()
    click.echo(f"Super Admin '{clean_username}' creado correctamente.")


if not is_vercel:
    init_db()


@app.before_request
def _ensure_serverless_db():
    if not _db_initialized and is_vercel:
        if request.path.startswith("/static/"):
            return
        init_db()


@app.before_request
def _block_suspended_user():
    """Expulsa inmediatamente a cualquier estudiante que haya sido suspendido con sesión activa."""
    if request.path.startswith(("/static/", "/login", "/logout", "/register", "/recuperar")):
        return
    user_to_check = None
    if current_user.is_authenticated:
        user_to_check = current_user
    else:
        raw_uid = session.get("_user_id")
        if raw_uid is not None:
            try:
                user_to_check = db.session.get(User, int(raw_uid))
            except Exception:
                user_to_check = None

    if user_to_check and getattr(user_to_check, "is_suspended", False):
        reason = user_to_check.suspended_reason or "Suspendida por el administrador."
        logout_user()
        session.pop("_user_id", None)
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": f"Tu cuenta se encuentra suspendida. Motivo: {reason}",
            }), 403
        session["suspended_notice"] = (
            f"Tu cuenta se encuentra suspendida. Motivo: {reason}. "
            "Contacta a tu docente o administrador para más información."
        )
        return redirect(url_for("login"))


@app.after_request
def _set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response

LESSON_CATEGORIES = [
    {
        "id": "py2java",
        "label_key": "cat_py2java",
        "icon": "",
        "color_class": "cat-python",
        "sections": [
            {
                "label_key": "cat_python_tutorial",
                "lessons": [
                    {"id": "py-home", "icon": ""},
                    {"id": "py-intro", "icon": ""},
                    {"id": "py-getstarted", "icon": ""},
                    {"id": "py-syntax", "icon": ""},
                    {"id": "py-comments", "icon": ""},
                    {"id": "py-variables", "icon": ""},
                    {"id": "py-datatypes", "icon": ""},
                    {"id": "py-numbers", "icon": ""},
                    {"id": "py-casting", "icon": ""},
                    {"id": "py-strings", "icon": ""},
                    {"id": "py-booleans", "icon": ""},
                    {"id": "py-operators", "icon": ""},
                    {"id": "py-lists", "icon": ""},
                    {"id": "py-tuples", "icon": ""},
                    {"id": "py-sets", "icon": ""},
                    {"id": "py-dicts", "icon": ""},
                    {"id": "py-ifelse", "icon": ""},
                    {"id": "py-while", "icon": ""},
                    {"id": "py-for", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_functions",
                "lessons": [
                    {"id": "py-functions", "icon": ""},
                    {"id": "py-lambda", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_classes",
                "lessons": [
                    {"id": "py-classes", "icon": ""},
                    {"id": "py-init", "icon": ""},
                    {"id": "py-self", "icon": ""},
                    {"id": "py-inheritance", "icon": ""},
                    {"id": "py-iterators", "icon": ""},
                    {"id": "py-polymorphism", "icon": ""},
                    {"id": "py-scope", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_modules",
                "lessons": [
                    {"id": "py-modules", "icon": ""},
                    {"id": "py-dates", "icon": ""},
                    {"id": "py-math", "icon": ""},
                    {"id": "py-json", "icon": ""},
                    {"id": "py-regex", "icon": ""},
                    {"id": "py-pip", "icon": ""},
                    {"id": "py-tryexcept", "icon": ""},
                    {"id": "py-userinput", "icon": ""},
                    {"id": "py-stringformat", "icon": ""},
                ],
            },
            {
                "label_key": "cat_file_handling",
                "lessons": [
                    {"id": "py-filehandling", "icon": ""},
                    {"id": "py-readfiles", "icon": ""},
                    {"id": "py-writefiles", "icon": ""},
                    {"id": "py-deletefiles", "icon": ""},
                ],
            },
            {
                "label_key": "cat_numpy",
                "lessons": [
                    {"id": "np-intro", "icon": ""},
                    {"id": "np-getstarted", "icon": ""},
                    {"id": "np-create", "icon": ""},
                    {"id": "np-indexing", "icon": ""},
                    {"id": "np-slicing", "icon": ""},
                    {"id": "np-datatypes", "icon": ""},
                    {"id": "np-copyview", "icon": ""},
                    {"id": "np-shape", "icon": ""},
                    {"id": "np-reshape", "icon": ""},
                    {"id": "np-iterating", "icon": ""},
                    {"id": "np-join", "icon": ""},
                    {"id": "np-split", "icon": ""},
                    {"id": "np-search", "icon": ""},
                    {"id": "np-sort", "icon": ""},
                    {"id": "np-filter", "icon": ""},
                    {"id": "np-random-intro", "icon": ""},
                    {"id": "np-datadist", "icon": ""},
                    {"id": "np-normal", "icon": ""},
                    {"id": "np-binomial", "icon": ""},
                    {"id": "np-poisson", "icon": ""},
                    {"id": "np-uniform", "icon": ""},
                    {"id": "np-logistic", "icon": ""},
                    {"id": "np-multinomial", "icon": ""},
                    {"id": "np-exponential", "icon": ""},
                    {"id": "np-chisquare", "icon": ""},
                    {"id": "np-rayleigh", "icon": ""},
                    {"id": "np-pareto", "icon": ""},
                    {"id": "np-zipf", "icon": ""},
                    {"id": "np-ufunc-intro", "icon": ""},
                    {"id": "np-create-ufunc", "icon": ""},
                    {"id": "np-arithmetic", "icon": ""},
                    {"id": "np-rounding", "icon": ""},
                    {"id": "np-logs", "icon": ""},
                    {"id": "np-summations", "icon": ""},
                    {"id": "np-products", "icon": ""},
                    {"id": "np-differences", "icon": ""},
                    {"id": "np-lcm", "icon": ""},
                    {"id": "np-gcd", "icon": ""},
                    {"id": "np-trig", "icon": ""},
                    {"id": "np-hyperbolic", "icon": ""},
                    {"id": "np-setops", "icon": ""},
                ],
            },
            {
                "label_key": "cat_pandas",
                "lessons": [
                    {"id": "pd-intro", "icon": ""},
                    {"id": "pd-getstarted", "icon": ""},
                    {"id": "pd-series", "icon": ""},
                    {"id": "pd-dataframes", "icon": ""},
                    {"id": "pd-readcsv", "icon": ""},
                    {"id": "pd-readjson", "icon": ""},
                    {"id": "pd-analyze", "icon": ""},
                    {"id": "pd-cleandata", "icon": ""},
                    {"id": "pd-emptycells", "icon": ""},
                    {"id": "pd-wrongformat", "icon": ""},
                    {"id": "pd-wrongdata", "icon": ""},
                    {"id": "pd-removedup", "icon": ""},
                    {"id": "pd-correlations", "icon": ""},
                    {"id": "pd-plotting", "icon": ""},
                ],
            },
            {
                "label_key": "cat_scipy",
                "lessons": [
                    {"id": "sc-intro", "icon": ""},
                    {"id": "sc-getstarted", "icon": ""},
                    {"id": "sc-constants", "icon": ""},
                    {"id": "sc-optimizers", "icon": ""},
                    {"id": "sc-sparsedata", "icon": ""},
                    {"id": "sc-graphs", "icon": ""},
                    {"id": "sc-spatialdata", "icon": ""},
                    {"id": "sc-matlab", "icon": ""},
                    {"id": "sc-interpolation", "icon": ""},
                    {"id": "sc-sigtests", "icon": ""},
                ],
            },
            {
                "label_key": "cat_mysql",
                "lessons": [
                    {"id": "sql-getstarted", "icon": ""},
                    {"id": "sql-createdb", "icon": ""},
                    {"id": "sql-createtable", "icon": ""},
                    {"id": "sql-insert", "icon": ""},
                    {"id": "sql-select", "icon": ""},
                    {"id": "sql-where", "icon": ""},
                    {"id": "sql-orderby", "icon": ""},
                    {"id": "sql-delete", "icon": ""},
                    {"id": "sql-droptable", "icon": ""},
                    {"id": "sql-update", "icon": ""},
                    {"id": "sql-limit", "icon": ""},
                    {"id": "sql-join", "icon": ""},
                ],
            },
            {
                "label_key": "cat_mongodb",
                "lessons": [
                    {"id": "mongo-getstarted", "icon": ""},
                    {"id": "mongo-createdb", "icon": ""},
                    {"id": "mongo-collection", "icon": ""},
                    {"id": "mongo-insert", "icon": ""},
                    {"id": "mongo-find", "icon": ""},
                    {"id": "mongo-query", "icon": ""},
                    {"id": "mongo-sort", "icon": ""},
                    {"id": "mongo-delete", "icon": ""},
                    {"id": "mongo-drop", "icon": ""},
                    {"id": "mongo-update", "icon": ""},
                    {"id": "mongo-limit", "icon": ""},
                ],
            },
            {
                "label_key": "cat_reference",
                "lessons": [
                    {"id": "ref-functions", "icon": ""},
                    {"id": "ref-strings", "icon": ""},
                    {"id": "ref-lists", "icon": ""},
                    {"id": "ref-dicts", "icon": ""},
                    {"id": "ref-tuples", "icon": ""},
                    {"id": "ref-sets", "icon": ""},
                    {"id": "ref-file", "icon": ""},
                    {"id": "ref-keywords", "icon": ""},
                    {"id": "ref-exceptions", "icon": ""},
                    {"id": "ref-glossary", "icon": ""},
                ],
            },
            {
                "label_key": "cat_section_exercises",
                "lessons": [
                    {"id": "ex-syntax", "icon": ""},
                    {"id": "ex-comments", "icon": ""},
                    {"id": "ex-variables", "icon": ""},
                    {"id": "ex-datatypes", "icon": ""},
                    {"id": "ex-numbers", "icon": ""},
                    {"id": "ex-strings", "icon": ""},
                    {"id": "ex-booleans", "icon": ""},
                    {"id": "ex-operators", "icon": ""},
                    {"id": "ex-lists", "icon": ""},
                    {"id": "ex-tuples", "icon": ""},
                    {"id": "ex-sets", "icon": ""},
                    {"id": "ex-dicts", "icon": ""},
                    {"id": "ex-ifelse", "icon": ""},
                    {"id": "ex-while", "icon": ""},
                    {"id": "ex-for", "icon": ""},
                    {"id": "ex-functions", "icon": ""},
                    {"id": "ex-lambda", "icon": ""},
                    {"id": "ex-classes", "icon": ""},
                    {"id": "ex-inheritance", "icon": ""},
                    {"id": "ex-modules", "icon": ""},
                ],
            },
            {
                "label_key": "cat_section_quiz",
                "lessons": [
                    {"id": "quiz-python-basics", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-strings", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-collections", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-control", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-functions", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-oop", "icon": "", "type": "quiz"},
                ],
            },
            {
                "label_key": "cat_section_examples",
                "lessons": [
                    {"id": "examples-hub", "icon": "", "type": "examples"}
                ],
            },
            {
                "label_key": "cat_section_practice",
                "lessons": [
                    {"id": "practice-hub", "icon": "", "type": "practice"}
                ],
            },
        ],
    }
]

# Lista plana para compatibilidad
LESSONS = [
    lesson
    for cat in LESSON_CATEGORIES
    for sec in cat["sections"]
    for lesson in sec["lessons"]
]

REFERENCE_CATEGORIES = [
    "basico",
    "tipos",
    "estructuras",
    "funciones",
    "entrada_salida",
    "orientado_objetos",
    "manejo_errores",
    "manipulacion_datos",
]


def get_lesson_category(lesson_id):
    """Devuelve la categoría a la que pertenece una lección."""
    for cat in LESSON_CATEGORIES:
        for sec in cat["sections"]:
            for lesson in sec["lessons"]:
                if lesson["id"] == lesson_id:
                    return cat
    return None


def get_lesson_neighbors(lesson_id):
    """Devuelve (prev_id, next_id) para la navegación entre lecciones dentro de la misma categoría."""
    for cat in LESSON_CATEGORIES:
        cat_lessons = [lesson_item for sec in cat["sections"] for lesson_item in sec["lessons"]]
        ids = [lesson_item["id"] for lesson_item in cat_lessons]
        if lesson_id in ids:
            idx = ids.index(lesson_id)
            prev_id = ids[idx - 1] if idx > 0 else None
            next_id = ids[idx + 1] if idx < len(ids) - 1 else None
            return prev_id, next_id
    return None, None


def _get_json_dict():
    """Obtiene el cuerpo JSON de la petición garantizando un diccionario."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _safe_int(val, default=0):
    try:
        if isinstance(val, bool):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


@app.route("/")
def index():
    return redirect(url_for("lesson", lesson_id="py-home"))


@app.route("/leccion/<lesson_id>")
def lesson(lesson_id):
    lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    if lesson_id.startswith("quiz-"):
        return redirect(url_for("quiz", topic=lesson_id))
    if lesson_id == "practice-hub":
        return redirect(url_for("practice_list"))
    if lesson_id == "examples-hub":
        return redirect(url_for("examples"))
    if lesson_id.startswith("ex-"):
        return redirect(url_for("exercise_topic", topic=lesson_id))

    valid_ids = [lesson_item["id"] for lesson_item in LESSONS]
    if lesson_id not in valid_ids:
        lesson_id = "py-home"
    prev_lesson, next_lesson = get_lesson_neighbors(lesson_id)
    current_category = get_lesson_category(lesson_id)
    current_category_id = current_category["id"] if current_category else "py2java"

    # Verificar prerrequisito
    prereq_warning = False
    prereq_lesson_id = None
    prereq_lesson_title = None
    if prev_lesson and lesson_id != "py-home":
        try:
            user = get_current_user()
            if user and user.id:
                prev_completed = LessonProgress.query.filter_by(
                    user_id=user.id, lesson_id=prev_lesson, completed=True
                ).first()
                if not prev_completed:
                    prereq_warning = True
                    prereq_lesson_id = prev_lesson
                    prereq_lesson_title = get_lesson_title(prev_lesson) or prev_lesson
        except Exception as e:
            print(f"[WARNING] Prerequisite check failed (DB issue): {e}", flush=True)
            db.session.rollback()

    return render_template(
        "lesson.html",
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        current_lesson=lesson_id,
        current_category=current_category_id,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        prereq_warning=prereq_warning,
        prereq_lesson_id=prereq_lesson_id,
        prereq_lesson_title=prereq_lesson_title,
        page="lesson",
        role=session.get("role", "student"),
    )


# --- Laboratorio de práctica ---
@app.route("/practica")
@app.route("/practice")
def practice_list():
    data = load_practice_problems()
    problems = data.get("problems", [])
    
    # Check completed problems for current user
    completed_ids = []
    if current_user.is_authenticated:
        completed_submissions = PracticeSubmission.query.filter_by(user_id=current_user.id, passed=True).all()
        completed_ids = [sub.problem_id for sub in completed_submissions]
        
    return render_template(
        "practice_list.html",
        problems=problems,
        completed_ids=completed_ids,
        categories=LESSON_CATEGORIES,
        page="practice"
    )

@app.route("/practica/<problem_id>")
def practice_editor(problem_id):
    problem = get_practice_problem(problem_id)
    if not problem:
        return redirect(url_for("practice_list"))
        
    # Check if previously completed to show starter code or previous answer
    previous_code = problem.get("starter_code", "")
    if current_user.is_authenticated:
        last_submission = PracticeSubmission.query.filter_by(user_id=current_user.id, problem_id=problem_id).order_by(PracticeSubmission.submitted_at.desc()).first()
        if last_submission:
            previous_code = last_submission.code

    return render_template(
        "practice_editor.html",
        problem=problem,
        previous_code=previous_code,
        categories=LESSON_CATEGORIES,
        page="practice"
    )

@app.route("/api/submit_practice", methods=["POST"])
def api_submit_practice():
    # Visitantes sin sesión pueden ejecutar pruebas, pero no guardar progreso ni XP
    if not current_user.is_authenticated:
        return jsonify({
            "ok": False,
            "anonymous": True,
            "xp_gained": 0,
            "message": "Inicia sesión para guardar tu progreso y ganar XP."
        })

    data = _get_json_dict()
    raw_problem_id = data.get("problem_id")
    problem_id = str(raw_problem_id).strip()[:50] if isinstance(raw_problem_id, (str, int)) and str(raw_problem_id).strip() else "unknown"
    raw_code = data.get("code")
    code = raw_code if isinstance(raw_code, str) else ""
    passed = bool(data.get("passed", False))
    tests_passed = _safe_int(data.get("tests_passed", 0), 0)
    tests_total = _safe_int(data.get("tests_total", 0), 0)
    
    user = current_user
    
    # Check if previously passed BEFORE adding the new submission
    prev_passed = PracticeSubmission.query.filter_by(user_id=user.id, problem_id=problem_id, passed=True).first()

    submission = PracticeSubmission(
        user_id=user.id,
        problem_id=problem_id,
        code=code,
        passed=passed,
        tests_passed=tests_passed,
        tests_total=tests_total
    )
    db.session.add(submission)
    
    xp_gained = 0
    if passed and not prev_passed:
        xp_gained = 50
        record_daily_activity(user.id)

        # Update LessonProgress record for practice XP tracking
        lp = LessonProgress.query.filter_by(
            user_id=user.id, lesson_id=f"practice-{problem_id}"
        ).first()
        if not lp:
            lp = LessonProgress(
                user_id=user.id,
                lesson_id=f"practice-{problem_id}",
                completed=True,
                score=xp_gained,
                completed_at=datetime.now(timezone.utc)
            )
            db.session.add(lp)
        else:
            lp.score = (lp.score or 0) + xp_gained

    db.session.commit()
    
    new_stats = get_progress_summary(user)
    lvl_info = get_level_info(new_stats["total_xp"])
    
    return jsonify({
        "ok": True,
        "xp_gained": xp_gained,
        "new_total": new_stats["total_xp"],
        "level": lvl_info["level"],
        "title": lvl_info["title"],
        "streak": new_stats["streak"]
    })

# --- Glosario ---
@app.route("/glosario")
def glossary():
    return render_template(
        "glossary.html",
        categories=LESSON_CATEGORIES,
        page="glossary",
    )


@app.route("/referencia")
def reference():
    return render_template(
        "reference.html",
        lessons=LESSONS,
        categories=LESSON_CATEGORIES,
        ref_categories=REFERENCE_CATEGORIES,
        current_category="",
        page="reference",
        role=session.get("role", "student"),
    )


@app.route("/api/traducir", methods=["POST"])
def api_translate():
    data = _get_json_dict()
    raw_code = data.get("code", "")
    python_code = raw_code if isinstance(raw_code, str) else ""
    raw_cls = data.get("class_name", "Program")
    class_name = raw_cls if isinstance(raw_cls, str) and raw_cls.strip() else "Program"

    result = translate(python_code, class_name=class_name)

    return jsonify(result)


def get_current_user():
    """Retorna el usuario autenticado o None."""
    if current_user.is_authenticated:
        return current_user
    user_id = session.get("user_id")
    if user_id:
        try:
            return db.session.get(User, user_id)
        except Exception:
            pass
    return None


@app.route("/api/progreso/ejercicio", methods=["POST"])
def api_ejercicio():
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = str(raw_lesson).strip()[:50] if isinstance(raw_lesson, (str, int)) and str(raw_lesson).strip() else "unknown"
    raw_ex = data.get("exercise_id")
    exercise_id = str(raw_ex).strip()[:50] if isinstance(raw_ex, (str, int)) and str(raw_ex).strip() else "unknown"
    passed = bool(data.get("passed", False))

    user = get_current_user()
    if not user or not user.id:
        return jsonify({"ok": False})

    # Check if previously passed BEFORE adding the new attempt (avoids SQLAlchemy autoflush)
    prev_passed = None
    if passed:
        prev_passed = ExerciseAttempt.query.filter_by(
            user_id=user.id, exercise_id=exercise_id, passed=True
        ).first()

    attempt = ExerciseAttempt(
        user_id=user.id, lesson_id=lesson_id, exercise_id=exercise_id, passed=passed
    )
    db.session.add(attempt)

    xp_gained = 0
    # Add XP if passed and not previously passed
    if passed:
        if not prev_passed:
            xp_gained = 25

            # Update LessonProgress score
            lp = LessonProgress.query.filter_by(
                user_id=user.id, lesson_id=lesson_id
            ).first()
            if not lp:
                lp = LessonProgress(user_id=user.id, lesson_id=lesson_id)
                db.session.add(lp)
            lp.score = (lp.score or 0) + xp_gained

    if passed:
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


@app.route("/api/progreso/leccion", methods=["POST"])
def api_leccion():
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = str(raw_lesson).strip()[:50] if isinstance(raw_lesson, str) and raw_lesson.strip() else None
    if not lesson_id:
        return jsonify({"ok": False})

    user = get_current_user()
    if not user or not user.id:
        return jsonify({"ok": False})

    lp = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson_id).first()

    xp_gained = 0
    if not lp:
        lp = LessonProgress(user_id=user.id, lesson_id=lesson_id, completed=True, score=0, completed_at=datetime.now(timezone.utc))
        db.session.add(lp)
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained
    elif not lp.completed:
        lp.completed = True
        lp.completed_at = datetime.now(timezone.utc)
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained

    record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


def record_daily_activity(user_id):
    """Registra la actividad diaria del usuario para el cálculo de racha."""
    if not user_id:
        return
    today = date.today()
    existing = DailyStreak.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.lessons_completed += 1
    else:
        streak_entry = DailyStreak(user_id=user_id, date=today, lessons_completed=1)
        db.session.add(streak_entry)


def calculate_streak(user_id):
    """Calcula la racha de días consecutivos de actividad."""
    if not user_id:
        return 0
    streaks = (
        DailyStreak.query.filter_by(user_id=user_id)
        .order_by(DailyStreak.date.desc())
        .all()
    )
    if not streaks:
        return 0

    today = date.today()
    # Allow today or yesterday as the start
    first_date = streaks[0].date
    if first_date != today and first_date != today - timedelta(days=1):
        return 0

    count = 1
    for i in range(1, len(streaks)):
        expected = first_date - timedelta(days=i)
        if streaks[i].date == expected:
            count += 1
        else:
            break
    return count


def get_progress_summary(user):
    if not user or not getattr(user, 'id', None):
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}
    try:
        progresses = LessonProgress.query.filter_by(user_id=user.id).all()
        completed = [p.lesson_id for p in progresses if p.completed]
        total_xp = sum((p.score or 0) for p in progresses)
        streak = calculate_streak(user.id)
        return {"completed_lessons": completed, "total_xp": total_xp, "streak": streak}
    except Exception as e:
        print(f"[WARNING] get_progress_summary error: {e}")
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}


def get_bulk_progress_summaries(users):
    """Calcula el resumen de progreso de múltiples usuarios en solo 2 consultas SQL."""
    user_ids = [u.id for u in users if getattr(u, "id", None)]
    if not user_ids:
        return {}

    result = {uid: {"completed_lessons": [], "total_xp": 0, "streak": 0} for uid in user_ids}
    try:
        all_progress = LessonProgress.query.filter(LessonProgress.user_id.in_(user_ids)).all()
        for p in all_progress:
            entry = result.get(p.user_id)
            if entry is not None:
                if p.completed:
                    entry["completed_lessons"].append(p.lesson_id)
                entry["total_xp"] += (p.score or 0)

        all_streaks = (
            DailyStreak.query.filter(DailyStreak.user_id.in_(user_ids))
            .order_by(DailyStreak.user_id, DailyStreak.date.desc())
            .all()
        )
        streaks_by_user = {}
        for s in all_streaks:
            streaks_by_user.setdefault(s.user_id, []).append(s.date)

        today = date.today()
        yesterday = today - timedelta(days=1)
        for uid, dates in streaks_by_user.items():
            if not dates:
                continue
            first_date = dates[0]
            if first_date != today and first_date != yesterday:
                continue
            count = 1
            for i in range(1, len(dates)):
                if dates[i] == first_date - timedelta(days=i):
                    count += 1
                else:
                    break
            result[uid]["streak"] = count
    except Exception as e:
        print(f"[WARNING] get_bulk_progress_summaries error: {e}", flush=True)
        db.session.rollback()

    return result


LEVEL_TITLES = {
    1: "Iniciado",
    2: "Novato",
    3: "Aprendiz",
    4: "Entusiasta",
    5: "Programador Junior",
    6: "Programador",
    7: "Desarrollador",
    8: "Ingeniero de Software",
    9: "Arquitecto",
    10: "Maestro del Código",
    11: "Mago de la Sintaxis",
    12: "Gurú de Algoritmos",
    13: "Hacker",
    14: "Ninja del Desarrollo",
    15: "Jedi del Software",
    16: "Titán de la Programación",
    17: "Leyenda Viva",
    18: "Semidiós del Código",
    19: "Dios del Código",
    20: "Entidad Binaria Superior"
}

def get_level_info(total_xp):
    level = (total_xp // 100) + 1
    if level >= 20:
        title = LEVEL_TITLES[20]
    else:
        title = LEVEL_TITLES.get(level, "Iniciado")
    return {"level": level, "title": title}


@app.route("/api/progreso/resumen", methods=["GET"])
def api_resumen():
    user = get_current_user()
    return jsonify(get_progress_summary(user))


@app.route("/api/buscar", methods=["GET"])
def api_buscar():
    q = request.args.get("q", "")
    results = search_lessons(q)
    return jsonify(results)


def _normalize_class_code(raw):
    """Normaliza un código de clase a mayúsculas alfanuméricas y guiones."""
    if not isinstance(raw, str):
        return ""
    cleaned = re.sub(r"[^A-Za-z0-9\-]", "", raw.strip().upper())
    return cleaned[:20]


def _generate_class_code(name=""):
    """Genera un código de clase único y fácil de compartir (ej. PROG-7K2M)."""
    prefix = re.sub(r"[^A-Za-z0-9]", "", (name or "CLS").upper())[:4] or "CLS"
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(30):
        suffix = "".join(secrets.choice(alphabet) for _ in range(4))
        candidate = f"{prefix}-{suffix}"
        if not Classroom.query.filter_by(code=candidate).first():
            return candidate
    return f"CLS-{secrets.token_hex(4).upper()}"


def _get_teacher_classrooms(teacher_id):
    return (
        Classroom.query.filter_by(teacher_id=teacher_id)
        .order_by(Classroom.created_at.desc())
        .all()
    )


def _get_teacher_section_ids(teacher_id):
    return {c.id for c in Classroom.query.filter_by(teacher_id=teacher_id).all()}


def _teacher_owns_student(teacher_id, student):
    """Regla de aislamiento estricta: verifica en BD que el estudiante pertenezca a una sección del docente."""
    if not student or student.role != "student" or not student.section_id:
        return False
    return (
        Classroom.query.filter_by(id=student.section_id, teacher_id=teacher_id).first()
        is not None
    )


def _log_audit(admin_user, action, target_username=None, reason=None, section_id=None, details=None):
    """Registra una entrada en la bitácora de auditoría dentro de la transacción actual."""
    entry = AuditLog(
        admin_id=getattr(admin_user, "id", None),
        admin_username=getattr(admin_user, "username", None) or "sistema",
        action=action,
        target_username=target_username,
        section_id=section_id,
        reason=(reason or "").strip() or None,
        details=(details or "").strip() or None,
    )
    db.session.add(entry)
    return entry


@app.route("/dashboard")
@login_required
def dashboard():
    summary = get_progress_summary(current_user)
    course_ids = _course_lesson_ids()
    completed_set = set(summary["completed_lessons"])
    completed_course_count = len(completed_set & course_ids)

    ui = load_ui_strings()
    category_breakdown = []
    for cat in LESSON_CATEGORIES:
        cat_lessons = _category_course_lessons(cat)
        done_cnt = sum(1 for lid in cat_lessons if lid in completed_set)
        total_cnt = len(cat_lessons)
        category_breakdown.append({
            "id": cat["id"],
            "name": ui.get(cat["label_key"], cat["id"]),
            "completed": done_cnt,
            "total": total_cnt,
            "pct": round(done_cnt / total_cnt * 100) if total_cnt > 0 else 0,
        })

    return render_template(
        "dashboard.html",
        user=current_user,
        classroom=current_user.classroom,
        summary=summary,
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        course_lesson_count=len(course_ids),
        completed_course_count=completed_course_count,
        category_breakdown=category_breakdown,
        page="dashboard",
    )


@app.route("/estudiante/unirse-seccion", methods=["POST"])
@login_required
@limiter.limit("10 per minute; 30 per hour", methods=["POST"])
def student_join_section():
    """Permite a un estudiante unirse (o cambiarse) a una sección mediante código de clase."""
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    raw_next = request.form.get("next") or request.referrer
    safe_next = _get_safe_next_url(raw_next, default=url_for("dashboard"))

    if current_user.role != "student":
        msg = "Solo los estudiantes pueden inscribirse en una sección."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(safe_next)

    raw_code = (_get_json_dict().get("class_code") if request.is_json else request.form.get("class_code")) or ""
    code = _normalize_class_code(raw_code)
    if not code:
        msg = "Debes ingresar un código de clase válido."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(safe_next)

    classroom = Classroom.query.filter_by(code=code).first()
    if not classroom:
        msg = f"El código de clase '{code}' no existe. Verifica el código con tu docente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 404
        flash(msg, "error")
        return redirect(safe_next)

    teacher = db.session.get(User, classroom.teacher_id)
    if not teacher or getattr(teacher, "is_suspended", False):
        msg = "No puedes unirte a esta sección porque la cuenta del docente se encuentra suspendida o inactiva."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(safe_next)

    current_user.section_id = classroom.id
    _log_audit(
        current_user,
        action="STUDENT_JOIN_SECTION",
        target_username=current_user.username,
        section_id=classroom.id,
        reason="Inscripción por código de clase",
        details=f"Sección: {classroom.name} ({classroom.code})",
    )
    db.session.commit()

    ok_msg = f"Te has unido correctamente a la sección {classroom.name} ({classroom.code})."
    if wants_json:
        return jsonify({
            "ok": True,
            "message": ok_msg,
            "section": {"id": classroom.id, "name": classroom.name, "code": classroom.code},
        })
    flash(ok_msg, "success")
    return redirect(safe_next)


@app.route("/roadmap")
@login_required
def roadmap():
    summary = get_progress_summary(current_user)
    return render_template(
        "roadmap.html", categories=LESSON_CATEGORIES, summary=summary, page="roadmap"
    )


@app.errorhandler(429)
def handle_rate_limit_exceeded(_err):
    msg = "Demasiados intentos en poco tiempo. Espera unos minutos antes de volver a intentarlo."
    wants_json = (
        request.is_json
        or request.path.startswith("/api/")
        or "application/json" in (request.headers.get("Accept") or "")
    )
    if wants_json:
        return jsonify({"ok": False, "error": msg}), 429

    endpoint = request.endpoint or ""
    if endpoint == "login":
        next_url = _get_safe_next_url(
            request.form.get("next") or request.args.get("next"),
            exclude_paths=("/login", "/logout", "/register"),
        )
        return (
            render_template(
                "login.html",
                error=msg,
                username=(request.form.get("username") or "").strip(),
                next_url=next_url,
                categories=LESSON_CATEGORIES,
            ),
            429,
        )
    if endpoint == "register":
        role = (request.form.get("role") or "student").strip()
        if role not in ("student", "teacher"):
            role = "student"
        form_data = {
            "username": (request.form.get("username") or "").strip(),
            "email": (request.form.get("email") or "").strip().lower(),
            "role": role,
            "class_code": _normalize_class_code(request.form.get("class_code", "")) if role == "student" else "",
        }
        return (
            render_template(
                "register.html",
                error=msg,
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            ),
            429,
        )
    if endpoint == "forgot_password":
        return (
            render_template(
                "forgot_password.html",
                error=msg,
                email=(request.form.get("email") or "").strip().lower(),
                categories=LESSON_CATEGORIES,
            ),
            429,
        )
    if endpoint == "reset_password":
        return (
            render_template(
                "reset_password.html",
                error=msg,
                email=(request.form.get("email") or session.get("recovery_email", "")).strip().lower(),
                demo_code=session.get("demo_reset_code") if _is_demo_reset_allowed() else None,
                recovery_notice=session.get("recovery_notice"),
                categories=LESSON_CATEGORIES,
            ),
            429,
        )
    return Response(msg, status=429, mimetype="text/plain")


# --- Autenticación ---


def _home_endpoint_for_role(role):
    if role == "superadmin":
        return "superadmin_dashboard"
    if role == "teacher":
        return "teacher_dashboard"
    return "dashboard"


@app.route("/api/db-status")
@login_required
def api_db_status():
    """Diagnóstico operativo de la base de datos (exclusivo para Super Admin, solo lectura)."""
    if current_user.role != "superadmin":
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    status = {
        "ok": False,
        "db_type": "postgresql" if is_postgres else "sqlite",
        "table_count": 0,
        "user_count": 0,
        "error": None,
    }

    try:
        db.session.execute(db.text("SELECT 1"))
        status["table_count"] = len(db.metadata.tables)
        status["user_count"] = User.query.count()
        status["ok"] = True
        return jsonify(status), 200
    except Exception as e:
        print(f"[ERROR in api_db_status]: {e}", flush=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        status["error"] = "Error de conexión con la base de datos. Revisa los registros del servidor."
        return jsonify(status), 503


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 15 per 15 minutes", methods=["POST"], key_func=_login_rate_limit_key)
@limiter.limit("30 per minute", methods=["POST"])
def login():
    raw_next = request.form.get("next") if request.method == "POST" else request.args.get("next")
    next_url = _get_safe_next_url(raw_next, exclude_paths=("/login", "/logout", "/register"))

    if current_user.is_authenticated:
        if getattr(current_user, "is_suspended", False):
            logout_user()
        else:
            return redirect(next_url or url_for(_home_endpoint_for_role(current_user.role)))

    suspended_notice = session.pop("suspended_notice", None)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        generic_auth_error = "Usuario o contraseña incorrectos."

        try:
            user = (
                User.query.filter_by(username=username).first()
                or User.query.filter(func.lower(User.username) == username.lower()).first()
            )
        except Exception as e:
            print(f"[ERROR in login]: {e}", flush=True)
            db.session.rollback()
            return render_template(
                "login.html",
                error="Servicio temporalmente no disponible. Intenta de nuevo en unos momentos.",
                username=username,
                next_url=next_url,
                categories=LESSON_CATEGORIES,
            )

        if not user:
            # Ejecuta verificación ficticia para igualar el tiempo de respuesta y evitar enumeración
            check_password_hash(_DUMMY_PASSWORD_HASH, password)
            return render_template(
                "login.html",
                error=generic_auth_error,
                username=username,
                next_url=next_url,
                categories=LESSON_CATEGORIES,
            )

        if check_password_hash(user.password_hash, password):
            if getattr(user, "is_suspended", False):
                reason = user.suspended_reason or "Cuenta suspendida por el administrador."
                return render_template(
                    "login.html",
                    error=f"Tu cuenta se encuentra suspendida. Motivo: {reason}. Contacta a tu docente o administrador.",
                    username=username,
                    next_url=next_url,
                    categories=LESSON_CATEGORIES,
                )
            login_user(user)
            return redirect(next_url or url_for(_home_endpoint_for_role(user.role)))

        return render_template(
            "login.html",
            error=generic_auth_error,
            username=username,
            next_url=next_url,
            categories=LESSON_CATEGORIES,
        )

    return render_template(
        "login.html",
        error=suspended_notice,
        username="",
        next_url=next_url,
        categories=LESSON_CATEGORIES,
    )


def _connect_ipv4_socket(host, port, timeout):
    """Abre conexión TCP priorizando IPv4 para evitar cuelgues por IPv6 sin ruta."""
    last_err = None
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        infos = []
    for af, socktype, proto, _, sa in infos:
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            sock.settimeout(timeout)
            sock.connect(sa)
            return sock
        except OSError as exc:
            last_err = exc
            if sock is not None:
                sock.close()
    if last_err is not None:
        raise last_err
    return socket.create_connection((host, port), timeout)


class _IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        return _connect_ipv4_socket(host, port, timeout)


class _IPv4SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        sock = _connect_ipv4_socket(host, port, timeout)
        return self.context.wrap_socket(sock, server_hostname=self._host)


def _is_mail_configured():
    """Indica si existe un proveedor de correo configurado (Resend API o SMTP)."""
    resend_api_key = (os.environ.get("RESEND_API_KEY") or "").strip().strip('"').strip("'")
    if resend_api_key:
        return True
    mail_username = (os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_EMAIL") or "").strip().strip('"').strip("'")
    raw_password = (os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or "").strip().strip('"').strip("'")
    mail_server = (os.environ.get("MAIL_SERVER") or "").strip().strip('"').strip("'")
    if not mail_server and mail_username and mail_username.lower().endswith("@gmail.com"):
        mail_server = "smtp.gmail.com"
    return bool(mail_server and mail_username and raw_password)


def _is_demo_reset_allowed():
    """El modo demo está desactivado por defecto y estrictamente prohibido en producción."""
    if is_production:
        return False
    return os.environ.get("ALLOW_DEMO_RESET", "false").strip().lower() in ("true", "1", "yes")


def send_recovery_email(to_email, username, code):
    """
    Envía correo real con el nombre de usuario y el código de 6 dígitos.
    Soporta Resend API por HTTPS o SMTP estándar sobre IPv4.
    Si no hay proveedor configurado, retorna (False, 'SMTP no configurado').
    """
    resend_api_key = (os.environ.get("RESEND_API_KEY") or "").strip().strip('"').strip("'")
    mail_username = (os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_EMAIL") or "").strip().strip('"').strip("'")
    raw_password = (os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or "").strip().strip('"').strip("'")
    mail_server = (os.environ.get("MAIL_SERVER") or "").strip().strip('"').strip("'")
    if not mail_server and mail_username and mail_username.lower().endswith("@gmail.com"):
        mail_server = "smtp.gmail.com"
    # Las contraseñas de aplicación de Google se muestran en grupos de 4 letras con espacios; quitarlos evita rechazos
    mail_password = raw_password.replace(" ", "") if "gmail" in mail_server.lower() else raw_password
    mail_port = _safe_int(os.environ.get("MAIL_PORT", 587), 587)
    mail_sender = (
        os.environ.get("MAIL_DEFAULT_SENDER")
        or mail_username
        or "Py2Java Edu <onboarding@resend.dev>"
    ).strip().strip('"').strip("'")
    mail_use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes") or mail_port == 465
    mail_use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes") and not mail_use_ssl

    safe_username = html.escape(username or "")
    safe_code = html.escape(str(code))
    subject = "Recuperación de cuenta — Py2Java Edu"
    text_content = (
        f"Hola {username},\n\n"
        "Hemos recibido una solicitud para recordar tu usuario y restablecer tu contraseña en Py2Java Edu.\n\n"
        f"Tu nombre de usuario es: {username}\n"
        f"Tu código de verificación es: {code}\n\n"
        "Este código expirará en 15 minutos. Si no solicitaste este cambio, ignora este correo.\n"
    )
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 8px; background: #ffffff;">
        <h2 style="color: #1e3a5f; text-align: center; margin-top: 0;">Recuperación de Cuenta — Py2Java Edu</h2>
        <p style="color: #333; font-size: 15px;">Hola,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.5;">Hemos recibido una solicitud para recordar tu nombre de usuario y restablecer tu contraseña.</p>
        
        <div style="background: #f4f6f8; padding: 16px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3776ab;">
            <p style="margin: 0 0 10px 0; font-size: 15px;"><strong>Tu nombre de usuario es:</strong> <span style="font-size: 16px; color: #1e3a5f; font-weight: bold;">{safe_username}</span></p>
            <p style="margin: 0; font-size: 15px;"><strong>Código de verificación:</strong> <span style="font-size: 24px; font-weight: bold; letter-spacing: 6px; color: #2e7d32; display: block; margin-top: 8px; font-family: monospace;">{safe_code}</span></p>
        </div>
        
        <p style="font-size: 13px; color: #777; line-height: 1.4;">Este código expirará en <strong>15 minutos</strong>. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
    </div>
    """

    # Opción 1: Resend API (HTTPS)
    if resend_api_key:
        try:
            resp = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": mail_sender,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content,
                },
                timeout=7,
            )
            if 200 <= resp.status_code < 300:
                return True, None
            err_txt = resp.text[:300]
            print(f"[ERROR EMAIL RESEND] HTTP {resp.status_code}: {err_txt}", flush=True)
            return False, "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde."
        except Exception as e:
            print(f"[ERROR EMAIL RESEND] {type(e).__name__}: {e}", flush=True)
            return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."

    # Opción 2: SMTP sobre IPv4 (Gmail, Outlook, Brevo SMTP, etc.)
    if not mail_server or not mail_username or not mail_password:
        print(f"[AVISO RECUPERACIÓN] Proveedor de correo no configurado para recuperación de '{username}'.", flush=True)
        return False, "SMTP no configurado"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = to_email
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        smtp_timeout = 7
        tls_ctx = ssl.create_default_context()
        if mail_use_ssl:
            with _IPv4SMTP_SSL(mail_server, mail_port, timeout=smtp_timeout, context=tls_ctx) as server:
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())
        else:
            with _IPv4SMTP(mail_server, mail_port, timeout=smtp_timeout) as server:
                server.ehlo()
                if mail_use_tls:
                    server.starttls(context=tls_ctx)
                    server.ehlo()
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        print(f"[ERROR EMAIL SMTP AUTH] {e}", flush=True)
        return False, "No se pudo enviar el correo de recuperación en este momento. Contacta al administrador."
    except (socket.timeout, TimeoutError) as e:
        print(f"[ERROR EMAIL SMTP TIMEOUT] {e}", flush=True)
        return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."
    except Exception as e:
        print(f"[ERROR EMAIL SMTP] Error al enviar correo a {to_email}: {type(e).__name__}: {e}", flush=True)
        return False, "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde."


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student").strip()
        if role not in ("student", "teacher"):
            role = "student"
        teacher_code = request.form.get("teacher_code", "").strip()
        class_code = _normalize_class_code(request.form.get("class_code", "")) if role == "student" else ""
        form_data = {
            "username": username,
            "email": email,
            "role": role,
            "class_code": class_code,
        }

        if not username or not email or not password:
            return render_template(
                "register.html",
                error="Todos los campos son requeridos (usuario, correo y contraseña).",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if not _is_valid_username(username):
            return render_template(
                "register.html",
                error="El nombre de usuario debe tener entre 3 y 30 caracteres y solo puede contener letras, números, guiones (-) o guiones bajos (_).",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if not _is_valid_email(email):
            return render_template(
                "register.html",
                error="Ingresa un correo electrónico válido.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if len(password) < MIN_PASSWORD_LENGTH:
            return render_template(
                "register.html",
                error=f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if role == "teacher" and (not TEACHER_SECRET_CODE or not hmac.compare_digest(teacher_code, TEACHER_SECRET_CODE)):
            return render_template(
                "register.html",
                error="Código de profesor incorrecto. Verifica tu clave de acceso.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        target_classroom = None
        try:
            existing_user = User.query.filter(func.lower(User.username) == username.lower()).first()
            existing_email = User.query.filter(func.lower(User.email) == email.lower()).first() if email else None
            if role == "student" and class_code:
                target_classroom = Classroom.query.filter_by(code=class_code).first()
        except Exception as e:
            print(f"[ERROR in register query]: {e}", flush=True)
            db.session.rollback()
            return render_template(
                "register.html",
                error="Servicio temporalmente no disponible. Intenta de nuevo en unos momentos.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if role == "student" and class_code:
            if not target_classroom:
                return render_template(
                    "register.html",
                    error=f"El código de clase '{class_code}' no existe. Verifica el código con tu docente o déjalo vacío para unirte después.",
                    form_data=form_data,
                    categories=LESSON_CATEGORIES,
                )
            classroom_teacher = db.session.get(User, target_classroom.teacher_id)
            if not classroom_teacher or getattr(classroom_teacher, "is_suspended", False):
                return render_template(
                    "register.html",
                    error="No puedes unirte a esta sección porque la cuenta del docente se encuentra suspendida o inactiva.",
                    form_data=form_data,
                    categories=LESSON_CATEGORIES,
                )

        if existing_user:
            return render_template(
                "register.html",
                error="El nombre de usuario ya está en uso. Elige otro.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        if existing_email:
            return render_template(
                "register.html",
                error="Este correo electrónico ya está registrado. Si olvidaste tu clave, usa la opción de recuperar cuenta.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

        try:
            hashed_pw = generate_password_hash(password)
            new_user = User(
                username=username,
                email=email,
                password_hash=hashed_pw,
                role=role,
                section_id=target_classroom.id if target_classroom else None,
            )
            db.session.add(new_user)
            db.session.flush()
            if target_classroom:
                _log_audit(
                    new_user,
                    action="STUDENT_JOIN_SECTION",
                    target_username=new_user.username,
                    section_id=target_classroom.id,
                    reason="Registro inicial con código de clase",
                    details=f"Sección: {target_classroom.name} ({target_classroom.code})",
                )
            db.session.commit()

            login_user(new_user)
            return redirect(
                url_for("teacher_dashboard" if role == "teacher" else "dashboard")
            )
        except Exception as e:
            print(f"[ERROR in register commit]: {e}", flush=True)
            db.session.rollback()
            return render_template(
                "register.html",
                error="Error al guardar el usuario en la base de datos. Intenta de nuevo.",
                form_data=form_data,
                categories=LESSON_CATEGORIES,
            )

    return render_template("register.html", form_data={}, categories=LESSON_CATEGORIES)


@app.route("/recuperar", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes; 15 per hour", methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email or not _is_valid_email(email):
            return render_template(
                "forgot_password.html",
                error="Debes ingresar un correo electrónico válido.",
                email=email,
                categories=LESSON_CATEGORIES,
            )

        mail_configured = _is_mail_configured()
        allow_demo = _is_demo_reset_allowed()
        if not mail_configured and not allow_demo:
            session.pop("demo_reset_code", None)
            session.pop("recovery_notice", None)
            return render_template(
                "forgot_password.html",
                error="El servicio de recuperación de contraseña por correo no está disponible en este momento. Contacta al administrador.",
                email=email,
                categories=LESSON_CATEGORIES,
            )

        generic_notice = (
            "Si el correo ingresado está registrado, recibirás un código de verificación de 6 dígitos "
            "en unos minutos. Revisa tu bandeja de entrada o la carpeta de spam."
        )

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            session["recovery_email"] = email
            session.pop("demo_reset_code", None)
            session["recovery_notice"] = generic_notice
            return redirect(url_for("reset_password"))

        # Generar código criptográficamente seguro de 6 dígitos numéricos
        code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        # Invalidar códigos anteriores no usados
        PasswordResetCode.query.filter_by(user_id=user.id, used=False).update({"used": True})

        reset_record = PasswordResetCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
            used=False,
            failed_attempts=0,
        )
        db.session.add(reset_record)
        db.session.commit()

        session["recovery_email"] = email
        if mail_configured:
            sent, reason = send_recovery_email(user.email, user.username, code)
            if sent:
                session.pop("demo_reset_code", None)
                session["recovery_notice"] = generic_notice
                return redirect(url_for("reset_password"))

            session.pop("demo_reset_code", None)
            session.pop("recovery_notice", None)
            return render_template(
                "forgot_password.html",
                error=reason or "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde.",
                email=email,
                categories=LESSON_CATEGORIES,
            )

        # Solo alcanzable en desarrollo local cuando ALLOW_DEMO_RESET=true explícitamente
        session["demo_reset_code"] = code
        session["recovery_notice"] = generic_notice
        return redirect(url_for("reset_password"))

    return render_template("forgot_password.html", categories=LESSON_CATEGORIES)


@app.route("/recuperar/verificar", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes", methods=["POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    email = (request.args.get("email") or session.get("recovery_email", "")).strip().lower()
    demo_code = session.get("demo_reset_code") if _is_demo_reset_allowed() else None
    recovery_notice = session.get("recovery_notice")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        code = request.form.get("code", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        generic_invalid_msg = "El código de verificación es inválido, ha expirado o el correo es incorrecto."

        if not email or not code or not new_password:
            return render_template(
                "reset_password.html",
                error="Todos los campos son obligatorios.",
                email=email,
                demo_code=demo_code,
                recovery_notice=recovery_notice,
                categories=LESSON_CATEGORIES,
            )

        if len(new_password) < MIN_PASSWORD_LENGTH:
            return render_template(
                "reset_password.html",
                error=f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
                email=email,
                demo_code=demo_code,
                recovery_notice=recovery_notice,
                categories=LESSON_CATEGORIES,
            )

        if new_password != confirm_password:
            return render_template(
                "reset_password.html",
                error="Las contraseñas no coinciden.",
                email=email,
                demo_code=demo_code,
                recovery_notice=recovery_notice,
                categories=LESSON_CATEGORIES,
            )

        user = User.query.filter(func.lower(User.email) == email).first()
        if not user:
            return render_template(
                "reset_password.html",
                error=generic_invalid_msg,
                email=email,
                categories=LESSON_CATEGORIES,
            )

        active_record = (
            PasswordResetCode.query.filter_by(user_id=user.id, used=False)
            .order_by(PasswordResetCode.created_at.desc())
            .first()
        )
        if not active_record:
            return render_template(
                "reset_password.html",
                error=generic_invalid_msg,
                email=email,
                categories=LESSON_CATEGORIES,
            )

        # Verificar expiración (con soporte timezone)
        record_expiry = active_record.expires_at
        if record_expiry.tzinfo is None:
            record_expiry = record_expiry.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        if record_expiry < now_utc:
            active_record.used = True
            db.session.commit()
            session.pop("demo_reset_code", None)
            return render_template(
                "reset_password.html",
                error="El código de verificación ha expirado (válido 15 minutos). Solicita uno nuevo.",
                email=email,
                categories=LESSON_CATEGORIES,
            )

        if (active_record.failed_attempts or 0) >= MAX_RESET_FAILED_ATTEMPTS:
            active_record.used = True
            db.session.commit()
            session.pop("demo_reset_code", None)
            return render_template(
                "reset_password.html",
                error="El código fue invalidado por demasiados intentos fallidos. Solicita uno nuevo.",
                email=email,
                categories=LESSON_CATEGORIES,
            )

        if not hmac.compare_digest(str(active_record.code or ""), code):
            active_record.failed_attempts = (active_record.failed_attempts or 0) + 1
            if active_record.failed_attempts >= MAX_RESET_FAILED_ATTEMPTS:
                active_record.used = True
                db.session.commit()
                session.pop("demo_reset_code", None)
                return render_template(
                    "reset_password.html",
                    error="El código fue invalidado por demasiados intentos fallidos. Solicita uno nuevo.",
                    email=email,
                    categories=LESSON_CATEGORIES,
                )
            db.session.commit()
            return render_template(
                "reset_password.html",
                error=generic_invalid_msg,
                email=email,
                demo_code=demo_code,
                recovery_notice=recovery_notice,
                categories=LESSON_CATEGORIES,
            )

        # Actualizar contraseña y marcar código como usado
        user.password_hash = generate_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        active_record.used = True
        db.session.commit()

        # Limpiar datos de sesión
        session.pop("recovery_email", None)
        session.pop("demo_reset_code", None)
        session.pop("recovery_notice", None)

        return render_template(
            "login.html",
            success="¡Contraseña actualizada con éxito! Ya puedes iniciar sesión con tu usuario y nueva clave.",
            username="",
            next_url=None,
            categories=LESSON_CATEGORIES,
        )

    return render_template(
        "reset_password.html",
        email=email,
        demo_code=demo_code,
        recovery_notice=recovery_notice,
        categories=LESSON_CATEGORIES,
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


ADMIN_STUDENTS_PER_PAGE = 20
ADMIN_AUDIT_PER_PAGE = 10


def _get_teacher_scoped_students(teacher_id, section_id_filter=None):
    """Devuelve (classrooms, allowed_section_ids, students_query) aislados estrictamente al docente."""
    classrooms = _get_teacher_classrooms(teacher_id)
    allowed_ids = [c.id for c in classrooms]
    if not allowed_ids:
        return classrooms, [], User.query.filter(db.false())

    if section_id_filter is not None and section_id_filter in allowed_ids:
        target_ids = [section_id_filter]
    else:
        target_ids = allowed_ids

    query = User.query.filter(
        User.role == "student",
        User.section_id.in_(target_ids),
    )
    return classrooms, allowed_ids, query


@app.route("/administrador")
@app.route("/profesor")
@login_required
def teacher_dashboard():
    if current_user.role == "superadmin":
        return redirect(url_for("superadmin_dashboard"))
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))

    # Parámetros de búsqueda, filtros, ordenamiento y paginación desde URL (GET)
    q = request.args.get("q", "").strip()
    raw_section = request.args.get("section_id", "").strip()
    section_filter = _safe_int(raw_section, 0) if raw_section else 0
    raw_level = request.args.get("level", "").strip()
    level_filter = _safe_int(raw_level, 0) if raw_level else 0
    status_filter = request.args.get("status", "all").strip()
    if status_filter not in ("all", "active", "suspended", "with_progress", "no_activity"):
        status_filter = "all"
    sort_by = request.args.get("sort", "xp_desc").strip()
    if sort_by not in ("xp_desc", "xp_asc", "progress_desc", "progress_asc", "name_asc", "name_desc", "date_desc", "date_asc"):
        sort_by = "xp_desc"
    page = max(1, _safe_int(request.args.get("page", 1), 1))
    audit_page = max(1, _safe_int(request.args.get("audit_page", 1), 1))

    classrooms = []
    classroom_map = {}
    classroom_counts = {}
    student_rows = []
    all_scoped_students = []
    total_xp = 0
    total_completed = 0
    active_count = 0
    suspended_count = 0
    level_counts = {}
    audit_logs = []
    audit_total = 0
    audit_total_pages = 1
    course_ids = _course_lesson_ids()
    total_course_lessons = len(course_ids) or 1

    try:
        classrooms = _get_teacher_classrooms(current_user.id)
        classroom_map = {c.id: c for c in classrooms}
        allowed_ids = list(classroom_map.keys())

        # Validar en backend que section_filter pertenezca al docente actual
        active_section_id = section_filter if section_filter in classroom_map else None

        if allowed_ids:
            # Conteo de estudiantes por sección del docente
            for c_id in allowed_ids:
                classroom_counts[c_id] = User.query.filter_by(role="student", section_id=c_id).count()

            # 1) Métricas generales del docente (sobre sus grupos o el grupo filtrado)
            scope_ids = [active_section_id] if active_section_id else allowed_ids
            all_scoped_students = User.query.filter(
                User.role == "student",
                User.section_id.in_(scope_ids),
            ).all()
            all_bulk = get_bulk_progress_summaries(all_scoped_students)
            for s in all_scoped_students:
                st = all_bulk.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
                lvl = get_level_info(st["total_xp"])
                completed_cnt = len(set(st["completed_lessons"]) & course_ids)
                total_xp += st["total_xp"]
                total_completed += completed_cnt
                if getattr(s, "is_suspended", False):
                    suspended_count += 1
                else:
                    active_count += 1
                level_counts[lvl["title"]] = level_counts.get(lvl["title"], 0) + 1

            # 2) Consulta filtrada en SQL (aislamiento + búsqueda username/email + estado cuenta)
            filtered_q = User.query.filter(
                User.role == "student",
                User.section_id.in_(scope_ids),
            )
            if q:
                like_pattern = f"%{q}%"
                filtered_q = filtered_q.filter(
                    or_(
                        User.username.ilike(like_pattern),
                        User.email.ilike(like_pattern),
                    )
                )
            if status_filter == "active":
                filtered_q = filtered_q.filter(User.is_suspended.is_(False))
            elif status_filter == "suspended":
                filtered_q = filtered_q.filter(User.is_suspended.is_(True))

            matched_students = filtered_q.all()
            matched_bulk = get_bulk_progress_summaries(matched_students)

            for s in matched_students:
                st = matched_bulk.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
                lvl = get_level_info(st["total_xp"])
                completed_cnt = len(set(st["completed_lessons"]) & course_ids)

                # Filtros calculados: nivel y actividad/progreso
                if level_filter and lvl["level"] != level_filter:
                    continue
                if status_filter == "with_progress" and completed_cnt == 0 and st["total_xp"] == 0:
                    continue
                if status_filter == "no_activity" and (completed_cnt > 0 or st["total_xp"] > 0):
                    continue

                cls = classroom_map.get(s.section_id)
                student_rows.append({
                    "id": s.id,
                    "username": s.username,
                    "email": s.email or "",
                    "total_xp": st["total_xp"],
                    "completed": completed_cnt,
                    "progress_pct": round(min(100, completed_cnt * 100 / total_course_lessons), 1),
                    "level": lvl["level"],
                    "title": lvl["title"],
                    "streak": st["streak"],
                    "section_id": s.section_id,
                    "section_name": cls.name if cls else "Sin sección",
                    "section_code": cls.code if cls else "",
                    "is_suspended": bool(getattr(s, "is_suspended", False)),
                    "suspended_reason": getattr(s, "suspended_reason", None) or "",
                    "suspended_at": s.suspended_at.strftime("%d/%m/%Y %H:%M") if getattr(s, "suspended_at", None) else "",
                    "created_at": s.created_at,
                    "created_at_str": s.created_at.strftime("%d/%m/%Y") if s.created_at else "N/A",
                })

            # Ordenamiento
            if sort_by == "xp_desc":
                student_rows.sort(key=lambda x: (-x["total_xp"], (x["username"] or "").lower()))
            elif sort_by == "xp_asc":
                student_rows.sort(key=lambda x: (x["total_xp"], (x["username"] or "").lower()))
            elif sort_by == "progress_desc":
                student_rows.sort(key=lambda x: (-x["completed"], -x["total_xp"]))
            elif sort_by == "progress_asc":
                student_rows.sort(key=lambda x: (x["completed"], x["total_xp"]))
            elif sort_by == "name_asc":
                student_rows.sort(key=lambda x: (x["username"] or "").lower())
            elif sort_by == "name_desc":
                student_rows.sort(key=lambda x: (x["username"] or "").lower(), reverse=True)
            elif sort_by == "date_desc":
                student_rows.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            elif sort_by == "date_asc":
                student_rows.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc))
    except Exception as e:
        print(f"[ERROR in teacher_dashboard]: {e}", flush=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        active_section_id = None

    total_filtered = len(student_rows)
    total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
    if page > total_pages:
        page = total_pages
    start_idx = (page - 1) * ADMIN_STUDENTS_PER_PAGE
    paginated_students = student_rows[start_idx : start_idx + ADMIN_STUDENTS_PER_PAGE]

    metrics = {
        "total_students": len(all_scoped_students),
        "active_students": active_count,
        "suspended_students": suspended_count,
        "avg_xp": round(total_xp / len(all_scoped_students)) if all_scoped_students else 0,
        "total_completed": total_completed,
        "total_course_lessons": len(course_ids),
        "level_labels": list(level_counts.keys()),
        "level_data": list(level_counts.values()),
    }

    filters = {
        "q": q,
        "section_id": active_section_id or "",
        "level": level_filter or "",
        "status": status_filter,
        "sort": sort_by,
        "page": page,
        "total_pages": total_pages,
        "total_filtered": total_filtered,
        "per_page": ADMIN_STUDENTS_PER_PAGE,
    }

    return render_template(
        "teacher_dashboard.html",
        students=paginated_students,
        classrooms=classrooms,
        classroom_counts=classroom_counts,
        metrics=metrics,
        filters=filters,
        level_titles=LEVEL_TITLES,
        categories=LESSON_CATEGORIES,
    )


@app.route("/profesor/secciones/crear", methods=["POST"])
@app.route("/administrador/secciones/crear", methods=["POST"])
@login_required
def admin_create_section():
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    if current_user.role != "teacher":
        if wants_json:
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        return redirect(url_for("dashboard"))

    data = _get_json_dict() if request.is_json else request.form
    name = str(data.get("name") or "").strip()[:100]
    raw_code = str(data.get("code") or "").strip()

    if len(name) < 2:
        msg = "El nombre de la sección debe tener al menos 2 caracteres (ej. PROG1-A)."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    if raw_code:
        code = _normalize_class_code(raw_code)
        if len(code) < 4:
            msg = "El código personalizado debe tener entre 4 y 20 caracteres alfanuméricos."
            if wants_json:
                return jsonify({"ok": False, "error": msg}), 400
            flash(msg, "error")
            return redirect(url_for("teacher_dashboard"))
        if Classroom.query.filter_by(code=code).first():
            msg = f"El código de clase '{code}' ya está en uso. Elige otro o déjalo vacío para generarlo automáticamente."
            if wants_json:
                return jsonify({"ok": False, "error": msg}), 409
            flash(msg, "error")
            return redirect(url_for("teacher_dashboard"))
    else:
        code = _generate_class_code(name)

    try:
        classroom = Classroom(name=name, code=code, teacher_id=current_user.id)
        db.session.add(classroom)
        db.session.flush()
        _log_audit(
            current_user,
            action="CREATE_SECTION",
            target_username=None,
            section_id=classroom.id,
            reason=f"Creación de sección '{name}'",
            details=f"Código de clase: {code}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR in admin_create_section]: {e}", flush=True)
        msg = "No se pudo crear la sección. Intenta nuevamente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 500
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    ok_msg = f"Sección '{classroom.name}' creada correctamente. Código para compartir: {classroom.code}"
    if wants_json:
        return jsonify({
            "ok": True,
            "message": ok_msg,
            "section": {"id": classroom.id, "name": classroom.name, "code": classroom.code},
        }), 201
    flash(ok_msg, "success")
    return redirect(url_for("teacher_dashboard"))


@app.route("/administrador/secciones/<int:section_id>/eliminar", methods=["POST"])
@app.route("/profesor/secciones/<int:section_id>/eliminar", methods=["POST"])
@login_required
def admin_delete_section(section_id):
    """Permite a un profesor eliminar su propia sección (o al Super Admin eliminar cualquiera) sin borrar estudiantes."""
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    if current_user.role not in ("teacher", "superadmin"):
        if wants_json:
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        return redirect(url_for("dashboard"))

    classroom = db.session.get(Classroom, section_id)
    if not classroom:
        msg = "Sección no encontrada."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 404
        flash(msg, "error")
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        _log_audit(
            current_user,
            action="UNAUTHORIZED_DELETE_SECTION_ATTEMPT",
            target_username=None,
            section_id=classroom.id,
            reason=f"Intento de eliminar sección ajena '{classroom.name}' ({classroom.code})",
        )
        db.session.commit()
        msg = "Acceso denegado: solo puedes eliminar tus propias secciones."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    sec_name = classroom.name
    sec_code = classroom.code
    try:
        # Desvincular estudiantes (conservan cuenta, XP e historial intactos) y referencias de auditoría
        detached_students = User.query.filter_by(section_id=classroom.id).update(
            {"section_id": None}, synchronize_session=False
        )
        AuditLog.query.filter_by(section_id=classroom.id).update(
            {"section_id": None}, synchronize_session=False
        )
        db.session.delete(classroom)
        _log_audit(
            current_user,
            action="DELETE_SECTION",
            target_username=None,
            section_id=None,
            reason=f"Eliminación de sección '{sec_name}'",
            details=f"Código: {sec_code} | Estudiantes desvinculados: {detached_students}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR in admin_delete_section]: {e}", flush=True)
        msg = "No se pudo eliminar la sección. Intenta nuevamente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 500
        flash(msg, "error")
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    ok_msg = f"Sección '{sec_name}' ({sec_code}) eliminada. {detached_students} estudiante(s) fueron desvinculados sin perder su progreso."
    if wants_json:
        return jsonify({"ok": True, "message": ok_msg, "detached_students": detached_students})
    flash(ok_msg, "success")
    return redirect(url_for(_home_endpoint_for_role(current_user.role)))


@app.route("/profesor/estudiante/<int:student_id>/suspender", methods=["POST"])
@app.route("/administrador/estudiante/<int:student_id>/suspender", methods=["POST"])
@login_required
def admin_suspend_student(student_id):
    """Borrado lógico (suspensión) de estudiante con motivo obligatorio y registro de auditoría."""
    if current_user.role != "teacher":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return jsonify({
            "success": False,
            "error": "Debes indicar un motivo obligatorio para suspender al estudiante (mínimo 5 caracteres).",
        }), 400

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404

    if not _teacher_owns_student(current_user.id, student):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_SUSPEND_ATTEMPT",
            target_username=student.username,
            section_id=student.section_id,
            reason=reason,
            details="Intento bloqueado: el estudiante no pertenece a las secciones del docente.",
        )
        db.session.commit()
        return jsonify({
            "success": False,
            "error": "Acceso denegado: este estudiante no pertenece a tus secciones.",
        }), 403

    if getattr(student, "is_suspended", False):
        return jsonify({"success": False, "error": "El estudiante ya se encuentra suspendido."}), 400

    cls = db.session.get(Classroom, student.section_id) if student.section_id else None
    student.is_suspended = True
    student.suspended_at = datetime.now(timezone.utc)
    student.suspended_reason = reason
    student.suspended_by = current_user.id

    _log_audit(
        current_user,
        action="SUSPEND_STUDENT",
        target_username=student.username,
        section_id=student.section_id,
        reason=reason,
        details=f"Grupo: {cls.name} ({cls.code})" if cls else "Sin sección",
    )
    db.session.commit()
    return jsonify({
        "success": True,
        "status": "suspended",
        "reason": reason,
        "suspended_at": student.suspended_at.strftime("%d/%m/%Y %H:%M"),
    })


@app.route("/profesor/estudiante/<int:student_id>/restaurar", methods=["POST"])
@app.route("/administrador/estudiante/<int:student_id>/restaurar", methods=["POST"])
@login_required
def admin_restore_student(student_id):
    """Restaura a un estudiante suspendido conservando intacto todo su progreso e historial."""
    if current_user.role != "teacher":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "Restauración de cuenta por el docente").strip()[:500]

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404

    if not _teacher_owns_student(current_user.id, student):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_RESTORE_ATTEMPT",
            target_username=student.username,
            section_id=student.section_id,
            reason=reason,
            details="Intento bloqueado: el estudiante no pertenece a las secciones del docente.",
        )
        db.session.commit()
        return jsonify({
            "success": False,
            "error": "Acceso denegado: este estudiante no pertenece a tus secciones.",
        }), 403

    if not getattr(student, "is_suspended", False):
        return jsonify({"success": False, "error": "El estudiante ya se encuentra activo."}), 400

    cls = db.session.get(Classroom, student.section_id) if student.section_id else None
    prev_reason = student.suspended_reason or ""
    student.is_suspended = False
    student.suspended_at = None
    student.suspended_reason = None
    student.suspended_by = None

    _log_audit(
        current_user,
        action="RESTORE_STUDENT",
        target_username=student.username,
        section_id=student.section_id,
        reason=reason,
        details=f"Grupo: {cls.name} ({cls.code}) | Motivo previo: {prev_reason}" if cls else f"Motivo previo: {prev_reason}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@app.route("/profesor/estudiante/<int:student_id>/eliminar", methods=["POST"])
@app.route("/administrador/estudiante/<int:student_id>/eliminar", methods=["POST"])
@login_required
def teacher_delete_student(student_id):
    """El borrado físico fue sustituido por suspensión lógica (Soft Delete) con motivo obligatorio."""
    return admin_suspend_student(student_id)


# --- Exportar CSV ---
@app.route("/profesor/export/csv")
@app.route("/administrador/export/csv")
@login_required
def teacher_export_csv():
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))

    raw_section = request.args.get("section_id", "").strip()
    section_filter = _safe_int(raw_section, 0) if raw_section else None
    classrooms, _, students_q = _get_teacher_scoped_students(current_user.id, section_filter)
    classroom_map = {c.id: c for c in classrooms}
    students = students_q.all()
    bulk_stats = get_bulk_progress_summaries(students)
    course_ids = _course_lesson_ids()

    si = StringIO()
    si.write('\ufeff')  # Agregamos BOM para que Excel detecte correctamente el UTF-8
    cw = csv.writer(si, delimiter=';')  # Usamos punto y coma que es el separador esperado por Excel en español
    cw.writerow(["Username", "Email", "Seccion", "Estado", "Total_XP", "Lecciones_Completadas", "Nivel", "Racha_Actual", "Fecha_Registro"])

    for s in students:
        stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
        lvl_info = get_level_info(stats["total_xp"])
        safe_user = s.username or ""
        if safe_user.startswith(("=", "+", "-", "@")):
            safe_user = "'" + safe_user
        cls = classroom_map.get(s.section_id)
        completed_cnt = len(set(stats["completed_lessons"]) & course_ids)
        cw.writerow([
            safe_user,
            s.email or "",
            f"{cls.name} ({cls.code})" if cls else "Sin sección",
            "Suspendido" if getattr(s, "is_suspended", False) else "Activo",
            stats["total_xp"],
            completed_cnt,
            lvl_info["title"],
            stats["streak"],
            s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A",
        ])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_estudiantes.csv"}
    )


# --- Exportar PDF ---
def _course_lesson_ids():
    """IDs de lecciones teóricas del curso (excluye quizzes, hubs y temas de ejercicios)."""
    return {
        l["id"] for l in LESSONS
        if not l.get("type") and not l["id"].startswith("ex-")
    }


@app.route("/profesor/export/pdf")
@app.route("/administrador/export/pdf")
@login_required
def admin_export_pdf():
    if current_user.role != "teacher":
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    try:
        from pdf_report import build_admin_report_pdf

        course_ids = _course_lesson_ids()
        total_course = len(course_ids) or 1

        raw_section = request.args.get("section_id", "").strip()
        section_filter = _safe_int(raw_section, 0) if raw_section else None
        _, _, students_q = _get_teacher_scoped_students(current_user.id, section_filter)
        students = students_q.all()
        bulk_stats = get_bulk_progress_summaries(students)

        rows = []
        level_counts = {}
        for s in students:
            stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
            lvl = get_level_info(stats["total_xp"])
            completed = len(set(stats["completed_lessons"]) & course_ids)
            rows.append({
                "username": s.username or "",
                "level": lvl["level"],
                "title": lvl["title"],
                "total_xp": stats["total_xp"],
                "completed": completed,
                "progress_pct": round(min(100, completed * 100 / total_course), 1),
                "streak": stats["streak"],
            })
            key = (lvl["level"] if lvl["level"] < 20 else 20, lvl["title"])
            level_counts[key] = level_counts.get(key, 0) + 1

        rows.sort(key=lambda r: r["total_xp"], reverse=True)
        n = len(rows)
        metrics = {
            "total_students": n,
            "avg_xp": round(sum(r["total_xp"] for r in rows) / n) if n else 0,
            "total_completed": sum(r["completed"] for r in rows),
            "avg_progress_pct": round(sum(r["progress_pct"] for r in rows) / n, 1) if n else 0,
            "total_course_lessons": len(course_ids),
            "active_streaks": sum(1 for r in rows if r["streak"] > 0),
            "level_distribution": [
                (f"Lv.{lv} - {title}", count)
                for (lv, title), count in sorted(level_counts.items())
            ],
        }

        pdf_bytes = build_admin_report_pdf(
            rows, metrics,
            site_title=load_ui_strings().get("site_title", "Py2Java Edu"),
            generated_by=current_user.username,
        )
    except Exception as e:
        print(f"[ERROR in admin_export_pdf]: {type(e).__name__}: {e}", flush=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF. Intenta de nuevo."}), 500

    filename = f"reporte_estudiantes_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Panel de Super Admin ---
@app.route("/superadmin")
@login_required
def superadmin_dashboard():
    if current_user.role != "superadmin":
        _log_audit(
            current_user,
            action="UNAUTHORIZED_SUPERADMIN_ACCESS",
            target_username=None,
            reason="Intento de acceso a /superadmin sin privilegios",
        )
        db.session.commit()
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    q = request.args.get("q", "").strip()
    raw_section = request.args.get("section_id", "").strip()
    status_filter = request.args.get("status", "all").strip()
    if status_filter not in ("all", "active", "suspended"):
        status_filter = "all"
    sort_by = request.args.get("sort", "xp_desc").strip()
    if sort_by not in ("xp_desc", "xp_asc", "progress_desc", "name_asc", "date_desc"):
        sort_by = "xp_desc"
    page = max(1, _safe_int(request.args.get("page", 1), 1))
    audit_page = max(1, _safe_int(request.args.get("audit_page", 1), 1))

    course_ids = _course_lesson_ids()
    total_course = len(course_ids) or 1

    all_teachers = User.query.filter_by(role="teacher").order_by(User.created_at.desc()).all()
    all_classrooms = Classroom.query.order_by(Classroom.created_at.desc()).all()
    classroom_map = {c.id: c for c in all_classrooms}
    teacher_map = {t.id: t for t in all_teachers}

    classroom_counts = {}
    for c in all_classrooms:
        classroom_counts[c.id] = User.query.filter_by(role="student", section_id=c.id).count()

    teacher_rows = []
    for t in all_teachers:
        t_secs = [c for c in all_classrooms if c.teacher_id == t.id]
        t_stu_cnt = sum(classroom_counts.get(c.id, 0) for c in t_secs)
        teacher_rows.append({
            "id": t.id,
            "username": t.username,
            "email": t.email or "",
            "sections_count": len(t_secs),
            "students_count": t_stu_cnt,
            "is_suspended": bool(getattr(t, "is_suspended", False)),
            "suspended_reason": getattr(t, "suspended_reason", None) or "",
            "created_at_str": t.created_at.strftime("%d/%m/%Y") if t.created_at else "N/A",
        })

    # Métricas globales de estudiantes
    all_students = User.query.filter_by(role="student").all()
    active_students_cnt = sum(1 for s in all_students if not getattr(s, "is_suspended", False))
    suspended_students_cnt = len(all_students) - active_students_cnt
    unassigned_students_cnt = sum(1 for s in all_students if s.section_id is None)

    # Consulta filtrada de estudiantes
    sq = User.query.filter_by(role="student")
    if q:
        like = f"%{q}%"
        sq = sq.filter(or_(User.username.ilike(like), User.email.ilike(like)))
    if raw_section == "unassigned":
        sq = sq.filter(User.section_id.is_(None))
    elif raw_section:
        sec_int = _safe_int(raw_section, 0)
        if sec_int in classroom_map:
            sq = sq.filter(User.section_id == sec_int)
    if status_filter == "active":
        sq = sq.filter(User.is_suspended.is_(False))
    elif status_filter == "suspended":
        sq = sq.filter(User.is_suspended.is_(True))

    matched = sq.all()
    bulk = get_bulk_progress_summaries(matched)
    student_rows = []
    for s in matched:
        st = bulk.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
        lvl = get_level_info(st["total_xp"])
        comp = len(set(st["completed_lessons"]) & course_ids)
        cls = classroom_map.get(s.section_id)
        t_owner = teacher_map.get(cls.teacher_id) if cls else None
        student_rows.append({
            "id": s.id,
            "username": s.username,
            "email": s.email or "",
            "level": lvl["level"],
            "title": lvl["title"],
            "total_xp": st["total_xp"],
            "completed": comp,
            "progress_pct": round(min(100, comp * 100 / total_course), 1),
            "section_id": s.section_id,
            "section_name": cls.name if cls else "Sin sección",
            "section_code": cls.code if cls else "",
            "teacher_name": t_owner.username if t_owner else "—",
            "is_suspended": bool(getattr(s, "is_suspended", False)),
            "suspended_reason": getattr(s, "suspended_reason", None) or "",
            "created_at": s.created_at,
        })

    if sort_by == "xp_desc":
        student_rows.sort(key=lambda x: (-x["total_xp"], (x["username"] or "").lower()))
    elif sort_by == "xp_asc":
        student_rows.sort(key=lambda x: (x["total_xp"], (x["username"] or "").lower()))
    elif sort_by == "progress_desc":
        student_rows.sort(key=lambda x: (-x["completed"], -x["total_xp"]))
    elif sort_by == "name_asc":
        student_rows.sort(key=lambda x: (x["username"] or "").lower())
    elif sort_by == "date_desc":
        student_rows.sort(key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    total_filtered = len(student_rows)
    total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
    page = min(page, total_pages)
    start = (page - 1) * ADMIN_STUDENTS_PER_PAGE
    paginated_students = student_rows[start : start + ADMIN_STUDENTS_PER_PAGE]

    # Bitácora global (todos los eventos del sistema)
    audit_q = AuditLog.query.order_by(AuditLog.created_at.desc())
    audit_total = audit_q.count()
    audit_per = 15
    audit_total_pages = max(1, math.ceil(audit_total / audit_per))
    audit_page = min(audit_page, audit_total_pages)
    audit_logs = audit_q.offset((audit_page - 1) * audit_per).limit(audit_per).all()

    metrics = {
        "total_students": len(all_students),
        "active_students": active_students_cnt,
        "suspended_students": suspended_students_cnt,
        "unassigned_students": unassigned_students_cnt,
        "total_teachers": len(all_teachers),
        "suspended_teachers": sum(1 for t in all_teachers if getattr(t, "is_suspended", False)),
        "total_classrooms": len(all_classrooms),
        "total_course_lessons": len(course_ids),
        "audit_total": audit_total,
    }
    filters = {
        "q": q,
        "section_id": raw_section,
        "status": status_filter,
        "sort": sort_by,
        "page": page,
        "total_pages": total_pages,
        "total_filtered": total_filtered,
        "audit_page": audit_page,
        "audit_total_pages": audit_total_pages,
    }
    return render_template(
        "superadmin_dashboard.html",
        metrics=metrics,
        teachers=teacher_rows,
        classrooms=all_classrooms,
        classroom_counts=classroom_counts,
        teacher_map=teacher_map,
        students=paginated_students,
        audit_logs=audit_logs,
        filters=filters,
        categories=LESSON_CATEGORIES,
    )


@app.route("/superadmin/usuario/<int:user_id>/suspender", methods=["POST"])
@login_required
def superadmin_suspend_user(user_id):
    """Super Admin puede suspender a cualquier estudiante o profesor (nunca a otro superadmin) con motivo obligatorio."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return jsonify({"success": False, "error": "Debes indicar un motivo obligatorio (mínimo 5 caracteres)."}), 400

    target = db.session.get(User, user_id)
    if not target or target.role == "superadmin":
        return jsonify({"success": False, "error": "Usuario no encontrado o protegido."}), 404

    if getattr(target, "is_suspended", False):
        return jsonify({"success": False, "error": "El usuario ya se encuentra suspendido."}), 400

    target.is_suspended = True
    target.suspended_at = datetime.now(timezone.utc)
    target.suspended_reason = reason
    target.suspended_by = current_user.id

    action = "SUPERADMIN_SUSPEND_TEACHER" if target.role == "teacher" else "SUPERADMIN_SUSPEND_STUDENT"
    _log_audit(
        current_user,
        action=action,
        target_username=target.username,
        section_id=target.section_id,
        reason=reason,
        details=f"Rol afectado: {target.role}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "suspended"})


@app.route("/superadmin/usuario/<int:user_id>/restaurar", methods=["POST"])
@login_required
def superadmin_restore_user(user_id):
    """Super Admin puede restaurar a cualquier estudiante o profesor suspendido."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "Restauración por Super Admin").strip()[:500]

    target = db.session.get(User, user_id)
    if not target or target.role == "superadmin":
        return jsonify({"success": False, "error": "Usuario no encontrado."}), 404

    if not getattr(target, "is_suspended", False):
        return jsonify({"success": False, "error": "El usuario ya está activo."}), 400

    prev_reason = target.suspended_reason or ""
    target.is_suspended = False
    target.suspended_at = None
    target.suspended_reason = None
    target.suspended_by = None

    action = "SUPERADMIN_RESTORE_TEACHER" if target.role == "teacher" else "SUPERADMIN_RESTORE_STUDENT"
    _log_audit(
        current_user,
        action=action,
        target_username=target.username,
        section_id=target.section_id,
        reason=reason,
        details=f"Rol afectado: {target.role} | Motivo previo: {prev_reason}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@app.route("/superadmin/estudiante/<int:student_id>/asignar-seccion", methods=["POST"])
@login_required
def superadmin_assign_section(student_id):
    """Permite al Super Admin asignar o quitar la sección de cualquier estudiante."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado."}), 404

    data = _get_json_dict() if request.is_json else request.form
    raw_sec = str(data.get("section_id") or "").strip()
    if not raw_sec:
        student.section_id = None
        detail = "Desvinculado de sección"
        new_sec_id = None
    else:
        sec_id = _safe_int(raw_sec, 0)
        cls = db.session.get(Classroom, sec_id)
        if not cls:
            return jsonify({"success": False, "error": "Sección no encontrada."}), 404
        student.section_id = cls.id
        detail = f"Asignado a sección {cls.name} ({cls.code})"
        new_sec_id = cls.id

    _log_audit(
        current_user,
        action="SUPERADMIN_ASSIGN_SECTION",
        target_username=student.username,
        section_id=new_sec_id,
        reason="Gestión de sección por Super Admin",
        details=detail,
    )
    db.session.commit()
    return jsonify({"success": True, "details": detail})


@app.route("/superadmin/export/csv")
@login_required
def superadmin_export_csv():
    if current_user.role != "superadmin":
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    all_classrooms = Classroom.query.all()
    classroom_map = {c.id: c for c in all_classrooms}
    students = User.query.filter_by(role="student").all()
    bulk_stats = get_bulk_progress_summaries(students)
    course_ids = _course_lesson_ids()

    si = StringIO()
    si.write('\ufeff')
    cw = csv.writer(si, delimiter=';')
    cw.writerow(["Username", "Email", "Seccion", "Estado", "Total_XP", "Lecciones_Completadas", "Nivel", "Racha_Actual", "Fecha_Registro"])
    for s in students:
        stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
        lvl_info = get_level_info(stats["total_xp"])
        safe_user = s.username or ""
        if safe_user.startswith(("=", "+", "-", "@")):
            safe_user = "'" + safe_user
        cls = classroom_map.get(s.section_id)
        cw.writerow([
            safe_user,
            s.email or "",
            f"{cls.name} ({cls.code})" if cls else "Sin sección",
            "Suspendido" if getattr(s, "is_suspended", False) else "Activo",
            stats["total_xp"],
            len(set(stats["completed_lessons"]) & course_ids),
            lvl_info["title"],
            stats["streak"],
            s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A",
        ])
    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_global_estudiantes.csv"},
    )


@app.route("/superadmin/export/pdf")
@login_required
def superadmin_export_pdf():
    if current_user.role != "superadmin":
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    try:
        from pdf_report import build_admin_report_pdf

        course_ids = _course_lesson_ids()
        total_course = len(course_ids) or 1
        students = User.query.filter_by(role="student").all()
        bulk_stats = get_bulk_progress_summaries(students)

        rows = []
        level_counts = {}
        for s in students:
            stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
            lvl = get_level_info(stats["total_xp"])
            completed = len(set(stats["completed_lessons"]) & course_ids)
            rows.append({
                "username": s.username or "",
                "level": lvl["level"],
                "title": lvl["title"],
                "total_xp": stats["total_xp"],
                "completed": completed,
                "progress_pct": round(min(100, completed * 100 / total_course), 1),
                "streak": stats["streak"],
            })
            key = (lvl["level"] if lvl["level"] < 20 else 20, lvl["title"])
            level_counts[key] = level_counts.get(key, 0) + 1

        rows.sort(key=lambda r: r["total_xp"], reverse=True)
        n = len(rows)
        metrics = {
            "total_students": n,
            "avg_xp": round(sum(r["total_xp"] for r in rows) / n) if n else 0,
            "total_completed": sum(r["completed"] for r in rows),
            "avg_progress_pct": round(sum(r["progress_pct"] for r in rows) / n, 1) if n else 0,
            "total_course_lessons": len(course_ids),
            "active_streaks": sum(1 for r in rows if r["streak"] > 0),
            "level_distribution": [
                (f"Lv.{lv} - {title}", count)
                for (lv, title), count in sorted(level_counts.items())
            ],
        }
        pdf_bytes = build_admin_report_pdf(
            rows, metrics,
            site_title=load_ui_strings().get("site_title", "Py2Java Edu"),
            generated_by=f"{current_user.username} (Super Admin)",
        )
    except Exception as e:
        print(f"[ERROR in superadmin_export_pdf]: {type(e).__name__}: {e}", flush=True)
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF global."}), 500

    filename = f"reporte_global_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Tabla de posiciones ---
@app.route("/leaderboard")
def leaderboard():
    board = []
    db_error = False
    teacher_section_ids = set()
    try:
        if current_user.is_authenticated and current_user.role == "teacher":
            teacher_section_ids = _get_teacher_section_ids(current_user.id)
        students = User.query.filter_by(role="student", is_suspended=False).all()
        bulk_stats = get_bulk_progress_summaries(students)
        for s in students:
            summary = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
            lvl_info = get_level_info(summary["total_xp"])
            can_view_profile = bool(
                current_user.is_authenticated
                and (
                    s.id == current_user.id
                    or current_user.role == "superadmin"
                    or (current_user.role == "teacher" and s.section_id in teacher_section_ids)
                )
            )
            board.append({
                "id": s.id,
                "username": s.username or "Anónimo",
                "total_xp": summary["total_xp"],
                "level": lvl_info["level"],
                "completed": len(summary["completed_lessons"]),
                "streak": summary["streak"],
                "can_view_profile": can_view_profile,
            })
        board.sort(key=lambda x: x["total_xp"], reverse=True)

        for i, entry in enumerate(board):
            entry["rank"] = i + 1
    except Exception as e:
        print(f"[ERROR in leaderboard]: {e}", flush=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        db_error = True

    current_uid = current_user.id if current_user.is_authenticated else None
    return render_template(
        "leaderboard.html",
        board=board,
        current_uid=current_uid,
        categories=LESSON_CATEGORIES,
        page="leaderboard",
        db_error=db_error,
    )



# --- Perfil de usuario ---
@app.route("/perfil")
@app.route("/perfil/<username>")
@login_required
def profile(username=None):
    if username:
        user = (
            User.query.filter_by(username=username).first()
            or User.query.filter(func.lower(User.username) == username.lower()).first_or_404()
        )
    else:
        user = current_user

    is_own_profile = current_user.id == user.id
    is_superadmin = current_user.role == "superadmin"
    is_owning_teacher = (
        current_user.role == "teacher"
        and _teacher_owns_student(current_user.id, user)
    )

    if not (is_own_profile or is_superadmin or is_owning_teacher):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_PROFILE_VIEW",
            target_username=user.username,
            section_id=user.section_id,
            reason="Intento de acceso a perfil sin autorización",
        )
        db.session.commit()
        return Response(
            "Acceso denegado: no tienes permisos para ver este perfil.",
            status=403,
            mimetype="text/plain",
        )

    can_view_class_code = is_own_profile or is_superadmin or is_owning_teacher

    summary = get_progress_summary(user)
    level = get_level_info(summary["total_xp"])["level"]

    # Últimas lecciones completadas y estadísticas
    recent = []
    quiz_results = []
    total_exercises = 0
    passed_exercises = 0

    try:
        recent = (
            LessonProgress.query.filter_by(user_id=user.id, completed=True)
            .order_by(LessonProgress.completed_at.desc())
            .limit(10)
            .all()
        )
        quiz_results = (
            QuizResult.query.filter_by(user_id=user.id)
            .order_by(QuizResult.completed_at.desc())
            .limit(10)
            .all()
        )
        total_exercises = ExerciseAttempt.query.filter_by(user_id=user.id).count()
        passed_exercises = ExerciseAttempt.query.filter_by(user_id=user.id, passed=True).count()
    except Exception as e:
        print(f"[ERROR in profile queries]: {e}", flush=True)
        try:
            db.session.rollback()
        except Exception:
            pass

    ui = load_ui_strings()
    completed_set = set(summary["completed_lessons"])
    cert_cards = []
    for cat in LESSON_CATEGORIES:
        cat_lessons = _category_course_lessons(cat)
        done_cnt = sum(1 for lid in cat_lessons if lid in completed_set)
        cert_cards.append({
            "id": cat["id"],
            "name": ui.get(cat["label_key"], cat["id"]),
            "completed": done_cnt,
            "total": len(cat_lessons),
            "is_complete": done_cnt >= len(cat_lessons) and len(cat_lessons) > 0,
        })

    return render_template(
        "profile.html",
        profile_user=user,
        classroom=user.classroom,
        is_own_profile=is_own_profile,
        can_view_class_code=can_view_class_code,
        summary=summary,
        level=level,
        recent=recent,
        quiz_results=quiz_results,
        total_exercises=total_exercises,
        passed_exercises=passed_exercises,
        cert_cards=cert_cards,
        categories=LESSON_CATEGORIES,
        page="profile",
    )


_SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _format_spanish_date(dt):
    return f"{dt.day:02d} de {_SPANISH_MONTHS[dt.month]} de {dt.year}"


def _category_course_lessons(cat):
    """Devuelve solo las lecciones teóricas completables de una categoría (sin quizzes, hubs ni ex-*)."""
    lessons_out = []
    for sec in cat.get("sections", []):
        for lesson_item in sec.get("lessons", []):
            lid = lesson_item["id"]
            if not lesson_item.get("type") and not lid.startswith("ex-"):
                lessons_out.append(lid)
    return lessons_out


def _get_certificate_context(user, section_id):
    target_cat = None
    for cat in LESSON_CATEGORIES:
        if cat["id"] == section_id:
            target_cat = cat
            break
    if not target_cat:
        return None

    summary = get_progress_summary(user)
    completed_set = set(summary["completed_lessons"])
    cat_lessons = _category_course_lessons(target_cat)
    completed_in_cat = [lid for lid in cat_lessons if lid in completed_set]
    is_complete = len(completed_in_cat) >= len(cat_lessons) and len(cat_lessons) > 0

    ui = load_ui_strings()
    now = datetime.now()
    return {
        "category_name": ui.get(target_cat["label_key"], section_id),
        "category_id": section_id,
        "total_lessons": len(cat_lessons),
        "completed_lessons": len(completed_in_cat),
        "is_complete": is_complete,
        "completion_date": _format_spanish_date(now),
        "completion_year": now.year,
        "site_title": ui.get("site_title", "Py2Java Edu"),
    }


# --- Certificado ---
@app.route("/certificado/<section_id>")
@login_required
def certificate(section_id):
    ctx = _get_certificate_context(current_user, section_id)
    if not ctx:
        return redirect(url_for("dashboard"))

    return render_template(
        "certificate.html",
        user=current_user,
        categories=LESSON_CATEGORIES,
        **ctx,
    )


@app.route("/certificado/<section_id>/pdf")
@login_required
def certificate_pdf(section_id):
    ctx = _get_certificate_context(current_user, section_id)
    if not ctx:
        return redirect(url_for("dashboard"))
    if not ctx["is_complete"]:
        return redirect(url_for("certificate", section_id=section_id))

    try:
        from pdf_report import build_certificate_pdf

        pdf_bytes = build_certificate_pdf(
            username=current_user.username,
            category_name=ctx["category_name"],
            category_id=ctx["category_id"],
            user_id=current_user.id,
            total_lessons=ctx["total_lessons"],
            completion_date=ctx["completion_date"],
            completion_year=ctx["completion_year"],
            site_title=ctx["site_title"],
        )
    except Exception as e:
        print(f"[ERROR in certificate_pdf]: {type(e).__name__}: {e}", flush=True)
        return jsonify({"ok": False, "error": "No se pudo generar el certificado PDF."}), 500

    safe_user = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in ("_", "-")) else "_"
        for ch in (current_user.username or "estudiante")
    ).strip("_") or "estudiante"
    filename = f"certificado_{section_id}_{safe_user}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Tema visual ---
@app.route("/api/theme", methods=["POST"])
def toggle_theme():
    data = _get_json_dict()
    theme = data.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"
    session["theme"] = theme
    return jsonify({"ok": True, "theme": theme})


@app.route("/configuracion", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        session["theme"] = theme if theme in ("light", "dark") else "light"
        safe_ref = _get_safe_next_url(request.referrer, default=url_for("index"))
        return redirect(safe_ref)

    return redirect(url_for("index"))


@app.route("/traductor")
def traductor():
    return render_template(
        "translator.html", categories=LESSON_CATEGORIES, page="translator"
    )


# --- Tutor IA ---

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


@app.route("/api/ai/tutor", methods=["POST"])
def api_ai_tutor():
    if not GEMINI_API_KEY:
        return jsonify(
            {"ok": False, "error": "API key no configurada. Configura GEMINI_API_KEY."}
        )

    data = _get_json_dict()
    raw_code = data.get("code", "")
    user_code = raw_code if isinstance(raw_code, str) else ""
    raw_lesson = data.get("lesson_id", "")
    lesson_id = raw_lesson if isinstance(raw_lesson, str) else ""
    raw_q = data.get("question", "")
    question = (raw_q if isinstance(raw_q, str) else "").strip()
    raw_mode = data.get("mode")
    mode = raw_mode if isinstance(raw_mode, str) and raw_mode else ("chat" if question else "analyze")
    raw_ex_q = data.get("exercise_question", "")
    exercise_question = raw_ex_q if isinstance(raw_ex_q, str) else ""
    history = data.get("history", [])

    # Load lesson context
    lesson_data = get_lesson(lesson_id)
    lesson_title = lesson_data.get("title", lesson_id)
    lesson_intro = lesson_data.get("intro", "")

    history_context = ""
    if isinstance(history, list) and history:
        history_lines = []
        for h in history[-4:]:
            if isinstance(h, dict):
                role = "Estudiante" if h.get("role") == "user" else "Tutor IA"
                txt = h.get("text", "").strip()
                if txt:
                    history_lines.append(f"{role}: {txt}")
        if history_lines:
            history_context = "Historial reciente de la conversación:\n" + "\n".join(history_lines) + "\n\n"

    if mode == "hint":
        system_prompt = f"""Eres un tutor de programación amigable y pedagógico para estudiantes que aprenden Python y Java.
Estás ayudando con un ejercicio de la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS ESTRICTAS:
- NUNCA des la respuesta directa ni el código resuelto completo al ejercicio.
- Da pistas progresivas y conceptuales que guíen al estudiante para que lo resuelva por sí mismo.
- Usa analogías simples y comprensibles.
- Responde en español de forma completa y concisa (máximo 3-4 oraciones).
- Concluye siempre tu idea para que la respuesta nunca quede cortada."""
        user_message = f"Pregunta del ejercicio: {exercise_question}\n\nIntento/código del estudiante: {user_code}\n\nDuda del estudiante: {question if question else 'No entiendo cómo resolverlo'}"

    elif mode == "chat" or question:
        system_prompt = f"""Eres un tutor de programación inteligente, didáctico y amigable para estudiantes de Python y Java.
Estás en la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS PRINCIPALES:
- Responde DIRECTA, CLARA y CONCRETAMENTE a la PREGUNTA o DUDA planteada por el estudiante.
- Sé didáctico pero sintético: explica el concepto en 2-3 párrafos claros y directos con ejemplos cortos de código.
- NUNCA te extiendas innecesariamente con introducciones vacías ni rodeos.
- Concluye SIEMPRE tu explicación y ejemplos para que tu respuesta sea 100% completa y no quede cortada a la mitad.
- Si el estudiante pregunta sobre sintaxis (comas, llaves, f-strings, concatenación, print, tipos de variables), explícaselo con un ejemplo sencillo de 'Correcto vs Incorrecto'.
- Responde siempre en español."""

        context_code = f"\n\nCódigo actual en el editor (solo para contexto si aplica):\n```python\n{user_code}\n```" if user_code.strip() else ""
        user_message = f"{history_context}Pregunta del estudiante: {question}{context_code}"

    else:  # mode == "analyze"
        system_prompt = f"""Eres un analizador de código Python/Java para estudiantes.
Estás en la lección "{lesson_title}".

REGLAS:
- Analiza el código del estudiante y da feedback constructivo y directo.
- Señala errores, mejoras de estilo y buenas prácticas de forma clara y pedagógica.
- Si el código está bien, felicita al estudiante y dale un consejo o tip de mejora conciso.
- Responde en español de forma completa y directa (máximo 3-4 párrafos estructurados)."""
        user_message = f"Analiza este código:\n```python\n{user_code}\n```"

    try:
        payload = {
            "contents": [
                {"parts": [{"text": system_prompt + "\n\n" + user_message}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
        }

        resp = http_requests.post(
            GEMINI_API_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        if resp.status_code == 429:
            return jsonify(
                {
                    "ok": False,
                    "error": "Límite de peticiones alcanzado (Error 429). Por favor, espera un momento antes de volver a preguntar.",
                }
            )

        resp.raise_for_status()
        result = resp.json()
        
        candidates = result.get("candidates", [])
        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
            parts = candidates[0]["content"]["parts"]
            ai_text = "".join([p.get("text", "") for p in parts if "text" in p])
        else:
            ai_text = "No se pudo generar una respuesta. Por favor formula tu pregunta nuevamente."

        return jsonify({"ok": True, "response": ai_text})
    except http_requests.exceptions.Timeout:
        return jsonify(
            {
                "ok": False,
                "error": "La IA tardó demasiado en responder. Intenta formular una pregunta más específica.",
            }
        )
    except Exception as e:
        print(f"[ERROR in api_ai_tutor]: {type(e).__name__}", flush=True)
        return jsonify({"ok": False, "error": "No fue posible conectar con el Tutor IA en este momento. Intenta de nuevo más tarde."})

# --- Ejercicios y quizzes ---

@app.route("/ejercicios/<topic>")
def exercise_topic(topic):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
    
    exercises = lesson_data.get("exercises", [])
    user = get_current_user()
    completed_exercises = []
    completed_count = 0
    
    if user and user.is_authenticated:
        attempts = ExerciseAttempt.query.filter_by(user_id=user.id, lesson_id=topic, passed=True).all()
        completed_set = {a.exercise_id for a in attempts} | {f"{a.lesson_id}-{a.exercise_id}" for a in attempts}
        completed_exercises = list(completed_set)
        for idx, ex in enumerate(exercises, start=1):
            ex_id = ex.get("id")
            if (ex_id and ex_id in completed_set) or f"{topic}-{idx}" in completed_set:
                completed_count += 1
        
    return render_template(
        "exercise_hub.html",
        topic=topic,
        exercise_data=lesson_data,
        exercises=exercises,
        completed_exercises=completed_exercises,
        completed_count=completed_count,
        categories=LESSON_CATEGORIES,
        page="exercises"
    )

@app.route("/ejercicio/<topic>/<int:exercise_num>")
def exercise_page(topic, exercise_num):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
        
    exercises = lesson_data.get("exercises", [])
    if exercise_num < 1 or exercise_num > len(exercises):
        return redirect(url_for("exercise_topic", topic=topic))
        
    current_exercise = exercises[exercise_num - 1]
    
    return render_template(
        "exercise.html",
        topic=topic,
        exercise_data=lesson_data,
        current_exercise=current_exercise,
        exercise_num=exercise_num,
        total_exercises=len(exercises),
        categories=LESSON_CATEGORIES,
        page="exercises"
    )


@app.route("/quiz/<topic>")
def quiz(topic):
    quiz_data = load_quiz(topic)
    if not quiz_data:
        return redirect(url_for("index"))
        
    return render_template(
        "quiz.html",
        quiz_data=quiz_data,
        categories=LESSON_CATEGORIES,
        page="quiz"
    )


@app.route("/api/quiz/resultado", methods=["POST"])
def api_quiz_result():
    data = _get_json_dict()
    raw_quiz_id = data.get("quiz_id")
    quiz_id = str(raw_quiz_id).strip()[:50] if isinstance(raw_quiz_id, str) and raw_quiz_id.strip() else None
    score = _safe_int(data.get("score", 0), 0)
    total = _safe_int(data.get("total", 0), 0)
    
    user = get_current_user()
    if user and quiz_id:
        result = QuizResult(user_id=user.id, quiz_id=quiz_id, score=score, total=total)
        db.session.add(result)
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False})


@app.route("/ejemplos")
def examples():
    catalog = load_examples_catalog()
    return render_template(
        "examples.html",
        example_categories=catalog.get("categories", []),
        categories=LESSON_CATEGORIES,
        page="examples"
    )


@app.route("/ejemplo/<example_id>")
def example_detail(example_id):
    example = get_example_by_id(example_id)
    if not example:
        return redirect(url_for("examples"))
        
    return render_template(
        "example_detail.html",
        example=example,
        categories=LESSON_CATEGORIES,
        page="examples"
    )



@app.context_processor
def inject_globals():
    ui = load_ui_strings()
    return {
        "lang": "es",
        "theme": session.get("theme", "light"),
        "t": ui,
        "get_lesson": lambda lid: get_lesson(lid),
        "get_lesson_title": lambda lid: get_lesson_title(lid),
        "get_reference": lambda cat: get_reference(cat),
    }


# --- Evaluaciones por sección ---

# Maps section label_keys to their evaluation file IDs
SECTION_EVAL_MAP = {
    "cat_python_tutorial": "eval-python-tutorial",
    "cat_python_functions": "eval-python-functions",
    "cat_python_classes": "eval-python-classes",
    "cat_python_modules": "eval-python-modules",
    "cat_file_handling": "eval-file-handling",
    "cat_numpy": "eval-numpy",
    "cat_pandas": "eval-pandas",
    "cat_scipy": "eval-scipy",
    "cat_mysql": "eval-mysql",
    "cat_mongodb": "eval-mongodb",
}


def get_section_lessons(section_key):
    """Returns the list of lesson IDs for a given section label_key."""
    for cat in LESSON_CATEGORIES:
        for sec in cat["sections"]:
            if sec["label_key"] == section_key:
                return [lesson["id"] for lesson in sec["lessons"]
                        if not lesson.get("type")]  # Exclude quiz/practice/examples entries
    return []


def get_section_eval_status(user_id, section_key):
    """Check if a section evaluation is unlocked and its pass status."""
    lesson_ids = get_section_lessons(section_key)
    if not lesson_ids:
        return {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0}

    # Count completed lessons
    completed = LessonProgress.query.filter(
        LessonProgress.user_id == user_id,
        LessonProgress.lesson_id.in_(lesson_ids),
        LessonProgress.completed == True
    ).count()

    completion_pct = round((completed / len(lesson_ids)) * 100) if lesson_ids else 0
    unlocked = completion_pct >= 80

    # Check best evaluation result
    best_eval = SectionEvaluation.query.filter_by(
        user_id=user_id, section_id=section_key
    ).order_by(SectionEvaluation.percentage.desc()).first()

    total_attempts = SectionEvaluation.query.filter_by(
        user_id=user_id, section_id=section_key
    ).count()

    return {
        "unlocked": unlocked,
        "passed": best_eval.passed if best_eval else False,
        "best_score": round(best_eval.percentage) if best_eval else 0,
        "attempts": total_attempts,
        "completion_pct": completion_pct,
        "completed_lessons": completed,
        "total_lessons": len(lesson_ids),
    }


def generate_adaptive_questions(section_key, user_id):
    """Generate an adaptive set of questions based on completed lessons."""
    eval_data = get_evaluation_for_section(section_key)
    if not eval_data:
        return [], eval_data

    lesson_questions = eval_data.get("lesson_questions", {})
    questions_per_eval = eval_data.get("questions_per_eval", 20)

    # Get completed lessons for this user in this section
    section_lessons = get_section_lessons(section_key)
    completed_records = LessonProgress.query.filter(
        LessonProgress.user_id == user_id,
        LessonProgress.lesson_id.in_(section_lessons),
        LessonProgress.completed == True
    ).all()
    completed_ids = {r.lesson_id for r in completed_records}

    # Collect questions only from completed lessons
    available = []
    for lesson_id in completed_ids:
        qs = lesson_questions.get(lesson_id, [])
        for q in qs:
            q_copy = dict(q)
            q_copy["source_lesson"] = lesson_id
            available.append(q_copy)

    # Select random subset
    num_questions = min(questions_per_eval, len(available))
    if num_questions == 0:
        return [], eval_data

    selected = random.sample(available, num_questions)
    random.shuffle(selected)
    return selected, eval_data


@app.route("/evaluacion/<section_key>")
@login_required
def evaluation_page(section_key):
    """Render the adaptive evaluation page for a section."""
    if section_key not in SECTION_EVAL_MAP:
        return redirect(url_for("dashboard"))

    user = current_user
    status = get_section_eval_status(user.id, section_key)

    if not status["unlocked"]:
        return redirect(url_for("dashboard"))

    questions, eval_data = generate_adaptive_questions(section_key, user.id)
    if not eval_data:
        return redirect(url_for("dashboard"))

    # Strip correct answers from questions sent to client (security)
    client_questions = []
    for q in questions:
        cq = {
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "difficulty": q.get("difficulty", "medium"),
            "source_lesson": q.get("source_lesson", ""),
        }
        if q["type"] == "multiple_choice":
            cq["options"] = q["options"]
        elif q["type"] == "complete_code":
            cq["code_template"] = q["code_template"]
        elif q["type"] == "true_false":
            pass  # No extra fields needed
        client_questions.append(cq)

    # Limpiar claves previas de evaluaciones en la sesión para no superar el límite de 4 KB de cookies
    for k in list(session.keys()):
        if k.startswith("eval_answers_") or k.startswith("eval_questions_"):
            session.pop(k, None)

    # Guardar únicamente el mapa compacto {id: respuesta_correcta} en la sesión
    answer_key = {}
    for q in questions:
        if q["type"] in ("multiple_choice", "true_false"):
            answer_key[q["id"]] = q["correct"]
        elif q["type"] == "complete_code":
            answer_key[q["id"]] = q["correct_answer"]

    session[f"eval_answers_{section_key}"] = answer_key
    session[f"eval_questions_{section_key}"] = [q["id"] for q in questions]

    # Get section display info
    ui = load_ui_strings()
    section_title = ui.get(section_key, section_key)

    # Time limit: 30s per question, capped at max 10 minutes (600s)
    raw_time = eval_data.get("time_per_question", 30) * len(client_questions)
    time_limit = min(600, raw_time)

    return render_template(
        "evaluation.html",
        section_key=section_key,
        section_title=section_title,
        eval_data=eval_data,
        questions=client_questions,
        questions_json=json.dumps(client_questions, ensure_ascii=False),
        time_limit=time_limit,
        status=status,
        passing_score=eval_data.get("passing_score", 70),
        categories=LESSON_CATEGORIES,
        page="evaluation",
    )


@app.route("/api/evaluacion/resultado", methods=["POST"])
@login_required
def api_evaluation_result():
    """Process and save evaluation results."""
    data = _get_json_dict()
    section_key = data.get("section_key", "")
    answers = data.get("answers", {})
    time_taken = _safe_int(data.get("time_taken", 0), 0)

    if not isinstance(section_key, str) or section_key not in SECTION_EVAL_MAP:
        return jsonify({"ok": False, "error": "Sección inválida"})
    if not isinstance(answers, dict):
        return jsonify({"ok": False, "error": "Formato de respuestas inválido"})

    user = current_user
    status = get_section_eval_status(user.id, section_key)
    if not status["unlocked"]:
        return jsonify({"ok": False, "error": "Debes completar al menos el 80% de las lecciones de la sección antes de presentar la evaluación."})

    eval_data = get_evaluation_for_section(section_key)
    question_source_map = {}
    catalog_answers = {}
    if eval_data:
        for lesson_id, qs in eval_data.get("lesson_questions", {}).items():
            for q in qs:
                question_source_map[q["id"]] = lesson_id
                catalog_answers[q["id"]] = (
                    q.get("correct_answer") if q.get("type") == "complete_code" else q.get("correct")
                )

    # Get answer key from session (or fall back to server catalog if cookie was dropped)
    answer_key = session.get(f"eval_answers_{section_key}", {})
    session_qids = session.get(f"eval_questions_{section_key}", [])
    if session_qids:
        question_ids = session_qids
    else:
        question_ids = [qid for qid in answers.keys() if isinstance(qid, str) and qid in catalog_answers]

    if not question_ids:
        return jsonify({"ok": False, "error": "Sesión de evaluación expirada"})
    score = 0
    total = len(question_ids)
    details = {}

    for qid in question_ids:
        raw_key = answer_key.get(qid, catalog_answers.get(qid))
        correct_val = raw_key.get("correct") if isinstance(raw_key, dict) else raw_key
        user_answer = answers.get(qid)
        source_lesson = question_source_map.get(qid, "")

        if source_lesson not in details:
            details[source_lesson] = {"correct": 0, "total": 0, "lesson_title": get_lesson_title(source_lesson)}

        details[source_lesson]["total"] += 1

        is_correct = False
        if isinstance(correct_val, bool):
            is_correct = (user_answer == correct_val)
        elif isinstance(correct_val, int):
            try:
                is_correct = (int(user_answer) == correct_val)
            except (ValueError, TypeError):
                is_correct = False
        elif isinstance(correct_val, str):
            is_correct = (str(user_answer).strip().lower() == correct_val.strip().lower())

        if is_correct:
            score += 1
            details[source_lesson]["correct"] += 1

    percentage = round((score / total) * 100, 1) if total > 0 else 0
    passed = percentage >= 70

    # Count previous attempts and check prior pass BEFORE adding the new evaluation (avoids autoflush)
    prev_attempts = SectionEvaluation.query.filter_by(
        user_id=user.id, section_id=section_key
    ).count()
    already_passed = None
    if passed:
        already_passed = SectionEvaluation.query.filter_by(
            user_id=user.id, section_id=section_key, passed=True
        ).first()

    # Save result
    evaluation = SectionEvaluation(
        user_id=user.id,
        section_id=section_key,
        score=score,
        total=total,
        percentage=percentage,
        passed=passed,
        time_taken=time_taken,
        attempt_number=prev_attempts + 1,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.session.add(evaluation)

    # Award XP if passed for first time
    xp_gained = 0
    if passed:
        if not already_passed:
            xp_gained = 100
            # Update a LessonProgress record for XP tracking
            lp = LessonProgress.query.filter_by(
                user_id=user.id, lesson_id=f"eval-{section_key}"
            ).first()
            if not lp:
                lp = LessonProgress(
                    user_id=user.id, lesson_id=f"eval-{section_key}",
                    completed=True, score=xp_gained, completed_at=datetime.now(timezone.utc)
                )
                db.session.add(lp)
            record_daily_activity(user.id)

    db.session.commit()

    # Clean up session
    session.pop(f"eval_answers_{section_key}", None)
    session.pop(f"eval_questions_{section_key}", None)

    return jsonify({
        "ok": True,
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": passed,
        "xp_gained": xp_gained,
        "attempt_number": prev_attempts + 1,
        "details": details,
    })


@app.route("/api/evaluacion/estados")
def api_evaluation_statuses():
    """Obtiene el estado de todas las evaluaciones de sección en solo 2 consultas SQL."""
    if not current_user.is_authenticated:
        return jsonify({k: {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0} for k in SECTION_EVAL_MAP})

    user_id = current_user.id
    completed_rows = LessonProgress.query.filter_by(user_id=user_id, completed=True).all()
    completed_set = {r.lesson_id for r in completed_rows}

    eval_rows = SectionEvaluation.query.filter_by(user_id=user_id).all()
    evals_by_sec = {}
    for r in eval_rows:
        evals_by_sec.setdefault(r.section_id, []).append(r)

    results = {}
    for section_key in SECTION_EVAL_MAP:
        lesson_ids = get_section_lessons(section_key)
        if not lesson_ids:
            results[section_key] = {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0}
            continue
        completed_cnt = sum(1 for lid in lesson_ids if lid in completed_set)
        completion_pct = round((completed_cnt / len(lesson_ids)) * 100)
        sec_evals = evals_by_sec.get(section_key, [])
        best_pct = max((e.percentage for e in sec_evals), default=0)
        passed = any(e.passed for e in sec_evals)
        results[section_key] = {
            "unlocked": completion_pct >= 80,
            "passed": passed,
            "best_score": round(best_pct),
            "attempts": len(sec_evals),
            "completion_pct": completion_pct,
            "completed_lessons": completed_cnt,
            "total_lessons": len(lesson_ids),
        }
    return jsonify(results)


@app.route("/api/evaluacion/estado/<section_key>")
def api_evaluation_status(section_key):
    """Get the evaluation readiness status for a section."""
    if not current_user.is_authenticated:
        return jsonify({"unlocked": False, "passed": False})

    status = get_section_eval_status(current_user.id, section_key)
    return jsonify(status)


@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").strip().lower() == "true"
    app.run(debug=debug_mode, port=5000)

