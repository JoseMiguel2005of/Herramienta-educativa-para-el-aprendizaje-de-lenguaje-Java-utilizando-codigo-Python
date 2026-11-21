"""initial_schema_constraints_and_indexes

Revision ID: 2255d98a99d3
Revises:
Create Date: 2026-11-21 13:13:02.922992

Migración inicial idempotente para bases de datos nuevas y existentes (SQLite y PostgreSQL):
- Crea todas las tablas del esquema si aún no existen (evitando ciclos FK en PostgreSQL).
- Añade columnas faltantes en instalaciones pre-Alembic.
- Limpia de forma segura duplicados previos en users.email, lesson_progress, daily_streaks y achievements
  preservando el mejor progreso y actividad acumulada antes de aplicar restricciones UNIQUE.
- Convierte columnas TIMESTAMP sin zona horaria a TIMESTAMPTZ (UTC) en PostgreSQL existente.
- Aplica UniqueConstraint e índices en llaves foráneas y columnas filtradas frecuentemente.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2255d98a99d3'
down_revision = None
branch_labels = None
depends_on = None


def _has_index(inspector, table_name, index_name, columns=None, unique=None):
    existing = inspector.get_indexes(table_name)
    for idx in existing:
        if idx.get("name") == index_name:
            return True
        if columns is not None and list(idx.get("column_names") or []) == list(columns):
            if unique is None or bool(idx.get("unique")) == bool(unique):
                return True
    return False


def _has_unique_constraint(inspector, table_name, constraint_name, columns):
    cols = list(columns)
    try:
        for uq in inspector.get_unique_constraints(table_name):
            if uq.get("name") == constraint_name or list(uq.get("column_names") or []) == cols:
                return True
    except NotImplementedError:
        pass
    for idx in inspector.get_indexes(table_name):
        if idx.get("unique") and list(idx.get("column_names") or []) == cols:
            return True
    return False


def _has_fk(inspector, table_name, constraint_name, constrained_columns, referred_table):
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("name") == constraint_name:
            return True
        if (
            list(fk.get("constrained_columns") or []) == list(constrained_columns)
            and fk.get("referred_table") == referred_table
        ):
            return True
    return False


def _ensure_index(inspector, table_name, index_name, columns, unique=False):
    if not _has_index(inspector, table_name, index_name, columns=columns, unique=unique):
        op.create_index(index_name, table_name, columns, unique=unique)


def _deduplicate_legacy_rows(conn):
    """Limpia duplicados históricos preservando el máximo progreso/actividad antes de crear UNIQUE."""
    # 1) Normalizar emails vacíos y deduplicar correos repetidos (sin borrar usuarios)
    conn.execute(
        sa.text("UPDATE users SET email = NULL WHERE email IS NOT NULL AND TRIM(email) = ''")
    )
    conn.execute(
        sa.text("UPDATE users SET email = LOWER(TRIM(email)) WHERE email IS NOT NULL")
    )
    dup_emails = conn.execute(
        sa.text(
            "SELECT email FROM users WHERE email IS NOT NULL "
            "GROUP BY email HAVING COUNT(*) > 1"
        )
    ).fetchall()
    for (dup_email,) in dup_emails:
        rows = conn.execute(
            sa.text(
                "SELECT id FROM users WHERE email = :email "
                "ORDER BY CASE WHEN is_suspended THEN 1 ELSE 0 END ASC, id ASC"
            ),
            {"email": dup_email},
        ).fetchall()
        keep_id = rows[0][0]
        for (other_id,) in rows[1:]:
            conn.execute(
                sa.text("UPDATE users SET email = NULL WHERE id = :uid"),
                {"uid": other_id},
            )

    # 2) Deduplicar lesson_progress(user_id, lesson_id) conservando completed/score/time_spent agregados
    dup_lp = conn.execute(
        sa.text(
            "SELECT user_id, lesson_id FROM lesson_progress "
            "GROUP BY user_id, lesson_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    for user_id, lesson_id in dup_lp:
        rows = conn.execute(
            sa.text(
                "SELECT id, completed, score, time_spent, completed_at "
                "FROM lesson_progress "
                "WHERE user_id = :uid AND lesson_id = :lid "
                "ORDER BY CASE WHEN completed THEN 0 ELSE 1 END ASC, id ASC"
            ),
            {"uid": user_id, "lid": lesson_id},
        ).fetchall()
        keep_id = rows[0][0]
        merged_completed = any(bool(r[1]) for r in rows)
        merged_score = max(int(r[2] or 0) for r in rows)
        merged_time = sum(int(r[3] or 0) for r in rows)
        completed_dates = [r[4] for r in rows if r[4] is not None]
        merged_completed_at = min(completed_dates) if completed_dates else None

        conn.execute(
            sa.text(
                "UPDATE lesson_progress "
                "SET completed = :completed, score = :score, time_spent = :time_spent, "
                "completed_at = :completed_at "
                "WHERE id = :keep_id"
            ),
            {
                "completed": merged_completed,
                "score": merged_score,
                "time_spent": merged_time,
                "completed_at": merged_completed_at,
                "keep_id": keep_id,
            },
        )
        for row in rows[1:]:
            conn.execute(
                sa.text("DELETE FROM lesson_progress WHERE id = :rid"),
                {"rid": row[0]},
            )

    # 3) Deduplicar daily_streaks(user_id, date) sumando lessons_completed
    dup_ds = conn.execute(
        sa.text(
            "SELECT user_id, date FROM daily_streaks "
            "GROUP BY user_id, date HAVING COUNT(*) > 1"
        )
    ).fetchall()
    for user_id, streak_date in dup_ds:
        rows = conn.execute(
            sa.text(
                "SELECT id, lessons_completed FROM daily_streaks "
                "WHERE user_id = :uid AND date = :dt ORDER BY id ASC"
            ),
            {"uid": user_id, "dt": streak_date},
        ).fetchall()
        keep_id = rows[0][0]
        total_lessons = sum(int(r[1] or 0) for r in rows)
        conn.execute(
            sa.text("UPDATE daily_streaks SET lessons_completed = :cnt WHERE id = :keep_id"),
            {"cnt": total_lessons, "keep_id": keep_id},
        )
        for row in rows[1:]:
            conn.execute(
                sa.text("DELETE FROM daily_streaks WHERE id = :rid"),
                {"rid": row[0]},
            )

    # 4) Deduplicar achievements(user_id, badge_id) conservando la primera fecha de desbloqueo
    dup_ach = conn.execute(
        sa.text(
            "SELECT user_id, badge_id FROM achievements "
            "GROUP BY user_id, badge_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    for user_id, badge_id in dup_ach:
        rows = conn.execute(
            sa.text(
                "SELECT id, unlocked_at FROM achievements "
                "WHERE user_id = :uid AND badge_id = :bid ORDER BY id ASC"
            ),
            {"uid": user_id, "bid": badge_id},
        ).fetchall()
        keep_id = rows[0][0]
        unlocked_dates = [r[1] for r in rows if r[1] is not None]
        if unlocked_dates:
            conn.execute(
                sa.text("UPDATE achievements SET unlocked_at = :u_at WHERE id = :keep_id"),
                {"u_at": min(unlocked_dates), "keep_id": keep_id},
            )
        for row in rows[1:]:
            conn.execute(
                sa.text("DELETE FROM achievements WHERE id = :rid"),
                {"rid": row[0]},
            )


def _upgrade_postgres_timestamps_to_timestamptz(conn):
    """En instalaciones PostgreSQL existentes, convierte TIMESTAMP naive a TIMESTAMPTZ (UTC)."""
    ts_columns = [
        ("users", "locked_until"),
        ("users", "created_at"),
        ("users", "suspended_at"),
        ("classrooms", "created_at"),
        ("audit_logs", "created_at"),
        ("lesson_progress", "completed_at"),
        ("exercise_attempts", "attempted_at"),
        ("achievements", "unlocked_at"),
        ("quiz_results", "completed_at"),
        ("practice_submissions", "submitted_at"),
        ("section_evaluations", "completed_at"),
        ("evaluation_sessions", "started_at"),
        ("evaluation_sessions", "expires_at"),
        ("password_reset_codes", "expires_at"),
        ("password_reset_codes", "created_at"),
    ]
    for table_name, col_name in ts_columns:
        row = conn.execute(
            sa.text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = :tbl AND column_name = :col"
            ),
            {"tbl": table_name, "col": col_name},
        ).fetchone()
        if row and row[0] == "timestamp without time zone":
            conn.execute(
                sa.text(
                    f'ALTER TABLE "{table_name}" '
                    f'ALTER COLUMN "{col_name}" TYPE TIMESTAMP WITH TIME ZONE '
                    f'USING "{col_name}" AT TIME ZONE \'UTC\''
                )
            )


def upgrade():
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1) Crear tablas faltantes (orden seguro sin ciclos FK en PostgreSQL)
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(length=80), nullable=False),
            sa.Column('email', sa.String(length=120), nullable=True),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=True),
            sa.Column('failed_login_attempts', sa.Integer(), nullable=True),
            sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('section_id', sa.Integer(), nullable=True),
            sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('suspended_reason', sa.Text(), nullable=True),
            sa.Column('suspended_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['suspended_by'], ['users.id'], name='fk_users_suspended_by'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        )
    else:
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        with op.batch_alter_table('users', schema=None) as batch_op:
            if 'email' not in user_cols:
                batch_op.add_column(sa.Column('email', sa.String(length=120), nullable=True))
            if 'failed_login_attempts' not in user_cols:
                batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
            if 'locked_until' not in user_cols:
                batch_op.add_column(sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
            if 'section_id' not in user_cols:
                batch_op.add_column(sa.Column('section_id', sa.Integer(), nullable=True))
            if 'is_suspended' not in user_cols:
                batch_op.add_column(sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default=sa.false()))
            if 'suspended_at' not in user_cols:
                batch_op.add_column(sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True))
            if 'suspended_reason' not in user_cols:
                batch_op.add_column(sa.Column('suspended_reason', sa.Text(), nullable=True))
            if 'suspended_by' not in user_cols:
                batch_op.add_column(sa.Column('suspended_by', sa.Integer(), nullable=True))
        conn.execute(sa.text("UPDATE users SET is_suspended = FALSE WHERE is_suspended IS NULL"))

    if 'classrooms' not in existing_tables:
        op.create_table(
            'classrooms',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('code', sa.String(length=20), nullable=False),
            sa.Column('teacher_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], name=op.f('fk_classrooms_teacher_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_classrooms')),
        )

    # Añadir FK diferida users.section_id -> classrooms.id (tras existir classrooms)
    inspector = sa.inspect(conn)
    if not _has_fk(inspector, 'users', 'fk_users_section_id', ['section_id'], 'classrooms'):
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_foreign_key('fk_users_section_id', 'classrooms', ['section_id'], ['id'])

    if 'achievements' not in existing_tables:
        op.create_table(
            'achievements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('badge_id', sa.String(length=100), nullable=False),
            sa.Column('unlocked_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_achievements_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_achievements')),
            sa.UniqueConstraint('user_id', 'badge_id', name='uq_achievements_user_badge'),
        )

    if 'daily_streaks' not in existing_tables:
        op.create_table(
            'daily_streaks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('lessons_completed', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_daily_streaks_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_streaks')),
            sa.UniqueConstraint('user_id', 'date', name='uq_daily_streaks_user_date'),
        )

    if 'evaluation_sessions' not in existing_tables:
        op.create_table(
            'evaluation_sessions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('section_key', sa.String(length=100), nullable=False),
            sa.Column('question_ids_json', sa.Text(), nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('submitted', sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_evaluation_sessions_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_sessions')),
        )

    if 'exercise_attempts' not in existing_tables:
        op.create_table(
            'exercise_attempts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('lesson_id', sa.String(length=100), nullable=False),
            sa.Column('exercise_id', sa.String(length=100), nullable=False),
            sa.Column('passed', sa.Boolean(), nullable=True),
            sa.Column('answer', sa.Text(), nullable=True),
            sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_exercise_attempts_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_exercise_attempts')),
        )

    if 'lesson_progress' not in existing_tables:
        op.create_table(
            'lesson_progress',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('lesson_id', sa.String(length=100), nullable=False),
            sa.Column('completed', sa.Boolean(), nullable=True),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('time_spent', sa.Integer(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_lesson_progress_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_lesson_progress')),
            sa.UniqueConstraint('user_id', 'lesson_id', name='uq_lesson_progress_user_lesson'),
        )

    if 'password_reset_codes' not in existing_tables:
        op.create_table(
            'password_reset_codes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=6), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=True),
            sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_password_reset_codes_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_password_reset_codes')),
        )
    else:
        prc_cols = {c["name"] for c in inspector.get_columns("password_reset_codes")}
        if 'failed_attempts' not in prc_cols:
            with op.batch_alter_table('password_reset_codes', schema=None) as batch_op:
                batch_op.add_column(sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'))
        conn.execute(
            sa.text("UPDATE password_reset_codes SET failed_attempts = 0 WHERE failed_attempts IS NULL")
        )

    if 'practice_submissions' not in existing_tables:
        op.create_table(
            'practice_submissions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('problem_id', sa.String(length=100), nullable=False),
            sa.Column('code', sa.Text(), nullable=False),
            sa.Column('passed', sa.Boolean(), nullable=True),
            sa.Column('tests_passed', sa.Integer(), nullable=True),
            sa.Column('tests_total', sa.Integer(), nullable=True),
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_practice_submissions_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_practice_submissions')),
        )

    if 'quiz_results' not in existing_tables:
        op.create_table(
            'quiz_results',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('quiz_id', sa.String(length=100), nullable=False),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('total', sa.Integer(), nullable=True),
            sa.Column('time_taken', sa.Integer(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_quiz_results_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_quiz_results')),
        )

    if 'section_evaluations' not in existing_tables:
        op.create_table(
            'section_evaluations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('section_id', sa.String(length=100), nullable=False),
            sa.Column('score', sa.Integer(), nullable=True),
            sa.Column('total', sa.Integer(), nullable=True),
            sa.Column('percentage', sa.Float(), nullable=True),
            sa.Column('passed', sa.Boolean(), nullable=True),
            sa.Column('time_taken', sa.Integer(), nullable=True),
            sa.Column('attempt_number', sa.Integer(), nullable=True),
            sa.Column('details_json', sa.Text(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_section_evaluations_user_id_users')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_section_evaluations')),
        )

    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('admin_id', sa.Integer(), nullable=True),
            sa.Column('admin_username', sa.String(length=80), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('target_username', sa.String(length=80), nullable=True),
            sa.Column('section_id', sa.Integer(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['admin_id'], ['users.id'], name=op.f('fk_audit_logs_admin_id_users')),
            sa.ForeignKeyConstraint(['section_id'], ['classrooms.id'], name=op.f('fk_audit_logs_section_id_classrooms')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')),
        )

    # 2) Limpieza segura de duplicados históricos antes de crear UNIQUE constraints / índices
    if existing_tables:
        _deduplicate_legacy_rows(conn)
        if dialect_name == "postgresql":
            _upgrade_postgres_timestamps_to_timestamptz(conn)

    # 3) Garantizar UniqueConstraint en tablas existentes pre-Alembic
    inspector = sa.inspect(conn)
    if not _has_unique_constraint(inspector, 'lesson_progress', 'uq_lesson_progress_user_lesson', ['user_id', 'lesson_id']):
        with op.batch_alter_table('lesson_progress', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_lesson_progress_user_lesson', ['user_id', 'lesson_id'])

    if not _has_unique_constraint(inspector, 'daily_streaks', 'uq_daily_streaks_user_date', ['user_id', 'date']):
        with op.batch_alter_table('daily_streaks', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_daily_streaks_user_date', ['user_id', 'date'])

    if not _has_unique_constraint(inspector, 'achievements', 'uq_achievements_user_badge', ['user_id', 'badge_id']):
        with op.batch_alter_table('achievements', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_achievements_user_badge', ['user_id', 'badge_id'])

    # 4) Garantizar todos los índices (únicos, llaves foráneas y columnas filtradas)
    inspector = sa.inspect(conn)
    index_specs = [
        # users
        ('users', 'ix_users_username', ['username'], True),
        ('users', 'ix_users_email', ['email'], True),
        ('users', 'ix_users_role', ['role'], False),
        ('users', 'ix_users_created_at', ['created_at'], False),
        ('users', 'ix_users_section_id', ['section_id'], False),
        ('users', 'ix_users_is_suspended', ['is_suspended'], False),
        ('users', 'ix_users_suspended_by', ['suspended_by'], False),
        # classrooms
        ('classrooms', 'ix_classrooms_code', ['code'], True),
        ('classrooms', 'ix_classrooms_teacher_id', ['teacher_id'], False),
        ('classrooms', 'ix_classrooms_created_at', ['created_at'], False),
        # audit_logs
        ('audit_logs', 'ix_audit_logs_admin_id', ['admin_id'], False),
        ('audit_logs', 'ix_audit_logs_action', ['action'], False),
        ('audit_logs', 'ix_audit_logs_section_id', ['section_id'], False),
        ('audit_logs', 'ix_audit_logs_created_at', ['created_at'], False),
        # lesson_progress
        ('lesson_progress', 'ix_lesson_progress_user_id', ['user_id'], False),
        ('lesson_progress', 'ix_lesson_progress_lesson_id', ['lesson_id'], False),
        ('lesson_progress', 'ix_lesson_progress_completed', ['completed'], False),
        ('lesson_progress', 'ix_lesson_progress_completed_at', ['completed_at'], False),
        # exercise_attempts
        ('exercise_attempts', 'ix_exercise_attempts_user_id', ['user_id'], False),
        ('exercise_attempts', 'ix_exercise_attempts_lesson_id', ['lesson_id'], False),
        ('exercise_attempts', 'ix_exercise_attempts_exercise_id', ['exercise_id'], False),
        ('exercise_attempts', 'ix_exercise_attempts_passed', ['passed'], False),
        # achievements
        ('achievements', 'ix_achievements_user_id', ['user_id'], False),
        ('achievements', 'ix_achievements_badge_id', ['badge_id'], False),
        # daily_streaks
        ('daily_streaks', 'ix_daily_streaks_user_id', ['user_id'], False),
        ('daily_streaks', 'ix_daily_streaks_date', ['date'], False),
        # quiz_results
        ('quiz_results', 'ix_quiz_results_user_id', ['user_id'], False),
        ('quiz_results', 'ix_quiz_results_quiz_id', ['quiz_id'], False),
        ('quiz_results', 'ix_quiz_results_completed_at', ['completed_at'], False),
        # practice_submissions
        ('practice_submissions', 'ix_practice_submissions_user_id', ['user_id'], False),
        ('practice_submissions', 'ix_practice_submissions_problem_id', ['problem_id'], False),
        ('practice_submissions', 'ix_practice_submissions_passed', ['passed'], False),
        ('practice_submissions', 'ix_practice_submissions_submitted_at', ['submitted_at'], False),
        # section_evaluations
        ('section_evaluations', 'ix_section_evaluations_user_id', ['user_id'], False),
        ('section_evaluations', 'ix_section_evaluations_section_id', ['section_id'], False),
        ('section_evaluations', 'ix_section_evaluations_passed', ['passed'], False),
        # evaluation_sessions
        ('evaluation_sessions', 'ix_evaluation_sessions_user_id', ['user_id'], False),
        ('evaluation_sessions', 'ix_evaluation_sessions_section_key', ['section_key'], False),
        ('evaluation_sessions', 'ix_evaluation_sessions_submitted', ['submitted'], False),
        # password_reset_codes
        ('password_reset_codes', 'ix_password_reset_codes_user_id', ['user_id'], False),
        ('password_reset_codes', 'ix_password_reset_codes_used', ['used'], False),
    ]
    for tbl, idx_name, cols, is_unique in index_specs:
        _ensure_index(inspector, tbl, idx_name, cols, unique=is_unique)


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if _has_fk(inspector, 'users', 'fk_users_section_id', ['section_id'], 'classrooms'):
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_constraint('fk_users_section_id', type_='foreignkey')

    for tbl in [
        'audit_logs',
        'section_evaluations',
        'quiz_results',
        'practice_submissions',
        'password_reset_codes',
        'lesson_progress',
        'exercise_attempts',
        'evaluation_sessions',
        'daily_streaks',
        'achievements',
        'classrooms',
        'users',
    ]:
        if tbl in set(sa.inspect(conn).get_table_names()):
            op.drop_table(tbl)
