"""Panel de Super Admin: usuarios, secciones globales, auditoría y exportaciones."""

import csv
import math
from io import StringIO

from flask import Response, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func, nullslast, or_

from content_loader import get_level_info, load_ui_strings
from models import AuditLog, Classroom, User, db, ensure_utc, utcnow

from py2java.blueprints import FlatBlueprint

from py2java.config import logger
from py2java.services.accounts import _home_endpoint_for_role
from py2java.services.classrooms import ADMIN_STUDENTS_PER_PAGE, _log_audit
from py2java.services.curriculum import LESSON_CATEGORIES, _course_lesson_ids
from py2java.services.progress import (
    _build_student_stats_subqueries,
    _get_classroom_student_counts,
    get_bulk_progress_summaries,
)
from py2java.services.security import _csv_safe, _get_json_dict, _safe_int
from py2java.services.timeutils import _app_now, _get_app_timezone

bp = FlatBlueprint("superadmin", __name__)


# --- Panel de Super Admin ---
@bp.route("/superadmin")
@login_required
def superadmin_dashboard():
    if current_user.role != "superadmin":
        _log_audit(
            current_user,
            action="UNAUTHORIZED_SUPERADMIN_ACCESS",
            target_username=None,
            reason="Intento de acceso a /superadmin sin privilegios",
        )
        db.session.commit()
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    q = request.args.get("q", "").strip()
    raw_section = request.args.get("section_id", "").strip()
    status_filter = request.args.get("status", "all").strip()
    if status_filter not in ("all", "active", "suspended"):
        status_filter = "all"
    sort_by = request.args.get("sort", "xp_desc").strip()
    if sort_by not in ("xp_desc", "xp_asc", "progress_desc", "name_asc", "date_desc", "date_asc"):
        sort_by = "xp_desc"
    page = max(1, _safe_int(request.args.get("page", 1), 1))
    audit_page = max(1, _safe_int(request.args.get("audit_page", 1), 1))

    course_ids = _course_lesson_ids()
    total_course = len(course_ids) or 1
    app_tz = _get_app_timezone()

    all_teachers = []
    all_classrooms = []
    classroom_map = {}
    teacher_map = {}
    classroom_counts = {}
    teacher_rows = []
    paginated_students = []
    total_students_cnt = 0
    active_students_cnt = 0
    suspended_students_cnt = 0
    unassigned_students_cnt = 0
    total_filtered = 0
    total_pages = 1
    audit_logs = []
    audit_total = 0
    audit_total_pages = 1

    try:
        all_teachers = User.query.filter_by(role="teacher").order_by(nullslast(User.created_at.desc()), User.id.desc()).all()
        all_classrooms = Classroom.query.order_by(nullslast(Classroom.created_at.desc()), Classroom.id.desc()).all()
        classroom_map = {c.id: c for c in all_classrooms}
        teacher_map = {t.id: t for t in all_teachers}

        # Conteo de estudiantes por sección en 1 consulta agregada GROUP BY (sin N+1)
        classroom_counts = _get_classroom_student_counts()

        sections_by_teacher = {}
        for c in all_classrooms:
            sections_by_teacher.setdefault(c.teacher_id, []).append(c)

        for t in all_teachers:
            t_secs = sections_by_teacher.get(t.id, [])
            t_stu_cnt = sum(classroom_counts.get(c.id, 0) for c in t_secs)
            t_created_utc = ensure_utc(t.created_at)
            teacher_rows.append({
                "id": t.id,
                "username": t.username,
                "email": t.email or "",
                "sections_count": len(t_secs),
                "students_count": t_stu_cnt,
                "is_suspended": bool(getattr(t, "is_suspended", False)),
                "suspended_reason": getattr(t, "suspended_reason", None) or "",
                "created_at_str": t_created_utc.astimezone(app_tz).strftime("%d/%m/%Y") if t_created_utc else "N/A",
            })

        # Métricas globales de estudiantes en 1 sola consulta agregada SQL
        stu_agg = (
            db.session.query(
                func.count(User.id),
                func.coalesce(func.sum(case((User.is_suspended.is_(True), 1), else_=0)), 0),
                func.coalesce(func.sum(case((User.section_id.is_(None), 1), else_=0)), 0),
            )
            .filter(User.role == "student")
            .one()
        )
        total_students_cnt = int(stu_agg[0] or 0)
        suspended_students_cnt = int(stu_agg[1] or 0)
        active_students_cnt = total_students_cnt - suspended_students_cnt
        unassigned_students_cnt = int(stu_agg[2] or 0)

        # Consulta filtrada, ordenada y paginada de estudiantes directamente en SQL
        lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = _build_student_stats_subqueries()
        sq = (
            db.session.query(User)
            .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
            .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
            .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
            .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
            .filter(User.role == "student")
        )
        if q:
            like = f"%{q}%"
            sq = sq.filter(or_(User.username.ilike(like), User.email.ilike(like)))
        if raw_section == "unassigned":
            sq = sq.filter(User.section_id.is_(None))
        elif raw_section:
            sec_int = _safe_int(raw_section, 0)
            if sec_int in classroom_map:
                sq = sq.filter(User.section_id == sec_int)
        if status_filter == "active":
            sq = sq.filter(User.is_suspended.is_(False))
        elif status_filter == "suspended":
            sq = sq.filter(User.is_suspended.is_(True))

        total_filtered = int(sq.with_entities(func.count(User.id)).scalar() or 0)
        total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
        page = min(page, total_pages)

        order_map = {
            "xp_desc": (total_xp_expr.desc(), func.lower(User.username).asc(), User.id.asc()),
            "xp_asc": (total_xp_expr.asc(), func.lower(User.username).asc(), User.id.asc()),
            "progress_desc": (completed_expr.desc(), total_xp_expr.desc(), func.lower(User.username).asc()),
            "name_asc": (func.lower(User.username).asc(), User.id.asc()),
            "date_desc": (nullslast(User.created_at.desc()), User.id.desc()),
            "date_asc": (nullslast(User.created_at.asc()), User.id.asc()),
        }

        page_rows = (
            sq.with_entities(
                User,
                completed_expr.label("completed_cnt"),
                total_xp_expr.label("total_xp"),
            )
            .order_by(*order_map[sort_by])
            .offset((page - 1) * ADMIN_STUDENTS_PER_PAGE)
            .limit(ADMIN_STUDENTS_PER_PAGE)
            .all()
        )
        for s, comp_val, xp_val in page_rows:
            comp = int(comp_val or 0)
            xp_int = int(xp_val or 0)
            lvl = get_level_info(xp_int)
            cls = classroom_map.get(s.section_id)
            t_owner = teacher_map.get(cls.teacher_id) if cls else None
            paginated_students.append({
                "id": s.id,
                "username": s.username,
                "email": s.email or "",
                "level": lvl["level"],
                "title": lvl["title"],
                "total_xp": xp_int,
                "completed": comp,
                "progress_pct": round(min(100, comp * 100 / total_course), 1),
                "section_id": s.section_id,
                "section_name": cls.name if cls else "Sin sección",
                "section_code": cls.code if cls else "",
                "teacher_name": t_owner.username if t_owner else "—",
                "is_suspended": bool(getattr(s, "is_suspended", False)),
                "suspended_reason": getattr(s, "suspended_reason", None) or "",
                "created_at": ensure_utc(s.created_at),
            })

        # Bitácora global (todos los eventos del sistema)
        audit_q = AuditLog.query.order_by(nullslast(AuditLog.created_at.desc()), AuditLog.id.desc())
        audit_total = audit_q.count()
        audit_per = 15
        audit_total_pages = max(1, math.ceil(audit_total / audit_per))
        audit_page = min(audit_page, audit_total_pages)
        audit_logs = audit_q.offset((audit_page - 1) * audit_per).limit(audit_per).all()
    except Exception as e:
        logger.error("Error en superadmin_dashboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass

    metrics = {
        "total_students": total_students_cnt,
        "active_students": active_students_cnt,
        "suspended_students": suspended_students_cnt,
        "unassigned_students": unassigned_students_cnt,
        "total_teachers": len(all_teachers),
        "suspended_teachers": sum(1 for t in all_teachers if getattr(t, "is_suspended", False)),
        "total_classrooms": len(all_classrooms),
        "total_course_lessons": len(course_ids),
        "audit_total": audit_total,
    }
    filters = {
        "q": q,
        "section_id": raw_section,
        "status": status_filter,
        "sort": sort_by,
        "page": page,
        "total_pages": total_pages,
        "total_filtered": total_filtered,
        "audit_page": audit_page,
        "audit_total_pages": audit_total_pages,
    }
    return render_template(
        "superadmin_dashboard.html",
        metrics=metrics,
        teachers=teacher_rows,
        classrooms=all_classrooms,
        classroom_counts=classroom_counts,
        teacher_map=teacher_map,
        students=paginated_students,
        audit_logs=audit_logs,
        filters=filters,
        categories=LESSON_CATEGORIES,
    )


@bp.route("/superadmin/usuario/<int:user_id>/suspender", methods=["POST"])
@login_required
def superadmin_suspend_user(user_id):
    """Super Admin puede suspender a cualquier estudiante o profesor (nunca a otro superadmin) con motivo obligatorio."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return jsonify({"success": False, "error": "Debes indicar un motivo obligatorio (mínimo 5 caracteres)."}), 400

    target = db.session.get(User, user_id)
    if not target or target.role == "superadmin":
        return jsonify({"success": False, "error": "Usuario no encontrado o protegido."}), 404

    if getattr(target, "is_suspended", False):
        return jsonify({"success": False, "error": "El usuario ya se encuentra suspendido."}), 400

    target.is_suspended = True
    target.suspended_at = utcnow()
    target.suspended_reason = reason
    target.suspended_by = current_user.id

    action = "SUPERADMIN_SUSPEND_TEACHER" if target.role == "teacher" else "SUPERADMIN_SUSPEND_STUDENT"
    _log_audit(
        current_user,
        action=action,
        target_username=target.username,
        section_id=target.section_id,
        reason=reason,
        details=f"Rol afectado: {target.role}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "suspended"})


@bp.route("/superadmin/usuario/<int:user_id>/restaurar", methods=["POST"])
@login_required
def superadmin_restore_user(user_id):
    """Super Admin puede restaurar a cualquier estudiante o profesor suspendido."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "Restauración por Super Admin").strip()[:500]

    target = db.session.get(User, user_id)
    if not target or target.role == "superadmin":
        return jsonify({"success": False, "error": "Usuario no encontrado."}), 404

    if not getattr(target, "is_suspended", False):
        return jsonify({"success": False, "error": "El usuario ya está activo."}), 400

    prev_reason = target.suspended_reason or ""
    target.is_suspended = False
    target.suspended_at = None
    target.suspended_reason = None
    target.suspended_by = None

    action = "SUPERADMIN_RESTORE_TEACHER" if target.role == "teacher" else "SUPERADMIN_RESTORE_STUDENT"
    _log_audit(
        current_user,
        action=action,
        target_username=target.username,
        section_id=target.section_id,
        reason=reason,
        details=f"Rol afectado: {target.role} | Motivo previo: {prev_reason}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@bp.route("/superadmin/estudiante/<int:student_id>/asignar-seccion", methods=["POST"])
@login_required
def superadmin_assign_section(student_id):
    """Permite al Super Admin asignar o quitar la sección de cualquier estudiante."""
    if current_user.role != "superadmin":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado."}), 404

    data = _get_json_dict() if request.is_json else request.form
    raw_sec = str(data.get("section_id") or "").strip()
    if not raw_sec:
        student.section_id = None
        detail = "Desvinculado de sección"
        new_sec_id = None
    else:
        sec_id = _safe_int(raw_sec, 0)
        cls = db.session.get(Classroom, sec_id)
        if not cls:
            return jsonify({"success": False, "error": "Sección no encontrada."}), 404
        student.section_id = cls.id
        detail = f"Asignado a sección {cls.name} ({cls.code})"
        new_sec_id = cls.id

    _log_audit(
        current_user,
        action="SUPERADMIN_ASSIGN_SECTION",
        target_username=student.username,
        section_id=new_sec_id,
        reason="Gestión de sección por Super Admin",
        details=detail,
    )
    db.session.commit()
    return jsonify({"success": True, "details": detail})


@bp.route("/superadmin/export/csv")
@login_required
def superadmin_export_csv():
    if current_user.role != "superadmin":
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    all_classrooms = Classroom.query.all()
    classroom_map = {c.id: c for c in all_classrooms}
    students = User.query.filter_by(role="student").all()
    bulk_stats = get_bulk_progress_summaries(students)
    course_ids = _course_lesson_ids()

    si = StringIO()
    si.write('\ufeff')
    cw = csv.writer(si, delimiter=';')
    cw.writerow(["Username", "Email", "Seccion", "Estado", "Total_XP", "Lecciones_Completadas", "Nivel", "Racha_Actual", "Fecha_Registro"])
    for s in students:
        stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
        lvl_info = get_level_info(stats["total_xp"])
        cls = classroom_map.get(s.section_id)
        section_label = f"{cls.name} ({cls.code})" if cls else "Sin sección"
        cw.writerow([
            _csv_safe(s.username or ""),
            _csv_safe(s.email or ""),
            _csv_safe(section_label),
            _csv_safe("Suspendido" if getattr(s, "is_suspended", False) else "Activo"),
            stats["total_xp"],
            len(set(stats["completed_lessons"]) & course_ids),
            _csv_safe(lvl_info["title"]),
            stats["streak"],
            _csv_safe(s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A"),
        ])
    output = si.getvalue()
    si.close()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_global_estudiantes.csv"},
    )


@bp.route("/superadmin/export/pdf")
@login_required
def superadmin_export_pdf():
    if current_user.role != "superadmin":
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    try:
        from pdf_report import build_admin_report_pdf

        course_ids = _course_lesson_ids()
        total_course = len(course_ids) or 1
        students = User.query.filter_by(role="student").all()
        bulk_stats = get_bulk_progress_summaries(students)

        rows = []
        level_counts = {}
        for s in students:
            stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
            lvl = get_level_info(stats["total_xp"])
            completed = len(set(stats["completed_lessons"]) & course_ids)
            rows.append({
                "username": s.username or "",
                "level": lvl["level"],
                "title": lvl["title"],
                "total_xp": stats["total_xp"],
                "completed": completed,
                "progress_pct": round(min(100, completed * 100 / total_course), 1),
                "streak": stats["streak"],
            })
            key = (lvl["level"] if lvl["level"] < 20 else 20, lvl["title"])
            level_counts[key] = level_counts.get(key, 0) + 1

        rows.sort(key=lambda r: r["total_xp"], reverse=True)
        n = len(rows)
        metrics = {
            "total_students": n,
            "avg_xp": round(sum(r["total_xp"] for r in rows) / n) if n else 0,
            "total_completed": sum(r["completed"] for r in rows),
            "avg_progress_pct": round(sum(r["progress_pct"] for r in rows) / n, 1) if n else 0,
            "total_course_lessons": len(course_ids),
            "active_streaks": sum(1 for r in rows if r["streak"] > 0),
            "level_distribution": [
                (f"Lv.{lv} - {title}", count)
                for (lv, title), count in sorted(level_counts.items())
            ],
        }
        pdf_bytes = build_admin_report_pdf(
            rows, metrics,
            site_title=load_ui_strings().get("site_title", "Py2Java Edu"),
            generated_by=f"{current_user.username} (Super Admin)",
        )
    except Exception as e:
        logger.error("Error en superadmin_export_pdf (%s): %s", type(e).__name__, e)
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF global."}), 500

    filename = f"reporte_global_{_app_now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
