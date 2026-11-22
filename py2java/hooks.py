"""Hooks de petición, cabeceras de seguridad, contexto de plantillas y callbacks de sesión."""

import secrets

from flask import Response, flash, g, jsonify, redirect, request, session, url_for
from flask_login import current_user, logout_user
from flask_wtf.csrf import CSRFError

from content_loader import (
    LEVEL_TITLES,
    get_lesson,
    get_lesson_title,
    get_level_title,
    get_reference,
    load_ui_strings,
)
from models import User, db

from py2java.config import is_production, logger
from py2java.extensions import login_manager
from py2java.services.security import strip_exercise_answers_filter


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


def _generate_csp_nonce():
    """Genera un nonce criptográfico único por petición para Content-Security-Policy."""
    g.csp_nonce = secrets.token_urlsafe(16)


def _inject_security_context():
    return {"csp_nonce": getattr(g, "csp_nonce", "")}


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


def inject_globals():
    ui = load_ui_strings()
    return {
        "lang": "es",
        "theme": session.get("theme", "light"),
        "t": ui,
        "level_titles": LEVEL_TITLES,
        "get_level_title": get_level_title,
        "current_user_id": current_user.id if current_user.is_authenticated else None,
        "get_lesson": lambda lid: get_lesson(lid),
        "get_lesson_title": lambda lid: get_lesson_title(lid),
        "get_reference": lambda cat: get_reference(cat),
    }


def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()


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


def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        logger.error("Error en load_user(user_id=%s): %s", user_id, e)
        db.session.rollback()
        return None


def register_hooks(app):
    """Registra hooks de petición, procesadores de contexto y callbacks de Flask-Login."""
    app.before_request(_block_suspended_user)
    app.before_request(_generate_csp_nonce)
    app.context_processor(_inject_security_context)
    app.context_processor(inject_globals)
    app.after_request(_set_security_headers)
    app.errorhandler(CSRFError)(handle_csrf_error)
    app.teardown_appcontext(shutdown_session)
    app.add_template_filter(strip_exercise_answers_filter, "strip_exercise_answers")
    login_manager.unauthorized_handler(_handle_unauthorized)
    login_manager.user_loader(load_user)
