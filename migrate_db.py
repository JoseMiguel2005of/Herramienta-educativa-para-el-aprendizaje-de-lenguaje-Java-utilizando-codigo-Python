"""
Script seguro e idempotente de migración de base de datos (SQLite y PostgreSQL).

Crea las nuevas tablas (`classrooms`, `audit_logs`) y añade las nuevas columnas
en `users` (`section_id`, `is_suspended`, `suspended_at`, `suspended_reason`,
`suspended_by`) sin modificar ni borrar ningún dato existente.

Uso:
    python migrate_db.py
"""

from app import app, db, init_db, is_postgres


def run_migration():
    print(f"[MIGRATE] Motor detectado: {'PostgreSQL' if is_postgres else 'SQLite'}")
    init_db()
    with app.app_context():
        tables = sorted(db.metadata.tables.keys())
        print(f"[MIGRATE] Tablas registradas ({len(tables)}): {', '.join(tables)}")
        print("[MIGRATE] Migración completada correctamente sin pérdida de datos.")


if __name__ == "__main__":
    run_migration()
