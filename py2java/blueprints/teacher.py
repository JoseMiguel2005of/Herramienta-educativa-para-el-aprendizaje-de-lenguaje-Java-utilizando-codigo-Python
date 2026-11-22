"""Panel de profesor: secciones, estudiantes, suspensiones y exportaciones."""

import csv
import math
from io import StringIO

from flask import Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, distinct, func, nullslast, or_

from content_loader import LEVEL_TITLES, get_level_info, load_ui_strings
from models import AuditLog, Classroom, SectionEvaluation, User, db, ensure_utc, utcnow

from py2java.blueprints import FlatBlueprint

from py2java.config import logger
from py2java.services.accounts import _home_endpoint_for_role
from py2java.services.classrooms import (
    ADMIN_STUDENTS_PER_PAGE,
    _generate_class_code,
    _get_teacher_classrooms,
    _get_teacher_scoped_students,
    _log_audit,
    _normalize_class_code,
    _teacher_owns_student,
)
from py2java.services.curriculum import LESSON_CATEGORIES, _course_lesson_ids
from py2java.services.evaluation import SECTION_EVAL_MAP
from py2java.services.progress import (
    _build_student_stats_subqueries,
    _get_bulk_streaks,
    _get_classroom_student_counts,
    get_bulk_progress_summaries,
)
from py2java.services.security import _csv_safe, _get_json_dict, _safe_int
from py2java.services.timeutils import _app_now, _get_app_timezone

bp = FlatBlueprint("teacher", __name__)


@bp.route("/administrador")
@bp.route("/profesor")
@login_required
def teacher_dashboard():
    if current_user.role == "superadmin":
        return redirect(url_for("superadmin_dashboard"))
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))

    # Parámetros de búsqueda, filtros, ordenamiento y paginación desde URL (GET)
    q = request.args.get("q", "").strip()
    raw_section = request.args.get("section_id", "").strip()
    section_filter = _safe_int(raw_section, 0) if raw_section else 0
    raw_level = request.args.get("level", "").strip()
    level_filter = _safe_int(raw_level, 0) if raw_level else 0
    status_filter = request.args.get("status", "all").strip()
    if status_filter not in ("all", "active", "suspended", "with_progress", "no_activity"):
        status_filter = "all"
    sort_by = request.args.get("sort", "xp_desc").strip()
    if sort_by not in ("xp_desc", "xp_asc", "progress_desc", "progress_asc", "name_asc", "name_desc", "date_desc", "date_asc"):
        sort_by = "xp_desc"
    page = max(1, _safe_int(request.args.get("page", 1), 1))

    classrooms = []
    classroom_map = {}
    classroom_counts = {}
    paginated_students = []
    total_scoped_students = 0
    total_filtered = 0
    total_pages = 1
    total_xp = 0
    total_completed = 0
    active_count = 0
    suspended_count = 0
    level_counts = {}
    eval_agg_map = {}
    active_section_id = None
    course_ids = _course_lesson_ids()
    total_course_lessons = len(course_ids) or 1

    try:
        classrooms = _get_teacher_classrooms(current_user.id)
        classroom_map = {c.id: c for c in classrooms}
        allowed_ids = list(classroom_map.keys())

        # Validar en backend que section_filter pertenezca al docente actual
        active_section_id = section_filter if section_filter in classroom_map else None

        if allowed_ids:
            # 1) Conteo de estudiantes por sección en 1 consulta agregada GROUP BY
            classroom_counts = _get_classroom_student_counts(allowed_ids)

            scope_ids = [active_section_id] if active_section_id else allowed_ids
            scope_user_ids_select = db.select(User.id).where(
                User.role == "student",
                User.section_id.in_(scope_ids),
            )
            lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = (
                _build_student_stats_subqueries(scope_user_ids_select)
            )

            base_scope_q = (
                db.session.query(User)
                .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
                .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
                .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
                .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
                .filter(User.role == "student", User.section_id.in_(scope_ids))
            )

            # 2) Métricas agregadas del alcance en SQL (sin cargar todos los estudiantes en RAM)
            agg_total, agg_suspended, agg_xp, agg_completed = (
                base_scope_q.with_entities(
                    func.count(User.id),
                    func.coalesce(func.sum(case((User.is_suspended.is_(True), 1), else_=0)), 0),
                    func.coalesce(func.sum(total_xp_expr), 0),
                    func.coalesce(func.sum(completed_expr), 0),
                ).one()
            )
            total_scoped_students = int(agg_total or 0)
            suspended_count = int(agg_suspended or 0)
            active_count = total_scoped_students - suspended_count
            total_xp = int(agg_xp or 0)
            total_completed = int(agg_completed or 0)

            # Distribución por nivel en SQL (máximo 20 filas agregadas)
            level_bucket_expr = case(
                *[(total_xp_expr < lv * 100, lv) for lv in range(1, 20)],
                else_=20,
            )
            level_dist_rows = (
                base_scope_q.with_entities(level_bucket_expr.label("lvl"), func.count(User.id))
                .group_by(level_bucket_expr)
                .order_by(level_bucket_expr.asc())
                .all()
            )
            for lv_num, lv_cnt in level_dist_rows:
                lv_title = LEVEL_TITLES.get(int(lv_num), "Iniciado")
                level_counts[lv_title] = int(lv_cnt or 0)

            # 3) Filtros, ordenamiento y paginación directamente en SQL
            filtered_q = base_scope_q
            if q:
                like_pattern = f"%{q}%"
                filtered_q = filtered_q.filter(
                    or_(
                        User.username.ilike(like_pattern),
                        User.email.ilike(like_pattern),
                    )
                )
            if status_filter == "active":
                filtered_q = filtered_q.filter(User.is_suspended.is_(False))
            elif status_filter == "suspended":
                filtered_q = filtered_q.filter(User.is_suspended.is_(True))
            elif status_filter == "with_progress":
                filtered_q = filtered_q.filter(or_(completed_expr > 0, total_xp_expr > 0))
            elif status_filter == "no_activity":
                filtered_q = filtered_q.filter(completed_expr == 0, total_xp_expr == 0)

            if level_filter >= 20:
                filtered_q = filtered_q.filter(total_xp_expr >= 1900)
            elif level_filter >= 1:
                filtered_q = filtered_q.filter(
                    total_xp_expr >= (level_filter - 1) * 100,
                    total_xp_expr < level_filter * 100,
                )

            total_filtered = int(filtered_q.with_entities(func.count(User.id)).scalar() or 0)
            total_pages = max(1, math.ceil(total_filtered / ADMIN_STUDENTS_PER_PAGE))
            if page > total_pages:
                page = total_pages

            order_map = {
                "xp_desc": (total_xp_expr.desc(), func.lower(User.username).asc(), User.id.asc()),
                "xp_asc": (total_xp_expr.asc(), func.lower(User.username).asc(), User.id.asc()),
                "progress_desc": (completed_expr.desc(), total_xp_expr.desc(), func.lower(User.username).asc()),
                "progress_asc": (completed_expr.asc(), total_xp_expr.asc(), func.lower(User.username).asc()),
                "name_asc": (func.lower(User.username).asc(), User.id.asc()),
                "name_desc": (func.lower(User.username).desc(), User.id.desc()),
                "date_desc": (nullslast(User.created_at.desc()), User.id.desc()),
                "date_asc": (nullslast(User.created_at.asc()), User.id.asc()),
            }

            page_rows = (
                filtered_q.with_entities(
                    User,
                    completed_expr.label("completed_cnt"),
                    total_xp_expr.label("total_xp"),
                )
                .order_by(*order_map[sort_by])
                .offset((page - 1) * ADMIN_STUDENTS_PER_PAGE)
                .limit(ADMIN_STUDENTS_PER_PAGE)
                .all()
            )
            page_streaks = _get_bulk_streaks([s.id for s, _, _ in page_rows])
            app_tz = _get_app_timezone()

            for s, completed_val, xp_val in page_rows:
                completed_cnt = int(completed_val or 0)
                xp_int = int(xp_val or 0)
                lvl = get_level_info(xp_int)
                cls = classroom_map.get(s.section_id)
                created_utc = ensure_utc(s.created_at)
                suspended_utc = ensure_utc(getattr(s, "suspended_at", None))
                paginated_students.append({
                    "id": s.id,
                    "username": s.username,
                    "email": s.email or "",
                    "total_xp": xp_int,
                    "completed": completed_cnt,
                    "progress_pct": round(min(100, completed_cnt * 100 / total_course_lessons), 1),
                    "level": lvl["level"],
                    "title": lvl["title"],
                    "streak": page_streaks.get(s.id, 0),
                    "section_id": s.section_id,
                    "section_name": cls.name if cls else "Sin sección",
                    "section_code": cls.code if cls else "",
                    "is_suspended": bool(getattr(s, "is_suspended", False)),
                    "suspended_reason": getattr(s, "suspended_reason", None) or "",
                    "suspended_at": suspended_utc.astimezone(app_tz).strftime("%d/%m/%Y %H:%M") if suspended_utc else "",
                    "created_at": created_utc,
                    "created_at_str": created_utc.astimezone(app_tz).strftime("%d/%m/%Y") if created_utc else "N/A",
                })

            # 4) Resumen agregado real de SectionEvaluation para los estudiantes del docente (1 consulta SQL)
            eval_rows = (
                db.session.query(
                    SectionEvaluation.section_id,
                    func.count(SectionEvaluation.id).label("attempts"),
                    func.count(distinct(SectionEvaluation.user_id)).label("students_attempted"),
                    func.count(
                        distinct(case((SectionEvaluation.passed.is_(True), SectionEvaluation.user_id), else_=None))
                    ).label("students_passed"),
                    func.avg(SectionEvaluation.percentage).label("avg_score"),
                )
                .filter(SectionEvaluation.user_id.in_(scope_user_ids_select))
                .group_by(SectionEvaluation.section_id)
                .all()
            )
            for sec_id, attempts_cnt, stu_att, stu_pass, avg_pct in eval_rows:
                eval_agg_map[sec_id] = {
                    "attempts": int(attempts_cnt or 0),
                    "students_attempted": int(stu_att or 0),
                    "students_passed": int(stu_pass or 0),
                    "avg_score": round(float(avg_pct or 0.0), 1),
                }
    except Exception as e:
        logger.error("Error en teacher_dashboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        active_section_id = None

    ui = load_ui_strings()
    eval_summary = []
    for sec_key in SECTION_EVAL_MAP:
        agg = eval_agg_map.get(sec_key) or {
            "attempts": 0,
            "students_attempted": 0,
            "students_passed": 0,
            "avg_score": 0.0,
        }
        stu_att = agg["students_attempted"]
        pass_rate = round((agg["students_passed"] / stu_att) * 100) if stu_att > 0 else 0
        eval_summary.append({
            "key": sec_key,
            "label": ui.get(sec_key, sec_key),
            "attempts": agg["attempts"],
            "students_attempted": stu_att,
            "students_passed": agg["students_passed"],
            "pass_rate": pass_rate,
            "avg_score": agg["avg_score"],
        })

    metrics = {
        "total_students": total_scoped_students,
        "active_students": active_count,
        "suspended_students": suspended_count,
        "avg_xp": round(total_xp / total_scoped_students) if total_scoped_students else 0,
        "total_completed": total_completed,
        "total_course_lessons": len(course_ids),
        "level_labels": list(level_counts.keys()),
        "level_data": list(level_counts.values()),
    }

    filters = {
        "q": q,
        "section_id": active_section_id or "",
        "level": level_filter or "",
        "status": status_filter,
        "sort": sort_by,
        "page": page,
        "total_pages": total_pages,
        "total_filtered": total_filtered,
        "per_page": ADMIN_STUDENTS_PER_PAGE,
    }

    return render_template(
        "teacher_dashboard.html",
        students=paginated_students,
        classrooms=classrooms,
        classroom_counts=classroom_counts,
        metrics=metrics,
        filters=filters,
        eval_summary=eval_summary,
        level_titles=LEVEL_TITLES,
        categories=LESSON_CATEGORIES,
    )


@bp.route("/profesor/secciones/crear", methods=["POST"])
@bp.route("/administrador/secciones/crear", methods=["POST"])
@login_required
def admin_create_section():
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    if current_user.role != "teacher":
        if wants_json:
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        return redirect(url_for("dashboard"))

    data = _get_json_dict() if request.is_json else request.form
    name = str(data.get("name") or "").strip()[:100]
    raw_code = str(data.get("code") or "").strip()

    if len(name) < 2:
        msg = "El nombre de la sección debe tener al menos 2 caracteres (ej. PROG1-A)."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    if raw_code:
        code = _normalize_class_code(raw_code)
        if len(code) < 4:
            msg = "El código personalizado debe tener entre 4 y 20 caracteres alfanuméricos."
            if wants_json:
                return jsonify({"ok": False, "error": msg}), 400
            flash(msg, "error")
            return redirect(url_for("teacher_dashboard"))
        if Classroom.query.filter_by(code=code).first():
            msg = f"El código de clase '{code}' ya está en uso. Elige otro o déjalo vacío para generarlo automáticamente."
            if wants_json:
                return jsonify({"ok": False, "error": msg}), 409
            flash(msg, "error")
            return redirect(url_for("teacher_dashboard"))
    else:
        code = _generate_class_code(name)

    try:
        classroom = Classroom(name=name, code=code, teacher_id=current_user.id)
        db.session.add(classroom)
        db.session.flush()
        _log_audit(
            current_user,
            action="CREATE_SECTION",
            target_username=None,
            section_id=classroom.id,
            reason=f"Creación de sección '{name}'",
            details=f"Código de clase: {code}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Error en admin_create_section: %s", e)
        msg = "No se pudo crear la sección. Intenta nuevamente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 500
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    ok_msg = f"Sección '{classroom.name}' creada correctamente. Código para compartir: {classroom.code}"
    if wants_json:
        return jsonify({
            "ok": True,
            "message": ok_msg,
            "section": {"id": classroom.id, "name": classroom.name, "code": classroom.code},
        }), 201
    flash(ok_msg, "success")
    return redirect(url_for("teacher_dashboard"))


@bp.route("/administrador/secciones/<int:section_id>/eliminar", methods=["POST"])
@bp.route("/profesor/secciones/<int:section_id>/eliminar", methods=["POST"])
@login_required
def admin_delete_section(section_id):
    """Permite a un profesor eliminar su propia sección (o al Super Admin eliminar cualquiera) sin borrar estudiantes."""
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    if current_user.role not in ("teacher", "superadmin"):
        if wants_json:
            return jsonify({"ok": False, "error": "No autorizado"}), 403
        return redirect(url_for("dashboard"))

    classroom = db.session.get(Classroom, section_id)
    if not classroom:
        msg = "Sección no encontrada."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 404
        flash(msg, "error")
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    if current_user.role == "teacher" and classroom.teacher_id != current_user.id:
        _log_audit(
            current_user,
            action="UNAUTHORIZED_DELETE_SECTION_ATTEMPT",
            target_username=None,
            section_id=classroom.id,
            reason=f"Intento de eliminar sección ajena '{classroom.name}' ({classroom.code})",
        )
        db.session.commit()
        msg = "Acceso denegado: solo puedes eliminar tus propias secciones."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(url_for("teacher_dashboard"))

    sec_name = classroom.name
    sec_code = classroom.code
    try:
        # Desvincular estudiantes (conservan cuenta, XP e historial intactos) y referencias de auditoría
        detached_students = User.query.filter_by(section_id=classroom.id).update(
            {"section_id": None}, synchronize_session=False
        )
        AuditLog.query.filter_by(section_id=classroom.id).update(
            {"section_id": None}, synchronize_session=False
        )
        db.session.delete(classroom)
        _log_audit(
            current_user,
            action="DELETE_SECTION",
            target_username=None,
            section_id=None,
            reason=f"Eliminación de sección '{sec_name}'",
            details=f"Código: {sec_code} | Estudiantes desvinculados: {detached_students}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error("Error en admin_delete_section: %s", e)
        msg = "No se pudo eliminar la sección. Intenta nuevamente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 500
        flash(msg, "error")
        return redirect(url_for(_home_endpoint_for_role(current_user.role)))

    ok_msg = f"Sección '{sec_name}' ({sec_code}) eliminada. {detached_students} estudiante(s) fueron desvinculados sin perder su progreso."
    if wants_json:
        return jsonify({"ok": True, "message": ok_msg, "detached_students": detached_students})
    flash(ok_msg, "success")
    return redirect(url_for(_home_endpoint_for_role(current_user.role)))


@bp.route("/profesor/estudiante/<int:student_id>/suspender", methods=["POST"])
@bp.route("/administrador/estudiante/<int:student_id>/suspender", methods=["POST"])
@login_required
def admin_suspend_student(student_id):
    """Borrado lógico (suspensión) de estudiante con motivo obligatorio y registro de auditoría."""
    if current_user.role != "teacher":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "").strip()[:500]
    if len(reason) < 5:
        return jsonify({
            "success": False,
            "error": "Debes indicar un motivo obligatorio para suspender al estudiante (mínimo 5 caracteres).",
        }), 400

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404

    if not _teacher_owns_student(current_user.id, student):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_SUSPEND_ATTEMPT",
            target_username=student.username,
            section_id=student.section_id,
            reason=reason,
            details="Intento bloqueado: el estudiante no pertenece a las secciones del docente.",
        )
        db.session.commit()
        return jsonify({
            "success": False,
            "error": "Acceso denegado: este estudiante no pertenece a tus secciones.",
        }), 403

    if getattr(student, "is_suspended", False):
        return jsonify({"success": False, "error": "El estudiante ya se encuentra suspendido."}), 400

    cls = db.session.get(Classroom, student.section_id) if student.section_id else None
    student.is_suspended = True
    student.suspended_at = utcnow()
    student.suspended_reason = reason
    student.suspended_by = current_user.id

    _log_audit(
        current_user,
        action="SUSPEND_STUDENT",
        target_username=student.username,
        section_id=student.section_id,
        reason=reason,
        details=f"Grupo: {cls.name} ({cls.code})" if cls else "Sin sección",
    )
    db.session.commit()
    return jsonify({
        "success": True,
        "status": "suspended",
        "reason": reason,
        "suspended_at": student.suspended_at.strftime("%d/%m/%Y %H:%M"),
    })


@bp.route("/profesor/estudiante/<int:student_id>/restaurar", methods=["POST"])
@bp.route("/administrador/estudiante/<int:student_id>/restaurar", methods=["POST"])
@login_required
def admin_restore_student(student_id):
    """Restaura a un estudiante suspendido conservando intacto todo su progreso e historial."""
    if current_user.role != "teacher":
        return jsonify({"success": False, "error": "No autorizado"}), 403

    data = _get_json_dict() if request.is_json else request.form
    reason = str(data.get("reason") or "Restauración de cuenta por el docente").strip()[:500]

    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404

    if not _teacher_owns_student(current_user.id, student):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_RESTORE_ATTEMPT",
            target_username=student.username,
            section_id=student.section_id,
            reason=reason,
            details="Intento bloqueado: el estudiante no pertenece a las secciones del docente.",
        )
        db.session.commit()
        return jsonify({
            "success": False,
            "error": "Acceso denegado: este estudiante no pertenece a tus secciones.",
        }), 403

    if not getattr(student, "is_suspended", False):
        return jsonify({"success": False, "error": "El estudiante ya se encuentra activo."}), 400

    cls = db.session.get(Classroom, student.section_id) if student.section_id else None
    prev_reason = student.suspended_reason or ""
    student.is_suspended = False
    student.suspended_at = None
    student.suspended_reason = None
    student.suspended_by = None

    _log_audit(
        current_user,
        action="RESTORE_STUDENT",
        target_username=student.username,
        section_id=student.section_id,
        reason=reason,
        details=f"Grupo: {cls.name} ({cls.code}) | Motivo previo: {prev_reason}" if cls else f"Motivo previo: {prev_reason}",
    )
    db.session.commit()
    return jsonify({"success": True, "status": "active"})


@bp.route("/profesor/estudiante/<int:student_id>/eliminar", methods=["POST"])
@bp.route("/administrador/estudiante/<int:student_id>/eliminar", methods=["POST"])
@login_required
def teacher_delete_student(student_id):
    """El borrado físico fue sustituido por suspensión lógica (Soft Delete) con motivo obligatorio."""
    return admin_suspend_student(student_id)


# --- Exportar CSV ---
@bp.route("/profesor/export/csv")
@bp.route("/administrador/export/csv")
@login_required
def teacher_export_csv():
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))

    raw_section = request.args.get("section_id", "").strip()
    section_filter = _safe_int(raw_section, 0) if raw_section else None
    classrooms, _, students_q = _get_teacher_scoped_students(current_user.id, section_filter)
    classroom_map = {c.id: c for c in classrooms}
    students = students_q.all()
    bulk_stats = get_bulk_progress_summaries(students)
    course_ids = _course_lesson_ids()

    si = StringIO()
    si.write('\ufeff')  # Agregamos BOM para que Excel detecte correctamente el UTF-8
    cw = csv.writer(si, delimiter=';')  # Usamos punto y coma que es el separador esperado por Excel en español
    cw.writerow(["Username", "Email", "Seccion", "Estado", "Total_XP", "Lecciones_Completadas", "Nivel", "Racha_Actual", "Fecha_Registro"])

    for s in students:
        stats = bulk_stats.get(s.id, {"completed_lessons": [], "total_xp": 0, "streak": 0})
        lvl_info = get_level_info(stats["total_xp"])
        cls = classroom_map.get(s.section_id)
        completed_cnt = len(set(stats["completed_lessons"]) & course_ids)
        section_label = f"{cls.name} ({cls.code})" if cls else "Sin sección"
        cw.writerow([
            _csv_safe(s.username or ""),
            _csv_safe(s.email or ""),
            _csv_safe(section_label),
            _csv_safe("Suspendido" if getattr(s, "is_suspended", False) else "Activo"),
            stats["total_xp"],
            completed_cnt,
            _csv_safe(lvl_info["title"]),
            stats["streak"],
            _csv_safe(s.created_at.strftime("%Y-%m-%d") if s.created_at else "N/A"),
        ])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_estudiantes.csv"}
    )


@bp.route("/profesor/export/pdf")
@bp.route("/administrador/export/pdf")
@login_required
def admin_export_pdf():
    if current_user.role != "teacher":
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    try:
        from pdf_report import build_admin_report_pdf

        course_ids = _course_lesson_ids()
        total_course = len(course_ids) or 1

        raw_section = request.args.get("section_id", "").strip()
        section_filter = _safe_int(raw_section, 0) if raw_section else None
        _, _, students_q = _get_teacher_scoped_students(current_user.id, section_filter)
        students = students_q.all()
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
            generated_by=current_user.username,
        )
    except Exception as e:
        logger.error("Error en admin_export_pdf (%s): %s", type(e).__name__, e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"ok": False, "error": "No se pudo generar el reporte PDF. Intenta de nuevo."}), 500

    filename = f"reporte_estudiantes_{_app_now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
