"""Application Factory principal de Py2Java Edu."""

import os
from flask import Flask

from models import db
from py2java.blueprints import register_blueprints
from py2java.cli import register_cli
from py2java.config import PROJECT_ROOT, configure_app
from py2java.errors import register_error_handlers
from py2java.extensions import csrf, limiter, login_manager, migrate
from py2java.hooks import register_hooks


def create_app(config_overrides=None):
    """Construye y configura la instancia de la aplicación Flask."""
    app = Flask(
        __name__,
        template_folder=os.path.join(PROJECT_ROOT, "templates"),
        static_folder=os.path.join(PROJECT_ROOT, "static"),
    )

    configure_app(app, config_overrides=config_overrides)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)

    # Registrar hooks, manejadores de error, CLI y blueprints
    register_hooks(app)
    register_error_handlers(app)
    register_cli(app)
    register_blueprints(app)

    return app
