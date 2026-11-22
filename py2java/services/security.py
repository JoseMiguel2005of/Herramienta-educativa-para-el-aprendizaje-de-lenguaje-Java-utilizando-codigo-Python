"""Utilidades de seguridad: CSV seguro, redirecciones internas, IP de cliente y claves de rate-limit."""

import re

from flask import request
from flask_limiter.util import get_remote_address
from flask_login import current_user
from urllib.parse import urlparse

from py2java.config import is_vercel


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(val):
    """Neutraliza CSV Formula Injection anteponiendo apóstrofo a prefijos peligrosos."""
    if val is None:
        return ""
    text = str(val)
    if text.startswith(_CSV_FORMULA_PREFIXES) or text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


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


def strip_exercise_answers_filter(raw_html):
    """Elimina atributos data-answer del HTML de ejercicios antes de enviarlo al navegador."""
    if not isinstance(raw_html, str):
        return ""
    return _DATA_ANSWER_ATTR_RE.sub("", raw_html)


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
