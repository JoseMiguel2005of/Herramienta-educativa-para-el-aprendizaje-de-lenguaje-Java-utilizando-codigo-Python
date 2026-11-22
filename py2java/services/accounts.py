"""Servicios de cuentas: Super Admin inicial, usuario actual y página de inicio por rol."""

import os

from flask_login import current_user
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash

from models import User, db

from py2java.config import logger
from py2java.services.validation import (
    MIN_PASSWORD_LENGTH,
    _is_valid_email,
    _is_valid_username,
)


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


def _home_endpoint_for_role(role):
    if role == "superadmin":
        return "superadmin_dashboard"
    if role == "teacher":
        return "teacher_dashboard"
    return "dashboard"


def get_current_user():
    """Retorna el usuario autenticado o None."""
    if current_user.is_authenticated:
        return current_user
    return None
