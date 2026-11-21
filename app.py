import ast
import csv
import hashlib
import hmac
import html
from io import StringIO
import json
import logging
import math
import os
import random
import re
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from dotenv import load_dotenv

load_dotenv()

import click
import requests as http_requests
from flask import (Flask, Response, flash, g, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import case, distinct, false, func, nullslast, or_
from werkzeug.security import check_password_hash, generate_password_hash

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import socket
import ssl

from content_loader import (LESSON_ALIASES, get_lesson, get_lesson_title, get_reference,
                            load_lesson, get_lesson_exercise,
                            get_valid_exercise_ids, get_valid_practice_ids,
                            load_ui_strings, load_quiz, load_all_quizzes,
                            load_examples_catalog, get_example_by_id,
                            load_practice_problems, get_practice_problem,
                            get_evaluation_for_section, load_all_evaluations)
from models import (AuditLog, Classroom, ExerciseAttempt, LessonProgress, User, QuizResult,
                    PracticeSubmission, DailyStreak, SectionEvaluation, EvaluationSession,
                    PasswordResetCode, db, ensure_utc, utcnow)
from search_index import search_lessons
from translator import translate

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
    logger.warning("SECRET_KEY no configurada en desarrollo local. Usando clave temporal aleatoria.")
elif len(_secret) < 32:
    logger.warning("SECRET_KEY tiene menos de 32 caracteres. Usa una clave de al menos 32 caracteres en producción.")

app.secret_key = _secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = is_production

csrf = CSRFProtect(app)

TEACHER_SECRET_CODE = os.environ.get("TEACHER_SECRET_CODE", "")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
MIN_PASSWORD_LENGTH = 8
MAX_RESET_FAILED_ATTEMPTS = 5
_DUMMY_PASSWORD_HASH = generate_password_hash("py2java-dummy-timing-guard")
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(val):
    """Neutraliza CSV Formula Injection anteponiendo apóstrofo a prefijos peligrosos."""
    if val is None:
        return ""
    text = str(val)
    if text.startswith(_CSV_FORMULA_PREFIXES) or text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _is_valid_username(username):
    return bool(username and USERNAME_RE.fullmatch(username))


def _is_valid_email(email):
    return bool(email and len(email) <= 120 and EMAIL_RE.fullmatch(email))


def _is_safe_redirect_url(raw_next):
    """Permite únicamente rutas relativas internas estrictas, bloqueando Open Redirect."""
    if not raw_next or not isinstance(raw_next, str):
        return False
    cleaned = raw_next.strip()
    if not cleaned or "\\" in cleaned or any(ord(c) < 32 for c in cleaned):
        return False
    parsed = urlparse(cleaned)
    return (
        parsed.scheme == ""
        and parsed.netloc == ""
        and cleaned.startswith("/")
        and not cleaned.startswith(("//", "/\\"))
    )


def _extract_relative_from_referrer(referrer):
    """Extrae una ruta relativa desde Referer solo si coincide exactamente con el host actual."""
    if not referrer or not isinstance(referrer, str):
        return ""
    cleaned = referrer.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme in ("http", "https") and parsed.netloc == request.host:
        rel = parsed.path or "/"
        if parsed.query:
            rel = f"{rel}?{parsed.query}"
        return rel
    return cleaned


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


def _user_rate_limit_key():
    """Clave de rate-limiting por usuario autenticado (con fallback a IP)."""
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return f"ip:{_get_client_ip()}"


_DATA_ANSWER_ATTR_RE = re.compile(r"""\s+data-answer\s*=\s*(?:"[^"]*"|'[^']*')""", re.I)
_DATA_ANSWER_EXTRACT_RE = re.compile(r"""data-answer\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


@app.template_filter("strip_exercise_answers")
def strip_exercise_answers_filter(raw_html):
    """Elimina atributos data-answer del HTML de ejercicios antes de enviarlo al navegador."""
    if not isinstance(raw_html, str):
        return ""
    return _DATA_ANSWER_ATTR_RE.sub("", raw_html)


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
migrate = Migrate(app, db, render_as_batch=True)

_APP_TZ_CACHE = {}


def _get_app_timezone():
    """Resuelve la zona horaria operativa (por defecto America/Bogota) para rachas y reportes."""
    tz_name = (os.environ.get("APP_TIMEZONE") or "America/Bogota").strip() or "America/Bogota"
    if tz_name in _APP_TZ_CACHE:
        return _APP_TZ_CACHE[tz_name]

    tz = None
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = None

    if tz is None:
        match = re.fullmatch(r"(?:UTC|GMT)?\s*([+-])(\d{1,2})(?::?(\d{2}))?", tz_name, re.I)
        if match:
            sign = 1 if match.group(1) == "+" else -1
            hours = int(match.group(2))
            mins = int(match.group(3) or 0)
            if hours <= 14 and mins < 60:
                tz = timezone(timedelta(hours=sign * hours, minutes=sign * mins))

    if tz is None:
        logger.warning("APP_TIMEZONE inválido o sin datos IANA ('%s'); usando UTC.", tz_name)
        tz = timezone.utc

    _APP_TZ_CACHE[tz_name] = tz
    return tz


def _app_now():
    """Fecha y hora actual en la zona horaria operativa, derivada siempre de UTC."""
    return utcnow().astimezone(_get_app_timezone())


def _get_app_today():
    """Fecha calendario actual en la zona horaria operativa (consistente con UTC)."""
    return _app_now().date()


login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"
login_manager.init_app(app)


@login_manager.unauthorized_handler
def _handle_unauthorized():
    wants_json = (
        request.is_json
        or request.path.startswith("/api/")
        or "application/json" in (request.headers.get("Accept") or "")
    )
    if wants_json:
        return jsonify({
            "ok": False,
            "error": "Debes iniciar sesión para usar esta función.",
        }), 401
    flash(login_manager.login_message, login_manager.login_message_category)
    next_path = request.full_path.rstrip("?")
    return redirect(url_for("login", next=next_path))


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logger.error("Error en load_user(user_id=%s): %s", user_id, e)
        db.session.rollback()
        return None


def _bootstrap_initial_superadmin():
    """Crea un Super Admin inicial desde variables de entorno SOLO si aún no existe ninguno."""
    existing_sa = User.query.filter_by(role="superadmin").first()
    if existing_sa:
        return False

    sa_username = (os.environ.get("SUPERADMIN_USERNAME") or "").strip()
    sa_email = (os.environ.get("SUPERADMIN_EMAIL") or "").strip().lower()
    sa_password = os.environ.get("SUPERADMIN_PASSWORD") or ""

    if not (sa_username or sa_email or sa_password):
        logger.info(
            "No existe ninguna cuenta Super Admin. Ejecuta 'flask create-superadmin' "
            "o define SUPERADMIN_USERNAME, SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD."
        )
        return False

    if not (sa_username and sa_email and sa_password):
        logger.warning(
            "Variables de bootstrap de Super Admin incompletas. "
            "Se requieren SUPERADMIN_USERNAME, SUPERADMIN_EMAIL y SUPERADMIN_PASSWORD."
        )
        return False

    if not _is_valid_username(sa_username):
        logger.warning(
            "SUPERADMIN_USERNAME inválido (debe tener 3-30 caracteres: letras, números, _ o -)."
        )
        return False

    if not _is_valid_email(sa_email):
        logger.warning("SUPERADMIN_EMAIL no tiene un formato de correo válido.")
        return False

    if len(sa_password) < MIN_PASSWORD_LENGTH:
        logger.warning(
            "SUPERADMIN_PASSWORD debe tener al menos %d caracteres.", MIN_PASSWORD_LENGTH
        )
        return False

    collision = User.query.filter(
        or_(
            func.lower(User.username) == sa_username.lower(),
            func.lower(User.email) == sa_email.lower(),
        )
    ).first()
    if collision:
        logger.warning(
            "No se creó Super Admin desde variables de entorno porque el usuario o correo ya existe."
        )
        return False

    superadmin_user = User(
        username=sa_username,
        email=sa_email or None,
        password_hash=generate_password_hash(sa_password),
        role="superadmin",
        is_suspended=False,
    )
    db.session.add(superadmin_user)
    db.session.commit()
    logger.info("Cuenta Super Admin inicial '%s' creada desde variables de entorno.", sa_username)
    return True


@app.cli.command("bootstrap-superadmin")
def bootstrap_superadmin_command():
    """Crea la cuenta Super Admin inicial desde variables de entorno si aún no existe."""
    created = _bootstrap_initial_superadmin()
    if created:
        click.echo("Super Admin inicial creado desde variables de entorno.")
    else:
        click.echo("No se creó ningún Super Admin nuevo (revisa los logs para detalles).")


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
    """Crea una cuenta Super Admin de forma segura desde la CLI (requiere 'flask db upgrade' previo)."""
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
        email=clean_email or None,
        password_hash=generate_password_hash(password),
        role="superadmin",
        is_suspended=False,
    )
    db.session.add(new_sa)
    db.session.commit()
    logger.info("Super Admin '%s' creado mediante CLI.", clean_username)
    click.echo(f"Super Admin '{clean_username}' creado correctamente.")


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


@app.before_request
def _generate_csp_nonce():
    """Genera un nonce criptográfico único por petición para Content-Security-Policy."""
    g.csp_nonce = secrets.token_urlsafe(16)


@app.context_processor
def _inject_security_context():
    return {"csp_nonce": getattr(g, "csp_nonce", "")}


@app.errorhandler(CSRFError)
def handle_csrf_error(err):
    msg = "Token CSRF inválido o expirado. Recarga la página e intenta de nuevo."
    wants_json = (
        request.is_json
        or request.path.startswith("/api/")
        or "application/json" in (request.headers.get("Accept") or "")
    )
    if wants_json:
        return jsonify({"ok": False, "success": False, "error": msg}), 400
    return Response(msg, status=400, mimetype="text/plain")


@app.after_request
def _set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    if request.is_secure or forwarded_proto == "https" or is_production:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    nonce = getattr(g, "csp_nonce", "")
    script_nonce = f"'nonce-{nonce}'" if nonce else ""
    csp_directives = [
        "default-src 'self'",
        f"script-src 'self' {script_nonce} https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'wasm-unsafe-eval'",
        f"script-src-elem 'self' {script_nonce} https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "script-src-attr 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: blob:",
        "connect-src 'self' https://cdn.jsdelivr.net",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
    ]
    response.headers.setdefault("Content-Security-Policy", "; ".join(csp_directives))
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
            logger.warning("Prerequisite check failed (DB issue): %s", e)
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

XP_PER_LESSON = 10
XP_PER_EXERCISE = 25
XP_PER_PRACTICE = 50
XP_PER_EVALUATION = 100
MAX_PRACTICE_CODE_CHARS = 8000


def _normalize_answer_text(val):
    return re.sub(r"\s+", " ", str(val).strip().lower())


def _is_trivial_function_body(body):
    """Devuelve True si el cuerpo de una función solo contiene pass, ... o docstrings."""
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            if stmt.value.value is Ellipsis or isinstance(stmt.value.value, str):
                continue
        return False
    return True


def _validate_practice_code_ast(problem, code):
    """Valida estáticamente (sin exec) que el código tenga sintaxis válida e implemente la función pedida."""
    if not isinstance(code, str):
        return False, "El código enviado es inválido."
    stripped = code.strip()
    if not stripped or len(code) > MAX_PRACTICE_CODE_CHARS:
        return False, f"El código debe tener entre 1 y {MAX_PRACTICE_CODE_CHARS} caracteres."

    starter = (problem.get("starter_code") or "").strip()
    if stripped == starter:
        return False, "Debes implementar tu solución antes de enviarla."

    try:
        user_tree = ast.parse(code)
    except SyntaxError:
        return False, "El código contiene errores de sintaxis Python."

    required_funcs = set()
    if starter:
        try:
            starter_tree = ast.parse(starter)
            for node in ast.walk(starter_tree):
                if isinstance(node, ast.FunctionDef):
                    required_funcs.add(node.name)
        except SyntaxError:
            pass

    if required_funcs:
        user_funcs = {
            node.name: node
            for node in ast.walk(user_tree)
            if isinstance(node, ast.FunctionDef)
        }
        for fname in required_funcs:
            fn_node = user_funcs.get(fname)
            if not fn_node or _is_trivial_function_body(fn_node.body):
                return False, f"Debes implementar el cuerpo de la función '{fname}'."

    return True, None


def _extract_exercise_blanks(ex, lang="python"):
    use_java = lang == "java" and bool(ex.get("template_html_java"))
    tpl = ex.get("template_html_java") if use_java else ex.get("template_html")
    if isinstance(tpl, str) and tpl:
        extracted = [
            html.unescape(m.group(1) if m.group(1) is not None else m.group(2))
            for m in _DATA_ANSWER_EXTRACT_RE.finditer(tpl)
        ]
        if extracted:
            return extracted
    ans = ex.get("answer_java") if use_java and ex.get("answer_java") is not None else ex.get("answer")
    if ans is not None:
        return [str(ans)]
    if ex.get("expected_output") is not None:
        return [str(ex["expected_output"])]
    return []


def _grade_exercise_submission(ex, lang, raw_answer, raw_answers):
    """Califica estrictamente en el servidor una respuesta de ejercicio del currículo."""
    ex_type = ex.get("type") or "fill-blank"
    use_java = lang == "java" and bool(
        ex.get("question_java") or ex.get("template_html_java") or ex.get("options_java")
    )
    explanation = (
        ex.get("explanation_java") or ex.get("explanation") or ""
        if use_java
        else ex.get("explanation") or ""
    )

    if ex_type == "multiple-choice":
        correct_raw = (
            ex.get("correct_java", ex.get("correct"))
            if (use_java and ex.get("options_java"))
            else ex.get("correct")
        )
        correct_idx = _safe_int(correct_raw, -1)
        if isinstance(raw_answer, bool) or raw_answer is None:
            selected_idx = -1
        else:
            selected_idx = _safe_int(raw_answer, -1)
        passed = correct_idx >= 0 and selected_idx == correct_idx
        return passed, {
            "type": "multiple-choice",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
            "selected_index": selected_idx,
            "correct_index": correct_idx if passed else None,
        }

    if ex_type == "reorder":
        lines = ex.get("lines") or []
        expected = list(range(len(lines)))
        if isinstance(raw_answers, list) and len(raw_answers) == len(expected):
            cleaned = []
            valid_list = True
            for item in raw_answers:
                if isinstance(item, bool):
                    valid_list = False
                    break
                val = _safe_int(item, -1)
                if val < 0:
                    valid_list = False
                    break
                cleaned.append(val)
            passed = valid_list and bool(expected) and cleaned == expected
        else:
            passed = False
        return passed, {
            "type": "reorder",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
        }

    if ex_type == "find-error":
        correct_line = _safe_int(ex.get("error_line", -1), -1)
        if isinstance(raw_answer, bool) or raw_answer is None:
            selected_line = -1
        else:
            selected_line = _safe_int(raw_answer, -1)
        passed = correct_line >= 0 and selected_line == correct_line
        return passed, {
            "type": "find-error",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
            "selected_line": selected_line,
            "correct_line": correct_line if passed else None,
        }

    # fill-blank o freeform
    expected_blanks = _extract_exercise_blanks(ex, "java" if use_java else "python")
    if isinstance(raw_answers, list):
        user_blanks = ["" if v is None else str(v) for v in raw_answers]
    elif raw_answer is not None:
        user_blanks = [str(raw_answer)]
    else:
        user_blanks = []

    input_results = []
    for idx, exp_val in enumerate(expected_blanks):
        u_val = user_blanks[idx] if idx < len(user_blanks) else ""
        input_results.append(_normalize_answer_text(u_val) == _normalize_answer_text(exp_val))

    passed = bool(expected_blanks) and len(user_blanks) == len(expected_blanks) and all(input_results)
    return passed, {
        "type": "fill-blank",
        "explanation": explanation,
        "hint": ex.get("hint") or "",
        "input_results": input_results,
    }


def _get_exercise_solution(ex, lang="python"):
    """Devuelve la solución de un ejercicio para el botón 'Ver Solución' (sin otorgar XP)."""
    ex_type = ex.get("type") or "fill-blank"
    use_java = lang == "java" and bool(
        ex.get("question_java") or ex.get("template_html_java") or ex.get("options_java")
    )
    explanation = (
        ex.get("explanation_java") or ex.get("explanation") or ""
        if use_java
        else ex.get("explanation") or ""
    )
    if ex_type == "multiple-choice":
        correct_raw = (
            ex.get("correct_java", ex.get("correct"))
            if (use_java and ex.get("options_java"))
            else ex.get("correct")
        )
        return {"type": "multiple-choice", "correct_index": _safe_int(correct_raw, -1), "explanation": explanation}
    if ex_type == "reorder":
        return {"type": "reorder", "order": list(range(len(ex.get("lines") or []))), "explanation": explanation}
    if ex_type == "find-error":
        return {"type": "find-error", "error_line": _safe_int(ex.get("error_line", -1), -1), "explanation": explanation}
    return {
        "type": "fill-blank",
        "answers": _extract_exercise_blanks(ex, "java" if use_java else "python"),
        "explanation": explanation,
    }


@app.route("/api/submit_practice", methods=["POST"])
@limiter.limit("20 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_submit_practice():
    # Visitantes sin sesión pueden ejecutar pruebas en Pyodide, pero no guardar progreso ni XP
    if not current_user.is_authenticated:
        return jsonify({
            "ok": False,
            "anonymous": True,
            "xp_gained": 0,
            "message": "Inicia sesión para guardar tu progreso y ganar XP."
        })

    data = _get_json_dict()
    raw_problem_id = data.get("problem_id")
    problem_id = raw_problem_id.strip() if isinstance(raw_problem_id, str) else ""
    problem = get_practice_problem(problem_id)
    if not problem:
        return jsonify({"ok": False, "error": "Problema de práctica no encontrado en el currículo."}), 400

    raw_code = data.get("code")
    if not isinstance(raw_code, str) or len(raw_code) > MAX_PRACTICE_CODE_CHARS:
        return jsonify({"ok": False, "error": f"El código no puede superar {MAX_PRACTICE_CODE_CHARS} caracteres."}), 400
    code = raw_code

    expected_total = len(problem.get("test_cases") or [])
    raw_passed = data.get("passed", False) is True
    tests_passed = _safe_int(data.get("tests_passed", 0), 0)
    tests_total = _safe_int(data.get("tests_total", 0), 0)

    # Validar estructuralmente la solución en servidor antes de aceptar passed=True
    passed = False
    if raw_passed and expected_total > 0 and tests_total == expected_total and tests_passed == expected_total:
        ast_ok, ast_err = _validate_practice_code_ast(problem, code)
        if not ast_ok:
            return jsonify({"ok": False, "error": ast_err}), 400
        passed = True
    else:
        tests_passed = max(0, min(tests_passed, expected_total))
        tests_total = expected_total

    user = current_user

    # Comprobar si ya fue aprobado previamente ANTES de insertar el nuevo envío
    prev_passed = PracticeSubmission.query.filter_by(
        user_id=user.id, problem_id=problem_id, passed=True
    ).first()

    submission = PracticeSubmission(
        user_id=user.id,
        problem_id=problem_id,
        code=code,
        passed=passed,
        tests_passed=tests_passed,
        tests_total=tests_total,
    )
    db.session.add(submission)

    xp_gained = 0
    if passed and not prev_passed:
        xp_gained = XP_PER_PRACTICE
        record_daily_activity(user.id)

    db.session.commit()

    new_stats = get_progress_summary(user)
    lvl_info = get_level_info(new_stats["total_xp"])

    return jsonify({
        "ok": True,
        "passed": passed,
        "xp_gained": xp_gained,
        "new_total": new_stats["total_xp"],
        "level": lvl_info["level"],
        "title": lvl_info["title"],
        "streak": new_stats["streak"],
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
    return None


@app.route("/api/progreso/ejercicio", methods=["POST"])
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_ejercicio():
    """Evalúa un ejercicio en el servidor contra content_loader y registra progreso/XP si corresponde."""
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = raw_lesson.strip() if isinstance(raw_lesson, str) else ""
    raw_ex = data.get("exercise_id")
    exercise_id = raw_ex.strip() if isinstance(raw_ex, str) else ""
    lang = data.get("lang", "python")
    if lang not in ("python", "java"):
        lang = "python"

    lesson_data, exercise = get_lesson_exercise(lesson_id, exercise_id)
    if not lesson_data or not exercise:
        return jsonify({"ok": False, "error": "Lección o ejercicio no encontrado en el currículo."}), 400

    canonical_lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    canonical_exercise_id = exercise.get("id") or exercise_id

    # El servidor califica estrictamente la respuesta (ignora cualquier 'passed' del cliente)
    raw_answer = data.get("answer")
    raw_answers = data.get("answers")
    passed, verdict = _grade_exercise_submission(exercise, lang, raw_answer, raw_answers)

    user = get_current_user()
    if not user or not user.id:
        return jsonify({
            "ok": True,
            "anonymous": True,
            "passed": passed,
            "xp_gained": 0,
            **verdict,
        })

    prev_passed = None
    if passed:
        prev_passed = ExerciseAttempt.query.filter_by(
            user_id=user.id, exercise_id=canonical_exercise_id, passed=True
        ).first()

    submitted_repr = raw_answers if raw_answers is not None else raw_answer
    try:
        answer_str = json.dumps(submitted_repr, ensure_ascii=False)[:1000]
    except (TypeError, ValueError):
        answer_str = str(submitted_repr)[:1000]

    attempt = ExerciseAttempt(
        user_id=user.id,
        lesson_id=canonical_lesson_id,
        exercise_id=canonical_exercise_id,
        passed=passed,
        answer=answer_str,
    )
    db.session.add(attempt)

    xp_gained = 0
    if passed:
        if not prev_passed:
            xp_gained = XP_PER_EXERCISE
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify({
        "ok": True,
        "anonymous": False,
        "passed": passed,
        "xp_gained": xp_gained,
        "summary": get_progress_summary(user),
        **verdict,
    })


@app.route("/api/ejercicio/solucion", methods=["POST"])
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_exercise_solution():
    """Devuelve la solución pedagógica de un ejercicio existente sin otorgar XP ni registrar aprobación."""
    data = _get_json_dict()
    lesson_id = data.get("lesson_id", "").strip() if isinstance(data.get("lesson_id"), str) else ""
    exercise_id = data.get("exercise_id", "").strip() if isinstance(data.get("exercise_id"), str) else ""
    lang = data.get("lang", "python")
    if lang not in ("python", "java"):
        lang = "python"

    lesson_data, exercise = get_lesson_exercise(lesson_id, exercise_id)
    if not lesson_data or not exercise:
        return jsonify({"ok": False, "error": "Ejercicio no encontrado."}), 400

    return jsonify({"ok": True, **_get_exercise_solution(exercise, lang)})


@app.route("/api/progreso/leccion", methods=["POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_leccion():
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = raw_lesson.strip() if isinstance(raw_lesson, str) else ""
    lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)

    course_ids = _course_lesson_ids()
    if not lesson_id or lesson_id not in course_ids or load_lesson(lesson_id) is None:
        return jsonify({"ok": False, "error": "Lección inválida o no perteneciente al currículo."}), 400

    user = current_user
    lp = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson_id).first()

    xp_gained = 0
    if not lp:
        lp = LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            completed=True,
            score=XP_PER_LESSON,
            completed_at=utcnow(),
        )
        db.session.add(lp)
        xp_gained = XP_PER_LESSON
    elif not lp.completed:
        lp.completed = True
        lp.completed_at = utcnow()
        lp.score = XP_PER_LESSON
        xp_gained = XP_PER_LESSON

    if xp_gained > 0:
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


def record_daily_activity(user_id):
    """Registra la actividad diaria del usuario en la zona horaria operativa para el cálculo de racha."""
    if not user_id:
        return
    today = _get_app_today()
    existing = DailyStreak.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.lessons_completed = (existing.lessons_completed or 0) + 1
    else:
        streak_entry = DailyStreak(user_id=user_id, date=today, lessons_completed=1)
        db.session.add(streak_entry)


def _compute_streak_from_dates(dates, today):
    """Calcula la racha consecutiva dada una lista ordenada descendente de fechas únicas."""
    if not dates:
        return 0
    yesterday = today - timedelta(days=1)
    first_date = dates[0]
    if first_date != today and first_date != yesterday:
        return 0
    count = 1
    for i in range(1, len(dates)):
        if dates[i] == first_date - timedelta(days=i):
            count += 1
        else:
            break
    return count


def calculate_streak(user_id):
    """Calcula la racha de días consecutivos de actividad usando la zona horaria operativa."""
    if not user_id:
        return 0
    rows = (
        db.session.query(DailyStreak.date)
        .filter_by(user_id=user_id)
        .distinct()
        .order_by(DailyStreak.date.desc())
        .all()
    )
    return _compute_streak_from_dates([r[0] for r in rows], _get_app_today())


def _get_bulk_streaks(user_ids):
    """Calcula la racha actual para un conjunto acotado de IDs de usuario en una sola consulta."""
    if not user_ids:
        return {}
    rows = (
        db.session.query(DailyStreak.user_id, DailyStreak.date)
        .filter(DailyStreak.user_id.in_(user_ids))
        .distinct()
        .order_by(DailyStreak.user_id.asc(), DailyStreak.date.desc())
        .all()
    )
    dates_by_user = {}
    for uid, day in rows:
        dates_by_user.setdefault(uid, []).append(day)

    today = _get_app_today()
    return {
        uid: _compute_streak_from_dates(dates_by_user.get(uid, []), today)
        for uid in user_ids
    }


def _get_classroom_student_counts(section_ids=None):
    """Cuenta estudiantes por sección en una sola consulta agregada GROUP BY (elimina N+1)."""
    query = db.session.query(User.section_id, func.count(User.id)).filter(
        User.role == "student",
        User.section_id.isnot(None),
    )
    if section_ids is not None:
        if not section_ids:
            return {}
        query = query.filter(User.section_id.in_(section_ids))
    return {sec_id: int(cnt) for sec_id, cnt in query.group_by(User.section_id).all()}


def _build_student_stats_subqueries(user_ids_select=None):
    """Construye subconsultas GROUP BY por usuario para calcular XP y lecciones directamente en SQL."""
    course_ids = _course_lesson_ids()
    valid_exercise_ids = get_valid_exercise_ids()
    valid_practice_ids = get_valid_practice_ids()
    valid_eval_keys = set(SECTION_EVAL_MAP.keys())

    lp_q = db.session.query(
        LessonProgress.user_id.label("user_id"),
        func.count(distinct(LessonProgress.lesson_id)).label("completed_cnt"),
    ).filter(
        LessonProgress.completed.is_(True),
        LessonProgress.lesson_id.in_(course_ids) if course_ids else false(),
    )
    if user_ids_select is not None:
        lp_q = lp_q.filter(LessonProgress.user_id.in_(user_ids_select))
    lp_sub = lp_q.group_by(LessonProgress.user_id).subquery()

    ex_q = db.session.query(
        ExerciseAttempt.user_id.label("user_id"),
        func.count(distinct(ExerciseAttempt.exercise_id)).label("ex_cnt"),
    ).filter(
        ExerciseAttempt.passed.is_(True),
        ExerciseAttempt.exercise_id.in_(valid_exercise_ids) if valid_exercise_ids else false(),
    )
    if user_ids_select is not None:
        ex_q = ex_q.filter(ExerciseAttempt.user_id.in_(user_ids_select))
    ex_sub = ex_q.group_by(ExerciseAttempt.user_id).subquery()

    pr_q = db.session.query(
        PracticeSubmission.user_id.label("user_id"),
        func.count(distinct(PracticeSubmission.problem_id)).label("pr_cnt"),
    ).filter(
        PracticeSubmission.passed.is_(True),
        PracticeSubmission.problem_id.in_(valid_practice_ids) if valid_practice_ids else false(),
    )
    if user_ids_select is not None:
        pr_q = pr_q.filter(PracticeSubmission.user_id.in_(user_ids_select))
    pr_sub = pr_q.group_by(PracticeSubmission.user_id).subquery()

    ev_q = db.session.query(
        SectionEvaluation.user_id.label("user_id"),
        func.count(distinct(SectionEvaluation.section_id)).label("ev_cnt"),
    ).filter(
        SectionEvaluation.passed.is_(True),
        SectionEvaluation.section_id.in_(valid_eval_keys) if valid_eval_keys else false(),
    )
    if user_ids_select is not None:
        ev_q = ev_q.filter(SectionEvaluation.user_id.in_(user_ids_select))
    ev_sub = ev_q.group_by(SectionEvaluation.user_id).subquery()

    completed_expr = func.coalesce(lp_sub.c.completed_cnt, 0)
    total_xp_expr = (
        completed_expr * XP_PER_LESSON
        + func.coalesce(ex_sub.c.ex_cnt, 0) * XP_PER_EXERCISE
        + func.coalesce(pr_sub.c.pr_cnt, 0) * XP_PER_PRACTICE
        + func.coalesce(ev_sub.c.ev_cnt, 0) * XP_PER_EVALUATION
    )
    return lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr


def get_progress_summary(user):
    """Calcula lecciones completadas reales y XP total sumando únicamente desde las tablas reales."""
    if not user or not getattr(user, "id", None):
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}
    try:
        course_ids = _course_lesson_ids()
        valid_exercise_ids = get_valid_exercise_ids()
        valid_practice_ids = get_valid_practice_ids()
        valid_eval_keys = set(SECTION_EVAL_MAP.keys())

        progresses = LessonProgress.query.filter_by(user_id=user.id, completed=True).all()
        completed_set = {p.lesson_id for p in progresses if p.lesson_id in course_ids}

        passed_ex_rows = (
            db.session.query(ExerciseAttempt.exercise_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_ex_set = {r[0] for r in passed_ex_rows if r[0] in valid_exercise_ids}

        passed_pr_rows = (
            db.session.query(PracticeSubmission.problem_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_pr_set = {r[0] for r in passed_pr_rows if r[0] in valid_practice_ids}

        passed_ev_rows = (
            db.session.query(SectionEvaluation.section_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_ev_set = {r[0] for r in passed_ev_rows if r[0] in valid_eval_keys}

        total_xp = (
            len(completed_set) * XP_PER_LESSON
            + len(passed_ex_set) * XP_PER_EXERCISE
            + len(passed_pr_set) * XP_PER_PRACTICE
            + len(passed_ev_set) * XP_PER_EVALUATION
        )
        streak = calculate_streak(user.id)
        return {
            "completed_lessons": sorted(completed_set),
            "total_xp": total_xp,
            "streak": streak,
        }
    except Exception as e:
        logger.warning("get_progress_summary error: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}


def get_bulk_progress_summaries(users):
    """Calcula el resumen de progreso y XP real de múltiples usuarios desde las tablas reales."""
    user_ids = [u.id for u in users if getattr(u, "id", None)]
    if not user_ids:
        return {}

    result = {uid: {"completed_lessons": [], "total_xp": 0, "streak": 0} for uid in user_ids}
    try:
        course_ids = _course_lesson_ids()
        valid_exercise_ids = get_valid_exercise_ids()
        valid_practice_ids = get_valid_practice_ids()
        valid_eval_keys = set(SECTION_EVAL_MAP.keys())

        lessons_by_user = {uid: set() for uid in user_ids}
        ex_by_user = {uid: set() for uid in user_ids}
        pr_by_user = {uid: set() for uid in user_ids}
        ev_by_user = {uid: set() for uid in user_ids}

        all_progress = LessonProgress.query.filter(
            LessonProgress.user_id.in_(user_ids),
            LessonProgress.completed.is_(True),
        ).all()
        for p in all_progress:
            if p.lesson_id in course_ids:
                lessons_by_user[p.user_id].add(p.lesson_id)

        all_ex = (
            db.session.query(ExerciseAttempt.user_id, ExerciseAttempt.exercise_id)
            .filter(ExerciseAttempt.user_id.in_(user_ids), ExerciseAttempt.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, ex_id in all_ex:
            if ex_id in valid_exercise_ids:
                ex_by_user[uid].add(ex_id)

        all_pr = (
            db.session.query(PracticeSubmission.user_id, PracticeSubmission.problem_id)
            .filter(PracticeSubmission.user_id.in_(user_ids), PracticeSubmission.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, prob_id in all_pr:
            if prob_id in valid_practice_ids:
                pr_by_user[uid].add(prob_id)

        all_ev = (
            db.session.query(SectionEvaluation.user_id, SectionEvaluation.section_id)
            .filter(SectionEvaluation.user_id.in_(user_ids), SectionEvaluation.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, sec_id in all_ev:
            if sec_id in valid_eval_keys:
                ev_by_user[uid].add(sec_id)

        streaks_map = _get_bulk_streaks(user_ids)
        for uid in user_ids:
            comp = lessons_by_user[uid]
            result[uid]["completed_lessons"] = sorted(comp)
            result[uid]["total_xp"] = (
                len(comp) * XP_PER_LESSON
                + len(ex_by_user[uid]) * XP_PER_EXERCISE
                + len(pr_by_user[uid]) * XP_PER_PRACTICE
                + len(ev_by_user[uid]) * XP_PER_EVALUATION
            )
            result[uid]["streak"] = streaks_map.get(uid, 0)
    except Exception as e:
        logger.warning("get_bulk_progress_summaries error: %s", e)
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
    raw_next = (request.form.get("next") or "").strip() or _extract_relative_from_referrer(request.referrer)
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
        logger.error("Error en api_db_status: %s", e)
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
            logger.error("Error en login al consultar usuario: %s", e)
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
            logger.error("Error de envío Resend HTTP %s: %s", resp.status_code, err_txt)
            return False, "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde."
        except Exception as e:
            logger.error("Error de envío Resend (%s): %s", type(e).__name__, e)
            return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."

    # Opción 2: SMTP sobre IPv4 (Gmail, Outlook, Brevo SMTP, etc.)
    if not mail_server or not mail_username or not mail_password:
        logger.warning("Proveedor de correo no configurado para recuperación de '%s'.", username)
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
        logger.error("Error de autenticación SMTP: %s", e)
        return False, "No se pudo enviar el correo de recuperación en este momento. Contacta al administrador."
    except (socket.timeout, TimeoutError) as e:
        logger.error("Timeout en servidor SMTP: %s", e)
        return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."
    except Exception as e:
        logger.error("Error SMTP al enviar correo a %s (%s): %s", to_email, type(e).__name__, e)
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
            logger.error("Error en register query: %s", e)
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
                email=email or None,
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
            logger.error("Error en register commit: %s", e)
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
        expires_at = utcnow() + timedelta(minutes=15)

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

        # Verificar expiración en UTC consistente
        record_expiry = ensure_utc(active_record.expires_at)
        now_utc = utcnow()
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


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


ADMIN_STUDENTS_PER_PAGE = 20
ADMIN_AUDIT_PER_PAGE = 10
LEADERBOARD_PER_PAGE = 50


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

    classrooms = []
    classroom_map = {}
    classroom_counts = {}
    paginated_students = []
    total_scoped_students = 0
    total_filtered = 0
    total_pages = 1
    total_xp = 0
    total_completed = 0
    active_count = 0
    suspended_count = 0
    level_counts = {}
    active_section_id = None
    course_ids = _course_lesson_ids()
    total_course_lessons = len(course_ids) or 1

    try:
        classrooms = _get_teacher_classrooms(current_user.id)
        classroom_map = {c.id: c for c in classrooms}
        allowed_ids = list(classroom_map.keys())

        # Validar en backend que section_filter pertenezca al docente actual
        active_section_id = section_filter if section_filter in classroom_map else None

        if allowed_ids:
            # 1) Conteo de estudiantes por sección en 1 consulta agregada GROUP BY
            classroom_counts = _get_classroom_student_counts(allowed_ids)

            scope_ids = [active_section_id] if active_section_id else allowed_ids
            scope_user_ids_select = db.select(User.id).where(
                User.role == "student",
                User.section_id.in_(scope_ids),
            )
            lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = (
                _build_student_stats_subqueries(scope_user_ids_select)
            )

            base_scope_q = (
                db.session.query(User)
                .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
                .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
                .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
                .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
                .filter(User.role == "student", User.section_id.in_(scope_ids))
            )

            # 2) Métricas agregadas del alcance en SQL (sin cargar todos los estudiantes en RAM)
            agg_total, agg_suspended, agg_xp, agg_completed = (
                base_scope_q.with_entities(
                    func.count(User.id),
                    func.coalesce(func.sum(case((User.is_suspended.is_(True), 1), else_=0)), 0),
                    func.coalesce(func.sum(total_xp_expr), 0),
                    func.coalesce(func.sum(completed_expr), 0),
                ).one()
            )
            total_scoped_students = int(agg_total or 0)
            suspended_count = int(agg_suspended or 0)
            active_count = total_scoped_students - suspended_count
            total_xp = int(agg_xp or 0)
            total_completed = int(agg_completed or 0)

            # Distribución por nivel en SQL (máximo 20 filas agregadas)
            level_bucket_expr = case(
                *[(total_xp_expr < lv * 100, lv) for lv in range(1, 20)],
                else_=20,
            )
            level_dist_rows = (
                base_scope_q.with_entities(level_bucket_expr.label("lvl"), func.count(User.id))
                .group_by(level_bucket_expr)
                .order_by(level_bucket_expr.asc())
                .all()
            )
            for lv_num, lv_cnt in level_dist_rows:
                lv_title = LEVEL_TITLES.get(int(lv_num), "Iniciado")
                level_counts[lv_title] = int(lv_cnt or 0)

            # 3) Filtros, ordenamiento y paginación directamente en SQL
            filtered_q = base_scope_q
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
            elif status_filter == "with_progress":
                filtered_q = filtered_q.filter(or_(completed_expr > 0, total_xp_expr > 0))
            elif status_filter == "no_activity":
                filtered_q = filtered_q.filter(completed_expr == 0, total_xp_expr == 0)

            if level_filter >= 20:
                filtered_q = filtered_q.filter(total_xp_expr >= 1900)
            elif level_filter >= 1:
                filtered_q = filtered_q.filter(
                    total_xp_expr >= (level_filter - 1) * 100,
                    total_xp_expr < level_filter * 100,
                )

            total_filtered = int(filtered_q.with_entities(func.count(User.id)).scalar() or 0)
            total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
            if page > total_pages:
                page = total_pages

            order_map = {
                "xp_desc": (total_xp_expr.desc(), func.lower(User.username).asc(), User.id.asc()),
                "xp_asc": (total_xp_expr.asc(), func.lower(User.username).asc(), User.id.asc()),
                "progress_desc": (completed_expr.desc(), total_xp_expr.desc(), func.lower(User.username).asc()),
                "progress_asc": (completed_expr.asc(), total_xp_expr.asc(), func.lower(User.username).asc()),
                "name_asc": (func.lower(User.username).asc(), User.id.asc()),
                "name_desc": (func.lower(User.username).desc(), User.id.desc()),
                "date_desc": (nullslast(User.created_at.desc()), User.id.desc()),
                "date_asc": (nullslast(User.created_at.asc()), User.id.asc()),
            }

            page_rows = (
                filtered_q.with_entities(
                    User,
                    completed_expr.label("completed_cnt"),
                    total_xp_expr.label("total_xp"),
                )
                .order_by(*order_map[sort_by])
                .offset((page - 1) * ADMIN_STUDENTS_PER_PAGE)
                .limit(ADMIN_STUDENTS_PER_PAGE)
                .all()
            )
            page_streaks = _get_bulk_streaks([s.id for s, _, _ in page_rows])
            app_tz = _get_app_timezone()

            for s, completed_val, xp_val in page_rows:
                completed_cnt = int(completed_val or 0)
                xp_int = int(xp_val or 0)
                lvl = get_level_info(xp_int)
                cls = classroom_map.get(s.section_id)
                created_utc = ensure_utc(s.created_at)
                suspended_utc = ensure_utc(getattr(s, "suspended_at", None))
                paginated_students.append({
                    "id": s.id,
                    "username": s.username,
                    "email": s.email or "",
                    "total_xp": xp_int,
                    "completed": completed_cnt,
                    "progress_pct": round(min(100, completed_cnt * 100 / total_course_lessons), 1),
                    "level": lvl["level"],
                    "title": lvl["title"],
                    "streak": page_streaks.get(s.id, 0),
                    "section_id": s.section_id,
                    "section_name": cls.name if cls else "Sin sección",
                    "section_code": cls.code if cls else "",
                    "is_suspended": bool(getattr(s, "is_suspended", False)),
                    "suspended_reason": getattr(s, "suspended_reason", None) or "",
                    "suspended_at": suspended_utc.astimezone(app_tz).strftime("%d/%m/%Y %H:%M") if suspended_utc else "",
                    "created_at": created_utc,
                    "created_at_str": created_utc.astimezone(app_tz).strftime("%d/%m/%Y") if created_utc else "N/A",
                })
    except Exception as e:
        logger.error("Error en teacher_dashboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        active_section_id = None

    metrics = {
        "total_students": total_scoped_students,
        "active_students": active_count,
        "suspended_students": suspended_count,
        "avg_xp": round(total_xp / total_scoped_students) if total_scoped_students else 0,
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
        logger.error("Error en admin_create_section: %s", e)
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
        logger.error("Error en admin_delete_section: %s", e)
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
    student.suspended_at = utcnow()
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
        cls = classroom_map.get(s.section_id)
        completed_cnt = len(set(stats["completed_lessons"]) & course_ids)
        section_label = f"{cls.name} ({cls.code})" if cls else "Sin sección"
        cw.writerow([
            _csv_safe(s.username or ""),
            _csv_safe(s.email or ""),
            _csv_safe(section_label),
            _csv_safe("Suspendido" if getattr(s, "is_suspended", False) else "Activo"),
            stats["total_xp"],
            completed_cnt,
            _csv_safe(lvl_info["title"]),
            stats["streak"],
            _csv_safe(s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A"),
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
        logger.error("Error en admin_export_pdf (%s): %s", type(e).__name__, e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF. Intenta de nuevo."}), 500

    filename = f"reporte_estudiantes_{_app_now().strftime('%Y%m%d_%H%M')}.pdf"
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
    if sort_by not in ("xp_desc", "xp_asc", "progress_desc", "name_asc", "date_desc", "date_asc"):
        sort_by = "xp_desc"
    page = max(1, _safe_int(request.args.get("page", 1), 1))
    audit_page = max(1, _safe_int(request.args.get("audit_page", 1), 1))

    course_ids = _course_lesson_ids()
    total_course = len(course_ids) or 1
    app_tz = _get_app_timezone()

    all_teachers = []
    all_classrooms = []
    classroom_map = {}
    teacher_map = {}
    classroom_counts = {}
    teacher_rows = []
    paginated_students = []
    total_students_cnt = 0
    active_students_cnt = 0
    suspended_students_cnt = 0
    unassigned_students_cnt = 0
    total_filtered = 0
    total_pages = 1
    audit_logs = []
    audit_total = 0
    audit_total_pages = 1

    try:
        all_teachers = User.query.filter_by(role="teacher").order_by(nullslast(User.created_at.desc()), User.id.desc()).all()
        all_classrooms = Classroom.query.order_by(nullslast(Classroom.created_at.desc()), Classroom.id.desc()).all()
        classroom_map = {c.id: c for c in all_classrooms}
        teacher_map = {t.id: t for t in all_teachers}

        # Conteo de estudiantes por sección en 1 consulta agregada GROUP BY (sin N+1)
        classroom_counts = _get_classroom_student_counts()

        sections_by_teacher = {}
        for c in all_classrooms:
            sections_by_teacher.setdefault(c.teacher_id, []).append(c)

        for t in all_teachers:
            t_secs = sections_by_teacher.get(t.id, [])
            t_stu_cnt = sum(classroom_counts.get(c.id, 0) for c in t_secs)
            t_created_utc = ensure_utc(t.created_at)
            teacher_rows.append({
                "id": t.id,
                "username": t.username,
                "email": t.email or "",
                "sections_count": len(t_secs),
                "students_count": t_stu_cnt,
                "is_suspended": bool(getattr(t, "is_suspended", False)),
                "suspended_reason": getattr(t, "suspended_reason", None) or "",
                "created_at_str": t_created_utc.astimezone(app_tz).strftime("%d/%m/%Y") if t_created_utc else "N/A",
            })

        # Métricas globales de estudiantes en 1 sola consulta agregada SQL
        stu_agg = (
            db.session.query(
                func.count(User.id),
                func.coalesce(func.sum(case((User.is_suspended.is_(True), 1), else_=0)), 0),
                func.coalesce(func.sum(case((User.section_id.is_(None), 1), else_=0)), 0),
            )
            .filter(User.role == "student")
            .one()
        )
        total_students_cnt = int(stu_agg[0] or 0)
        suspended_students_cnt = int(stu_agg[1] or 0)
        active_students_cnt = total_students_cnt - suspended_students_cnt
        unassigned_students_cnt = int(stu_agg[2] or 0)

        # Consulta filtrada, ordenada y paginada de estudiantes directamente en SQL
        lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = _build_student_stats_subqueries()
        sq = (
            db.session.query(User)
            .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
            .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
            .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
            .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
            .filter(User.role == "student")
        )
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

        total_filtered = int(sq.with_entities(func.count(User.id)).scalar() or 0)
        total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
        page = min(page, total_pages)

        order_map = {
            "xp_desc": (total_xp_expr.desc(), func.lower(User.username).asc(), User.id.asc()),
            "xp_asc": (total_xp_expr.asc(), func.lower(User.username).asc(), User.id.asc()),
            "progress_desc": (completed_expr.desc(), total_xp_expr.desc(), func.lower(User.username).asc()),
            "name_asc": (func.lower(User.username).asc(), User.id.asc()),
            "date_desc": (nullslast(User.created_at.desc()), User.id.desc()),
            "date_asc": (nullslast(User.created_at.asc()), User.id.asc()),
        }

        page_rows = (
            sq.with_entities(
                User,
                completed_expr.label("completed_cnt"),
                total_xp_expr.label("total_xp"),
            )
            .order_by(*order_map[sort_by])
            .offset((page - 1) * ADMIN_STUDENTS_PER_PAGE)
            .limit(ADMIN_STUDENTS_PER_PAGE)
            .all()
        )
        for s, comp_val, xp_val in page_rows:
            comp = int(comp_val or 0)
            xp_int = int(xp_val or 0)
            lvl = get_level_info(xp_int)
            cls = classroom_map.get(s.section_id)
            t_owner = teacher_map.get(cls.teacher_id) if cls else None
            paginated_students.append({
                "id": s.id,
                "username": s.username,
                "email": s.email or "",
                "level": lvl["level"],
                "title": lvl["title"],
                "total_xp": xp_int,
                "completed": comp,
                "progress_pct": round(min(100, comp * 100 / total_course), 1),
                "section_id": s.section_id,
                "section_name": cls.name if cls else "Sin sección",
                "section_code": cls.code if cls else "",
                "teacher_name": t_owner.username if t_owner else "—",
                "is_suspended": bool(getattr(s, "is_suspended", False)),
                "suspended_reason": getattr(s, "suspended_reason", None) or "",
                "created_at": ensure_utc(s.created_at),
            })

        # Bitácora global (todos los eventos del sistema)
        audit_q = AuditLog.query.order_by(nullslast(AuditLog.created_at.desc()), AuditLog.id.desc())
        audit_total = audit_q.count()
        audit_per = 15
        audit_total_pages = max(1, math.ceil(audit_total / audit_per))
        audit_page = min(audit_page, audit_total_pages)
        audit_logs = audit_q.offset((audit_page - 1) * audit_per).limit(audit_per).all()
    except Exception as e:
        logger.error("Error en superadmin_dashboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass

    metrics = {
        "total_students": total_students_cnt,
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
    target.suspended_at = utcnow()
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
        cls = classroom_map.get(s.section_id)
        section_label = f"{cls.name} ({cls.code})" if cls else "Sin sección"
        cw.writerow([
            _csv_safe(s.username or ""),
            _csv_safe(s.email or ""),
            _csv_safe(section_label),
            _csv_safe("Suspendido" if getattr(s, "is_suspended", False) else "Activo"),
            stats["total_xp"],
            len(set(stats["completed_lessons"]) & course_ids),
            _csv_safe(lvl_info["title"]),
            stats["streak"],
            _csv_safe(s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A"),
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
        logger.error("Error en superadmin_export_pdf (%s): %s", type(e).__name__, e)
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF global."}), 500

    filename = f"reporte_global_{_app_now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Tabla de posiciones ---
@app.route("/leaderboard")
def leaderboard():
    board = []
    podium = []
    db_error = False
    teacher_section_ids = set()
    page_num = max(1, _safe_int(request.args.get("page", 1), 1))
    total_pages = 1
    total_students = 0
    try:
        if current_user.is_authenticated and current_user.role == "teacher":
            teacher_section_ids = _get_teacher_section_ids(current_user.id)

        active_students_select = db.select(User.id).where(
            User.role == "student",
            User.is_suspended.is_(False),
        )
        lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = (
            _build_student_stats_subqueries(active_students_select)
        )
        base_q = (
            db.session.query(User)
            .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
            .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
            .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
            .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
            .filter(User.role == "student", User.is_suspended.is_(False))
        )

        total_students = int(base_q.with_entities(func.count(User.id)).scalar() or 0)
        total_pages = max(1, math.ceil(total_students / LEADERBOARD_PER_PAGE))
        if page_num > total_pages:
            page_num = total_pages

        ordered_q = base_q.with_entities(
            User,
            completed_expr.label("completed_cnt"),
            total_xp_expr.label("total_xp"),
        ).order_by(
            total_xp_expr.desc(),
            completed_expr.desc(),
            func.lower(User.username).asc(),
            User.id.asc(),
        )

        offset = (page_num - 1) * LEADERBOARD_PER_PAGE
        page_rows = ordered_q.offset(offset).limit(LEADERBOARD_PER_PAGE).all()
        page_streaks = _get_bulk_streaks([s.id for s, _, _ in page_rows])

        def _row_to_entry(s, completed_val, xp_val, rank_num, streak_val):
            xp_int = int(xp_val or 0)
            lvl_info = get_level_info(xp_int)
            can_view_profile = bool(
                current_user.is_authenticated
                and (
                    s.id == current_user.id
                    or current_user.role == "superadmin"
                    or (current_user.role == "teacher" and s.section_id in teacher_section_ids)
                )
            )
            return {
                "id": s.id,
                "username": s.username or "Anónimo",
                "total_xp": xp_int,
                "level": lvl_info["level"],
                "completed": int(completed_val or 0),
                "streak": streak_val,
                "can_view_profile": can_view_profile,
                "rank": rank_num,
            }

        for idx, (s, completed_val, xp_val) in enumerate(page_rows):
            board.append(
                _row_to_entry(s, completed_val, xp_val, offset + idx + 1, page_streaks.get(s.id, 0))
            )

        if page_num == 1:
            podium = board[:3]
        elif total_students >= 3:
            top3_rows = ordered_q.limit(3).all()
            podium = [
                _row_to_entry(s, comp_val, xp_val, i + 1, 0)
                for i, (s, comp_val, xp_val) in enumerate(top3_rows)
            ]
    except Exception as e:
        logger.error("Error en leaderboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        db_error = True

    current_uid = current_user.id if current_user.is_authenticated else None
    return render_template(
        "leaderboard.html",
        board=board,
        podium=podium,
        page_num=page_num,
        total_pages=total_pages,
        total_students=total_students,
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
        course_ids = _course_lesson_ids()
        recent = (
            LessonProgress.query.filter(
                LessonProgress.user_id == user.id,
                LessonProgress.completed == True,
                LessonProgress.lesson_id.in_(course_ids),
            )
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
        logger.error("Error en profile queries: %s", e)
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
    now = _app_now()
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
        logger.error("Error en certificate_pdf (%s): %s", type(e).__name__, e)
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
        raw_next = (request.form.get("next") or "").strip() or _extract_relative_from_referrer(request.referrer)
        safe_ref = _get_safe_next_url(raw_next, default=url_for("index"))
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
AI_TUTOR_MAX_CODE_CHARS = 4000
AI_TUTOR_MAX_QUESTION_CHARS = 1000
AI_TUTOR_MAX_EXERCISE_Q_CHARS = 1000
AI_TUTOR_MAX_HISTORY_ITEMS = 12
AI_TUTOR_MAX_HISTORY_ENTRY_CHARS = 1000
AI_TUTOR_MAX_HISTORY_TOTAL_CHARS = 4000


@app.route("/api/ai/tutor", methods=["POST"])
@login_required
@limiter.limit("15 per minute; 100 per hour", methods=["POST"], key_func=_user_rate_limit_key)
def api_ai_tutor():
    if not GEMINI_API_KEY:
        return jsonify(
            {"ok": False, "error": "El servicio de Tutor IA no está disponible en este momento."}
        ), 503

    data = _get_json_dict()
    raw_code = data.get("code", "")
    if not isinstance(raw_code, str):
        return jsonify({"ok": False, "error": "Formato de código inválido."}), 400
    if len(raw_code) > AI_TUTOR_MAX_CODE_CHARS:
        return jsonify(
            {"ok": False, "error": f"El código supera el límite máximo permitido ({AI_TUTOR_MAX_CODE_CHARS} caracteres)."}
        ), 400
    user_code = raw_code

    raw_q = data.get("question", "")
    if not isinstance(raw_q, str):
        return jsonify({"ok": False, "error": "Formato de pregunta inválido."}), 400
    question = raw_q.strip()
    if len(question) > AI_TUTOR_MAX_QUESTION_CHARS:
        return jsonify(
            {"ok": False, "error": f"La pregunta supera el límite máximo permitido ({AI_TUTOR_MAX_QUESTION_CHARS} caracteres)."}
        ), 400

    raw_ex_q = data.get("exercise_question", "")
    if not isinstance(raw_ex_q, str):
        return jsonify({"ok": False, "error": "Formato de enunciado inválido."}), 400
    if len(raw_ex_q) > AI_TUTOR_MAX_EXERCISE_Q_CHARS:
        return jsonify(
            {"ok": False, "error": f"El enunciado supera el límite máximo permitido ({AI_TUTOR_MAX_EXERCISE_Q_CHARS} caracteres)."}
        ), 400
    exercise_question = raw_ex_q.strip()

    raw_lesson = data.get("lesson_id", "")
    lesson_id = raw_lesson.strip()[:60] if isinstance(raw_lesson, str) else ""

    raw_mode = data.get("mode")
    mode = raw_mode.strip() if isinstance(raw_mode, str) and raw_mode.strip() else ("chat" if question else "analyze")
    if mode not in ("chat", "analyze", "hint"):
        return jsonify({"ok": False, "error": "Modo de tutoría inválido."}), 400

    history = data.get("history", [])
    if history is None:
        history = []
    if not isinstance(history, list):
        return jsonify({"ok": False, "error": "El historial de conversación debe ser una lista."}), 400
    if len(history) > AI_TUTOR_MAX_HISTORY_ITEMS:
        return jsonify(
            {"ok": False, "error": f"El historial supera el máximo permitido ({AI_TUTOR_MAX_HISTORY_ITEMS} mensajes)."}
        ), 400

    history_context = ""
    if history:
        history_lines = []
        total_hist_chars = 0
        for h in history[-4:]:
            if not isinstance(h, dict):
                return jsonify({"ok": False, "error": "Entrada inválida en el historial."}), 400
            raw_txt = h.get("text", "")
            if not isinstance(raw_txt, str):
                return jsonify({"ok": False, "error": "Texto inválido en el historial."}), 400
            txt = raw_txt.strip()
            if len(txt) > AI_TUTOR_MAX_HISTORY_ENTRY_CHARS:
                return jsonify(
                    {"ok": False, "error": f"Cada mensaje del historial no puede superar {AI_TUTOR_MAX_HISTORY_ENTRY_CHARS} caracteres."}
                ), 400
            if txt:
                total_hist_chars += len(txt)
                if total_hist_chars > AI_TUTOR_MAX_HISTORY_TOTAL_CHARS:
                    return jsonify(
                        {"ok": False, "error": f"El tamaño total del historial supera el máximo permitido ({AI_TUTOR_MAX_HISTORY_TOTAL_CHARS} caracteres)."}
                    ), 400
                role = "Estudiante" if h.get("role") == "user" else "Tutor IA"
                history_lines.append(f"{role}: {txt}")
        if history_lines:
            history_context = "Historial reciente de la conversación:\n" + "\n".join(history_lines) + "\n\n"

    # Cargar contexto únicamente si la lección existe en el currículo
    lesson_data = load_lesson(lesson_id) if lesson_id else None
    lesson_title = lesson_data.get("title", "Python y Java") if lesson_data else "Python y Java"
    lesson_intro = lesson_data.get("intro", "") if lesson_data else ""

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
        logger.error("Error en api_ai_tutor (%s)", type(e).__name__)
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
@limiter.limit("20 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_quiz_result():
    """Califica un quiz estrictamente en el servidor contra content_loader (ignora score/total del cliente)."""
    data = _get_json_dict()
    raw_quiz_id = data.get("quiz_id")
    quiz_id = raw_quiz_id.strip() if isinstance(raw_quiz_id, str) else ""
    quiz_data = load_quiz(quiz_id)
    if not quiz_data:
        return jsonify({"ok": False, "error": "Quiz no encontrado en el currículo."}), 400

    questions = quiz_data.get("questions") or []
    raw_answers = data.get("answers")
    if not isinstance(raw_answers, (dict, list)):
        return jsonify({"ok": False, "error": "Debes enviar tus respuestas para calificar el quiz."}), 400

    score = 0
    total = len(questions)
    results = []

    for idx, q in enumerate(questions):
        qid = str(q.get("id", idx))
        if isinstance(raw_answers, dict):
            user_ans = raw_answers.get(qid, raw_answers.get(str(idx)))
        else:
            user_ans = raw_answers[idx] if idx < len(raw_answers) else None

        correct_idx = _safe_int(q.get("correct", -1), -1)
        if isinstance(user_ans, bool) or user_ans is None:
            selected_idx = -1
        else:
            selected_idx = _safe_int(user_ans, -1)

        is_correct = correct_idx >= 0 and selected_idx == correct_idx
        if is_correct:
            score += 1
        results.append({
            "id": qid,
            "index": idx,
            "selected": selected_idx,
            "correct": correct_idx,
            "is_correct": is_correct,
            "explanation": q.get("explanation") or "",
        })

    percentage = round((score / total) * 100) if total > 0 else 0
    saved = False
    user = get_current_user()
    if user and user.id:
        result = QuizResult(user_id=user.id, quiz_id=quiz_id, score=score, total=total)
        db.session.add(result)
        record_daily_activity(user.id)
        db.session.commit()
        saved = True

    return jsonify({
        "ok": True,
        "saved": saved,
        "anonymous": not saved,
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
    })


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

    # Limpiar claves heredadas de evaluaciones en la cookie de sesión
    for k in list(session.keys()):
        if k.startswith("eval_answers_") or k.startswith("eval_questions_"):
            session.pop(k, None)

    # Get section display info
    ui = load_ui_strings()
    section_title = ui.get(section_key, section_key)

    # Time limit: 30s per question, capped at max 10 minutes (600s)
    raw_time = eval_data.get("time_per_question", 30) * len(client_questions)
    time_limit = min(600, raw_time)

    # Invalidar sesiones anteriores no enviadas para esta sección y crear sesión en servidor
    now_utc = utcnow()
    EvaluationSession.query.filter_by(
        user_id=user.id, section_key=section_key, submitted=False
    ).update({"submitted": True}, synchronize_session=False)

    eval_session = EvaluationSession(
        user_id=user.id,
        section_key=section_key,
        question_ids_json=json.dumps([q["id"] for q in questions]),
        started_at=now_utc,
        expires_at=now_utc + timedelta(seconds=time_limit),
        submitted=False,
    )
    db.session.add(eval_session)
    db.session.commit()

    return render_template(
        "evaluation.html",
        section_key=section_key,
        section_title=section_title,
        eval_data=eval_data,
        eval_session_id=eval_session.id,
        questions=client_questions,
        questions_json=json.dumps(client_questions, ensure_ascii=False),
        time_limit=time_limit,
        status=status,
        passing_score=eval_data.get("passing_score", 70),
        categories=LESSON_CATEGORIES,
        page="evaluation",
    )


EVAL_NETWORK_GRACE_SECONDS = 30


@app.route("/api/evaluacion/resultado", methods=["POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_evaluation_result():
    """Califica una evaluación estrictamente contra la EvaluationSession almacenada en servidor."""
    data = _get_json_dict()
    section_key = data.get("section_key", "")
    answers = data.get("answers", {})
    requested_session_id = _safe_int(data.get("session_id"), 0)

    if not isinstance(section_key, str) or section_key not in SECTION_EVAL_MAP:
        return jsonify({"ok": False, "error": "Sección inválida."}), 400
    if not isinstance(answers, dict):
        return jsonify({"ok": False, "error": "Formato de respuestas inválido."}), 400

    user = current_user
    status = get_section_eval_status(user.id, section_key)
    if not status["unlocked"]:
        return jsonify({
            "ok": False,
            "error": "Debes completar al menos el 80% de las lecciones de la sección antes de presentar la evaluación.",
        }), 403

    eval_data = get_evaluation_for_section(section_key)
    if not eval_data:
        return jsonify({"ok": False, "error": "Evaluación no disponible."}), 404

    if requested_session_id > 0:
        eval_session = EvaluationSession.query.filter_by(
            id=requested_session_id,
            user_id=user.id,
            section_key=section_key,
            submitted=False,
        ).first()
    else:
        eval_session = (
            EvaluationSession.query.filter_by(
                user_id=user.id,
                section_key=section_key,
                submitted=False,
            )
            .order_by(EvaluationSession.started_at.desc())
            .first()
        )

    if not eval_session:
        return jsonify({
            "ok": False,
            "error": "No tienes una sesión de evaluación activa o ya fue enviada. Inicia un nuevo intento.",
        }), 400

    now_utc = utcnow()
    started_at = ensure_utc(eval_session.started_at)
    expires_at = ensure_utc(eval_session.expires_at)

    if now_utc > expires_at + timedelta(seconds=EVAL_NETWORK_GRACE_SECONDS):
        eval_session.submitted = True
        db.session.commit()
        return jsonify({
            "ok": False,
            "error": "El tiempo límite de la evaluación ha expirado. Inicia un nuevo intento.",
        }), 400

    try:
        question_ids = json.loads(eval_session.question_ids_json or "[]")
    except (TypeError, ValueError):
        question_ids = []

    if not isinstance(question_ids, list) or not question_ids:
        eval_session.submitted = True
        db.session.commit()
        return jsonify({"ok": False, "error": "Sesión de evaluación inválida."}), 400

    question_source_map = {}
    catalog_answers = {}
    for lesson_id, qs in eval_data.get("lesson_questions", {}).items():
        for q in qs:
            question_source_map[q["id"]] = lesson_id
            catalog_answers[q["id"]] = (
                q.get("correct_answer") if q.get("type") == "complete_code" else q.get("correct")
            )

    # Calificar SIEMPRE contra el conjunto completo asignado en EvaluationSession
    score = 0
    total = len(question_ids)
    details = {}

    for qid in question_ids:
        correct_val = catalog_answers.get(qid)
        user_answer = answers.get(qid)
        source_lesson = question_source_map.get(qid, "")

        if source_lesson not in details:
            details[source_lesson] = {
                "correct": 0,
                "total": 0,
                "lesson_title": get_lesson_title(source_lesson),
            }

        details[source_lesson]["total"] += 1

        is_correct = False
        if isinstance(correct_val, bool):
            is_correct = isinstance(user_answer, bool) and (user_answer is correct_val)
        elif isinstance(correct_val, int):
            if not isinstance(user_answer, bool) and user_answer is not None:
                try:
                    is_correct = int(user_answer) == correct_val
                except (ValueError, TypeError):
                    is_correct = False
        elif isinstance(correct_val, str):
            if isinstance(user_answer, str):
                is_correct = _normalize_answer_text(user_answer) == _normalize_answer_text(correct_val)

        if is_correct:
            score += 1
            details[source_lesson]["correct"] += 1

    passing_score = _safe_int(eval_data.get("passing_score", 70), 70)
    percentage = round((score / total) * 100, 1) if total > 0 else 0.0
    passed = percentage >= passing_score
    actual_time_taken = max(0, int((now_utc - started_at).total_seconds()))

    # Contar intentos previos y verificar aprobación previa ANTES de insertar el nuevo registro
    prev_attempts = SectionEvaluation.query.filter_by(
        user_id=user.id, section_id=section_key
    ).count()
    already_passed = None
    if passed:
        already_passed = SectionEvaluation.query.filter_by(
            user_id=user.id, section_id=section_key, passed=True
        ).first()

    # Marcar sesión como enviada y guardar resultado real en SectionEvaluation (sin registros sintéticos en LessonProgress)
    eval_session.submitted = True
    evaluation = SectionEvaluation(
        user_id=user.id,
        section_id=section_key,
        score=score,
        total=total,
        percentage=percentage,
        passed=passed,
        time_taken=actual_time_taken,
        attempt_number=prev_attempts + 1,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.session.add(evaluation)

    xp_gained = 0
    if passed and not already_passed:
        xp_gained = XP_PER_EVALUATION
        record_daily_activity(user.id)

    db.session.commit()

    return jsonify({
        "ok": True,
        "score": score,
        "total": total,
        "percentage": percentage,
        "passing_score": passing_score,
        "passed": passed,
        "xp_gained": xp_gained,
        "attempt_number": prev_attempts + 1,
        "details": details,
        "summary": get_progress_summary(user),
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

