"""API JSON: progreso, ejercicios, quizzes, búsqueda, traducción, tema, tutor IA y diagnóstico."""

import json

import requests as http_requests
from flask import jsonify, request, session
from flask_login import current_user, login_required

from content_loader import LESSON_ALIASES, get_lesson_exercise, load_lesson, load_quiz
from models import ExerciseAttempt, LessonProgress, QuizResult, User, db, utcnow
from search_index import search_lessons
from translator import translate

from py2java.blueprints import FlatBlueprint

from py2java.config import is_postgres, logger
from py2java.extensions import limiter
from py2java.services.accounts import get_current_user
from py2java.services.ai_tutor import (
    AI_TUTOR_MAX_CODE_CHARS,
    AI_TUTOR_MAX_EXERCISE_Q_CHARS,
    AI_TUTOR_MAX_HISTORY_ENTRY_CHARS,
    AI_TUTOR_MAX_HISTORY_ITEMS,
    AI_TUTOR_MAX_HISTORY_TOTAL_CHARS,
    AI_TUTOR_MAX_QUESTION_CHARS,
    GEMINI_API_KEY,
    GEMINI_API_URL,
)
from py2java.services.curriculum import _course_lesson_ids
from py2java.services.exercises import (
    PASSED_AFTER_SOLUTION_MARKER,
    SOLUTION_VIEWED_MARKER,
    XP_PER_EXERCISE,
    XP_PER_LESSON,
    _get_exercise_solution,
    _grade_exercise_submission,
)
from py2java.services.progress import get_progress_summary, record_daily_activity
from py2java.services.security import _get_json_dict, _safe_int, _user_rate_limit_key

bp = FlatBlueprint("api", __name__)


@bp.route("/api/traducir", methods=["POST"])
def api_translate():
    data = _get_json_dict()
    raw_code = data.get("code", "")
    python_code = raw_code if isinstance(raw_code, str) else ""
    raw_cls = data.get("class_name", "Program")
    class_name = raw_cls if isinstance(raw_cls, str) and raw_cls.strip() else "Program"

    result = translate(python_code, class_name=class_name)

    return jsonify(result)


@bp.route("/api/progreso/ejercicio", methods=["POST"])
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_ejercicio():
    """Evalúa un ejercicio en el servidor contra content_loader y registra progreso/XP si corresponde."""
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = raw_lesson.strip() if isinstance(raw_lesson, str) else ""
    raw_ex = data.get("exercise_id")
    exercise_id = raw_ex.strip() if isinstance(raw_ex, str) else ""
    lang = data.get("lang", "python")
    if lang not in ("python", "java"):
        lang = "python"

    lesson_data, exercise = get_lesson_exercise(lesson_id, exercise_id)
    if not lesson_data or not exercise:
        return jsonify({"ok": False, "error": "Lección o ejercicio no encontrado en el currículo."}), 400

    canonical_lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    canonical_exercise_id = exercise.get("id") or exercise_id

    # El servidor califica estrictamente la respuesta (ignora cualquier 'passed' del cliente)
    raw_answer = data.get("answer")
    raw_answers = data.get("answers")
    raw_actual_output = data.get("actual_output")
    passed, verdict = _grade_exercise_submission(
        exercise, lang, raw_answer, raw_answers, raw_actual_output=raw_actual_output
    )

    viewed_in_session = set(session.get("viewed_solutions") or [])
    user = get_current_user()
    if not user or not user.id:
        return jsonify({
            "ok": True,
            "anonymous": True,
            "passed": passed,
            "xp_gained": 0,
            "xp_blocked_by_solution": bool(passed and canonical_exercise_id in viewed_in_session),
            **verdict,
        })

    prev_passed = ExerciseAttempt.query.filter_by(
        user_id=user.id, exercise_id=canonical_exercise_id, passed=True
    ).first()

    solution_viewed_db = (
        ExerciseAttempt.query.filter_by(
            user_id=user.id,
            exercise_id=canonical_exercise_id,
            answer=SOLUTION_VIEWED_MARKER,
        ).first()
        is not None
    )
    solution_viewed = (not prev_passed) and (
        solution_viewed_db or canonical_exercise_id in viewed_in_session
    )
    xp_blocked_by_solution = bool(passed and solution_viewed)

    submitted_repr = raw_answers if raw_answers is not None else raw_answer
    try:
        answer_str = json.dumps(submitted_repr, ensure_ascii=False)[:1000]
    except (TypeError, ValueError):
        answer_str = str(submitted_repr)[:1000]

    # Si el usuario consultó "Ver Solución" antes de aprobar por cuenta propia, no se otorga XP ni passed=True
    if xp_blocked_by_solution:
        attempt = ExerciseAttempt(
            user_id=user.id,
            lesson_id=canonical_lesson_id,
            exercise_id=canonical_exercise_id,
            passed=False,
            answer=PASSED_AFTER_SOLUTION_MARKER,
        )
    else:
        attempt = ExerciseAttempt(
            user_id=user.id,
            lesson_id=canonical_lesson_id,
            exercise_id=canonical_exercise_id,
            passed=passed,
            answer=answer_str,
        )
    db.session.add(attempt)

    xp_gained = 0
    if passed and not xp_blocked_by_solution:
        if not prev_passed:
            xp_gained = XP_PER_EXERCISE
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify({
        "ok": True,
        "anonymous": False,
        "passed": passed,
        "xp_gained": xp_gained,
        "xp_blocked_by_solution": xp_blocked_by_solution,
        "summary": get_progress_summary(user),
        **verdict,
    })


@bp.route("/api/ejercicio/solucion", methods=["POST"])
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_exercise_solution():
    """Devuelve la solución pedagógica de un ejercicio y bloquea el +25 XP si aún no fue aprobado."""
    data = _get_json_dict()
    lesson_id = data.get("lesson_id", "").strip() if isinstance(data.get("lesson_id"), str) else ""
    exercise_id = data.get("exercise_id", "").strip() if isinstance(data.get("exercise_id"), str) else ""
    lang = data.get("lang", "python")
    if lang not in ("python", "java"):
        lang = "python"

    lesson_data, exercise = get_lesson_exercise(lesson_id, exercise_id)
    if not lesson_data or not exercise:
        return jsonify({"ok": False, "error": "Ejercicio no encontrado."}), 400

    canonical_lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    canonical_exercise_id = exercise.get("id") or exercise_id

    viewed_list = list(session.get("viewed_solutions") or [])
    if canonical_exercise_id not in viewed_list:
        viewed_list.append(canonical_exercise_id)
        session["viewed_solutions"] = viewed_list[-200:]

    xp_blocked = True
    user = get_current_user()
    if user and user.id:
        already_passed = (
            ExerciseAttempt.query.filter_by(
                user_id=user.id, exercise_id=canonical_exercise_id, passed=True
            ).first()
            is not None
        )
        if already_passed:
            xp_blocked = False
        else:
            already_marked = (
                ExerciseAttempt.query.filter_by(
                    user_id=user.id,
                    exercise_id=canonical_exercise_id,
                    answer=SOLUTION_VIEWED_MARKER,
                ).first()
                is not None
            )
            if not already_marked:
                db.session.add(
                    ExerciseAttempt(
                        user_id=user.id,
                        lesson_id=canonical_lesson_id,
                        exercise_id=canonical_exercise_id,
                        passed=False,
                        answer=SOLUTION_VIEWED_MARKER,
                    )
                )
                db.session.commit()

    return jsonify({"ok": True, "xp_blocked": xp_blocked, **_get_exercise_solution(exercise, lang)})


@bp.route("/api/progreso/leccion", methods=["POST"])
@login_required
@limiter.limit("30 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_leccion():
    data = _get_json_dict()
    raw_lesson = data.get("lesson_id")
    lesson_id = raw_lesson.strip() if isinstance(raw_lesson, str) else ""
    lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)

    course_ids = _course_lesson_ids()
    if not lesson_id or lesson_id not in course_ids or load_lesson(lesson_id) is None:
        return jsonify({"ok": False, "error": "Lección inválida o no perteneciente al currículo."}), 400

    user = current_user
    lp = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson_id).first()

    xp_gained = 0
    if not lp:
        lp = LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            completed=True,
            score=XP_PER_LESSON,
            completed_at=utcnow(),
        )
        db.session.add(lp)
        xp_gained = XP_PER_LESSON
    elif not lp.completed:
        lp.completed = True
        lp.completed_at = utcnow()
        lp.score = XP_PER_LESSON
        xp_gained = XP_PER_LESSON

    if xp_gained > 0:
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


@bp.route("/api/progreso/resumen", methods=["GET"])
def api_resumen():
    user = get_current_user()
    summary = get_progress_summary(user)
    summary["authenticated"] = bool(user and getattr(user, "id", None))
    return jsonify(summary)


@bp.route("/api/buscar", methods=["GET"])
def api_buscar():
    q = request.args.get("q", "")
    results = search_lessons(q)
    return jsonify(results)


@bp.route("/api/db-status")
@login_required
def api_db_status():
    """Diagnóstico operativo de la base de datos (exclusivo para Super Admin, solo lectura)."""
    if current_user.role != "superadmin":
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    status = {
        "ok": False,
        "db_type": "postgresql" if is_postgres else "sqlite",
        "table_count": 0,
        "user_count": 0,
        "error": None,
    }

    try:
        db.session.execute(db.text("SELECT 1"))
        status["table_count"] = len(db.metadata.tables)
        status["user_count"] = User.query.count()
        status["ok"] = True
        return jsonify(status), 200
    except Exception as e:
        logger.error("Error en api_db_status: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        status["error"] = "Error de conexión con la base de datos. Revisa los registros del servidor."
        return jsonify(status), 503


# --- Tema visual ---
@bp.route("/api/theme", methods=["POST"])
def toggle_theme():
    data = _get_json_dict()
    theme = data.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"
    session["theme"] = theme
    return jsonify({"ok": True, "theme": theme})


@bp.route("/api/ai/tutor", methods=["POST"])
@login_required
@limiter.limit("15 per minute; 100 per hour", methods=["POST"], key_func=_user_rate_limit_key)
def api_ai_tutor():
    if not GEMINI_API_KEY:
        return jsonify(
            {"ok": False, "error": "El servicio de Tutor IA no está disponible en este momento."}
        ), 503

    data = _get_json_dict()
    raw_code = data.get("code", "")
    if not isinstance(raw_code, str):
        return jsonify({"ok": False, "error": "Formato de código inválido."}), 400
    if len(raw_code) > AI_TUTOR_MAX_CODE_CHARS:
        return jsonify(
            {"ok": False, "error": f"El código supera el límite máximo permitido ({AI_TUTOR_MAX_CODE_CHARS} caracteres)."}
        ), 400
    user_code = raw_code

    raw_q = data.get("question", "")
    if not isinstance(raw_q, str):
        return jsonify({"ok": False, "error": "Formato de pregunta inválido."}), 400
    question = raw_q.strip()
    if len(question) > AI_TUTOR_MAX_QUESTION_CHARS:
        return jsonify(
            {"ok": False, "error": f"La pregunta supera el límite máximo permitido ({AI_TUTOR_MAX_QUESTION_CHARS} caracteres)."}
        ), 400

    raw_ex_q = data.get("exercise_question", "")
    if not isinstance(raw_ex_q, str):
        return jsonify({"ok": False, "error": "Formato de enunciado inválido."}), 400
    if len(raw_ex_q) > AI_TUTOR_MAX_EXERCISE_Q_CHARS:
        return jsonify(
            {"ok": False, "error": f"El enunciado supera el límite máximo permitido ({AI_TUTOR_MAX_EXERCISE_Q_CHARS} caracteres)."}
        ), 400
    exercise_question = raw_ex_q.strip()

    raw_lesson = data.get("lesson_id", "")
    lesson_id = raw_lesson.strip()[:60] if isinstance(raw_lesson, str) else ""

    raw_mode = data.get("mode")
    mode = raw_mode.strip() if isinstance(raw_mode, str) and raw_mode.strip() else ("chat" if question else "analyze")
    if mode not in ("chat", "analyze", "hint"):
        return jsonify({"ok": False, "error": "Modo de tutoría inválido."}), 400

    history = data.get("history", [])
    if history is None:
        history = []
    if not isinstance(history, list):
        return jsonify({"ok": False, "error": "El historial de conversación debe ser una lista."}), 400
    if len(history) > AI_TUTOR_MAX_HISTORY_ITEMS:
        return jsonify(
            {"ok": False, "error": f"El historial supera el máximo permitido ({AI_TUTOR_MAX_HISTORY_ITEMS} mensajes)."}
        ), 400

    history_context = ""
    if history:
        history_lines = []
        total_hist_chars = 0
        for h in history[-4:]:
            if not isinstance(h, dict):
                return jsonify({"ok": False, "error": "Entrada inválida en el historial."}), 400
            raw_txt = h.get("text", "")
            if not isinstance(raw_txt, str):
                return jsonify({"ok": False, "error": "Texto inválido en el historial."}), 400
            txt = raw_txt.strip()
            if len(txt) > AI_TUTOR_MAX_HISTORY_ENTRY_CHARS:
                return jsonify(
                    {"ok": False, "error": f"Cada mensaje del historial no puede superar {AI_TUTOR_MAX_HISTORY_ENTRY_CHARS} caracteres."}
                ), 400
            if txt:
                total_hist_chars += len(txt)
                if total_hist_chars > AI_TUTOR_MAX_HISTORY_TOTAL_CHARS:
                    return jsonify(
                        {"ok": False, "error": f"El tamaño total del historial supera el máximo permitido ({AI_TUTOR_MAX_HISTORY_TOTAL_CHARS} caracteres)."}
                    ), 400
                role = "Estudiante" if h.get("role") == "user" else "Tutor IA"
                history_lines.append(f"{role}: {txt}")
        if history_lines:
            history_context = "Historial reciente de la conversación:\n" + "\n".join(history_lines) + "\n\n"

    # Cargar contexto únicamente si la lección existe en el currículo
    lesson_data = load_lesson(lesson_id) if lesson_id else None
    lesson_title = lesson_data.get("title", "Python y Java") if lesson_data else "Python y Java"
    lesson_intro = lesson_data.get("intro", "") if lesson_data else ""

    if mode == "hint":
        system_prompt = f"""Eres un tutor de programación amigable y pedagógico para estudiantes que aprenden Python y Java.
Estás ayudando con un ejercicio de la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS ESTRICTAS:
- NUNCA des la respuesta directa ni el código resuelto completo al ejercicio.
- Da pistas progresivas y conceptuales que guíen al estudiante para que lo resuelva por sí mismo.
- Usa analogías simples y comprensibles.
- Responde en español de forma completa y concisa (máximo 3-4 oraciones).
- Concluye siempre tu idea para que la respuesta nunca quede cortada."""
        user_message = f"Pregunta del ejercicio: {exercise_question}\n\nIntento/código del estudiante: {user_code}\n\nDuda del estudiante: {question if question else 'No entiendo cómo resolverlo'}"

    elif mode == "chat" or question:
        system_prompt = f"""Eres un tutor de programación inteligente, didáctico y amigable para estudiantes de Python y Java.
Estás en la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS PRINCIPALES:
- Responde DIRECTA, CLARA y CONCRETAMENTE a la PREGUNTA o DUDA planteada por el estudiante.
- Sé didáctico pero sintético: explica el concepto en 2-3 párrafos claros y directos con ejemplos cortos de código.
- NUNCA te extiendas innecesariamente con introducciones vacías ni rodeos.
- Concluye SIEMPRE tu explicación y ejemplos para que tu respuesta sea 100% completa y no quede cortada a la mitad.
- Si el estudiante pregunta sobre sintaxis (comas, llaves, f-strings, concatenación, print, tipos de variables), explícaselo con un ejemplo sencillo de 'Correcto vs Incorrecto'.
- Responde siempre en español."""

        context_code = f"\n\nCódigo actual en el editor (solo para contexto si aplica):\n```python\n{user_code}\n```" if user_code.strip() else ""
        user_message = f"{history_context}Pregunta del estudiante: {question}{context_code}"

    else:  # mode == "analyze"
        system_prompt = f"""Eres un analizador de código Python/Java para estudiantes.
Estás en la lección "{lesson_title}".

REGLAS:
- Analiza el código del estudiante y da feedback constructivo y directo.
- Señala errores, mejoras de estilo y buenas prácticas de forma clara y pedagógica.
- Si el código está bien, felicita al estudiante y dale un consejo o tip de mejora conciso.
- Responde en español de forma completa y directa (máximo 3-4 párrafos estructurados)."""
        user_message = f"Analiza este código:\n```python\n{user_code}\n```"

    try:
        payload = {
            "contents": [
                {"parts": [{"text": system_prompt + "\n\n" + user_message}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
        }

        resp = http_requests.post(
            GEMINI_API_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        if resp.status_code == 429:
            return jsonify(
                {
                    "ok": False,
                    "error": "Límite de peticiones alcanzado (Error 429). Por favor, espera un momento antes de volver a preguntar.",
                }
            )

        resp.raise_for_status()
        result = resp.json()
        
        candidates = result.get("candidates", [])
        if candidates and "content" in candidates[0] and "parts" in candidates[0]["content"]:
            parts = candidates[0]["content"]["parts"]
            ai_text = "".join([p.get("text", "") for p in parts if "text" in p])
        else:
            ai_text = "No se pudo generar una respuesta. Por favor formula tu pregunta nuevamente."

        return jsonify({"ok": True, "response": ai_text})
    except http_requests.exceptions.Timeout:
        return jsonify(
            {
                "ok": False,
                "error": "La IA tardó demasiado en responder. Intenta formular una pregunta más específica.",
            }
        )
    except Exception as e:
        logger.error("Error en api_ai_tutor (%s)", type(e).__name__)
        return jsonify({"ok": False, "error": "No fue posible conectar con el Tutor IA en este momento. Intenta de nuevo más tarde."})


@bp.route("/api/quiz/resultado", methods=["POST"])
@limiter.limit("20 per minute", methods=["POST"], key_func=_user_rate_limit_key)
def api_quiz_result():
    """Califica un quiz estrictamente en el servidor contra content_loader (ignora score/total del cliente)."""
    data = _get_json_dict()
    raw_quiz_id = data.get("quiz_id")
    quiz_id = raw_quiz_id.strip() if isinstance(raw_quiz_id, str) else ""
    quiz_data = load_quiz(quiz_id)
    if not quiz_data:
        return jsonify({"ok": False, "error": "Quiz no encontrado en el currículo."}), 400

    questions = quiz_data.get("questions") or []
    raw_answers = data.get("answers")
    if not isinstance(raw_answers, (dict, list)):
        return jsonify({"ok": False, "error": "Debes enviar tus respuestas para calificar el quiz."}), 400

    score = 0
    total = len(questions)
    results = []

    for idx, q in enumerate(questions):
        qid = str(q.get("id", idx))
        if isinstance(raw_answers, dict):
            user_ans = raw_answers.get(qid, raw_answers.get(str(idx)))
        else:
            user_ans = raw_answers[idx] if idx < len(raw_answers) else None

        correct_idx = _safe_int(q.get("correct", -1), -1)
        if isinstance(user_ans, bool) or user_ans is None:
            selected_idx = -1
        else:
            selected_idx = _safe_int(user_ans, -1)

        is_correct = correct_idx >= 0 and selected_idx == correct_idx
        if is_correct:
            score += 1
        results.append({
            "id": qid,
            "index": idx,
            "selected": selected_idx,
            "correct": correct_idx,
            "is_correct": is_correct,
            "explanation": q.get("explanation") or "",
        })

    percentage = round((score / total) * 100) if total > 0 else 0
    raw_time_taken = data.get("time_taken")
    time_taken = None
    if raw_time_taken is not None and not isinstance(raw_time_taken, bool):
        parsed_time = _safe_int(raw_time_taken, -1)
        if parsed_time >= 0:
            max_allowed = (_safe_int(quiz_data.get("time_limit"), 0) or 7200) + 60
            time_taken = min(parsed_time, max_allowed)

    saved = False
    user = get_current_user()
    if user and user.id:
        result = QuizResult(
            user_id=user.id,
            quiz_id=quiz_id,
            score=score,
            total=total,
            time_taken=time_taken,
        )
        db.session.add(result)
        record_daily_activity(user.id)
        db.session.commit()
        saved = True

    return jsonify({
        "ok": True,
        "saved": saved,
        "anonymous": not saved,
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
    })
