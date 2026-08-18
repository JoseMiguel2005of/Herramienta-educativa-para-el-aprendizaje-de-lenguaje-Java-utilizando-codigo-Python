from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")  # 'student' or 'teacher'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
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
