"""Contexto, emisión persistente y verificación pública de certificados de finalización."""

import hashlib
import hmac
import secrets
import uuid

from flask import current_app

from content_loader import load_ui_strings
from models import IssuedCertificate, db, ensure_utc, utcnow

from py2java.services.curriculum import LESSON_CATEGORIES, _category_course_lessons
from py2java.services.progress import get_progress_summary
from py2java.services.timeutils import _app_now, _get_app_timezone


_SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _format_spanish_date(dt):
    return f"{dt.day:02d} de {_SPANISH_MONTHS[dt.month]} de {dt.year}"


def _generate_verification_code(user_id, section_id):
    """Genera un código único no predecible (UUID4 + HMAC-SHA256) para certificados."""
    raw_secret = (getattr(current_app, "secret_key", None) or "").encode("utf-8")
    if not raw_secret:
        raw_secret = secrets.token_bytes(32)
    nonce = uuid.uuid4().hex
    payload = f"{user_id}:{section_id}:{nonce}:{secrets.token_hex(8)}".encode("utf-8")
    digest = hmac.new(raw_secret, payload, hashlib.sha256).hexdigest().upper()
    return f"PY2J-{digest[:8]}-{digest[8:16]}-{digest[16:24]}"


def get_or_issue_certificate(user, section_id, category_name, total_lessons):
    """Obtiene el certificado emitido del usuario o lo crea y persiste por primera vez."""
    existing = IssuedCertificate.query.filter_by(
        user_id=user.id, section_key=section_id
    ).first()
    if existing:
        return existing

    code = _generate_verification_code(user.id, section_id)
    while IssuedCertificate.query.filter_by(verification_code=code).first() is not None:
        code = _generate_verification_code(user.id, section_id)

    cert = IssuedCertificate(
        user_id=user.id,
        section_key=section_id,
        course_name=category_name,
        total_lessons=int(total_lessons or 0),
        verification_code=code,
        issued_at=utcnow(),
    )
    db.session.add(cert)
    db.session.commit()
    return cert


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
    category_name = ui.get(target_cat["label_key"], section_id)
    app_tz = _get_app_timezone()

    if is_complete:
        cert = get_or_issue_certificate(user, section_id, category_name, len(cat_lessons))
        issued_local = ensure_utc(cert.issued_at).astimezone(app_tz)
        verification_code = cert.verification_code
        completion_date = _format_spanish_date(issued_local)
        completion_year = issued_local.year
    else:
        now = _app_now()
        verification_code = None
        completion_date = _format_spanish_date(now)
        completion_year = now.year

    return {
        "category_name": category_name,
        "category_id": section_id,
        "total_lessons": len(cat_lessons),
        "completed_lessons": len(completed_in_cat),
        "is_complete": is_complete,
        "verification_code": verification_code,
        "completion_date": completion_date,
        "completion_year": completion_year,
        "site_title": ui.get("site_title", "Py2Java Edu"),
    }
