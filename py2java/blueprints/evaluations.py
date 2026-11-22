"""Evaluaciones finales por sección (páginas y API)."""

import json
from datetime import timedelta

from flask import flash, jsonify, redirect, render_template, session, url_for
from flask_login import current_user, login_required

from content_loader import get_evaluation_for_section, get_lesson_title, load_ui_strings
from models import (
    EvaluationSession,
    LessonProgress,
    SectionEvaluation,
    db,
    ensure_utc,
    utcnow,
)

from py2java.blueprints import FlatBlueprint

from py2java.extensions import limiter
from py2java.services.curriculum import LESSON_CATEGORIES
from py2java.services.evaluation import (
    EVAL_NETWORK_GRACE_SECONDS,
    SECTION_EVAL_MAP,
    generate_adaptive_questions,
    get_section_eval_status,
    get_section_lessons,
)
from py2java.services.exercises import XP_PER_EVALUATION, _normalize_answer_text
from py2java.services.progress import get_progress_summary, record_daily_activity
from py2java.services.security import _get_json_dict, _safe_int, _user_rate_limit_key

bp = FlatBlueprint("evaluations", __name__)


@bp.route("/evaluacion/<section_key>")
@login_required
def evaluation_page(section_key):
    """Render the adaptive evaluation page for a section."""
    if section_key not in SECTION_EVAL_MAP:
        return redirect(url_for("dashboard"))

    user = current_user
    status = get_section_eval_status(user.id, section_key)

    if not status["unlocked"]:
        return redirect(url_for("dashboard"))

    questions, eval_data = generate_adaptive_questions(section_key, user.id)
    if not eval_data or not questions:
        flash("No hay preguntas disponibles para esta evaluación en este momento.", "error")
        return redirect(url_for("dashboard"))

    # Strip correct answers from questions sent to client (security)
    client_questions = []
    for q in questions:
        cq = {
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "difficulty": q.get("difficulty", "medium"),
            "source_lesson": q.get("source_lesson", ""),
        }
        if q["type"] == "multiple_choice":
            cq["options"] = q["options"]
        elif q["type"] == "complete_code":
            cq["code_template"] = q["code_template"]
        elif q["type"] == "true_false":
            pass  # No extra fields needed
        client_questions.append(cq)

    # Limpiar claves heredadas de evaluaciones en la cookie de sesión
    for k in list(session.keys()):
        if k.startswith("eval_answers_") or k.startswith("eval_questions_"):
            session.pop(k, None)

    # Get section display info
    ui = load_ui_strings()
    section_title = ui.get(section_key, section_key)

    # Time limit: 30s per question, capped at max 10 minutes (600s)
    raw_time = eval_data.get("time_per_question", 30) * len(client_questions)
    time_limit = min(600, raw_time)

    # Invalidar sesiones anteriores no enviadas para esta sección y crear sesión en servidor
    now_utc = utcnow()
    EvaluationSession.query.filter_by(
        user_id=user.id, section_key=section_key, submitted=False
    ).update({"submitted": True}, synchronize_session=False)

    eval_session = EvaluationSession(
        user_id=user.id,
        section_key=section_key,
        question_ids_json=json.dumps([q["id"] for q in questions]),
        started_at=now_utc,
        expires_at=now_utc + timedelta(seconds=time_limit),
        submitted=False,
    )
    db.session.add(eval_session)
    db.session.commit()

    return render_template(
        "evaluation.html",
        section_key=section_key,
        section_title=section_title,
        eval_data=eval_data,
        eval_session_id=eval_session.id,
        questions=client_questions,
        questions_json=json.dumps(client_questions, ensure_ascii=False),
        time_limit=time_limit,
        status=status,
        passing_score=eval_data.get("passing_score", 70),
        categories=LESSON_CATEGORIES,
        page="evaluation",
    )


@bp.route("/api/evaluacion/resultado", methods=["POST"])
@login_required
@limiter.limit("10 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_evaluation_result():
    """Califica una evaluación estrictamente contra la EvaluationSession almacenada en servidor."""
    data = _get_json_dict()
    section_key = data.get("section_key", "")
    answers = data.get("answers", {})
    requested_session_id = _safe_int(data.get("session_id"), 0)

    if not isinstance(section_key, str) or section_key not in SECTION_EVAL_MAP:
        return jsonify({"ok": False, "error": "Sección inválida."}), 400
    if not isinstance(answers, dict):
        return jsonify({"ok": False, "error": "Formato de respuestas inválido."}), 400

    user = current_user
    status = get_section_eval_status(user.id, section_key)
    if not status["unlocked"]:
        return jsonify({
            "ok": False,
            "error": "Debes completar al menos el 80% de las lecciones de la sección antes de presentar la evaluación.",
        }), 403

    eval_data = get_evaluation_for_section(section_key)
    if not eval_data:
        return jsonify({"ok": False, "error": "Evaluación no disponible."}), 404

    if requested_session_id > 0:
        eval_session = EvaluationSession.query.filter_by(
            id=requested_session_id,
            user_id=user.id,
            section_key=section_key,
            submitted=False,
        ).first()
    else:
        eval_session = (
            EvaluationSession.query.filter_by(
                user_id=user.id,
                section_key=section_key,
                submitted=False,
            )
            .order_by(EvaluationSession.started_at.desc())
            .first()
        )

    if not eval_session:
        return jsonify({
            "ok": False,
            "error": "No tienes una sesión de evaluación activa o ya fue enviada. Inicia un nuevo intento.",
        }), 400

    now_utc = utcnow()
    started_at = ensure_utc(eval_session.started_at)
    expires_at = ensure_utc(eval_session.expires_at)

    if now_utc > expires_at + timedelta(seconds=EVAL_NETWORK_GRACE_SECONDS):
        eval_session.submitted = True
        db.session.commit()
        return jsonify({
            "ok": False,
            "error": "El tiempo límite de la evaluación ha expirado. Inicia un nuevo intento.",
        }), 400

    try:
        question_ids = json.loads(eval_session.question_ids_json or "[]")
    except (TypeError, ValueError):
        question_ids = []

    if not isinstance(question_ids, list) or not question_ids:
        eval_session.submitted = True
        db.session.commit()
        return jsonify({"ok": False, "error": "Sesión de evaluación inválida."}), 400

    question_source_map = {}
    catalog_answers = {}
    for lesson_id, qs in eval_data.get("lesson_questions", {}).items():
        for q in qs:
            question_source_map[q["id"]] = lesson_id
            catalog_answers[q["id"]] = (
                q.get("correct_answer") if q.get("type") == "complete_code" else q.get("correct")
            )

    # Calificar SIEMPRE contra el conjunto completo asignado en EvaluationSession
    score = 0
    total = len(question_ids)
    details = {}

    for qid in question_ids:
        correct_val = catalog_answers.get(qid)
        user_answer = answers.get(qid)
        source_lesson = question_source_map.get(qid, "")

        if source_lesson not in details:
            details[source_lesson] = {
                "correct": 0,
                "total": 0,
                "lesson_title": get_lesson_title(source_lesson),
            }

        details[source_lesson]["total"] += 1

        is_correct = False
        if isinstance(correct_val, bool):
            is_correct = isinstance(user_answer, bool) and (user_answer is correct_val)
        elif isinstance(correct_val, int):
            if not isinstance(user_answer, bool) and user_answer is not None:
                try:
                    is_correct = int(user_answer) == correct_val
                except (ValueError, TypeError):
                    is_correct = False
        elif isinstance(correct_val, str):
            if isinstance(user_answer, str):
                is_correct = _normalize_answer_text(user_answer) == _normalize_answer_text(correct_val)

        if is_correct:
            score += 1
            details[source_lesson]["correct"] += 1

    passing_score = _safe_int(eval_data.get("passing_score", 70), 70)
    percentage = round((score / total) * 100, 1) if total > 0 else 0.0
    passed = percentage >= passing_score
    actual_time_taken = max(0, int((now_utc - started_at).total_seconds()))

    # Contar intentos previos y verificar aprobación previa ANTES de insertar el nuevo registro
    prev_attempts = SectionEvaluation.query.filter_by(
        user_id=user.id, section_id=section_key
    ).count()
    already_passed = None
    if passed:
        already_passed = SectionEvaluation.query.filter_by(
            user_id=user.id, section_id=section_key, passed=True
        ).first()

    # Marcar sesión como enviada y guardar resultado real en SectionEvaluation (sin registros sintéticos en LessonProgress)
    eval_session.submitted = True
    evaluation = SectionEvaluation(
        user_id=user.id,
        section_id=section_key,
        score=score,
        total=total,
        percentage=percentage,
        passed=passed,
        time_taken=actual_time_taken,
        attempt_number=prev_attempts + 1,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.session.add(evaluation)

    xp_gained = 0
    if passed and not already_passed:
        xp_gained = XP_PER_EVALUATION
        record_daily_activity(user.id)

    db.session.commit()

    return jsonify({
        "ok": True,
        "score": score,
        "total": total,
        "percentage": percentage,
        "passing_score": passing_score,
        "passed": passed,
        "xp_gained": xp_gained,
        "attempt_number": prev_attempts + 1,
        "details": details,
        "summary": get_progress_summary(user),
    })


@bp.route("/api/evaluacion/estados")
def api_evaluation_statuses():
    """Obtiene el estado de todas las evaluaciones de sección en solo 2 consultas SQL."""
    if not current_user.is_authenticated:
        return jsonify({k: {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0} for k in SECTION_EVAL_MAP})

    user_id = current_user.id
    completed_rows = LessonProgress.query.filter_by(user_id=user_id, completed=True).all()
    completed_set = {r.lesson_id for r in completed_rows}

    eval_rows = SectionEvaluation.query.filter_by(user_id=user_id).all()
    evals_by_sec = {}
    for r in eval_rows:
        evals_by_sec.setdefault(r.section_id, []).append(r)

    results = {}
    for section_key in SECTION_EVAL_MAP:
        lesson_ids = get_section_lessons(section_key)
        if not lesson_ids:
            results[section_key] = {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0}
            continue
        completed_cnt = sum(1 for lid in lesson_ids if lid in completed_set)
        completion_pct = round((completed_cnt / len(lesson_ids)) * 100)
        sec_evals = evals_by_sec.get(section_key, [])
        best_pct = max((e.percentage for e in sec_evals), default=0)
        passed = any(e.passed for e in sec_evals)
        results[section_key] = {
            "unlocked": completion_pct >= 80,
            "passed": passed,
            "best_score": round(best_pct),
            "attempts": len(sec_evals),
            "completion_pct": completion_pct,
            "completed_lessons": completed_cnt,
            "total_lessons": len(lesson_ids),
        }
    return jsonify(results)


@bp.route("/api/evaluacion/estado/<section_key>")
def api_evaluation_status(section_key):
    """Get the evaluation readiness status for a section."""
    if not current_user.is_authenticated:
        return jsonify({"unlocked": False, "passed": False})

    status = get_section_eval_status(current_user.id, section_key)
    return jsonify(status)
