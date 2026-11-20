from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")  # 'student', 'teacher' (Profesor) or 'superadmin'
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Aislamiento por sección / grupo (1 a N: cada estudiante pertenece a una sección)
    section_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", use_alter=True, name="fk_users_section_id"),
        nullable=True,
        index=True,
    )

    # Borrado lógico (Soft Delete: Suspender / Restaurar)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)
    suspended_at = db.Column(db.DateTime, nullable=True)
    suspended_reason = db.Column(db.Text, nullable=True)
    suspended_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", use_alter=True, name="fk_users_suspended_by"),
        nullable=True,
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    score = db.Column(db.Integer, default=0)  # XP gained
    time_spent = db.Column(db.Integer, default=0)  # in seconds
    completed_at = db.Column(db.DateTime, nullable=True)


class ExerciseAttempt(db.Model):
    __tablename__ = "exercise_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    exercise_id = db.Column(db.String(100), nullable=False)
    passed = db.Column(db.Boolean, default=False)
    answer = db.Column(db.Text, nullable=True)
    attempted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Achievement(db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    badge_id = db.Column(db.String(100), nullable=False)
    unlocked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class DailyStreak(db.Model):
    __tablename__ = "daily_streaks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    lessons_completed = db.Column(db.Integer, default=0)


class QuizResult(db.Model):
    __tablename__ = "quiz_results"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    time_taken = db.Column(db.Integer, nullable=True)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class PracticeSubmission(db.Model):
    __tablename__ = "practice_submissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    problem_id = db.Column(db.String(100), nullable=False)
    code = db.Column(db.Text, nullable=False)
    passed = db.Column(db.Boolean, default=False)
    tests_passed = db.Column(db.Integer, default=0)
    tests_total = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SectionEvaluation(db.Model):
    __tablename__ = "section_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    section_id = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False)
    time_taken = db.Column(db.Integer, nullable=True)
    attempt_number = db.Column(db.Integer, default=1)
    details_json = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class PasswordResetCode(db.Model):
    __tablename__ = "password_reset_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
