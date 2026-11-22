"""Pruebas de aislamiento de roles (RBAC) y prevención de IDOR."""

from flask import render_template

from models import AuditLog, Classroom, User, db
from py2java.services.curriculum import LESSON_CATEGORIES
from tests.conftest import login_as


def _seed_two_teachers_and_students(make_user, make_classroom):
    sa_id = make_user("sa_root", role="superadmin")
    prof_a_id = make_user("prof_a", role="teacher")
    prof_b_id = make_user("prof_b", role="teacher")

    sec_a_id = make_classroom("Sección Alpha", "ALPHA-111", prof_a_id)
    sec_b_id = make_classroom("Sección Beta", "BETA-222", prof_b_id)

    stu_a_id = make_user("alumno_a", role="student", section_id=sec_a_id)
    stu_b_id = make_user("alumno_b", role="student", section_id=sec_b_id)
    stu_free_id = make_user("alumno_libre", role="student", section_id=None)

    return {
        "superadmin": sa_id,
        "prof_a": prof_a_id,
        "prof_b": prof_b_id,
        "sec_a": sec_a_id,
        "sec_b": sec_b_id,
        "stu_a": stu_a_id,
        "stu_b": stu_b_id,
        "stu_free": stu_free_id,
    }


def test_teacher_a_cannot_view_suspend_restore_delete_or_export_teacher_b_students(
    app, make_user, make_classroom
):
    ids = _seed_two_teachers_and_students(make_user, make_classroom)

    c_prof_a = app.test_client()
    assert login_as(c_prof_a, "prof_a").status_code == 302

    # 1. Docente A NO puede ver el perfil de Alumno B ni de Alumno libre (403 + auditoría)
    r_prof_b = c_prof_a.get("/perfil/alumno_b")
    assert r_prof_b.status_code == 403
    assert "BETA-222" not in r_prof_b.get_data(as_text=True)

    r_free = c_prof_a.get("/perfil/alumno_libre")
    assert r_free.status_code == 403

    # 2. Docente A NO puede suspender a Alumno B
    r_susp = c_prof_a.post(
        f"/profesor/estudiante/{ids['stu_b']}/suspender",
        json={"reason": "Intento no autorizado de suspensión"},
    )
    assert r_susp.status_code == 403
    assert r_susp.get_json()["success"] is False

    with app.app_context():
        stu_b = db.session.get(User, ids["stu_b"])
        assert stu_b.is_suspended is False

    # 3. Docente B suspende a Alumno B; Docente A NO puede restaurarlo
    c_prof_b = app.test_client()
    assert login_as(c_prof_b, "prof_b").status_code == 302
    r_susp_b = c_prof_b.post(
        f"/profesor/estudiante/{ids['stu_b']}/suspender",
        json={"reason": "Suspensión legítima del docente titular"},
    )
    assert r_susp_b.status_code == 200
    assert r_susp_b.get_json()["success"] is True

    r_rest_a = c_prof_a.post(
        f"/profesor/estudiante/{ids['stu_b']}/restaurar",
        json={"reason": "Intento ajeno de restauración"},
    )
    assert r_rest_a.status_code == 403
    with app.app_context():
        assert db.session.get(User, ids["stu_b"]).is_suspended is True

    # 4. Docente A NO puede eliminar la sección del Docente B
    r_del_sec = c_prof_a.post(
        f"/profesor/secciones/{ids['sec_b']}/eliminar",
        headers={"Accept": "application/json"},
    )
    assert r_del_sec.status_code == 403
    with app.app_context():
        assert db.session.get(Classroom, ids["sec_b"]) is not None

    # 5. Docente A en /profesor y /profesor/export/csv (incluso manipulando section_id=sec_b) solo ve a Alumno A
    r_dash = c_prof_a.get(f"/profesor?section_id={ids['sec_b']}")
    assert r_dash.status_code == 200
    dash_html = r_dash.get_data(as_text=True)
    assert "alumno_a" in dash_html
    assert "alumno_b" not in dash_html
    assert "BETA-222" not in dash_html

    r_csv = c_prof_a.get(f"/profesor/export/csv?section_id={ids['sec_b']}")
    assert r_csv.status_code == 200
    csv_text = r_csv.get_data(as_text=True)
    assert "alumno_a" in csv_text
    assert "alumno_b" not in csv_text
    assert "alumno_libre" not in csv_text

    # 6. Verificar registro de intentos no autorizados en AuditLog
    with app.app_context():
        actions = {log.action for log in AuditLog.query.all()}
        assert "UNAUTHORIZED_PROFILE_VIEW" in actions
        assert "UNAUTHORIZED_SUSPEND_ATTEMPT" in actions
        assert "UNAUTHORIZED_RESTORE_ATTEMPT" in actions
        assert "UNAUTHORIZED_DELETE_SECTION_ATTEMPT" in actions


def test_teacher_a_can_manage_own_student(app, make_user, make_classroom):
    ids = _seed_two_teachers_and_students(make_user, make_classroom)

    c_prof_a = app.test_client()
    assert login_as(c_prof_a, "prof_a").status_code == 302

    # Ver perfil de su propio estudiante
    r_profile = c_prof_a.get("/perfil/alumno_a")
    assert r_profile.status_code == 200
    assert "ALPHA-111" in r_profile.get_data(as_text=True)

    # Suspender y restaurar a su propio estudiante
    r_susp = c_prof_a.post(
        f"/profesor/estudiante/{ids['stu_a']}/suspender",
        json={"reason": "Incumplimiento de normas en laboratorio"},
    )
    assert r_susp.status_code == 200
    assert r_susp.get_json()["success"] is True

    r_rest = c_prof_a.post(
        f"/profesor/estudiante/{ids['stu_a']}/restaurar",
        json={"reason": "Situación aclarada con el estudiante"},
    )
    assert r_rest.status_code == 200
    assert r_rest.get_json()["success"] is True


def test_student_cannot_access_teacher_or_superadmin_routes(app, make_user, make_classroom):
    ids = _seed_two_teachers_and_students(make_user, make_classroom)

    c_stu = app.test_client()
    assert login_as(c_stu, "alumno_a").status_code == 302

    # Vistas HTML redirigen a /dashboard
    for route in ("/profesor", "/administrador", "/superadmin", "/profesor/export/csv", "/superadmin/export/csv"):
        r = c_stu.get(route, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["Location"].endswith("/dashboard")

    # Endpoints JSON / acciones devuelven 403
    for route in ("/profesor/export/pdf", "/superadmin/export/pdf", "/api/db-status"):
        r = c_stu.get(route)
        assert r.status_code == 403

    r_create = c_stu.post(
        "/profesor/secciones/crear",
        json={"name": "FakeSec"},
        headers={"Accept": "application/json"},
    )
    assert r_create.status_code == 403

    r_susp = c_stu.post(
        f"/profesor/estudiante/{ids['stu_b']}/suspender",
        json={"reason": "Intento de estudiante"},
    )
    assert r_susp.status_code == 403

    r_sa_susp = c_stu.post(
        f"/superadmin/usuario/{ids['prof_a']}/suspender",
        json={"reason": "Intento de estudiante en superadmin"},
    )
    assert r_sa_susp.status_code == 403


def test_profile_requires_login_and_hides_classroom_code_from_third_parties(
    app, make_user, make_classroom
):
    ids = _seed_two_teachers_and_students(make_user, make_classroom)

    # Anónimo redirigido a /login
    c_anon = app.test_client()
    for path in ("/perfil", "/perfil/alumno_a"):
        r = c_anon.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    # Estudiante B no puede ver el perfil de Estudiante A (403, nunca filtra ALPHA-111)
    c_stu_b = app.test_client()
    assert login_as(c_stu_b, "alumno_b").status_code == 302
    r_other = c_stu_b.get("/perfil/alumno_a")
    assert r_other.status_code == 403
    assert "ALPHA-111" not in r_other.get_data(as_text=True)

    # Estudiante A sí ve su propio perfil y su código de clase
    c_stu_a = app.test_client()
    assert login_as(c_stu_a, "alumno_a").status_code == 302
    r_own = c_stu_a.get("/perfil")
    assert r_own.status_code == 200
    assert "ALPHA-111" in r_own.get_data(as_text=True)

    # Super Admin sí puede ver perfiles y códigos
    c_sa = app.test_client()
    assert login_as(c_sa, "sa_root").status_code == 302
    r_sa = c_sa.get("/perfil/alumno_b")
    assert r_sa.status_code == 200
    assert "BETA-222" in r_sa.get_data(as_text=True)

    # Además, la plantilla profile.html oculta explícitamente classroom.code cuando can_view_class_code=False
    with app.test_request_context("/perfil/alumno_a"):
        stu_a = db.session.get(User, ids["stu_a"])
        cls_a = db.session.get(Classroom, ids["sec_a"])
        rendered = render_template(
            "profile.html",
            profile_user=stu_a,
            classroom=cls_a,
            is_own_profile=False,
            can_view_class_code=False,
            summary={"total_xp": 0, "streak": 0, "completed_lessons": []},
            level=1,
            recent=[],
            quiz_results=[],
            total_exercises=0,
            passed_exercises=0,
            cert_cards=[],
            categories=LESSON_CATEGORIES,
            page="profile",
        )
        assert cls_a.name in rendered
        assert cls_a.code not in rendered
