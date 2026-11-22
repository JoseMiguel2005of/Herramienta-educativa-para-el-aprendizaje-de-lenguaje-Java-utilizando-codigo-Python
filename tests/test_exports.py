"""Pruebas de exportaciones seguras: saneamiento CSV anti-fórmulas y generación PDF."""

import pytest

from models import LessonProgress, db, utcnow
from py2java.services.curriculum import LESSON_CATEGORIES, _category_course_lessons
from py2java.services.security import _csv_safe
from tests.conftest import login_as


# =====================================================================
# 1. Saneamiento anti-fórmulas en CSV (=, +, -, @, \t, \r)
# =====================================================================


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        ("=CMD|' /C calc'!A0", "'=CMD|' /C calc'!A0"),
        ("+1+1", "'+1+1"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
        ("\t=1+1", "'\t=1+1"),
        ("\r=1+1", "'\r=1+1"),
        ("   =HYPERLINK(\"http://evil\")", "'   =HYPERLINK(\"http://evil\")"),
        ("usuario_normal", "usuario_normal"),
        ("", ""),
        (None, ""),
    ],
)
def test_csv_safe_neutralizes_formula_injection(raw_value, expected):
    assert _csv_safe(raw_value) == expected


def test_teacher_and_superadmin_csv_exports_sanitize_dangerous_cells(
    app, make_user, make_classroom
):
    sa_id = make_user("sa_csv", role="superadmin")
    prof_id = make_user("prof_csv", role="teacher")
    sec_id = make_classroom("=HYPERLINK(evil)", "CSV-100", prof_id)

    # Crear alumnos con valores potencialmente maliciosos en username y email
    make_user("=cmd_user", email="+sum@test.edu", role="student", section_id=sec_id)
    make_user("-neg_user", email="@at@test.edu", role="student", section_id=sec_id)
    make_user("\ttab_user", email="\rcr@test.edu", role="student", section_id=sec_id)

    for role_user, endpoint in (
        ("prof_csv", "/profesor/export/csv"),
        ("sa_csv", "/superadmin/export/csv"),
    ):
        c = app.test_client()
        assert login_as(c, role_user).status_code == 302
        resp = c.get(endpoint)
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

        text = resp.get_data(as_text=True)
        # BOM UTF-8 + separador ';'
        assert text.startswith("\ufeff")
        assert "Username;Email;Seccion;" in text

        # Todas las celdas peligrosas deben venir neutralizadas con apóstrofo inicial
        assert "'=cmd_user" in text
        assert "'+sum@test.edu" in text
        assert "'-neg_user" in text
        assert "'@at@test.edu" in text
        assert "'\ttab_user" in text
        assert "'\rcr@test.edu" in text
        assert "'=HYPERLINK(evil) (CSV-100)" in text


# =====================================================================
# 2. Generación de reportes y certificados PDF sin errores
# =====================================================================


def test_teacher_and_superadmin_pdf_exports_succeed(app, make_user, make_classroom):
    make_user("sa_pdf", role="superadmin")
    prof_id = make_user("prof_pdf", role="teacher")
    sec_id = make_classroom("Sección PDF", "PDF-200", prof_id)
    stu_id = make_user("alumno_pdf", role="student", section_id=sec_id)

    with app.app_context():
        db.session.add(
            LessonProgress(
                user_id=stu_id,
                lesson_id="py-home",
                completed=True,
                score=10,
                completed_at=utcnow(),
            )
        )
        db.session.commit()

    # PDF del profesor
    c_prof = app.test_client()
    assert login_as(c_prof, "prof_pdf").status_code == 302
    r_prof_pdf = c_prof.get("/profesor/export/pdf")
    assert r_prof_pdf.status_code == 200
    assert r_prof_pdf.mimetype == "application/pdf"
    assert r_prof_pdf.data.startswith(b"%PDF-")
    assert len(r_prof_pdf.data) > 500

    # PDF global del superadmin
    c_sa = app.test_client()
    assert login_as(c_sa, "sa_pdf").status_code == 302
    r_sa_pdf = c_sa.get("/superadmin/export/pdf")
    assert r_sa_pdf.status_code == 200
    assert r_sa_pdf.mimetype == "application/pdf"
    assert r_sa_pdf.data.startswith(b"%PDF-")
    assert len(r_sa_pdf.data) > 500


def test_student_certificate_pdf_generates_valid_pdf_when_module_complete(app, client, make_user):
    stu_id = make_user("cert_grad", role="student")
    target_cat = LESSON_CATEGORIES[0]
    cat_id = target_cat["id"]
    cat_lessons = _category_course_lessons(target_cat)
    assert len(cat_lessons) > 0

    login_as(client, "cert_grad")

    # Sin completar el módulo redirige a la vista de certificado (no genera PDF)
    r_incomplete = client.get(f"/certificado/{cat_id}/pdf", follow_redirects=False)
    assert r_incomplete.status_code == 302

    # Al completar todas las lecciones del módulo, descarga el PDF válido
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

    r_cert_pdf = client.get(f"/certificado/{cat_id}/pdf")
    assert r_cert_pdf.status_code == 200
    assert r_cert_pdf.mimetype == "application/pdf"
    assert r_cert_pdf.data.startswith(b"%PDF-")
    assert len(r_cert_pdf.data) > 500
