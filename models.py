from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))


def utcnow():
    """Devuelve la fecha y hora actual siempre en UTC (offset-aware)."""
    return datetime.now(timezone.utc)


def ensure_utc(dt):
    """Normaliza cualquier datetime (naive o aware) a UTC offset-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class UTCDateTime(db.TypeDecorator):
    """Columna de fecha/hora UTC consistente entre PostgreSQL (TIMESTAMPTZ) y SQLite."""

    impl = db.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return ensure_utc(value)

    def process_result_value(self, value, dialect):
        return ensure_utc(value)


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(UTCDateTime, default=utcnow, index=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", index=True)  # 'student', 'teacher' (Profesor) or 'superadmin'
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(UTCDateTime, nullable=True)
    created_at = db.Column(UTCDateTime, default=utcnow, index=True)

    # Aislamiento por sección / grupo (1 a N: cada estudiante pertenece a una sección)
    section_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", use_alter=True, name="fk_users_section_id"),
        nullable=True,
        index=True,
    )

    # Borrado lógico (Soft Delete: Suspender / Restaurar)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False, index=True)
    suspended_at = db.Column(UTCDateTime, nullable=True)
    suspended_reason = db.Column(db.Text, nullable=True)
    suspended_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", use_alter=True, name="fk_users_suspended_by"),
        nullable=True,
        index=True,
    )

    @property
    def is_active(self):
        return not bool(self.is_suspended)

    # Relaciones
    classroom = db.relationship(
        "Classroom",
        foreign_keys=[section_id],
        backref=db.backref("students", lazy=True),
    )
    owned_classrooms = db.relationship(
        "Classroom",
        foreign_keys=[Classroom.teacher_id],
        backref=db.backref("teacher", lazy=True),
        lazy=True,
    )
    progress = db.relationship("LessonProgress", backref="user", lazy=True, cascade="all, delete-orphan")
    attempts = db.relationship("ExerciseAttempt", backref="user", lazy=True, cascade="all, delete-orphan")
    achievements = db.relationship("Achievement", backref="user", lazy=True, cascade="all, delete-orphan")
    streaks = db.relationship("DailyStreak", backref="user", lazy=True, cascade="all, delete-orphan")
    quiz_results = db.relationship("QuizResult", backref="user", lazy=True, cascade="all, delete-orphan")
    practice_submissions = db.relationship(
        "PracticeSubmission", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    evaluations = db.relationship(
        "SectionEvaluation", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    evaluation_sessions = db.relationship(
        "EvaluationSession", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    reset_codes = db.relationship(
        "PasswordResetCode", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    admin_username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(50), nullable=False, index=True)
    target_username = db.Column(db.String(80), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=True, index=True)
    reason = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(UTCDateTime, default=utcnow, index=True)


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = db.Column(db.String(100), nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False, index=True)
    score = db.Column(db.Integer, default=0)  # XP gained
    time_spent = db.Column(db.Integer, default=0)  # in seconds
    completed_at = db.Column(UTCDateTime, nullable=True, index=True)


class ExerciseAttempt(db.Model):
    __tablename__ = "exercise_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = db.Column(db.String(100), nullable=False, index=True)
    exercise_id = db.Column(db.String(100), nullable=False, index=True)
    passed = db.Column(db.Boolean, default=False, index=True)
    answer = db.Column(db.Text, nullable=True)
    attempted_at = db.Column(UTCDateTime, default=utcnow)


class Achievement(db.Model):
    __tablename__ = "achievements"
    __table_args__ = (
        db.UniqueConstraint("user_id", "badge_id", name="uq_achievements_user_badge"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    badge_id = db.Column(db.String(100), nullable=False, index=True)
    unlocked_at = db.Column(UTCDateTime, default=utcnow)


class DailyStreak(db.Model):
    __tablename__ = "daily_streaks"
    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_daily_streaks_user_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    lessons_completed = db.Column(db.Integer, default=0)


class QuizResult(db.Model):
    __tablename__ = "quiz_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = db.Column(db.String(100), nullable=False, index=True)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    time_taken = db.Column(db.Integer, nullable=True)
    completed_at = db.Column(UTCDateTime, default=utcnow, index=True)


class PracticeSubmission(db.Model):
    __tablename__ = "practice_submissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    problem_id = db.Column(db.String(100), nullable=False, index=True)
    code = db.Column(db.Text, nullable=False)
    passed = db.Column(db.Boolean, default=False, index=True)
    tests_passed = db.Column(db.Integer, default=0)
    tests_total = db.Column(db.Integer, default=0)
    submitted_at = db.Column(UTCDateTime, default=utcnow, index=True)


class SectionEvaluation(db.Model):
    __tablename__ = "section_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    section_id = db.Column(db.String(100), nullable=False, index=True)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False, index=True)
    time_taken = db.Column(db.Integer, nullable=True)
    attempt_number = db.Column(db.Integer, default=1)
    details_json = db.Column(db.Text, nullable=True)
    completed_at = db.Column(UTCDateTime, default=utcnow)


class EvaluationSession(db.Model):
    __tablename__ = "evaluation_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    section_key = db.Column(db.String(100), nullable=False, index=True)
    question_ids_json = db.Column(db.Text, nullable=False)
    started_at = db.Column(UTCDateTime, default=utcnow, nullable=False)
    expires_at = db.Column(UTCDateTime, nullable=False)
    submitted = db.Column(db.Boolean, default=False, nullable=False, index=True)


class PasswordResetCode(db.Model):
    __tablename__ = "password_reset_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(UTCDateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, index=True)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(UTCDateTime, default=utcnow)
