"""Pruebas de Evaluaciones en servidor (EvaluationSession) y Progreso/XP Anti-Trampa."""

import json
from datetime import timedelta

import content_loader
from models import (
    EvaluationSession,
    ExerciseAttempt,
    LessonProgress,
    PracticeSubmission,
    QuizResult,
    SectionEvaluation,
    db,
    utcnow,
)
from py2java.services.exercises import (
    SOLUTION_VIEWED_MARKER,
    XP_PER_EVALUATION,
    XP_PER_EXERCISE,
    XP_PER_LESSON,
    _extract_exercise_blanks,
)
from tests.conftest import complete_section_lessons, login_as


def _build_correct_eval_answers(section_key, question_ids):
    """Construye un mapa {qid: respuesta_correcta} a partir del catálogo oficial."""
    eval_data = content_loader.get_evaluation_for_section(section_key)
    catalog = {}
    for qs in eval_data.get("lesson_questions", {}).values():
        for q in qs:
            catalog[q["id"]] = (
                q.get("correct_answer") if q.get("type") == "complete_code" else q.get("correct")
            )
    return {qid: catalog[qid] for qid in question_ids if qid in catalog}


# =====================================================================
# 1. EvaluationSession en servidor y anti-trampa de evaluaciones
# =====================================================================


def test_evaluation_requires_80_percent_completion(app, client, make_user):
    uid = make_user("eval_locked_user")
    login_as(client, "eval_locked_user")

    # Con 0% completado: GET redirige a /dashboard y POST responde 403
    r_get = client.get("/evaluacion/cat_python_functions", follow_redirects=False)
    assert r_get.status_code == 302
    assert r_get.headers["Location"].endswith("/dashboard")

    r_post = client.post(
        "/api/evaluacion/resultado",
        json={"section_key": "cat_python_functions", "answers": {}},
    )
    assert r_post.status_code == 403
    assert r_post.get_json()["ok"] is False

    # Con 50% (1 de 2 lecciones) sigue bloqueado
    complete_section_lessons(app, uid, "cat_python_functions", ratio=0.5)
    r_post_half = client.post(
        "/api/evaluacion/resultado",
        json={"section_key": "cat_python_functions", "answers": {}},
    )
    assert r_post_half.status_code == 403


def test_evaluation_rejects_missing_expired_duplicate_and_manipulated_sessions(
    app, client, make_user
):
    uid = make_user("eval_student")
    complete_section_lessons(app, uid, "cat_python_functions", ratio=1.0)
    login_as(client, "eval_student")

    # 1) Envío SIN sesión activa en EvaluationSession => 400
    r_no_sess = client.post(
        "/api/evaluacion/resultado",
        json={"section_key": "cat_python_functions", "answers": {"q1": 0}},
    )
    assert r_no_sess.status_code == 400
    assert r_no_sess.get_json()["ok"] is False

    # 2) Abrir GET /evaluacion/cat_python_functions crea EvaluationSession en BD y NO guarda respuestas en cookie
    r_page = client.get("/evaluacion/cat_python_functions")
    assert r_page.status_code == 200
    with client.session_transaction() as sess:
        assert not any(k.startswith("eval_answers_") for k in sess.keys())

    with app.app_context():
        ev_sess = EvaluationSession.query.filter_by(
            user_id=uid, section_key="cat_python_functions", submitted=False
        ).first()
        assert ev_sess is not None
        sess_id = ev_sess.id
        qids = json.loads(ev_sess.question_ids_json)
        assert len(qids) >= 2

    # 3) Manipulación: enviar solo 1 pregunta correcta intentando sacar 100%
    # El servidor debe calificar contra TODO el conjunto question_ids_json
    all_correct = _build_correct_eval_answers("cat_python_functions", qids)
    single_answer = {qids[0]: all_correct[qids[0]]}
    r_partial = client.post(
        "/api/evaluacion/resultado",
        json={
            "section_key": "cat_python_functions",
            "session_id": sess_id,
            "answers": single_answer,
        },
    )
    assert r_partial.status_code == 200
    payload = r_partial.get_json()
    assert payload["ok"] is True
    assert payload["total"] == len(qids)
    assert payload["score"] == 1
    assert payload["passed"] is False
    assert payload["xp_gained"] == 0

    # 4) Entrega DUPLICADA con la misma session_id => 400
    r_dup = client.post(
        "/api/evaluacion/resultado",
        json={
            "section_key": "cat_python_functions",
            "session_id": sess_id,
            "answers": all_correct,
        },
    )
    assert r_dup.status_code == 400
    assert r_dup.get_json()["ok"] is False

    # 5) Sesión EXPIRADA => 400 y se marca submitted=True
    r_page2 = client.get("/evaluacion/cat_python_functions")
    assert r_page2.status_code == 200
    with app.app_context():
        ev_exp = EvaluationSession.query.filter_by(
            user_id=uid, section_key="cat_python_functions", submitted=False
        ).first()
        exp_id = ev_exp.id
        ev_exp.expires_at = utcnow() - timedelta(seconds=120)
        db.session.commit()

    r_exp = client.post(
        "/api/evaluacion/resultado",
        json={
            "section_key": "cat_python_functions",
            "session_id": exp_id,
            "answers": all_correct,
        },
    )
    assert r_exp.status_code == 400
    assert "expirado" in r_exp.get_json()["error"].lower()
    with app.app_context():
        assert db.session.get(EvaluationSession, exp_id).submitted is True

    # 6) Entrega legítima con todas las respuestas correctas => aprueba y otorga XP una sola vez
    assert client.get("/evaluacion/cat_python_functions").status_code == 200
    with app.app_context():
        ev_ok = EvaluationSession.query.filter_by(
            user_id=uid, section_key="cat_python_functions", submitted=False
        ).first()
        ok_id = ev_ok.id
        ok_qids = json.loads(ev_ok.question_ids_json)

    ok_answers = _build_correct_eval_answers("cat_python_functions", ok_qids)
    r_pass = client.post(
        "/api/evaluacion/resultado",
        json={
            "section_key": "cat_python_functions",
            "session_id": ok_id,
            "answers": ok_answers,
        },
    )
    assert r_pass.status_code == 200
    pass_data = r_pass.get_json()
    assert pass_data["passed"] is True
    assert pass_data["score"] == len(ok_qids)
    assert pass_data["xp_gained"] == XP_PER_EVALUATION

    # Segundo intento aprobado NO duplica XP
    assert client.get("/evaluacion/cat_python_functions").status_code == 200
    with app.app_context():
        ev_ok2 = EvaluationSession.query.filter_by(
            user_id=uid, section_key="cat_python_functions", submitted=False
        ).first()
        ok2_id = ev_ok2.id
        ok2_qids = json.loads(ev_ok2.question_ids_json)

    r_pass2 = client.post(
        "/api/evaluacion/resultado",
        json={
            "section_key": "cat_python_functions",
            "session_id": ok2_id,
            "answers": _build_correct_eval_answers("cat_python_functions", ok2_qids),
        },
    )
    assert r_pass2.status_code == 200
    assert r_pass2.get_json()["passed"] is True
    assert r_pass2.get_json()["xp_gained"] == 0


# =====================================================================
# 2. Validación estricta de IDs (lecciones, ejercicios, práctica y quizzes)
# =====================================================================


def test_lesson_exercise_practice_and_quiz_validate_real_ids_and_server_grading(
    app, client, make_user
):
    uid = make_user("progress_student")
    login_as(client, "progress_student")

    # Lecciones: rechaza ID inexistente, traversal y ejercicios (no son lección de curso)
    for bad_lid in ("leccion-falsa-999", "../ui", "ex-variables", ""):
        r = client.post("/api/progreso/leccion", json={"lesson_id": bad_lid})
        assert r.status_code == 400
        assert r.get_json()["ok"] is False

    # Lección real otorga +10 XP una sola vez
    r_l1 = client.post("/api/progreso/leccion", json={"lesson_id": "py-variables"})
    assert r_l1.status_code == 200
    assert r_l1.get_json()["xp_gained"] == XP_PER_LESSON

    r_l2 = client.post("/api/progreso/leccion", json={"lesson_id": "py-variables"})
    assert r_l2.status_code == 200
    assert r_l2.get_json()["xp_gained"] == 0

    # Ejercicios: rechaza IDs falsos e ignora "passed": True manipulado desde cliente
    r_bad_ex = client.post(
        "/api/progreso/ejercicio",
        json={"lesson_id": "leccion-falsa", "exercise_id": "ex-fake", "passed": True},
    )
    assert r_bad_ex.status_code == 400

    r_cheat_ex = client.post(
        "/api/progreso/ejercicio",
        json={
            "lesson_id": "ex-variables",
            "exercise_id": "ex-var-2",
            "answers": ["MAL", "MAL"],
            "passed": True,
        },
    )
    assert r_cheat_ex.status_code == 200
    assert r_cheat_ex.get_json()["passed"] is False
    assert r_cheat_ex.get_json()["xp_gained"] == 0

    # Ejercicio real con respuestas correctas otorga +25 XP solo la primera vez
    _, ex2 = content_loader.get_lesson_exercise("ex-variables", "ex-var-2")
    blanks2 = _extract_exercise_blanks(ex2, "python")
    r_ok_ex = client.post(
        "/api/progreso/ejercicio",
        json={"lesson_id": "ex-variables", "exercise_id": "ex-var-2", "answers": blanks2},
    )
    assert r_ok_ex.status_code == 200
    assert r_ok_ex.get_json()["passed"] is True
    assert r_ok_ex.get_json()["xp_gained"] == XP_PER_EXERCISE

    r_ok_ex_dup = client.post(
        "/api/progreso/ejercicio",
        json={"lesson_id": "ex-variables", "exercise_id": "ex-var-2", "answers": blanks2},
    )
    assert r_ok_ex_dup.status_code == 200
    assert r_ok_ex_dup.get_json()["xp_gained"] == 0

    # Práctica: rechaza problem_id inexistente y código starter sin implementar
    r_bad_pr = client.post(
        "/api/submit_practice",
        json={"problem_id": "pr-no-existe", "code": "print(1)", "passed": True, "tests_passed": 3, "tests_total": 3},
    )
    assert r_bad_pr.status_code == 400

    problem = content_loader.get_practice_problem("pr-hello-name")
    r_trivial_pr = client.post(
        "/api/submit_practice",
        json={
            "problem_id": "pr-hello-name",
            "code": problem["starter_code"],
            "passed": True,
            "tests_passed": len(problem["test_cases"]),
            "tests_total": len(problem["test_cases"]),
        },
    )
    assert r_trivial_pr.status_code == 400

    # Quiz: rechaza quiz_id falso e ignora score/total enviados por el cliente
    r_bad_q = client.post("/api/quiz/resultado", json={"quiz_id": "quiz-falso", "answers": {}})
    assert r_bad_q.status_code == 400

    quiz_data = content_loader.load_quiz("quiz-python-basics")
    r_cheat_q = client.post(
        "/api/quiz/resultado",
        json={
            "quiz_id": "quiz-python-basics",
            "answers": {},
            "score": 999,
            "total": 1,
        },
    )
    assert r_cheat_q.status_code == 200
    qd = r_cheat_q.get_json()
    assert qd["score"] == 0
    assert qd["total"] == len(quiz_data["questions"])

    with app.app_context():
        saved_q = QuizResult.query.filter_by(user_id=uid, quiz_id="quiz-python-basics").first()
        assert saved_q is not None
        assert saved_q.score == 0
        assert saved_q.total == len(quiz_data["questions"])


# =====================================================================
# 3. Bloqueo de XP tras usar "Ver Solución"
# =====================================================================


def test_viewing_solution_blocks_xp_even_after_submitting_correct_answer(app, client, make_user):
    uid = make_user("solution_peeker")
    login_as(client, "solution_peeker")

    # 1) Consultar "Ver Solución" para ex-variables / ex-var-1
    r_sol = client.post(
        "/api/ejercicio/solucion",
        json={"lesson_id": "ex-variables", "exercise_id": "ex-var-1", "lang": "python"},
    )
    assert r_sol.status_code == 200
    sol_data = r_sol.get_json()
    assert sol_data["ok"] is True
    assert sol_data["xp_blocked"] is True
    correct_blanks = sol_data["answers"]
    assert len(correct_blanks) > 0

    with app.app_context():
        marker = ExerciseAttempt.query.filter_by(
            user_id=uid, exercise_id="ex-var-1", answer=SOLUTION_VIEWED_MARKER
        ).first()
        assert marker is not None

    # 2) Incluso si el estudiante borra la clave en su cookie de sesión, la marca en BD persiste el bloqueo
    with client.session_transaction() as sess:
        sess.pop("viewed_solutions", None)

    # 3) Enviar ahora las respuestas exactas de la solución => passed=True pero xp_gained=0 y xp_blocked_by_solution=True
    r_submit = client.post(
        "/api/progreso/ejercicio",
        json={
            "lesson_id": "ex-variables",
            "exercise_id": "ex-var-1",
            "lang": "python",
            "answers": correct_blanks,
        },
    )
    assert r_submit.status_code == 200
    sub_data = r_submit.get_json()
    assert sub_data["ok"] is True
    assert sub_data["passed"] is True
    assert sub_data["xp_blocked_by_solution"] is True
    assert sub_data["xp_gained"] == 0
    assert sub_data["summary"]["total_xp"] == 0

    # Confirmar que no quedó registrado ningún intento con passed=True que sume XP
    with app.app_context():
        assert (
            ExerciseAttempt.query.filter_by(user_id=uid, exercise_id="ex-var-1", passed=True).count()
            == 0
        )
