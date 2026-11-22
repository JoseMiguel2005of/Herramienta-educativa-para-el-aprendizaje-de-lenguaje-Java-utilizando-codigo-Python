"""Autenticación: inicio de sesión, registro, recuperación de contraseña, cierre de sesión y ajustes."""

import hmac
import secrets
from datetime import timedelta

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from content_loader import load_ui_strings
from models import (
    AuditLog,
    Classroom,
    IssuedCertificate,
    PasswordResetCode,
    SectionEvaluation,
    User,
    db,
    ensure_utc,
    utcnow,
)

from py2java.blueprints import FlatBlueprint

from py2java.config import logger
from py2java.extensions import limiter
from py2java.services.accounts import _home_endpoint_for_role
from py2java.services.classrooms import _log_audit, _normalize_class_code
from py2java.services.curriculum import LESSON_CATEGORIES
from py2java.services.mail import (
    _is_demo_reset_allowed,
    _is_mail_configured,
    send_recovery_email,
)
from py2java.services.security import (
    _extract_relative_from_referrer,
    _get_safe_next_url,
    _login_rate_limit_key,
)
from py2java.services.validation import (
    MAX_RESET_FAILED_ATTEMPTS,
    MIN_PASSWORD_LENGTH,
    TEACHER_SECRET_CODE,
    _DUMMY_PASSWORD_HASH,
    _is_valid_email,
    _is_valid_username,
)

bp = FlatBlueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
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


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
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

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Las contraseñas no coinciden.",
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


@bp.route("/recuperar", methods=["GET", "POST"])
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


@bp.route("/recuperar/verificar", methods=["GET", "POST"])
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


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@bp.route("/configuracion", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        session["theme"] = theme if theme in ("light", "dark") else "light"
        raw_next = (request.form.get("next") or "").strip() or _extract_relative_from_referrer(request.referrer)
        safe_ref = _get_safe_next_url(raw_next, default=url_for("index"))
        return redirect(safe_ref)

    return redirect(url_for("index"))


@bp.route("/cuenta", methods=["GET"])
@login_required
def account_settings():
    """Vista de configuración de cuenta: perfil/correo, contraseña, historial de evaluaciones y baja propia."""
    from py2java.services.timeutils import _get_app_timezone

    ui = load_ui_strings()
    app_tz = _get_app_timezone()

    eval_rows = (
        SectionEvaluation.query.filter_by(user_id=current_user.id)
        .order_by(SectionEvaluation.completed_at.desc(), SectionEvaluation.id.desc())
        .all()
    )
    eval_history = []
    for ev in eval_rows:
        dt = ensure_utc(ev.completed_at)
        eval_history.append({
            "section_id": ev.section_id,
            "section_label": ui.get(ev.section_id, ev.section_id),
            "attempt_number": ev.attempt_number or 1,
            "score": ev.score or 0,
            "total": ev.total or 0,
            "percentage": round(float(ev.percentage or 0.0), 1),
            "passed": bool(ev.passed),
            "time_taken": ev.time_taken or 0,
            "completed_at_str": dt.astimezone(app_tz).strftime("%d/%m/%Y %H:%M") if dt else "—",
        })

    cert_rows = (
        IssuedCertificate.query.filter_by(user_id=current_user.id)
        .order_by(IssuedCertificate.issued_at.desc())
        .all()
    )
    issued_certs = []
    for cert in cert_rows:
        dt = ensure_utc(cert.issued_at)
        issued_certs.append({
            "section_key": cert.section_key,
            "course_name": cert.course_name,
            "verification_code": cert.verification_code,
            "issued_at_str": dt.astimezone(app_tz).strftime("%d/%m/%Y") if dt else "—",
        })

    return render_template(
        "account.html",
        eval_history=eval_history,
        issued_certs=issued_certs,
        categories=LESSON_CATEGORIES,
        page="account",
    )


@bp.route("/cuenta/perfil", methods=["POST"])
@login_required
def account_update_profile():
    """Permite al usuario autenticado actualizar su correo electrónico."""
    email = request.form.get("email", "").strip().lower()
    if not _is_valid_email(email):
        flash("Ingresa un correo electrónico válido.", "error")
        return redirect(url_for("account_settings"))

    existing = User.query.filter(
        func.lower(User.email) == email,
        User.id != current_user.id,
    ).first()
    if existing:
        flash("Este correo electrónico ya está registrado en otra cuenta.", "error")
        return redirect(url_for("account_settings"))

    old_email = current_user.email or ""
    current_user.email = email
    _log_audit(
        current_user,
        action="UPDATE_PROFILE_EMAIL",
        target_username=current_user.username,
        section_id=current_user.section_id,
        reason="Actualización de correo desde configuración de cuenta",
        details=f"{old_email} -> {email}",
    )
    db.session.commit()
    flash("Correo electrónico actualizado correctamente.", "success")
    return redirect(url_for("account_settings"))


@bp.route("/cuenta/password", methods=["POST"])
@login_required
def account_change_password():
    """Permite al usuario autenticado cambiar su contraseña verificando la clave actual."""
    current_pw = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm_pw = request.form.get("confirm_password", "")

    if not check_password_hash(current_user.password_hash, current_pw):
        flash("La contraseña actual es incorrecta.", "error")
        return redirect(url_for("account_settings"))

    if len(new_pw) < MIN_PASSWORD_LENGTH:
        flash(f"La nueva contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.", "error")
        return redirect(url_for("account_settings"))

    if new_pw != confirm_pw:
        flash("Las nuevas contraseñas no coinciden.", "error")
        return redirect(url_for("account_settings"))

    current_user.password_hash = generate_password_hash(new_pw)
    _log_audit(
        current_user,
        action="CHANGE_PASSWORD",
        target_username=current_user.username,
        section_id=current_user.section_id,
        reason="Cambio de contraseña por el propio usuario",
    )
    db.session.commit()
    flash("Contraseña actualizada con éxito.", "success")
    return redirect(url_for("account_settings"))


@bp.route("/cuenta/eliminar", methods=["POST"])
@login_required
def account_delete_self():
    """Elimina la cuenta propia con doble confirmación (usuario + contraseña actual)."""
    if current_user.role == "superadmin":
        flash("Las cuentas Super Admin no pueden autoeliminarse desde la interfaz.", "error")
        return redirect(url_for("account_settings"))

    confirm_username = request.form.get("confirm_username", "").strip()
    current_pw = request.form.get("current_password", "")

    if confirm_username != current_user.username:
        flash("El nombre de usuario de confirmación no coincide.", "error")
        return redirect(url_for("account_settings"))

    if not check_password_hash(current_user.password_hash, current_pw):
        flash("Contraseña actual incorrecta. No se eliminó la cuenta.", "error")
        return redirect(url_for("account_settings"))

    user_id = current_user.id
    username = current_user.username
    role = current_user.role
    sec_id = current_user.section_id

    try:
        # Si es profesor, desvincular estudiantes y eliminar sus secciones antes de borrar la cuenta
        owned_ids = [c.id for c in Classroom.query.filter_by(teacher_id=user_id).all()]
        if owned_ids:
            User.query.filter(User.section_id.in_(owned_ids)).update(
                {"section_id": None}, synchronize_session=False
            )
            AuditLog.query.filter(AuditLog.section_id.in_(owned_ids)).update(
                {"section_id": None}, synchronize_session=False
            )
            Classroom.query.filter(Classroom.id.in_(owned_ids)).delete(synchronize_session=False)

        # Limpiar referencias en AuditLog y User.suspended_by antes de borrar el usuario
        AuditLog.query.filter_by(admin_id=user_id).update(
            {"admin_id": None}, synchronize_session=False
        )
        User.query.filter_by(suspended_by=user_id).update(
            {"suspended_by": None}, synchronize_session=False
        )

        db.session.add(
            AuditLog(
                admin_id=None,
                admin_username=username,
                action="SELF_DELETE_ACCOUNT",
                target_username=username,
                section_id=sec_id if sec_id not in owned_ids else None,
                reason="Eliminación voluntaria de cuenta por el usuario",
                details=f"Rol eliminado: {role}",
            )
        )
        user_obj = db.session.get(User, user_id)
        if user_obj:
            db.session.delete(user_obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Error al eliminar cuenta propia (%s): %s", username, e)
        flash("No se pudo eliminar la cuenta en este momento. Intenta de nuevo.", "error")
        return redirect(url_for("account_settings"))

    logout_user()
    flash("Tu cuenta y todos tus datos fueron eliminados permanentemente.", "info")
    return redirect(url_for("login"))
