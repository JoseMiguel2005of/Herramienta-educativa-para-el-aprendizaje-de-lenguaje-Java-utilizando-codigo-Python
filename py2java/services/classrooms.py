"""Secciones de clase, alcance docente y bitácora de auditoría."""

import re
import secrets

from models import AuditLog, Classroom, User, db


ADMIN_STUDENTS_PER_PAGE = 20


LEADERBOARD_PER_PAGE = 50


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
