"""Validación de credenciales y constantes de cuentas."""

import os
import re

from werkzeug.security import generate_password_hash


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
