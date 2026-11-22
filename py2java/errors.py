"""Manejadores centralizados de errores HTTP (403, 404, 429, 500)."""

from flask import Response, jsonify, render_template, request, session

from models import db
from py2java.config import logger
from py2java.services.classrooms import _normalize_class_code
from py2java.services.curriculum import LESSON_CATEGORIES
from py2java.services.mail import _is_demo_reset_allowed
from py2java.services.security import _get_safe_next_url


def _wants_json_error():
    return (
        request.path.startswith("/api/")
        or request.is_json
        or "application/json" in (request.headers.get("Accept") or "")
    )


def handle_forbidden(_err):
    msg = "No tienes permisos para acceder a este recurso."
    if _wants_json_error():
        return jsonify({"ok": False, "code": 403, "error": msg}), 403
    return render_template("errors/403.html", categories=LESSON_CATEGORIES, page="error"), 403


def handle_not_found(_err):
    msg = "El recurso o página solicitada no existe."
    if _wants_json_error():
        return jsonify({"ok": False, "code": 404, "error": msg}), 404
    return render_template("errors/404.html", categories=LESSON_CATEGORIES, page="error"), 404


def handle_internal_error(err):
    logger.exception("Error interno 500 en %s %s: %s", request.method, request.path, err)
    try:
        db.session.rollback()
    except Exception:
        pass
    msg = "Ocurrió un error interno en el servidor. Intenta nuevamente en unos momentos."
    if _wants_json_error():
        return jsonify({"ok": False, "code": 500, "error": msg}), 500
    return render_template("errors/500.html", categories=LESSON_CATEGORIES, page="error"), 500


def handle_rate_limit_exceeded(_err):
    msg = "Demasiados intentos en poco tiempo. Espera unos minutos antes de volver a intentarlo."
    if _wants_json_error():
        return jsonify({"ok": False, "code": 429, "error": msg}), 429

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


def register_error_handlers(app):
    """Registra los manejadores de errores HTTP en la aplicación Flask."""
    app.errorhandler(403)(handle_forbidden)
    app.errorhandler(404)(handle_not_found)
    app.errorhandler(429)(handle_rate_limit_exceeded)
    app.errorhandler(500)(handle_internal_error)
