"""Contenido educativo y vistas del estudiante: lecciones, ejercicios, quizzes, ejemplos, progreso y perfil."""

import math

from flask import (
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from content_loader import (
    LESSON_ALIASES,
    get_example_by_id,
    get_lesson,
    get_lesson_title,
    get_level_info,
    load_examples_catalog,
    load_quiz,
    load_ui_strings,
)
from models import (
    Classroom,
    ExerciseAttempt,
    IssuedCertificate,
    LessonProgress,
    QuizResult,
    SectionEvaluation,
    User,
    db,
    ensure_utc,
)

from py2java.blueprints import FlatBlueprint

from py2java.config import logger
from py2java.extensions import limiter
from py2java.services.accounts import get_current_user
from py2java.services.certificates import _format_spanish_date, _get_certificate_context
from py2java.services.timeutils import _get_app_timezone
from py2java.services.classrooms import (
    LEADERBOARD_PER_PAGE,
    _get_teacher_section_ids,
    _log_audit,
    _normalize_class_code,
    _teacher_owns_student,
)
from py2java.services.curriculum import (
    LESSONS,
    LESSON_CATEGORIES,
    REFERENCE_CATEGORIES,
    _category_course_lessons,
    _course_lesson_ids,
    get_lesson_category,
    get_lesson_neighbors,
)
from py2java.services.exercises import (
    PASSED_AFTER_SOLUTION_MARKER,
    SOLUTION_VIEWED_MARKER,
)
from py2java.services.progress import (
    _build_student_stats_subqueries,
    _get_bulk_streaks,
    get_progress_summary,
)
from py2java.services.security import (
    _extract_relative_from_referrer,
    _get_json_dict,
    _get_safe_next_url,
    _safe_int,
)

bp = FlatBlueprint("lessons", __name__)


@bp.route("/sw.js")
def service_worker():
    """Sirve el Service Worker desde la raíz con scope global '/'."""
    response = send_from_directory(
        current_app.static_folder,
        "sw.js",
        mimetype="application/javascript",
    )
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.route("/")
def index():
    return render_template(
        "welcome.html",
        page="welcome",
        categories=LESSON_CATEGORIES,
        total_lessons=len(_course_lesson_ids()),
    )


@bp.route("/leccion/<lesson_id>")
def lesson(lesson_id):
    lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    if lesson_id.startswith("quiz-"):
        return redirect(url_for("quiz", topic=lesson_id))
    if lesson_id == "practice-hub":
        return redirect(url_for("practice_list"))
    if lesson_id == "examples-hub":
        return redirect(url_for("examples"))
    if lesson_id.startswith("ex-"):
        return redirect(url_for("exercise_topic", topic=lesson_id))

    valid_ids = [lesson_item["id"] for lesson_item in LESSONS]
    if lesson_id not in valid_ids:
        abort(404)
    prev_lesson, next_lesson = get_lesson_neighbors(lesson_id)
    current_category = get_lesson_category(lesson_id)
    current_category_id = current_category["id"] if current_category else "py2java"

    # Verificar prerrequisito y estado de completado de la lección actual
    prereq_warning = False
    prereq_lesson_id = None
    prereq_lesson_title = None
    is_course_lesson = lesson_id in _course_lesson_ids()
    lesson_completed = False
    is_external_db_lesson = lesson_id.startswith(("sql-", "mongo-"))
    try:
        user = get_current_user()
        if user and user.id:
            if is_course_lesson:
                lesson_completed = (
                    LessonProgress.query.filter_by(
                        user_id=user.id, lesson_id=lesson_id, completed=True
                    ).first()
                    is not None
                )
            if prev_lesson and lesson_id != "py-home" and prev_lesson in _course_lesson_ids():
                prev_completed = LessonProgress.query.filter_by(
                    user_id=user.id, lesson_id=prev_lesson, completed=True
                ).first()
                if not prev_completed:
                    prereq_warning = True
                    prereq_lesson_id = prev_lesson
                    prereq_lesson_title = get_lesson_title(prev_lesson) or prev_lesson
    except Exception as e:
        logger.warning("Prerequisite/completion check failed (DB issue): %s", e)
        db.session.rollback()

    return render_template(
        "lesson.html",
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        current_lesson=lesson_id,
        current_category=current_category_id,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        prereq_warning=prereq_warning,
        prereq_lesson_id=prereq_lesson_id,
        prereq_lesson_title=prereq_lesson_title,
        is_course_lesson=is_course_lesson,
        lesson_completed=lesson_completed,
        is_external_db_lesson=is_external_db_lesson,
        page="lesson",
        role=session.get("role", "student"),
    )


# --- Glosario ---
@bp.route("/glosario")
def glossary():
    return render_template(
        "glossary.html",
        categories=LESSON_CATEGORIES,
        page="glossary",
    )


@bp.route("/referencia")
def reference():
    return render_template(
        "reference.html",
        lessons=LESSONS,
        categories=LESSON_CATEGORIES,
        ref_categories=REFERENCE_CATEGORIES,
        current_category="",
        page="reference",
        role=session.get("role", "student"),
    )


@bp.route("/traductor")
def traductor():
    return render_template(
        "translator.html", categories=LESSON_CATEGORIES, page="translator"
    )


@bp.route("/ejercicios/<topic>")
def exercise_topic(topic):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
    
    exercises = lesson_data.get("exercises", [])
    user = get_current_user()
    completed_exercises = []
    completed_count = 0
    
    if user and user.is_authenticated:
        attempts = ExerciseAttempt.query.filter_by(user_id=user.id, lesson_id=topic, passed=True).all()
        completed_set = {a.exercise_id for a in attempts} | {f"{a.lesson_id}-{a.exercise_id}" for a in attempts}
        completed_exercises = list(completed_set)
        for idx, ex in enumerate(exercises, start=1):
            ex_id = ex.get("id")
            if (ex_id and ex_id in completed_set) or f"{topic}-{idx}" in completed_set:
                completed_count += 1
        
    return render_template(
        "exercise_hub.html",
        topic=topic,
        exercise_data=lesson_data,
        exercises=exercises,
        completed_exercises=completed_exercises,
        completed_count=completed_count,
        categories=LESSON_CATEGORIES,
        page="exercises"
    )


@bp.route("/ejercicio/<topic>/<int:exercise_num>")
def exercise_page(topic, exercise_num):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
        
    exercises = lesson_data.get("exercises", [])
    if exercise_num < 1 or exercise_num > len(exercises):
        return redirect(url_for("exercise_topic", topic=topic))
        
    current_exercise = exercises[exercise_num - 1]
    
    return render_template(
        "exercise.html",
        topic=topic,
        exercise_data=lesson_data,
        current_exercise=current_exercise,
        exercise_num=exercise_num,
        total_exercises=len(exercises),
        categories=LESSON_CATEGORIES,
        page="exercises"
    )


@bp.route("/quiz/<topic>")
def quiz(topic):
    quiz_data = load_quiz(topic)
    if not quiz_data:
        return redirect(url_for("index"))
        
    return render_template(
        "quiz.html",
        quiz_data=quiz_data,
        categories=LESSON_CATEGORIES,
        page="quiz"
    )


@bp.route("/ejemplos")
def examples():
    catalog = load_examples_catalog()
    return render_template(
        "examples.html",
        example_categories=catalog.get("categories", []),
        categories=LESSON_CATEGORIES,
        page="examples"
    )


@bp.route("/ejemplo/<example_id>")
def example_detail(example_id):
    example = get_example_by_id(example_id)
    if not example:
        return redirect(url_for("examples"))
        
    return render_template(
        "example_detail.html",
        example=example,
        categories=LESSON_CATEGORIES,
        page="examples"
    )


@bp.route("/dashboard")
@login_required
def dashboard():
    summary = get_progress_summary(current_user)
    course_ids = _course_lesson_ids()
    completed_set = set(summary["completed_lessons"])
    completed_course_count = len(completed_set & course_ids)

    ui = load_ui_strings()
    category_breakdown = []
    for cat in LESSON_CATEGORIES:
        for sec in cat.get("sections", []):
            sec_lessons = [
                lesson_item["id"]
                for lesson_item in sec.get("lessons", [])
                if lesson_item["id"] in course_ids
            ]
            if not sec_lessons:
                continue
            done_cnt = sum(1 for lid in sec_lessons if lid in completed_set)
            total_cnt = len(sec_lessons)
            category_breakdown.append({
                "id": sec["label_key"],
                "name": ui.get(sec["label_key"], sec["label_key"]),
                "completed": done_cnt,
                "total": total_cnt,
                "pct": round(done_cnt / total_cnt * 100) if total_cnt > 0 else 0,
            })

    return render_template(
        "dashboard.html",
        user=current_user,
        classroom=current_user.classroom,
        summary=summary,
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        course_lesson_count=len(course_ids),
        completed_course_count=completed_course_count,
        category_breakdown=category_breakdown,
        page="dashboard",
    )


@bp.route("/estudiante/unirse-seccion", methods=["POST"])
@login_required
@limiter.limit("10 per minute; 30 per hour", methods=["POST"])
def student_join_section():
    """Permite a un estudiante unirse (o cambiarse) a una sección mediante código de clase."""
    wants_json = request.is_json or "application/json" in (request.headers.get("Accept") or "")
    raw_next = (request.form.get("next") or "").strip() or _extract_relative_from_referrer(request.referrer)
    safe_next = _get_safe_next_url(raw_next, default=url_for("dashboard"))

    if current_user.role != "student":
        msg = "Solo los estudiantes pueden inscribirse en una sección."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(safe_next)

    raw_code = (_get_json_dict().get("class_code") if request.is_json else request.form.get("class_code")) or ""
    code = _normalize_class_code(raw_code)
    if not code:
        msg = "Debes ingresar un código de clase válido."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "error")
        return redirect(safe_next)

    classroom = Classroom.query.filter_by(code=code).first()
    if not classroom:
        msg = f"El código de clase '{code}' no existe. Verifica el código con tu docente."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 404
        flash(msg, "error")
        return redirect(safe_next)

    teacher = db.session.get(User, classroom.teacher_id)
    if not teacher or getattr(teacher, "is_suspended", False):
        msg = "No puedes unirte a esta sección porque la cuenta del docente se encuentra suspendida o inactiva."
        if wants_json:
            return jsonify({"ok": False, "error": msg}), 403
        flash(msg, "error")
        return redirect(safe_next)

    current_user.section_id = classroom.id
    _log_audit(
        current_user,
        action="STUDENT_JOIN_SECTION",
        target_username=current_user.username,
        section_id=classroom.id,
        reason="Inscripción por código de clase",
        details=f"Sección: {classroom.name} ({classroom.code})",
    )
    db.session.commit()

    ok_msg = f"Te has unido correctamente a la sección {classroom.name} ({classroom.code})."
    if wants_json:
        return jsonify({
            "ok": True,
            "message": ok_msg,
            "section": {"id": classroom.id, "name": classroom.name, "code": classroom.code},
        })
    flash(ok_msg, "success")
    return redirect(safe_next)


@bp.route("/roadmap")
@login_required
def roadmap():
    summary = get_progress_summary(current_user)
    course_ids = _course_lesson_ids()
    completed_course_count = len(set(summary["completed_lessons"]) & course_ids)
    return render_template(
        "roadmap.html",
        categories=LESSON_CATEGORIES,
        summary=summary,
        course_lesson_ids=course_ids,
        course_lesson_count=len(course_ids),
        completed_course_count=completed_course_count,
        page="roadmap",
    )


# --- Tabla de posiciones ---
@bp.route("/leaderboard")
def leaderboard():
    board = []
    podium = []
    db_error = False
    teacher_section_ids = set()
    page_num = max(1, _safe_int(request.args.get("page", 1), 1))
    total_pages = 1
    total_students = 0
    try:
        if current_user.is_authenticated and current_user.role == "teacher":
            teacher_section_ids = _get_teacher_section_ids(current_user.id)

        active_students_select = db.select(User.id).where(
            User.role == "student",
            User.is_suspended.is_(False),
        )
        lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr = (
            _build_student_stats_subqueries(active_students_select)
        )
        base_q = (
            db.session.query(User)
            .outerjoin(lp_sub, lp_sub.c.user_id == User.id)
            .outerjoin(ex_sub, ex_sub.c.user_id == User.id)
            .outerjoin(pr_sub, pr_sub.c.user_id == User.id)
            .outerjoin(ev_sub, ev_sub.c.user_id == User.id)
            .filter(User.role == "student", User.is_suspended.is_(False))
        )

        total_students = int(base_q.with_entities(func.count(User.id)).scalar() or 0)
        total_pages = max(1, math.ceil(total_students / LEADERBOARD_PER_PAGE))
        if page_num > total_pages:
            page_num = total_pages

        ordered_q = base_q.with_entities(
            User,
            completed_expr.label("completed_cnt"),
            total_xp_expr.label("total_xp"),
        ).order_by(
            total_xp_expr.desc(),
            completed_expr.desc(),
            func.lower(User.username).asc(),
            User.id.asc(),
        )

        offset = (page_num - 1) * LEADERBOARD_PER_PAGE
        page_rows = ordered_q.offset(offset).limit(LEADERBOARD_PER_PAGE).all()
        page_streaks = _get_bulk_streaks([s.id for s, _, _ in page_rows])

        def _row_to_entry(s, completed_val, xp_val, rank_num, streak_val):
            xp_int = int(xp_val or 0)
            lvl_info = get_level_info(xp_int)
            can_view_profile = bool(
                current_user.is_authenticated
                and (
                    s.id == current_user.id
                    or current_user.role == "superadmin"
                    or (current_user.role == "teacher" and s.section_id in teacher_section_ids)
                )
            )
            return {
                "id": s.id,
                "username": s.username or "Anónimo",
                "total_xp": xp_int,
                "level": lvl_info["level"],
                "completed": int(completed_val or 0),
                "streak": streak_val,
                "can_view_profile": can_view_profile,
                "rank": rank_num,
            }

        for idx, (s, completed_val, xp_val) in enumerate(page_rows):
            board.append(
                _row_to_entry(s, completed_val, xp_val, offset + idx + 1, page_streaks.get(s.id, 0))
            )

        if page_num == 1:
            podium = board[:3]
        elif total_students >= 3:
            top3_rows = ordered_q.limit(3).all()
            podium = [
                _row_to_entry(s, comp_val, xp_val, i + 1, 0)
                for i, (s, comp_val, xp_val) in enumerate(top3_rows)
            ]
    except Exception as e:
        logger.error("Error en leaderboard: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        db_error = True

    current_uid = current_user.id if current_user.is_authenticated else None
    return render_template(
        "leaderboard.html",
        board=board,
        podium=podium,
        page_num=page_num,
        total_pages=total_pages,
        total_students=total_students,
        current_uid=current_uid,
        categories=LESSON_CATEGORIES,
        page="leaderboard",
        db_error=db_error,
    )


# --- Perfil de usuario ---
@bp.route("/perfil")
@bp.route("/perfil/<username>")
@login_required
def profile(username=None):
    if username:
        user = (
            User.query.filter_by(username=username).first()
            or User.query.filter(func.lower(User.username) == username.lower()).first_or_404()
        )
    else:
        user = current_user

    is_own_profile = current_user.id == user.id
    is_superadmin = current_user.role == "superadmin"
    is_owning_teacher = (
        current_user.role == "teacher"
        and _teacher_owns_student(current_user.id, user)
    )

    if not (is_own_profile or is_superadmin or is_owning_teacher):
        _log_audit(
            current_user,
            action="UNAUTHORIZED_PROFILE_VIEW",
            target_username=user.username,
            section_id=user.section_id,
            reason="Intento de acceso a perfil sin autorización",
        )
        db.session.commit()
        return Response(
            "Acceso denegado: no tienes permisos para ver este perfil.",
            status=403,
            mimetype="text/plain",
        )

    can_view_class_code = is_own_profile or is_superadmin or is_owning_teacher

    summary = get_progress_summary(user)
    level = get_level_info(summary["total_xp"])["level"]

    # Últimas lecciones completadas y estadísticas
    recent = []
    quiz_results = []
    eval_results = []
    total_exercises = 0
    passed_exercises = 0

    try:
        course_ids = _course_lesson_ids()
        recent = (
            LessonProgress.query.filter(
                LessonProgress.user_id == user.id,
                LessonProgress.completed == True,
                LessonProgress.lesson_id.in_(course_ids),
            )
            .order_by(LessonProgress.completed_at.desc())
            .limit(10)
            .all()
        )
        quiz_results = (
            QuizResult.query.filter_by(user_id=user.id)
            .order_by(QuizResult.completed_at.desc())
            .limit(10)
            .all()
        )
        eval_results = (
            SectionEvaluation.query.filter_by(user_id=user.id)
            .order_by(SectionEvaluation.completed_at.desc())
            .limit(15)
            .all()
        )
        total_exercises = ExerciseAttempt.query.filter(
            ExerciseAttempt.user_id == user.id,
            or_(
                ExerciseAttempt.answer.is_(None),
                ExerciseAttempt.answer.notin_((SOLUTION_VIEWED_MARKER, PASSED_AFTER_SOLUTION_MARKER)),
            ),
        ).count()
        passed_exercises = ExerciseAttempt.query.filter_by(user_id=user.id, passed=True).count()
    except Exception as e:
        logger.error("Error en profile queries: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass

    ui = load_ui_strings()
    completed_set = set(summary["completed_lessons"])
    cert_cards = []
    for cat in LESSON_CATEGORIES:
        cat_lessons = _category_course_lessons(cat)
        done_cnt = sum(1 for lid in cat_lessons if lid in completed_set)
        cert_cards.append({
            "id": cat["id"],
            "name": ui.get(cat["label_key"], cat["id"]),
            "completed": done_cnt,
            "total": len(cat_lessons),
            "is_complete": done_cnt >= len(cat_lessons) and len(cat_lessons) > 0,
        })

    return render_template(
        "profile.html",
        profile_user=user,
        classroom=user.classroom,
        is_own_profile=is_own_profile,
        can_view_class_code=can_view_class_code,
        summary=summary,
        level=level,
        recent=recent,
        quiz_results=quiz_results,
        eval_results=eval_results,
        total_exercises=total_exercises,
        passed_exercises=passed_exercises,
        cert_cards=cert_cards,
        categories=LESSON_CATEGORIES,
        page="profile",
    )


# --- Certificado ---
@bp.route("/certificado/<section_id>")
@login_required
def certificate(section_id):
    ctx = _get_certificate_context(current_user, section_id)
    if not ctx:
        return redirect(url_for("dashboard"))

    return render_template(
        "certificate.html",
        user=current_user,
        categories=LESSON_CATEGORIES,
        **ctx,
    )


@bp.route("/certificado/<section_id>/pdf")
@login_required
def certificate_pdf(section_id):
    ctx = _get_certificate_context(current_user, section_id)
    if not ctx:
        return redirect(url_for("dashboard"))
    if not ctx["is_complete"]:
        return redirect(url_for("certificate", section_id=section_id))

    try:
        from pdf_report import build_certificate_pdf

        verify_url = url_for("verify_certificate", codigo=ctx["verification_code"], _external=True)
        pdf_bytes = build_certificate_pdf(
            username=current_user.username,
            category_name=ctx["category_name"],
            category_id=ctx["category_id"],
            user_id=current_user.id,
            total_lessons=ctx["total_lessons"],
            completion_date=ctx["completion_date"],
            completion_year=ctx["completion_year"],
            site_title=ctx["site_title"],
            verification_code=ctx["verification_code"],
            verify_url=verify_url,
        )
    except Exception as e:
        logger.error("Error en certificate_pdf (%s): %s", type(e).__name__, e)
        return jsonify({"ok": False, "error": "No se pudo generar el certificado PDF."}), 500

    safe_user = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch in ("_", "-")) else "_"
        for ch in (current_user.username or "estudiante")
    ).strip("_") or "estudiante"
    filename = f"certificado_{section_id}_{safe_user}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.route("/certificado/verificar/<codigo>")
def verify_certificate(codigo):
    """Ruta pública para verificar autenticidad de un certificado emitido (sin exponer PII)."""
    clean_code = (codigo or "").strip().upper()[:64]
    cert = (
        IssuedCertificate.query.filter_by(verification_code=clean_code).first()
        if clean_code
        else None
    )
    if not cert:
        return (
            render_template(
                "certificate_verify.html",
                valid=False,
                searched_code=clean_code,
                categories=LESSON_CATEGORIES,
            ),
            404,
        )

    owner = db.session.get(User, cert.user_id)
    recipient_name = owner.username if owner else "Estudiante"
    issued_local = ensure_utc(cert.issued_at).astimezone(_get_app_timezone())
    issued_date_str = _format_spanish_date(issued_local)

    return render_template(
        "certificate_verify.html",
        valid=True,
        cert=cert,
        recipient_name=recipient_name,
        issued_date_str=issued_date_str,
        categories=LESSON_CATEGORIES,
    )
