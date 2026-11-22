"""Pruebas de Fase 10: Certificados verificables, flujos de roles, migraciones e infraestructura."""

import json
import re
import zlib
from datetime import timedelta
from pathlib import Path

from flask_migrate import upgrade as alembic_upgrade
from sqlalchemy import inspect

from models import (
    AuditLog,
    Classroom,
    IssuedCertificate,
    LessonProgress,
    QuizResult,
    SectionEvaluation,
    User,
    db,
    utcnow,
)
from py2java import create_app
from py2java.services.curriculum import LESSON_CATEGORIES, _category_course_lessons
from tests.conftest import login_as

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _extract_pdf_text_bytes(pdf_bytes: bytes) -> str:
    """Extrae texto legible de un PDF fpdf2 descomprimiendo streams FlateDecode."""
    chunks = [pdf_bytes.decode("latin-1", errors="ignore")]
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
        try:
            decompressed = zlib.decompress(match.group(1))
            chunks.append(decompressed.decode("latin-1", errors="ignore"))
        except Exception:
            pass
    return "\n".join(chunks)


# =====================================================================
# 1. Migración Alembic desde cero (incluye `issued_certificates`)
# =====================================================================


def test_alembic_upgrade_creates_issued_certificates_table(tmp_path):
    db_file = tmp_path / "alembic_phase10.sqlite"
    mig_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}",
            "SECRET_KEY": "pytest-alembic-secret-key-at-least-32-chars-long",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with mig_app.app_context():
        alembic_upgrade(directory=str(PROJECT_ROOT / "migrations"))
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert "issued_certificates" in tables
        cols = {c["name"] for c in inspector.get_columns("issued_certificates")}
        assert {"id", "user_id", "section_key", "course_name", "total_lessons", "verification_code", "issued_at"} <= cols
        db.session.remove()
        db.engine.dispose()


# =====================================================================
# 2. Certificados verificables (modelo + HTML + PDF + ruta pública)
# =====================================================================


def test_verifiable_certificate_persists_code_in_html_pdf_and_public_verify(
    app, client, make_user, make_classroom
):
    prof_id = make_user("prof_cert", role="teacher")
    sec_id = make_classroom("Sección Privada", "PRIV-999", prof_id)
    stu_id = make_user(
        "graduado_p10",
        email="privado_no_exponer@test.edu",
        role="student",
        section_id=sec_id,
    )

    target_cat = LESSON_CATEGORIES[0]
    cat_id = target_cat["id"]
    cat_lessons = _category_course_lessons(target_cat)
    assert len(cat_lessons) > 0

    with app.app_context():
        for lid in cat_lessons:
            db.session.add(
                LessonProgress(
                    user_id=stu_id,
                    lesson_id=lid,
                    completed=True,
                    score=10,
                    completed_at=utcnow(),
                )
            )
        db.session.commit()

    assert login_as(client, "graduado_p10").status_code == 302

    # 1) HTML emite y persiste el código de verificación no predecible
    r_html = client.get(f"/certificado/{cat_id}")
    assert r_html.status_code == 200
    html = r_html.get_data(as_text=True)

    with app.app_context():
        certs = IssuedCertificate.query.filter_by(user_id=stu_id, section_key=cat_id).all()
        assert len(certs) == 1
        code = certs[0].verification_code
        assert code.startswith("PY2J-")
        assert len(code) >= 24

    assert code in html
    assert f"/certificado/verificar/{code}" in html

    # 2) PDF reutiliza exactamente el mismo código y lo incluye en el documento
    r_pdf = client.get(f"/certificado/{cat_id}/pdf")
    assert r_pdf.status_code == 200
    assert r_pdf.mimetype == "application/pdf"
    assert r_pdf.data.startswith(b"%PDF-")
    pdf_text = _extract_pdf_text_bytes(r_pdf.data)
    assert code in pdf_text
    assert f"/certificado/verificar/{code}" in pdf_text

    # Re-consultar no crea registros duplicados
    with app.app_context():
        assert IssuedCertificate.query.filter_by(user_id=stu_id, section_key=cat_id).count() == 1

    # 3) Verificación pública SIN sesión autenticada
    anon = app.test_client()
    r_verify = anon.get(f"/certificado/verificar/{code}")
    assert r_verify.status_code == 200
    v_html = r_verify.get_data(as_text=True)
    assert "Certificado Auténtico y Verificado" in v_html
    assert "graduado_p10" in v_html
    assert code in v_html
    # Nunca debe exponer datos privados sensibles (email ni código de sección)
    assert "privado_no_exponer@test.edu" not in v_html
    assert "PRIV-999" not in v_html

    # 4) Código inexistente devuelve 404
    r_invalid = anon.get("/certificado/verificar/PY2J-INVALIDO-00000000-00000000")
    assert r_invalid.status_code == 404
    assert "Certificado No Encontrado" in r_invalid.get_data(as_text=True)


# =====================================================================
# 3. Flujos de Estudiante: registro UI, /cuenta, pistas/solución en práctica
# =====================================================================


def test_register_template_has_confirm_password_toggle_and_loading_attr(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="confirm_password"' in html
    assert 'data-toggle-password="password"' in html
    assert 'data-toggle-password="confirm_password"' in html
    assert 'data-loading-text=' in html


def test_student_account_settings_update_password_history_and_self_delete(app, client, make_user):
    stu_id = make_user("stu_cuenta", email="stu_old@test.edu", password="OldPassword123!")
    make_user("otro_cuenta", email="taken@test.edu", password="Password123!")

    with app.app_context():
        db.session.add(
            SectionEvaluation(
                user_id=stu_id,
                section_id="python",
                score=17,
                total=20,
                percentage=85.0,
                passed=True,
                attempt_number=1,
                completed_at=utcnow(),
            )
        )
        db.session.commit()

    assert login_as(client, "stu_cuenta", "OldPassword123!").status_code == 302

    # GET /cuenta muestra historial de evaluaciones y formularios
    r_acc = client.get("/cuenta")
    assert r_acc.status_code == 200
    acc_html = r_acc.get_data(as_text=True)
    assert "stu_old@test.edu" in acc_html
    assert "85" in acc_html

    # Editar correo: rechaza correo inválido y correo duplicado
    r_bad_email = client.post("/cuenta/perfil", data={"email": "no-es-correo"}, follow_redirects=True)
    assert "correo electrónico válido" in r_bad_email.get_data(as_text=True)

    r_dup_email = client.post("/cuenta/perfil", data={"email": "taken@test.edu"}, follow_redirects=True)
    assert "ya está registrado" in r_dup_email.get_data(as_text=True)

    # Editar correo válido
    r_ok_email = client.post("/cuenta/perfil", data={"email": "stu_new@test.edu"}, follow_redirects=True)
    assert "Correo electrónico actualizado" in r_ok_email.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, stu_id).email == "stu_new@test.edu"

    # Cambiar contraseña: falla si contraseña actual es errónea o si no coinciden
    r_bad_curr = client.post(
        "/cuenta/password",
        data={
            "current_password": "WrongPassword!",
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
        follow_redirects=True,
    )
    assert "contraseña actual es incorrecta" in r_bad_curr.get_data(as_text=True)

    r_mismatch = client.post(
        "/cuenta/password",
        data={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword456!",
            "confirm_password": "OtherPassword456!",
        },
        follow_redirects=True,
    )
    assert "no coinciden" in r_mismatch.get_data(as_text=True)

    # Cambio de contraseña válido
    r_ok_pw = client.post(
        "/cuenta/password",
        data={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword456!",
            "confirm_password": "NewPassword456!",
        },
        follow_redirects=True,
    )
    assert "Contraseña actualizada con éxito" in r_ok_pw.get_data(as_text=True)

    # Verificar que la nueva contraseña funciona al iniciar sesión
    client.post("/logout")
    assert login_as(client, "stu_cuenta", "OldPassword123!").status_code == 200
    assert login_as(client, "stu_cuenta", "NewPassword456!").status_code == 302

    # Auto-eliminación rechazada si confirmación de usuario o contraseña no coincide
    r_del_wrong = client.post(
        "/cuenta/eliminar",
        data={"confirm_username": "wrong_name", "current_password": "NewPassword456!"},
        follow_redirects=True,
    )
    assert "no coincide" in r_del_wrong.get_data(as_text=True)

    # Auto-eliminación válida elimina usuario, cierra sesión y registra auditoría
    r_del_ok = client.post(
        "/cuenta/eliminar",
        data={"confirm_username": "stu_cuenta", "current_password": "NewPassword456!"},
        follow_redirects=False,
    )
    assert r_del_ok.status_code == 302
    assert client.get("/cuenta").status_code == 302
    with app.app_context():
        assert db.session.get(User, stu_id) is None
        log = AuditLog.query.filter_by(action="SELF_DELETE_ACCOUNT", target_username="stu_cuenta").first()
        assert log is not None


def test_superadmin_cannot_self_delete_account(app, client, make_user):
    sa_id = make_user("sa_protected", role="superadmin", password="SaPassword123!")
    assert login_as(client, "sa_protected", "SaPassword123!").status_code == 302
    resp = client.post(
        "/cuenta/eliminar",
        data={"confirm_username": "sa_protected", "current_password": "SaPassword123!"},
        follow_redirects=True,
    )
    assert "no pueden autoeliminarse" in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, sa_id) is not None


def test_practice_editor_renders_collapsible_hints_and_solution(client, make_user):
    make_user("prac_student", role="student")
    assert login_as(client, "prac_student").status_code == 302
    resp = client.get("/practica/pr-hello-name")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '<details class="practice-collapsible">' in html
    assert "Usa f-strings para formatear la cadena" in html
    assert "Solución de referencia" in html
    assert "def greet(name):" in html
    assert "practice-solution-code" in html


# =====================================================================
# 4. Flujos de Docente: auditoría acotada, editar sección, quitar alumno, resultados
# =====================================================================


def test_teacher_scoped_audit_edit_section_remove_student_and_results_with_idor(
    app, make_user, make_classroom
):
    prof_a_id = make_user("prof_a_p10", role="teacher")
    prof_b_id = make_user("prof_b_p10", role="teacher")
    sec_a_id = make_classroom("Sección A Original", "SECA-10", prof_a_id)
    sec_b_id = make_classroom("Sección B Privada", "SECB-10", prof_b_id)

    stu_a_id = make_user("alumno_a_p10", role="student", section_id=sec_a_id)
    stu_b_id = make_user("alumno_b_p10", role="student", section_id=sec_b_id)

    with app.app_context():
        db.session.add_all(
            [
                SectionEvaluation(
                    user_id=stu_a_id,
                    section_id="python",
                    score=9,
                    total=10,
                    percentage=90.0,
                    passed=True,
                    attempt_number=1,
                    completed_at=utcnow(),
                ),
                QuizResult(
                    user_id=stu_a_id,
                    quiz_id="quiz-python-basico",
                    score=4,
                    total=5,
                    completed_at=utcnow(),
                ),
                AuditLog(
                    admin_id=prof_a_id,
                    admin_username="prof_a_p10",
                    action="CREATE_SECTION",
                    section_id=sec_a_id,
                    reason="Alta propia de A",
                ),
                AuditLog(
                    admin_id=prof_b_id,
                    admin_username="prof_b_p10",
                    action="CREATE_SECTION",
                    section_id=sec_b_id,
                    reason="SECRETO_DEL_DOCENTE_B",
                ),
            ]
        )
        db.session.commit()

    c_a = app.test_client()
    assert login_as(c_a, "prof_a_p10").status_code == 302

    # 1) Bitácora en /profesor solo muestra eventos propios y NUNCA los del profesor B
    dash_html = c_a.get("/profesor").get_data(as_text=True)
    assert "Alta propia de A" in dash_html
    assert "SECRETO_DEL_DOCENTE_B" not in dash_html

    # 2) Editar nombre de sección propia -> OK; sección de B -> 403 IDOR
    r_edit_ok = c_a.post(
        f"/profesor/secciones/{sec_a_id}/editar",
        json={"name": "Sección A Renombrada"},
    )
    assert r_edit_ok.status_code == 200
    assert r_edit_ok.get_json()["ok"] is True
    with app.app_context():
        assert db.session.get(Classroom, sec_a_id).name == "Sección A Renombrada"
        assert AuditLog.query.filter_by(action="EDIT_SECTION", section_id=sec_a_id).first() is not None

    r_edit_idor = c_a.post(
        f"/profesor/secciones/{sec_b_id}/editar",
        json={"name": "Hackeada"},
    )
    assert r_edit_idor.status_code == 403
    with app.app_context():
        assert db.session.get(Classroom, sec_b_id).name == "Sección B Privada"

    # 3) Resultados detallados de evaluaciones/quizzes: propio -> 200; de B -> 403
    r_res_ok = c_a.get(f"/profesor/estudiante/{stu_a_id}/resultados")
    assert r_res_ok.status_code == 200
    payload = r_res_ok.get_json()
    assert payload["ok"] is True
    assert len(payload["evaluations"]) == 1
    assert payload["evaluations"][0]["percentage"] == 90.0
    assert len(payload["quizzes"]) == 1
    assert payload["quizzes"][0]["quiz_id"] == "quiz-python-basico"

    r_res_idor = c_a.get(f"/profesor/estudiante/{stu_b_id}/resultados")
    assert r_res_idor.status_code == 403

    # 4) Remover alumno de sección SIN suspender su cuenta global (+ IDOR check)
    r_rem_idor = c_a.post(f"/profesor/estudiante/{stu_b_id}/remover-seccion", json={})
    assert r_rem_idor.status_code == 403

    r_rem_ok = c_a.post(f"/profesor/estudiante/{stu_a_id}/remover-seccion", json={})
    assert r_rem_ok.status_code == 200
    assert r_rem_ok.get_json()["success"] is True

    with app.app_context():
        stu_a = db.session.get(User, stu_a_id)
        assert stu_a.section_id is None
        assert stu_a.is_suspended is False
        assert AuditLog.query.filter_by(action="REMOVE_STUDENT_SECTION", target_username="alumno_a_p10").first() is not None

    # El alumno removido todavía puede iniciar sesión normalmente
    c_stu = app.test_client()
    assert login_as(c_stu, "alumno_a_p10").status_code == 302


# =====================================================================
# 5. Flujos de Super Admin: crear profesor, cambiar rol, desbloquear, CSV AuditLog
# =====================================================================


def test_superadmin_create_teacher_change_role_unlock_and_audit_csv(
    app, make_user, make_classroom, monkeypatch
):
    monkeypatch.setenv("TEACHER_SECRET_CODE", "")
    make_user("sa_p10", role="superadmin")
    stu_id = make_user("stu_promote", role="student")
    locked_id = make_user(
        "stu_locked",
        role="student",
        is_suspended=True,
        suspended_reason="Bloqueo de prueba",
    )

    with app.app_context():
        u_locked = db.session.get(User, locked_id)
        u_locked.failed_login_attempts = 7
        u_locked.locked_until = utcnow() + timedelta(minutes=30)
        db.session.add(
            AuditLog(
                admin_username="=EVIL_ACTOR",
                action="CUSTOM_TEST_EVENT",
                target_username="+TARGET",
                reason="@FORMULA_REASON",
                details="-DETAIL_LINE",
            )
        )
        db.session.commit()

    c_sa = app.test_client()
    assert login_as(c_sa, "sa_p10").status_code == 302

    # 1) Crear profesor directamente sin depender de TEACHER_SECRET_CODE
    r_create = c_sa.post(
        "/superadmin/profesores/crear",
        json={
            "username": "prof_directo",
            "email": "prof_directo@test.edu",
            "password": "TeacherPassword123!",
        },
    )
    assert r_create.status_code == 201
    assert r_create.get_json()["ok"] is True

    with app.app_context():
        created_teacher = User.query.filter_by(username="prof_directo").first()
        assert created_teacher is not None
        assert created_teacher.role == "teacher"
        created_teacher_id = created_teacher.id

    # El docente recién creado puede iniciar sesión en /profesor
    c_new_prof = app.test_client()
    r_prof_login = login_as(c_new_prof, "prof_directo", "TeacherPassword123!")
    assert r_prof_login.status_code == 302
    assert r_prof_login.headers["Location"].endswith("/profesor")

    # Un estudiante NO puede crear docentes
    c_stu = app.test_client()
    assert login_as(c_stu, "stu_promote").status_code == 302
    r_unauth = c_stu.post(
        "/superadmin/profesores/crear",
        json={"username": "hack_prof", "email": "hack@test.edu", "password": "Password123!"},
    )
    assert r_unauth.status_code == 403

    # 2) Cambiar rol student -> teacher y teacher -> student (bloqueado si tiene secciones activas)
    sec_id = make_classroom("Sección Activa", "ACT-101", created_teacher_id)
    with app.app_context():
        db.session.get(User, stu_id).section_id = sec_id
        db.session.commit()

    # Promover estudiante -> profesor limpia section_id
    r_prom = c_sa.post(f"/superadmin/usuario/{stu_id}/cambiar-rol", json={"role": "teacher"})
    assert r_prom.status_code == 200
    with app.app_context():
        promoted = db.session.get(User, stu_id)
        assert promoted.role == "teacher"
        assert promoted.section_id is None

    # Degradar docente con secciones activas -> 400 bloqueado
    r_dem_blocked = c_sa.post(
        f"/superadmin/usuario/{created_teacher_id}/cambiar-rol",
        json={"role": "student"},
    )
    assert r_dem_blocked.status_code == 400
    assert "sección" in r_dem_blocked.get_json()["error"]

    # Degradar docente sin secciones -> 200 OK
    r_dem_ok = c_sa.post(f"/superadmin/usuario/{stu_id}/cambiar-rol", json={"role": "student"})
    assert r_dem_ok.status_code == 200
    with app.app_context():
        assert db.session.get(User, stu_id).role == "student"

    # 3) Desbloquear cuenta suspendida y/o bloqueada por rate-limit
    c_locked = app.test_client()
    for _ in range(6):
        c_locked.post("/login", data={"username": "stu_locked", "password": "WrongPassword!"})
    # El 6º intento dispara 429
    r_429 = c_locked.post("/login", data={"username": "stu_locked", "password": "Password123!"})
    assert r_429.status_code == 429

    r_unlock = c_sa.post(f"/superadmin/usuario/{locked_id}/desbloquear", json={})
    assert r_unlock.status_code == 200
    assert r_unlock.get_json()["success"] is True

    with app.app_context():
        u_after = db.session.get(User, locked_id)
        assert u_after.is_suspended is False
        assert u_after.failed_login_attempts == 0
        assert u_after.locked_until is None

    # Tras desbloquear, el usuario inicia sesión de inmediato
    assert login_as(c_locked, "stu_locked", "Password123!").status_code == 302

    # 4) Filtrar dashboard y exportar AuditLog completo a CSV con protección anti-fórmulas
    r_dash_filtered = c_sa.get("/superadmin?audit_action=CUSTOM_TEST_EVENT")
    assert r_dash_filtered.status_code == 200
    assert "CUSTOM_TEST_EVENT" in r_dash_filtered.get_data(as_text=True)

    r_csv = c_sa.get("/superadmin/export/auditoria/csv?audit_action=CUSTOM_TEST_EVENT")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.content_type
    csv_text = r_csv.get_data(as_text=True)
    assert csv_text.startswith("\ufeff")
    assert "Fecha_Hora;Actor;Accion;Afectado;Seccion_ID;Motivo;Detalle" in csv_text
    assert "'=EVIL_ACTOR" in csv_text
    assert "'+TARGET" in csv_text
    assert "'@FORMULA_REASON" in csv_text
    assert "'-DETAIL_LINE" in csv_text
    assert "SUPERADMIN_CREATE_TEACHER" not in csv_text


# =====================================================================
# 6. Infraestructura y documentación de tesis
# =====================================================================


def test_infrastructure_vercel_requirements_env_example_and_readme():
    # vercel.json moderno con /static/* antes del fallback a /app.py
    vercel_cfg = json.loads((PROJECT_ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert "builds" not in vercel_cfg
    assert "routes" not in vercel_cfg
    assert vercel_cfg.get("fluid") is True
    rewrites = vercel_cfg.get("rewrites", [])
    assert len(rewrites) >= 2
    assert rewrites[0]["source"].startswith("/static/")
    assert rewrites[-1]["destination"] == "/app.py"

    # requirements.txt con versiones exactas fijadas (==)
    req_lines = [
        line.strip()
        for line in (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(req_lines) >= 10
    for line in req_lines:
        assert "==" in line, f"Dependencia sin versión exacta fijada: {line}"

    # requirements-dev.txt separado para desarrollo/testing
    dev_text = (PROJECT_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in dev_text
    assert "pytest==" in dev_text

    # .env.example y README.md completos
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    for var in ("SECRET_KEY", "DATABASE_URL", "GEMINI_API_KEY", "APP_TIMEZONE", "ALLOW_DEMO_RESET"):
        assert var in env_example

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for keyword in ("flask --app app db upgrade", "create-superadmin", "pytest", "/certificado/verificar/", "Vercel"):
        assert keyword in readme
