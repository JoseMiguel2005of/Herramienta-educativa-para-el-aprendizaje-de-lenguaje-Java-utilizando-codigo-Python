"""Instancias de extensiones Flask (inicializadas dentro de create_app)."""

import os
from flask_limiter import Limiter
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from py2java.services.security import _get_client_ip

csrf = CSRFProtect()
migrate = Migrate(render_as_batch=True)
limiter = Limiter(
    key_func=_get_client_ip,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[],
)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"
