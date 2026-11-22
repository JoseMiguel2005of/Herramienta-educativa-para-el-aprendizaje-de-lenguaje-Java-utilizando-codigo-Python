"""Envío de correos de recuperación de contraseña (SMTP IPv4 / Resend)."""

import html
import os
import smtplib
import socket
import ssl

import requests as http_requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from py2java.config import is_production, logger
from py2java.services.security import _safe_int


def _connect_ipv4_socket(host, port, timeout):
    """Abre conexión TCP priorizando IPv4 para evitar cuelgues por IPv6 sin ruta."""
    last_err = None
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except OSError:
        infos = []
    for af, socktype, proto, _, sa in infos:
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            sock.settimeout(timeout)
            sock.connect(sa)
            return sock
        except OSError as exc:
            last_err = exc
            if sock is not None:
                sock.close()
    if last_err is not None:
        raise last_err
    return socket.create_connection((host, port), timeout)


class _IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        return _connect_ipv4_socket(host, port, timeout)


class _IPv4SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        sock = _connect_ipv4_socket(host, port, timeout)
        return self.context.wrap_socket(sock, server_hostname=self._host)


def _is_mail_configured():
    """Indica si existe un proveedor de correo configurado (Resend API o SMTP)."""
    resend_api_key = (os.environ.get("RESEND_API_KEY") or "").strip().strip('"').strip("'")
    if resend_api_key:
        return True
    mail_username = (os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_EMAIL") or "").strip().strip('"').strip("'")
    raw_password = (os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or "").strip().strip('"').strip("'")
    mail_server = (os.environ.get("MAIL_SERVER") or "").strip().strip('"').strip("'")
    if not mail_server and mail_username and mail_username.lower().endswith("@gmail.com"):
        mail_server = "smtp.gmail.com"
    return bool(mail_server and mail_username and raw_password)


def _is_demo_reset_allowed():
    """El modo demo está desactivado por defecto y estrictamente prohibido en producción."""
    if is_production:
        return False
    return os.environ.get("ALLOW_DEMO_RESET", "false").strip().lower() in ("true", "1", "yes")


def send_recovery_email(to_email, username, code):
    """
    Envía correo real con el nombre de usuario y el código de 6 dígitos.
    Soporta Resend API por HTTPS o SMTP estándar sobre IPv4.
    Si no hay proveedor configurado, retorna (False, 'SMTP no configurado').
    """
    resend_api_key = (os.environ.get("RESEND_API_KEY") or "").strip().strip('"').strip("'")
    mail_username = (os.environ.get("MAIL_USERNAME") or os.environ.get("SMTP_EMAIL") or "").strip().strip('"').strip("'")
    raw_password = (os.environ.get("MAIL_PASSWORD") or os.environ.get("SMTP_PASSWORD") or "").strip().strip('"').strip("'")
    mail_server = (os.environ.get("MAIL_SERVER") or "").strip().strip('"').strip("'")
    if not mail_server and mail_username and mail_username.lower().endswith("@gmail.com"):
        mail_server = "smtp.gmail.com"
    # Las contraseñas de aplicación de Google se muestran en grupos de 4 letras con espacios; quitarlos evita rechazos
    mail_password = raw_password.replace(" ", "") if "gmail" in mail_server.lower() else raw_password
    mail_port = _safe_int(os.environ.get("MAIL_PORT", 587), 587)
    mail_sender = (
        os.environ.get("MAIL_DEFAULT_SENDER")
        or mail_username
        or "Py2Java Edu <onboarding@resend.dev>"
    ).strip().strip('"').strip("'")
    mail_use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes") or mail_port == 465
    mail_use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes") and not mail_use_ssl

    safe_username = html.escape(username or "")
    safe_code = html.escape(str(code))
    subject = "Recuperación de cuenta — Py2Java Edu"
    text_content = (
        f"Hola {username},\n\n"
        "Hemos recibido una solicitud para recordar tu usuario y restablecer tu contraseña en Py2Java Edu.\n\n"
        f"Tu nombre de usuario es: {username}\n"
        f"Tu código de verificación es: {code}\n\n"
        "Este código expirará en 15 minutos. Si no solicitaste este cambio, ignora este correo.\n"
    )
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 8px; background: #ffffff;">
        <h2 style="color: #1e3a5f; text-align: center; margin-top: 0;">Recuperación de Cuenta — Py2Java Edu</h2>
        <p style="color: #333; font-size: 15px;">Hola,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.5;">Hemos recibido una solicitud para recordar tu nombre de usuario y restablecer tu contraseña.</p>
        
        <div style="background: #f4f6f8; padding: 16px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3776ab;">
            <p style="margin: 0 0 10px 0; font-size: 15px;"><strong>Tu nombre de usuario es:</strong> <span style="font-size: 16px; color: #1e3a5f; font-weight: bold;">{safe_username}</span></p>
            <p style="margin: 0; font-size: 15px;"><strong>Código de verificación:</strong> <span style="font-size: 24px; font-weight: bold; letter-spacing: 6px; color: #2e7d32; display: block; margin-top: 8px; font-family: monospace;">{safe_code}</span></p>
        </div>
        
        <p style="font-size: 13px; color: #777; line-height: 1.4;">Este código expirará en <strong>15 minutos</strong>. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
    </div>
    """

    # Opción 1: Resend API (HTTPS)
    if resend_api_key:
        try:
            resp = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": mail_sender,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content,
                },
                timeout=7,
            )
            if 200 <= resp.status_code < 300:
                return True, None
            err_txt = resp.text[:300]
            logger.error("Error de envío Resend HTTP %s: %s", resp.status_code, err_txt)
            return False, "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde."
        except Exception as e:
            logger.error("Error de envío Resend (%s): %s", type(e).__name__, e)
            return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."

    # Opción 2: SMTP sobre IPv4 (Gmail, Outlook, Brevo SMTP, etc.)
    if not mail_server or not mail_username or not mail_password:
        logger.warning("Proveedor de correo no configurado para recuperación de '%s'.", username)
        return False, "SMTP no configurado"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = to_email
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        smtp_timeout = 7
        tls_ctx = ssl.create_default_context()
        if mail_use_ssl:
            with _IPv4SMTP_SSL(mail_server, mail_port, timeout=smtp_timeout, context=tls_ctx) as server:
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())
        else:
            with _IPv4SMTP(mail_server, mail_port, timeout=smtp_timeout) as server:
                server.ehlo()
                if mail_use_tls:
                    server.starttls(context=tls_ctx)
                    server.ehlo()
                server.login(mail_username, mail_password)
                server.sendmail(mail_username, [to_email], msg.as_string())
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        logger.error("Error de autenticación SMTP: %s", e)
        return False, "No se pudo enviar el correo de recuperación en este momento. Contacta al administrador."
    except (socket.timeout, TimeoutError) as e:
        logger.error("Timeout en servidor SMTP: %s", e)
        return False, "El servicio de correo tardó demasiado en responder. Intenta de nuevo más tarde."
    except Exception as e:
        logger.error("Error SMTP al enviar correo a %s (%s): %s", to_email, type(e).__name__, e)
        return False, "No se pudo enviar el correo de recuperación en este momento. Intenta de nuevo más tarde."
