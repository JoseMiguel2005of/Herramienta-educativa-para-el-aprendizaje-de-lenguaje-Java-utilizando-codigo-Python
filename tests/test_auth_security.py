"""Pruebas de Autenticación, Cuentas, CSRF, Open Redirect, Path Traversal y XSS."""

from datetime import timedelta

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

import content_loader
import py2java.blueprints.auth as auth_bp
import py2java.services.mail as mail_service
from models import PasswordResetCode, PracticeSubmission, User, db, utcnow
from py2java.services.security import _get_safe_next_url, _is_safe_redirect_url
from tests.conftest import extract_csrf_token, login_as


# =====================================================================
# 1. Registro con validaciones estrictas
# =====================================================================


@pytest.mark.parametrize(
    "payload, expected_msg",
    [
        ({"username": "", "email": "", "password": "", "confirm_password": ""}, "Todos los campos son requeridos"),
        (
            {
                "username": "ab",
                "email": "ok@test.edu",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            "El nombre de usuario debe tener entre 3 y 30 caracteres",
        ),
        (
            {
                "username": "user!name",
                "email": "ok@test.edu",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            "El nombre de usuario debe tener entre 3 y 30 caracteres",
        ),
        (
            {
                "username": "con espacios",
                "email": "ok@test.edu",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            "El nombre de usuario debe tener entre 3 y 30 caracteres",
        ),
        (
            {
                "username": "x" * 31,
                "email": "ok@test.edu",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            "El nombre de usuario debe tener entre 3 y 30 caracteres",
        ),
        (
            {
                "username": "valid_user",
                "email": "correo-invalido",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            "correo electrónico válido",
        ),
        (
            {
                "username": "valid_user",
                "email": "valid@test.edu",
                "password": "short",
                "confirm_password": "short",
            },
            "al menos 8 caracteres",
        ),
        (
            {
                "username": "valid_user",
                "email": "valid@test.edu",
                "password": "Password123!",
                "confirm_password": "DifferentPassword123!",
            },
            "Las contraseñas no coinciden",
        ),
        (
            {
                "username": "prof_fake",
                "email": "proffake@test.edu",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "role": "teacher",
                "teacher_code": "WRONG-CODE",
            },
            "Código de profesor incorrecto",
        ),
    ],
)
def test_register_rejects_invalid_inputs(client, app, payload, expected_msg):
    resp = client.post("/register", data=payload)
    assert resp.status_code == 200
    assert expected_msg in resp.get_data(as_text=True)

    with app.app_context():
        assert User.query.count() == 0


def test_register_success_and_duplicate_checks(client, app):
    resp = client.post(
        "/register",
        data={
            "username": "Ana_Dev",
            "email": "Ana@Test.EDU",
            "password": "StrongPassword99!",
            "confirm_password": "StrongPassword99!",
            "role": "student",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")

    with app.app_context():
        user = User.query.filter_by(username="Ana_Dev").first()
        assert user is not None
        assert user.email == "ana@test.edu"
        assert user.password_hash != "StrongPassword99!"
        assert check_password_hash(user.password_hash, "StrongPassword99!")

    # Cerrar sesión para probar duplicados
    client.post("/logout")

    # Duplicado username (case-insensitive)
    resp_dup_u = client.post(
        "/register",
        data={
            "username": "ana_dev",
            "email": "otro@test.edu",
            "password": "StrongPassword99!",
            "confirm_password": "StrongPassword99!",
        },
    )
    assert resp_dup_u.status_code == 200
    assert "ya está en uso" in resp_dup_u.get_data(as_text=True)

    # Duplicado email (case-insensitive)
    resp_dup_e = client.post(
        "/register",
        data={
            "username": "otra_persona",
            "email": "ANA@test.edu",
            "password": "StrongPassword99!",
            "confirm_password": "StrongPassword99!",
        },
    )
    assert resp_dup_e.status_code == 200
    assert "ya está registrado" in resp_dup_e.get_data(as_text=True)


# =====================================================================
# 2. Login: sin enumeración de usuarios y con rate-limit
# =====================================================================


def test_login_no_user_enumeration_and_rate_limit(client, make_user):
    make_user("carlos_st", password="CorrectPassword1!")

    # Contraseña errónea para usuario existente vs usuario inexistente => mismo mensaje genérico
    resp_existing = client.post(
        "/login", data={"username": "carlos_st", "password": "WrongPassword1!"}
    )
    resp_missing = client.post(
        "/login", data={"username": "no_existe_999", "password": "WrongPassword1!"}
    )
    assert resp_existing.status_code == 200
    assert resp_missing.status_code == 200
    assert "Usuario o contraseña incorrectos." in resp_existing.get_data(as_text=True)
    assert "Usuario o contraseña incorrectos." in resp_missing.get_data(as_text=True)

    # El límite en POST /login es 5 por minuto por (IP, username).
    # Ya hicimos 1 intento para carlos_st; 4 más completan los 5 y el 6º debe devolver 429.
    for _ in range(4):
        r = client.post("/login", data={"username": "carlos_st", "password": "WrongPassword1!"})
        assert r.status_code == 200

    r_limited = client.post(
        "/login", data={"username": "carlos_st", "password": "WrongPassword1!"}
    )
    assert r_limited.status_code == 429

    # Otro usuario distinto desde la misma IP NO debe quedar bloqueado por el bucket de carlos_st
    make_user("lucia_st", password="CorrectPassword2!")
    r_other = client.post(
        "/login", data={"username": "lucia_st", "password": "CorrectPassword2!"}
    )
    assert r_other.status_code == 302


# =====================================================================
# 3. Reset OTP: ALLOW_DEMO_RESET=false y límite estricto de 5 intentos
# =====================================================================


def test_forgot_password_blocks_when_demo_disabled_and_no_mail(client, make_user, monkeypatch):
    make_user("alumno_reset", email="alumno_reset@test.edu")
    for env_key in (
        "RESEND_API_KEY",
        "MAIL_USERNAME",
        "SMTP_EMAIL",
        "MAIL_PASSWORD",
        "SMTP_PASSWORD",
        "MAIL_SERVER",
    ):
        monkeypatch.delenv(env_key, raising=False)
    monkeypatch.setenv("ALLOW_DEMO_RESET", "false")

    resp = client.post("/recuperar", data={"email": "alumno_reset@test.edu"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "no está disponible en este momento" in body

    with client.session_transaction() as sess:
        assert "demo_reset_code" not in sess


def test_reset_otp_enforces_five_attempts_and_expiry(client, app, make_user, monkeypatch):
    uid = make_user("otp_user", email="otp_user@test.edu", password="OldPassword123!")

    # Simular correo configurado y capturar OTP enviado
    sent_payloads = []
    monkeypatch.setattr(auth_bp, "_is_mail_configured", lambda: True)
    monkeypatch.setattr(
        auth_bp,
        "send_recovery_email",
        lambda to_email, username, code: (sent_payloads.append((to_email, username, code)) or (True, None)),
    )

    # Correo inexistente recibe misma redirección y aviso genérico (sin enumeración)
    resp_unknown = client.post("/recuperar", data={"email": "nobody@test.edu"})
    assert resp_unknown.status_code == 302
    assert len(sent_payloads) == 0

    # Solicitar OTP para usuario real
    resp_ok = client.post("/recuperar", data={"email": "otp_user@test.edu"})
    assert resp_ok.status_code == 302
    assert len(sent_payloads) == 1
    real_code = sent_payloads[0][2]
    assert len(real_code) == 6 and real_code.isdigit()

    # 4 intentos erróneos => incrementa contador pero no invalida aún
    wrong_code = "000000" if real_code != "000000" else "999999"
    for attempt in range(1, 5):
        r = client.post(
            "/recuperar/verificar",
            data={
                "email": "otp_user@test.edu",
                "code": wrong_code,
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
        )
        assert r.status_code == 200
        assert "inválido" in r.get_data(as_text=True)

    # 5º intento erróneo => invalida definitivamente el código
    r5 = client.post(
        "/recuperar/verificar",
        data={
            "email": "otp_user@test.edu",
            "code": wrong_code,
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert r5.status_code == 200
    assert "invalidado por demasiados intentos fallidos" in r5.get_data(as_text=True)

    with app.app_context():
        rec = PasswordResetCode.query.filter_by(user_id=uid).order_by(PasswordResetCode.id.desc()).first()
        assert rec.used is True
        assert rec.failed_attempts == 5

    # Incluso enviando ahora el código real, debe rechazarse porque ya fue invalidado
    r_after = client.post(
        "/recuperar/verificar",
        data={
            "email": "otp_user@test.edu",
            "code": real_code,
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert r_after.status_code == 200
    assert "inválido" in r_after.get_data(as_text=True)

    # Código expirado también se rechaza
    with app.app_context():
        expired = PasswordResetCode(
            user_id=uid,
            code="123456",
            expires_at=utcnow() - timedelta(minutes=1),
            used=False,
            failed_attempts=0,
        )
        db.session.add(expired)
        db.session.commit()

    r_exp = client.post(
        "/recuperar/verificar",
        data={
            "email": "otp_user@test.edu",
            "code": "123456",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert r_exp.status_code == 200
    assert "ha expirado" in r_exp.get_data(as_text=True)

    # Flujo válido con nuevo código
    with app.app_context():
        valid = PasswordResetCode(
            user_id=uid,
            code="654321",
            expires_at=utcnow() + timedelta(minutes=10),
            used=False,
            failed_attempts=0,
        )
        db.session.add(valid)
        db.session.commit()

    r_success = client.post(
        "/recuperar/verificar",
        data={
            "email": "otp_user@test.edu",
            "code": "654321",
            "new_password": "BrandNewPassword1!",
            "confirm_password": "BrandNewPassword1!",
        },
    )
    assert r_success.status_code == 200
    assert "Contraseña actualizada con éxito" in r_success.get_data(as_text=True)

    # Login con la nueva contraseña funciona
    r_login = login_as(client, "otp_user", "BrandNewPassword1!")
    assert r_login.status_code == 302


def test_demo_reset_strictly_disabled_in_production(monkeypatch):
    monkeypatch.setenv("ALLOW_DEMO_RESET", "true")
    monkeypatch.setattr(mail_service, "is_production", True)
    assert mail_service._is_demo_reset_allowed() is False


# =====================================================================
# 4. Protección CSRF en POSTs y /logout exclusivo por POST
# =====================================================================


def test_csrf_enforced_on_forms_and_api_and_logout_post_only(csrf_app, csrf_client):
    with csrf_app.app_context():
        user = User(
            username="csrf_student",
            email="csrf_student@test.edu",
            password_hash=generate_password_hash("Password123!"),
            role="student",
        )
        db.session.add(user)
        db.session.commit()

    # POST /login sin CSRF => 400
    r_no_csrf = csrf_client.post(
        "/login", data={"username": "csrf_student", "password": "Password123!"}
    )
    assert r_no_csrf.status_code == 400
    assert "CSRF" in r_no_csrf.get_data(as_text=True)

    # POST /login con token CSRF válido => 302
    r_login = login_as(csrf_client, "csrf_student", "Password123!", use_csrf=True)
    assert r_login.status_code == 302

    # POST JSON API sin cabecera X-CSRFToken => 400 JSON
    r_api_no_csrf = csrf_client.post(
        "/api/progreso/leccion", json={"lesson_id": "py-variables"}
    )
    assert r_api_no_csrf.status_code == 400
    assert r_api_no_csrf.get_json()["ok"] is False

    # Obtener meta csrf-token desde una página autenticada y enviarlo en X-CSRFToken => 200
    dash_html = csrf_client.get("/dashboard").get_data(as_text=True)
    csrf_token = extract_csrf_token(dash_html)
    r_api_ok = csrf_client.post(
        "/api/progreso/leccion",
        json={"lesson_id": "py-variables"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert r_api_ok.status_code == 200
    assert r_api_ok.get_json()["ok"] is True

    # GET /logout debe ser rechazado con 405 Method Not Allowed y mantener sesión activa
    r_logout_get = csrf_client.get("/logout")
    assert r_logout_get.status_code == 405
    assert csrf_client.get("/dashboard").status_code == 200

    # POST /logout sin CSRF => 400
    r_logout_no_csrf = csrf_client.post("/logout")
    assert r_logout_no_csrf.status_code == 400

    # POST /logout con CSRF => 302 y cierra sesión
    r_logout_ok = csrf_client.post("/logout", data={"csrf_token": csrf_token})
    assert r_logout_ok.status_code == 302
    assert csrf_client.get("/dashboard").status_code == 302


# =====================================================================
# 5. Open Redirect y Path Traversal
# =====================================================================


@pytest.mark.parametrize(
    "malicious_url",
    [
        "///evil.com",
        "//evil.com",
        "//evil.com/path",
        "https://evil.com/phish",
        "http://evil.com",
        "/\\evil.com",
        "javascript:alert(1)",
        "/dashboard\r\nSet-Cookie: evil=1",
    ],
)
def test_open_redirect_blocked(client, make_user, malicious_url):
    assert _is_safe_redirect_url(malicious_url) is False
    assert _get_safe_next_url(malicious_url) is None

    make_user("redir_user", password="Password123!")
    resp = client.post(
        "/login",
        data={"username": "redir_user", "password": "Password123!", "next": malicious_url},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/dashboard")

    # También en POST /configuracion
    resp_cfg = client.post(
        "/configuracion",
        data={"theme": "dark", "next": malicious_url},
        follow_redirects=False,
    )
    assert resp_cfg.status_code == 302
    assert "evil.com" not in resp_cfg.headers["Location"]


def test_path_traversal_blocked(client):
    traversal_ids = [
        "../ui",
        "../../app",
        "..\\..\\models",
        "py-home/../../ui",
        "../reference",
    ]
    for bad_id in traversal_ids:
        assert content_loader.load_lesson(bad_id) is None
        assert content_loader.load_quiz(bad_id) is None
        assert content_loader.load_evaluation(bad_id) is None

    # En rutas HTTP, una lección inexistente o traversal responde 404 (nunca 200)
    for bad_path in ("/leccion/no-existe", "/leccion/..%2Fui", "/leccion/..%5Cui"):
        r = client.get(bad_path)
        assert r.status_code == 404


# =====================================================================
# 6. Escape XSS en practice_editor y cabeceras de seguridad
# =====================================================================


def test_xss_escaped_in_practice_editor_and_security_headers(client, app, make_user):
    uid = make_user("xss_student", password="Password123!")
    xss_payload = '</textarea><script>alert("XSS")</script><img src=x onerror=alert(1)>'

    with app.app_context():
        db.session.add(
            PracticeSubmission(
                user_id=uid,
                problem_id="pr-hello-name",
                code=xss_payload,
                passed=False,
                tests_passed=0,
                tests_total=3,
            )
        )
        db.session.commit()

    login_as(client, "xss_student", "Password123!")
    resp = client.get("/practica/pr-hello-name")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    # El payload crudo NUNCA debe aparecer sin escapar
    assert '<script>alert("XSS")</script>' not in html
    assert "<img src=x onerror=alert(1)>" not in html
    # Sí debe aparecer correctamente escapado dentro del textarea
    assert "&lt;/textarea&gt;&lt;script&gt;alert(" in html

    # Verificar cabeceras de seguridad (CSP con nonce, nosniff, X-Frame-Options)
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "nonce-" in csp
    assert "object-src 'none'" in csp
