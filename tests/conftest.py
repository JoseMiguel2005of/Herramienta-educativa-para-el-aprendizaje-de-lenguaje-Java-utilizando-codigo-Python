"""Configuración y fixtures aislados de pytest (BD SQLite temporal por prueba)."""

import os
import re

# Aislar el entorno ANTES de importar py2java (impide usar la BD remota de .env)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "pytest-isolated-secret-key-at-least-32-chars-long"
os.environ["FLASK_DEBUG"] = "false"
os.environ["ALLOW_DEMO_RESET"] = "false"
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
for _prod_var in ("VERCEL", "AWS_LAMBDA_FUNCTION_NAME", "FLASK_ENV", "APP_ENV", "ENV"):
    os.environ.pop(_prod_var, None)

import pytest
from werkzeug.security import generate_password_hash

from models import Classroom, LessonProgress, User, db, utcnow
from py2java import create_app
from py2java.extensions import limiter
from py2java.services.evaluation import get_section_lessons

CSRF_INPUT_RE = re.compile(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', re.I)
CSRF_META_RE = re.compile(r'name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']', re.I)


def extract_csrf_token(html_text):
    """Extrae el token CSRF desde un formulario HTML o desde la meta etiqueta de base.html."""
    match = CSRF_INPUT_RE.search(html_text) or CSRF_META_RE.search(html_text)
    assert match is not None, "No se encontró token CSRF en la respuesta HTML."
    return match.group(1)


def _build_test_app(tmp_path, *, csrf_enabled=False, extra_config=None):
    db_file = tmp_path / "py2java_test.sqlite"
    cfg = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}",
        "SECRET_KEY": "pytest-isolated-secret-key-at-least-32-chars-long",
        "WTF_CSRF_ENABLED": csrf_enabled,
        "RATELIMIT_STORAGE_URI": "memory://",
    }
    if extra_config:
        cfg.update(extra_config)

    flask_app = create_app(cfg)
    with flask_app.app_context():
        db.create_all()
    return flask_app


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reinicia contadores en memoria de Flask-Limiter entre pruebas."""
    limiter.enabled = True
    try:
        limiter.reset()
    except Exception:
        pass
    yield
    try:
        limiter.reset()
    except Exception:
        pass


@pytest.fixture()
def app(tmp_path):
    """Aplicación Flask aislada con BD SQLite temporal limpia (CSRF desactivado para lógica de negocio)."""
    flask_app = _build_test_app(tmp_path, csrf_enabled=False)
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    """Cliente HTTP de pruebas conectado a la app aislada."""
    return app.test_client()


@pytest.fixture()
def csrf_app(tmp_path):
    """Aplicación Flask aislada con protección CSRF activa."""
    flask_app = _build_test_app(tmp_path, csrf_enabled=True)
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def csrf_client(csrf_app):
    """Cliente HTTP con protección CSRF habilitada."""
    return csrf_app.test_client()


@pytest.fixture()
def make_user(app):
    """Factory para crear usuarios en la BD de pruebas."""
    def _factory(
        username,
        email=None,
        password="Password123!",
        role="student",
        section_id=None,
        is_suspended=False,
        suspended_reason=None,
    ):
        with app.app_context():
            user = User(
                username=username,
                email=email if email is not None else f"{username.lower()}@test.edu",
                password_hash=generate_password_hash(password),
                role=role,
                section_id=section_id,
                is_suspended=is_suspended,
                suspended_reason=suspended_reason,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    return _factory


@pytest.fixture()
def make_classroom(app):
    """Factory para crear secciones (Classroom) en la BD de pruebas."""
    def _factory(name, code, teacher_id):
        with app.app_context():
            cls = Classroom(name=name, code=code, teacher_id=teacher_id)
            db.session.add(cls)
            db.session.commit()
            return cls.id

    return _factory


def login_as(test_client, username, password="Password123!", use_csrf=False):
    """Autentica un cliente de pruebas vía POST /login."""
    data = {"username": username, "password": password}
    if use_csrf:
        resp_get = test_client.get("/login")
        data["csrf_token"] = extract_csrf_token(resp_get.get_data(as_text=True))
    return test_client.post("/login", data=data, follow_redirects=False)


def complete_section_lessons(flask_app, user_id, section_key, ratio=1.0):
    """Marca como completadas las lecciones de una sección según la proporción dada."""
    lesson_ids = get_section_lessons(section_key)
    count = int(len(lesson_ids) * ratio)
    with flask_app.app_context():
        for lid in lesson_ids[:count]:
            if not LessonProgress.query.filter_by(user_id=user_id, lesson_id=lid).first():
                db.session.add(
                    LessonProgress(
                        user_id=user_id,
                        lesson_id=lid,
                        completed=True,
                        score=10,
                        completed_at=utcnow(),
                    )
                )
        db.session.commit()
    return lesson_ids[:count]
