"""Comandos CLI de Flask para administración segura de cuentas."""

import click
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from models import User, db
from py2java.config import logger
from py2java.services.accounts import _bootstrap_initial_superadmin
from py2java.services.validation import (
    MIN_PASSWORD_LENGTH,
    _is_valid_email,
    _is_valid_username,
)


def register_cli(app):
    """Registra comandos administrativos en la instancia Flask."""

    @app.cli.command("bootstrap-superadmin")
    def bootstrap_superadmin_command():
        """Crea la cuenta Super Admin inicial desde variables de entorno si aún no existe."""
        created = _bootstrap_initial_superadmin()
        if created:
            click.echo("Super Admin inicial creado desde variables de entorno.")
        else:
            click.echo("No se creó ningún Super Admin nuevo (revisa los logs para detalles).")

    @app.cli.command("create-superadmin")
    @click.option(
        "--username",
        prompt="Usuario Super Admin",
        help="Usuario (3-30 caracteres: letras, números, _ o -).",
    )
    @click.option("--email", prompt="Correo electrónico", help="Correo electrónico válido.")
    @click.option(
        "--password",
        prompt="Contraseña",
        hide_input=True,
        confirmation_prompt="Confirmar contraseña",
        help="Contraseña (mínimo 8 caracteres).",
    )
    def create_superadmin_command(username, email, password):
        """Crea una cuenta Super Admin de forma segura desde la CLI (requiere 'flask db upgrade' previo)."""
        clean_username = (username or "").strip()
        clean_email = (email or "").strip().lower()

        if not _is_valid_username(clean_username):
            raise click.ClickException(
                "El nombre de usuario debe tener entre 3 y 30 caracteres (solo letras, números, '-' o '_')."
            )
        if not _is_valid_email(clean_email):
            raise click.ClickException("Debes proporcionar un correo electrónico válido.")
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise click.ClickException(
                f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
            )

        if User.query.filter(func.lower(User.username) == clean_username.lower()).first():
            raise click.ClickException(f"El nombre de usuario '{clean_username}' ya existe.")
        if User.query.filter(func.lower(User.email) == clean_email.lower()).first():
            raise click.ClickException(f"El correo '{clean_email}' ya está registrado.")

        new_sa = User(
            username=clean_username,
            email=clean_email or None,
            password_hash=generate_password_hash(password),
            role="superadmin",
            is_suspended=False,
        )
        db.session.add(new_sa)
        db.session.commit()
        logger.info("Super Admin '%s' creado mediante CLI.", clean_username)
        click.echo(f"Super Admin '{clean_username}' creado correctamente.")
