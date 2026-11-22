"""Laboratorio de práctica de código."""

from flask import jsonify, redirect, render_template, url_for
from flask_login import current_user

from content_loader import get_level_info, get_practice_problem, load_practice_problems
from models import PracticeSubmission, db

from py2java.blueprints import FlatBlueprint

from py2java.extensions import limiter
from py2java.services.curriculum import LESSON_CATEGORIES
from py2java.services.exercises import (
    MAX_PRACTICE_CODE_CHARS,
    XP_PER_PRACTICE,
    _validate_practice_code_ast,
)
from py2java.services.progress import get_progress_summary, record_daily_activity
from py2java.services.security import _get_json_dict, _safe_int, _user_rate_limit_key

bp = FlatBlueprint("practice", __name__)


# --- Laboratorio de práctica ---
@bp.route("/practica")
@bp.route("/practice")
def practice_list():
    data = load_practice_problems()
    problems = data.get("problems", [])
    
    # Check completed problems for current user
    completed_ids = []
    if current_user.is_authenticated:
        completed_submissions = PracticeSubmission.query.filter_by(user_id=current_user.id, passed=True).all()
        completed_ids = [sub.problem_id for sub in completed_submissions]
        
    return render_template(
        "practice_list.html",
        problems=problems,
        completed_ids=completed_ids,
        categories=LESSON_CATEGORIES,
        page="practice"
    )


@bp.route("/practica/<problem_id>")
def practice_editor(problem_id):
    problem = get_practice_problem(problem_id)
    if not problem:
        return redirect(url_for("practice_list"))
        
    # Check if previously completed to show starter code or previous answer
    previous_code = problem.get("starter_code", "")
    if current_user.is_authenticated:
        last_submission = PracticeSubmission.query.filter_by(user_id=current_user.id, problem_id=problem_id).order_by(PracticeSubmission.submitted_at.desc()).first()
        if last_submission:
            previous_code = last_submission.code

    return render_template(
        "practice_editor.html",
        problem=problem,
        previous_code=previous_code,
        categories=LESSON_CATEGORIES,
        page="practice"
    )


@bp.route("/api/submit_practice", methods=["POST"])
@limiter.limit("20 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_submit_practice():
    # Visitantes sin sesión pueden ejecutar pruebas en Pyodide, pero no guardar progreso ni XP
    if not current_user.is_authenticated:
        return jsonify({
            "ok": False,
            "anonymous": True,
            "xp_gained": 0,
            "message": "Inicia sesión para guardar tu progreso y ganar XP."
        })

    data = _get_json_dict()
    raw_problem_id = data.get("problem_id")
    problem_id = raw_problem_id.strip() if isinstance(raw_problem_id, str) else ""
    problem = get_practice_problem(problem_id)
    if not problem:
        return jsonify({"ok": False, "error": "Problema de práctica no encontrado en el currículo."}), 400

    raw_code = data.get("code")
    if not isinstance(raw_code, str) or len(raw_code) > MAX_PRACTICE_CODE_CHARS:
        return jsonify({"ok": False, "error": f"El código no puede superar {MAX_PRACTICE_CODE_CHARS} caracteres."}), 400
    code = raw_code

    expected_total = len(problem.get("test_cases") or [])
    raw_passed = data.get("passed", False) is True
    tests_passed = _safe_int(data.get("tests_passed", 0), 0)
    tests_total = _safe_int(data.get("tests_total", 0), 0)

    # Validar estructuralmente la solución en servidor antes de aceptar passed=True
    passed = False
    if raw_passed and expected_total > 0 and tests_total == expected_total and tests_passed == expected_total:
        ast_ok, ast_err = _validate_practice_code_ast(problem, code)
        if not ast_ok:
            return jsonify({"ok": False, "error": ast_err}), 400
        passed = True
    else:
        tests_passed = max(0, min(tests_passed, expected_total))
        tests_total = expected_total

    user = current_user

    # Comprobar si ya fue aprobado previamente ANTES de insertar el nuevo envío
    prev_passed = PracticeSubmission.query.filter_by(
        user_id=user.id, problem_id=problem_id, passed=True
    ).first()

    submission = PracticeSubmission(
        user_id=user.id,
        problem_id=problem_id,
        code=code,
        passed=passed,
        tests_passed=tests_passed,
        tests_total=tests_total,
    )
    db.session.add(submission)

    xp_gained = 0
    if passed and not prev_passed:
        xp_gained = XP_PER_PRACTICE
        record_daily_activity(user.id)

    db.session.commit()

    new_stats = get_progress_summary(user)
    lvl_info = get_level_info(new_stats["total_xp"])

    return jsonify({
        "ok": True,
        "passed": passed,
        "xp_gained": xp_gained,
        "new_total": new_stats["total_xp"],
        "level": lvl_info["level"],
        "title": lvl_info["title"],
        "streak": new_stats["streak"],
    })
