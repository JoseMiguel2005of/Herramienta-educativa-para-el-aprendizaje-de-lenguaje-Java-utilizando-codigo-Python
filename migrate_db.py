"""
Script seguro e idempotente de migración de base de datos vía Alembic / Flask-Migrate.

Aplica todas las migraciones pendientes (`flask db upgrade`) y opcionalmente
ejecuta el bootstrap inicial de Super Admin si existen las variables de entorno
correspondientes y aún no existe ningún Super Admin.

Uso:
    python migrate_db.py
    # o directamente con Flask CLI:
    flask --app app db upgrade
"""

from flask_migrate import upgrade

from app import app, db, is_postgres, logger, _bootstrap_initial_superadmin


def run_migration():
    engine_label = "PostgreSQL" if is_postgres else "SQLite"
    logger.info("[MIGRATE] Motor detectado: %s", engine_label)
    with app.app_context():
        upgrade()
        _bootstrap_initial_superadmin()
        tables = sorted(db.metadata.tables.keys())
        logger.info("[MIGRATE] Tablas registradas (%d): %s", len(tables), ", ".join(tables))
        logger.info("[MIGRATE] Migración Alembic completada correctamente.")


if __name__ == "__main__":
    run_migration()
