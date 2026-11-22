"""Zona horaria operativa de la aplicación (rachas y reportes)."""

import os
import re
from datetime import timedelta, timezone

from models import utcnow

from py2java.config import logger

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


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
