"""Punto de entrada WSGI / CLI de Py2Java Edu (Application Factory)."""

import os

from models import db
from py2java import create_app
from py2java.config import is_postgres, is_production, is_vercel, logger
from py2java.extensions import csrf, limiter, login_manager, migrate
from py2java.services.accounts import _bootstrap_initial_superadmin
from py2java.services.curriculum import LESSONS, LESSON_CATEGORIES, _course_lesson_ids

app = create_app()

__all__ = [
    "app",
    "create_app",
    "db",
    "csrf",
    "limiter",
    "login_manager",
    "migrate",
    "is_postgres",
    "is_production",
    "is_vercel",
    "logger",
    "LESSON_CATEGORIES",
    "LESSONS",
    "_bootstrap_initial_superadmin",
    "_course_lesson_ids",
]

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").strip().lower() == "true"
    app.run(debug=debug_mode, port=5000)
