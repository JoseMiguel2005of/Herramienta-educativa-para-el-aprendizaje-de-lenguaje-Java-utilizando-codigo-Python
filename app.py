import csv
from io import StringIO
import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

import requests as http_requests
from flask import (Flask, Response, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from werkzeug.security import check_password_hash, generate_password_hash

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from content_loader import (get_lesson, get_lesson_title, get_reference,
                            load_ui_strings, load_quiz, load_all_quizzes,
                            load_examples_catalog, get_example_by_id,
                            load_practice_problems, get_practice_problem,
                            get_evaluation_for_section, load_all_evaluations)
from models import (ExerciseAttempt, LessonProgress, User, QuizResult,
                    PracticeSubmission, DailyStreak, SectionEvaluation,
                    PasswordResetCode, db)
from search_index import search_lessons
from translator import translate

app = Flask(__name__)
_secret = os.environ.get("SECRET_KEY")
if not _secret:
    _secret = os.urandom(32).hex()
    print("[AVISO] SECRET_KEY no configurada. Usando clave temporal.", flush=True)
app.secret_key = _secret

TEACHER_SECRET_CODE = os.environ.get("TEACHER_SECRET_CODE", "")

# Database Configuration
database_url = os.environ.get("DATABASE_URL")
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if "sslmode=" not in database_url and "localhost" not in database_url and "127.0.0.1" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    if is_vercel:
        # Serverless: use NullPool so each invocation opens/closes its own connection
        # This prevents accumulating idle connections that exhaust Supabase's pool_size limit
        from sqlalchemy.pool import NullPool
        engine_options = {
            "pool_pre_ping": True,
            "poolclass": NullPool,
        }
    else:
        engine_options = {
            "pool_pre_ping": True,
            "pool_size": 2,
            "max_overflow": 3,
            "pool_recycle": 280,
        }
else:
    # On Vercel serverless, working directory is read-only (/var/task), write SQLite to /tmp
    if is_vercel:
        sqlite_path = "/tmp/database_v2.sqlite"
    else:
        sqlite_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "database_v2.sqlite"
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + sqlite_path
    engine_options = {"pool_pre_ping": True}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        print(f"[ERROR in load_user]: {e}", flush=True)
        db.session.rollback()
        return None


def init_db():
    with app.app_context():
        try:
            db.create_all()
            # Migración automática: asegura que email, failed_login_attempts y locked_until existan en users
            for col_def in [
                "email VARCHAR(120)",
                "failed_login_attempts INTEGER DEFAULT 0",
                "locked_until TIMESTAMP"
            ]:
                try:
                    with db.engine.begin() as conn:
                        conn.execute(db.text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_def}"))
                except Exception:
                    try:
                        with db.engine.begin() as conn:
                            conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col_def}"))
                    except Exception:
                        pass
            print("[INFO] db.create_all() y migraciones ejecutadas con éxito.", flush=True)
        except Exception as e:
            print(f"[WARNING] db.create_all falló durante el inicio: {e}", flush=True)

init_db()

LESSON_CATEGORIES = [
    {
        "id": "py2java",
        "label_key": "cat_py2java",
        "icon": "",
        "color_class": "cat-python",
        "sections": [
            {
                "label_key": "cat_python_tutorial",
                "lessons": [
                    {"id": "py-home", "icon": ""},
                    {"id": "py-intro", "icon": ""},
                    {"id": "py-getstarted", "icon": ""},
                    {"id": "py-syntax", "icon": ""},
                    {"id": "py-comments", "icon": ""},
                    {"id": "py-variables", "icon": ""},
                    {"id": "py-datatypes", "icon": ""},
                    {"id": "py-numbers", "icon": ""},
                    {"id": "py-casting", "icon": ""},
                    {"id": "py-strings", "icon": ""},
                    {"id": "py-booleans", "icon": ""},
                    {"id": "py-operators", "icon": ""},
                    {"id": "py-lists", "icon": ""},
                    {"id": "py-tuples", "icon": ""},
                    {"id": "py-sets", "icon": ""},
                    {"id": "py-dicts", "icon": ""},
                    {"id": "py-ifelse", "icon": ""},
                    {"id": "py-while", "icon": ""},
                    {"id": "py-for", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_functions",
                "lessons": [
                    {"id": "py-functions", "icon": ""},
                    {"id": "py-lambda", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_classes",
                "lessons": [
                    {"id": "py-classes", "icon": ""},
                    {"id": "py-init", "icon": ""},
                    {"id": "py-self", "icon": ""},
                    {"id": "py-inheritance", "icon": ""},
                    {"id": "py-iterators", "icon": ""},
                    {"id": "py-polymorphism", "icon": ""},
                    {"id": "py-scope", "icon": ""},
                ],
            },
            {
                "label_key": "cat_python_modules",
                "lessons": [
                    {"id": "py-modules", "icon": ""},
                    {"id": "py-dates", "icon": ""},
                    {"id": "py-math", "icon": ""},
                    {"id": "py-json", "icon": ""},
                    {"id": "py-regex", "icon": ""},
                    {"id": "py-pip", "icon": ""},
                    {"id": "py-tryexcept", "icon": ""},
                    {"id": "py-userinput", "icon": ""},
                    {"id": "py-stringformat", "icon": ""},
                ],
            },
            {
                "label_key": "cat_file_handling",
                "lessons": [
                    {"id": "py-filehandling", "icon": ""},
                    {"id": "py-readfiles", "icon": ""},
                    {"id": "py-writefiles", "icon": ""},
                    {"id": "py-deletefiles", "icon": ""},
                ],
            },
            {
                "label_key": "cat_numpy",
                "lessons": [
                    {"id": "np-intro", "icon": ""},
                    {"id": "np-getstarted", "icon": ""},
                    {"id": "np-create", "icon": ""},
                    {"id": "np-indexing", "icon": ""},
                    {"id": "np-slicing", "icon": ""},
                    {"id": "np-datatypes", "icon": ""},
                    {"id": "np-copyview", "icon": ""},
                    {"id": "np-shape", "icon": ""},
                    {"id": "np-reshape", "icon": ""},
                    {"id": "np-iterating", "icon": ""},
                    {"id": "np-join", "icon": ""},
                    {"id": "np-split", "icon": ""},
                    {"id": "np-search", "icon": ""},
                    {"id": "np-sort", "icon": ""},
                    {"id": "np-filter", "icon": ""},
                    {"id": "np-random-intro", "icon": ""},
                    {"id": "np-datadist", "icon": ""},
                    {"id": "np-normal", "icon": ""},
                    {"id": "np-binomial", "icon": ""},
                    {"id": "np-poisson", "icon": ""},
                    {"id": "np-uniform", "icon": ""},
                    {"id": "np-logistic", "icon": ""},
                    {"id": "np-multinomial", "icon": ""},
                    {"id": "np-exponential", "icon": ""},
                    {"id": "np-chisquare", "icon": ""},
                    {"id": "np-rayleigh", "icon": ""},
                    {"id": "np-pareto", "icon": ""},
                    {"id": "np-zipf", "icon": ""},
                    {"id": "np-ufunc-intro", "icon": ""},
                    {"id": "np-create-ufunc", "icon": ""},
                    {"id": "np-arithmetic", "icon": ""},
                    {"id": "np-rounding", "icon": ""},
                    {"id": "np-logs", "icon": ""},
                    {"id": "np-summations", "icon": ""},
                    {"id": "np-products", "icon": ""},
                    {"id": "np-differences", "icon": ""},
                    {"id": "np-lcm", "icon": ""},
                    {"id": "np-gcd", "icon": ""},
                    {"id": "np-trig", "icon": ""},
                    {"id": "np-hyperbolic", "icon": ""},
                    {"id": "np-setops", "icon": ""},
                ],
            },
            {
                "label_key": "cat_pandas",
                "lessons": [
                    {"id": "pd-intro", "icon": ""},
                    {"id": "pd-getstarted", "icon": ""},
                    {"id": "pd-series", "icon": ""},
                    {"id": "pd-dataframes", "icon": ""},
                    {"id": "pd-readcsv", "icon": ""},
                    {"id": "pd-readjson", "icon": ""},
                    {"id": "pd-analyze", "icon": ""},
                    {"id": "pd-cleandata", "icon": ""},
                    {"id": "pd-emptycells", "icon": ""},
                    {"id": "pd-wrongformat", "icon": ""},
                    {"id": "pd-wrongdata", "icon": ""},
                    {"id": "pd-removedup", "icon": ""},
                    {"id": "pd-correlations", "icon": ""},
                    {"id": "pd-plotting", "icon": ""},
                ],
            },
            {
                "label_key": "cat_scipy",
                "lessons": [
                    {"id": "sc-intro", "icon": ""},
                    {"id": "sc-getstarted", "icon": ""},
                    {"id": "sc-constants", "icon": ""},
                    {"id": "sc-optimizers", "icon": ""},
                    {"id": "sc-sparsedata", "icon": ""},
                    {"id": "sc-graphs", "icon": ""},
                    {"id": "sc-spatialdata", "icon": ""},
                    {"id": "sc-matlab", "icon": ""},
                    {"id": "sc-interpolation", "icon": ""},
                    {"id": "sc-sigtests", "icon": ""},
                ],
            },
            {
                "label_key": "cat_mysql",
                "lessons": [
                    {"id": "sql-getstarted", "icon": ""},
                    {"id": "sql-createdb", "icon": ""},
                    {"id": "sql-createtable", "icon": ""},
                    {"id": "sql-insert", "icon": ""},
                    {"id": "sql-select", "icon": ""},
                    {"id": "sql-where", "icon": ""},
                    {"id": "sql-orderby", "icon": ""},
                    {"id": "sql-delete", "icon": ""},
                    {"id": "sql-droptable", "icon": ""},
                    {"id": "sql-update", "icon": ""},
                    {"id": "sql-limit", "icon": ""},
                    {"id": "sql-join", "icon": ""},
                ],
            },
            {
                "label_key": "cat_mongodb",
                "lessons": [
                    {"id": "mongo-getstarted", "icon": ""},
                    {"id": "mongo-createdb", "icon": ""},
                    {"id": "mongo-collection", "icon": ""},
                    {"id": "mongo-insert", "icon": ""},
                    {"id": "mongo-find", "icon": ""},
                    {"id": "mongo-query", "icon": ""},
                    {"id": "mongo-sort", "icon": ""},
                    {"id": "mongo-delete", "icon": ""},
                    {"id": "mongo-drop", "icon": ""},
                    {"id": "mongo-update", "icon": ""},
                    {"id": "mongo-limit", "icon": ""},
                ],
            },
            {
                "label_key": "cat_reference",
                "lessons": [
                    {"id": "ref-functions", "icon": ""},
                    {"id": "ref-strings", "icon": ""},
                    {"id": "ref-lists", "icon": ""},
                    {"id": "ref-dicts", "icon": ""},
                    {"id": "ref-tuples", "icon": ""},
                    {"id": "ref-sets", "icon": ""},
                    {"id": "ref-file", "icon": ""},
                    {"id": "ref-keywords", "icon": ""},
                    {"id": "ref-exceptions", "icon": ""},
                    {"id": "ref-glossary", "icon": ""},
                ],
            },
            {
                "label_key": "cat_section_exercises",
                "lessons": [
                    {"id": "ex-syntax", "icon": ""},
                    {"id": "ex-comments", "icon": ""},
                    {"id": "ex-variables", "icon": ""},
                    {"id": "ex-datatypes", "icon": ""},
                    {"id": "ex-numbers", "icon": ""},
                    {"id": "ex-strings", "icon": ""},
                    {"id": "ex-booleans", "icon": ""},
                    {"id": "ex-operators", "icon": ""},
                    {"id": "ex-lists", "icon": ""},
                    {"id": "ex-tuples", "icon": ""},
                    {"id": "ex-sets", "icon": ""},
                    {"id": "ex-dicts", "icon": ""},
                    {"id": "ex-ifelse", "icon": ""},
                    {"id": "ex-while", "icon": ""},
                    {"id": "ex-for", "icon": ""},
                    {"id": "ex-functions", "icon": ""},
                    {"id": "ex-lambda", "icon": ""},
                    {"id": "ex-classes", "icon": ""},
                    {"id": "ex-inheritance", "icon": ""},
                    {"id": "ex-modules", "icon": ""},
                ],
            },
            {
                "label_key": "cat_section_quiz",
                "lessons": [
                    {"id": "quiz-python-basics", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-strings", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-collections", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-control", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-functions", "icon": "", "type": "quiz"},
                    {"id": "quiz-python-oop", "icon": "", "type": "quiz"},
                ],
            },
            {
                "label_key": "cat_section_examples",
                "lessons": [
                    {"id": "examples-hub", "icon": "", "type": "examples"}
                ],
            },
            {
                "label_key": "cat_section_practice",
                "lessons": [
                    {"id": "practice-hub", "icon": "", "type": "practice"}
                ],
            },
        ],
    }
]

# Lista plana para compatibilidad
LESSONS = [
    lesson
    for cat in LESSON_CATEGORIES
    for sec in cat["sections"]
    for lesson in sec["lessons"]
]

REFERENCE_CATEGORIES = [
    "basico",
    "tipos",
    "estructuras",
    "funciones",
    "entrada_salida",
    "orientado_objetos",
    "manejo_errores",
    "manipulacion_datos",
]


def get_lesson_category(lesson_id):
    """Devuelve la categoría a la que pertenece una lección."""
    for cat in LESSON_CATEGORIES:
        for sec in cat["sections"]:
            for lesson in sec["lessons"]:
                if lesson["id"] == lesson_id:
                    return cat
    return None


def get_lesson_neighbors(lesson_id):
    """Devuelve (prev_id, next_id) para la navegación entre lecciones dentro de la misma categoría."""
    for cat in LESSON_CATEGORIES:
        cat_lessons = [lesson_item for sec in cat["sections"] for lesson_item in sec["lessons"]]
        ids = [lesson_item["id"] for lesson_item in cat_lessons]
        if lesson_id in ids:
            idx = ids.index(lesson_id)
            prev_id = ids[idx - 1] if idx > 0 else None
            next_id = ids[idx + 1] if idx < len(ids) - 1 else None
            return prev_id, next_id
    return None, None


@app.route("/")
def index():
    return redirect(url_for("lesson", lesson_id="py-home"))


@app.route("/leccion/<lesson_id>")
def lesson(lesson_id):
    if lesson_id.startswith("quiz-"):
        return redirect(url_for("quiz", topic=lesson_id))
    if lesson_id == "practice-hub":
        return redirect(url_for("practice_list"))
    if lesson_id == "examples-hub":
        return redirect(url_for("examples"))
    if lesson_id.startswith("ex-"):
        return redirect(url_for("exercise_topic", topic=lesson_id))

    valid_ids = [lesson_item["id"] for lesson_item in LESSONS]
    if lesson_id not in valid_ids:
        lesson_id = "py-home"
    prev_lesson, next_lesson = get_lesson_neighbors(lesson_id)
    current_category = get_lesson_category(lesson_id)
    current_category_id = current_category["id"] if current_category else "py2java"

    # Verificar prerrequisito
    prereq_warning = False
    prereq_lesson_id = None
    prereq_lesson_title = None
    if prev_lesson and lesson_id != "py-home":
        try:
            user = get_current_user()
            if user and user.id:
                prev_completed = LessonProgress.query.filter_by(
                    user_id=user.id, lesson_id=prev_lesson, completed=True
                ).first()
                if not prev_completed:
                    prereq_warning = True
                    prereq_lesson_id = prev_lesson
                    prereq_lesson_title = get_lesson_title(prev_lesson) or prev_lesson
        except Exception as e:
            print(f"[WARNING] Prerequisite check failed (DB issue): {e}", flush=True)
            db.session.rollback()

    return render_template(
        "lesson.html",
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        current_lesson=lesson_id,
        current_category=current_category_id,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        prereq_warning=prereq_warning,
        prereq_lesson_id=prereq_lesson_id,
        prereq_lesson_title=prereq_lesson_title,
        page="lesson",
        role=session.get("role", "student"),
    )


# --- Laboratorio de práctica ---
@app.route("/practica")
@app.route("/practice")
def practice_list():
    data = load_practice_problems()
    problems = data.get("problems", [])
    
    # Check completed problems for current user
    completed_ids = []
    if current_user.is_authenticated:
        completed_submissions = PracticeSubmission.query.filter_by(user_id=current_user.id, passed=True).all()
        completed_ids = [sub.problem_id for sub in completed_submissions]
        
    return render_template(
        "practice_list.html",
        problems=problems,
        completed_ids=completed_ids,
        categories=LESSON_CATEGORIES,
        page="practice"
    )

@app.route("/practica/<problem_id>")
def practice_editor(problem_id):
    problem = get_practice_problem(problem_id)
    if not problem:
        return redirect(url_for("practice_list"))
        
    # Check if previously completed to show starter code or previous answer
    previous_code = problem.get("starter_code", "")
    if current_user.is_authenticated:
        last_submission = PracticeSubmission.query.filter_by(user_id=current_user.id, problem_id=problem_id).order_by(PracticeSubmission.submitted_at.desc()).first()
        if last_submission:
            previous_code = last_submission.code

    return render_template(
        "practice_editor.html",
        problem=problem,
        previous_code=previous_code,
        categories=LESSON_CATEGORIES,
        page="practice"
    )

@app.route("/api/submit_practice", methods=["POST"])
@login_required
def api_submit_practice():
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id", "unknown")
    code = data.get("code", "")
    passed = data.get("passed", False)
    tests_passed = data.get("tests_passed", 0)
    tests_total = data.get("tests_total", 0)
    
    user = current_user
    
    # Check if previously passed BEFORE adding the new submission
    prev_passed = PracticeSubmission.query.filter_by(user_id=user.id, problem_id=problem_id, passed=True).first()

    submission = PracticeSubmission(
        user_id=user.id,
        problem_id=problem_id,
        code=code,
        passed=passed,
        tests_passed=tests_passed,
        tests_total=tests_total
    )
    db.session.add(submission)
    
    xp_gained = 0
    if passed and not prev_passed:
        xp_gained = 50
        record_daily_activity(user.id)

        # Update LessonProgress record for practice XP tracking
        lp = LessonProgress.query.filter_by(
            user_id=user.id, lesson_id=f"practice-{problem_id}"
        ).first()
        if not lp:
            lp = LessonProgress(
                user_id=user.id,
                lesson_id=f"practice-{problem_id}",
                completed=True,
                score=xp_gained,
                completed_at=datetime.now(timezone.utc)
            )
            db.session.add(lp)
        else:
            lp.score = (lp.score or 0) + xp_gained

    db.session.commit()
    
    new_stats = get_progress_summary(user)
    lvl_info = get_level_info(new_stats["total_xp"])
    
    return jsonify({
        "ok": True,
        "xp_gained": xp_gained,
        "new_total": new_stats["total_xp"],
        "level": lvl_info["level"],
        "title": lvl_info["title"],
        "streak": new_stats["streak"]
    })

# --- Glosario ---
@app.route("/glosario")
def glossary():
    return render_template(
        "glossary.html",
        categories=LESSON_CATEGORIES,
        page="glossary",
    )


@app.route("/referencia")
def reference():
    return render_template(
        "reference.html",
        lessons=LESSONS,
        categories=LESSON_CATEGORIES,
        ref_categories=REFERENCE_CATEGORIES,
        current_category="",
        page="reference",
        role=session.get("role", "student"),
    )


@app.route("/api/traducir", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    python_code = data.get("code", "")
    class_name = data.get("class_name", "Program")

    result = translate(python_code, class_name=class_name)

    return jsonify(result)


def get_current_user():
    """Retorna el usuario autenticado o None."""
    if current_user.is_authenticated:
        return current_user
    user_id = session.get("user_id")
    if user_id:
        try:
            return db.session.get(User, user_id)
        except Exception:
            pass
    return None


@app.route("/api/progreso/ejercicio", methods=["POST"])
def api_ejercicio():
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id", "unknown")
    exercise_id = data.get("exercise_id", "unknown")
    passed = data.get("passed", False)

    user = get_current_user()
    if not user or not user.id:
        return jsonify({"ok": False})

    attempt = ExerciseAttempt(
        user_id=user.id, lesson_id=lesson_id, exercise_id=exercise_id, passed=passed
    )
    db.session.add(attempt)

    xp_gained = 0
    # Add XP if passed and not previously passed
    if passed:
        prev_passed = ExerciseAttempt.query.filter_by(
            user_id=user.id, exercise_id=exercise_id, passed=True
        ).first()
        if not prev_passed:
            xp_gained = 25

            # Update LessonProgress score
            lp = LessonProgress.query.filter_by(
                user_id=user.id, lesson_id=lesson_id
            ).first()
            if not lp:
                lp = LessonProgress(user_id=user.id, lesson_id=lesson_id)
                db.session.add(lp)
            lp.score = (lp.score or 0) + xp_gained

    if passed:
        record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


@app.route("/api/progreso/leccion", methods=["POST"])
def api_leccion():
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id")
    if not lesson_id:
        return jsonify({"ok": False})

    user = get_current_user()
    if not user or not user.id:
        return jsonify({"ok": False})

    lp = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson_id).first()

    xp_gained = 0
    if not lp:
        lp = LessonProgress(user_id=user.id, lesson_id=lesson_id, completed=True, score=0, completed_at=datetime.now(timezone.utc))
        db.session.add(lp)
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained
    elif not lp.completed:
        lp.completed = True
        lp.completed_at = datetime.now(timezone.utc)
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained

    record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


def record_daily_activity(user_id):
    """Registra la actividad diaria del usuario para el cálculo de racha."""
    if not user_id:
        return
    today = date.today()
    existing = DailyStreak.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.lessons_completed += 1
    else:
        streak_entry = DailyStreak(user_id=user_id, date=today, lessons_completed=1)
        db.session.add(streak_entry)


def calculate_streak(user_id):
    """Calcula la racha de días consecutivos de actividad."""
    if not user_id:
        return 0
    streaks = (
        DailyStreak.query.filter_by(user_id=user_id)
        .order_by(DailyStreak.date.desc())
        .all()
    )
    if not streaks:
        return 0

    today = date.today()
    # Allow today or yesterday as the start
    first_date = streaks[0].date
    if first_date != today and first_date != today - timedelta(days=1):
        return 0

    count = 1
    for i in range(1, len(streaks)):
        expected = first_date - timedelta(days=i)
        if streaks[i].date == expected:
            count += 1
        else:
            break
    return count


def get_progress_summary(user):
    if not user or not getattr(user, 'id', None):
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}
    try:
        progresses = LessonProgress.query.filter_by(user_id=user.id).all()
        completed = [p.lesson_id for p in progresses if p.completed]
        total_xp = sum((p.score or 0) for p in progresses)
        streak = calculate_streak(user.id)
        return {"completed_lessons": completed, "total_xp": total_xp, "streak": streak}
    except Exception as e:
        print(f"[WARNING] get_progress_summary error: {e}")
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}


LEVEL_TITLES = {
    1: "Iniciado",
    2: "Novato",
    3: "Aprendiz",
    4: "Entusiasta",
    5: "Programador Junior",
    6: "Programador",
    7: "Desarrollador",
    8: "Ingeniero de Software",
    9: "Arquitecto",
    10: "Maestro del Código",
    11: "Mago de la Sintaxis",
    12: "Gurú de Algoritmos",
    13: "Hacker",
    14: "Ninja del Desarrollo",
    15: "Jedi del Software",
    16: "Titán de la Programación",
    17: "Leyenda Viva",
    18: "Semidiós del Código",
    19: "Dios del Código",
    20: "Entidad Binaria Superior"
}

def get_level_info(total_xp):
    level = (total_xp // 100) + 1
    if level >= 20:
        title = LEVEL_TITLES[20]
    else:
        title = LEVEL_TITLES.get(level, "Iniciado")
    return {"level": level, "title": title}


@app.route("/api/progreso/resumen", methods=["GET"])
def api_resumen():
    user = get_current_user()
    return jsonify(get_progress_summary(user))


@app.route("/api/buscar", methods=["GET"])
def api_buscar():
    q = request.args.get("q", "")
    results = search_lessons(q)
    return jsonify(results)


@app.route("/dashboard")
@login_required
def dashboard():
    summary = get_progress_summary(current_user)
    return render_template(
        "dashboard.html",
        user=current_user,
        summary=summary,
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        page="dashboard",
    )


@app.route("/roadmap")
@login_required
def roadmap():
    summary = get_progress_summary(current_user)
    return render_template(
        "roadmap.html", categories=LESSON_CATEGORIES, summary=summary, page="roadmap"
    )


# --- Autenticación ---


@app.route("/api/db-status")
@login_required
def api_db_status():
    """Diagnóstico de la base de datos (solo profesores)."""
    if current_user.role != "teacher":
        return jsonify({"ok": False, "error": "No autorizado"}), 403
    db_type = "postgresql" if database_url else "sqlite"
    uri_masked = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "@" in uri_masked:
        prefix, rest = uri_masked.split("@", 1)
        scheme = prefix.split("://")[0]
        uri_masked = f"{scheme}://****:****@{rest}"

    status = {
        "ok": False,
        "db_type": db_type,
        "uri": uri_masked,
        "is_vercel": bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")),
        "tables": [],
        "user_count": 0,
        "error": None,
    }

    try:
        db.create_all()
        status["tables"] = list(db.metadata.tables.keys())
        status["user_count"] = User.query.count()
        status["ok"] = True
    except Exception as e:
        print(f"[ERROR in api_db_status]: {e}", flush=True)
        status["error"] = str(e)

    return jsonify(status)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = User.query.filter_by(username=username).first()
        except Exception as e:
            print(f"[ERROR in login]: {e}", flush=True)
            db.session.rollback()
            try:
                db.create_all()
                user = User.query.filter_by(username=username).first()
            except Exception as e2:
                print(f"[CRITICAL in login retry]: {e2}", flush=True)
                db.session.rollback()
                return render_template(
                    "login.html",
                    error="Error de conexión con la base de datos. Si estás en Vercel, verifica que tu DATABASE_URL esté configurada o revisa /api/db-status.",
                    categories=LESSON_CATEGORIES,
                )

        if not user:
            return render_template(
                "login.html",
                error="Usuario o contraseña incorrectos.",
                categories=LESSON_CATEGORIES,
            )

        now_utc = datetime.now(timezone.utc)

        # 1. Verificar si la cuenta está bloqueada temporalmente
        if user.locked_until:
            user_lock = user.locked_until
            if user_lock.tzinfo is None:
                user_lock = user_lock.replace(tzinfo=timezone.utc)

            if user_lock > now_utc:
                remaining_seconds = int((user_lock - now_utc).total_seconds())
                remaining_mins = max(1, (remaining_seconds + 59) // 60)
                return render_template(
                    "login.html",
                    error=f"Cuenta bloqueada temporalmente por seguridad tras 3 intentos fallidos. Intenta de nuevo en {remaining_mins} minuto(s) o usa la opción de recuperar contraseña.",
                    categories=LESSON_CATEGORIES,
                )
            else:
                user.failed_login_attempts = 0
                user.locked_until = None
                db.session.commit()

        # 2. Contraseña correcta -> restablecer intentos y loguear
        if check_password_hash(user.password_hash, password):
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()
            login_user(user)
            return redirect(
                url_for("teacher_dashboard" if user.role == "teacher" else "dashboard")
            )

        # 3. Contraseña incorrecta -> Incrementar contador de intentos fallidos
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= 3:
            user.locked_until = now_utc + timedelta(minutes=10)
            db.session.commit()
            return render_template(
                "login.html",
                error="Has alcanzado el límite de 3 intentos fallidos. Tu cuenta ha sido bloqueada temporalmente por 10 minutos por seguridad. Puedes usar '¿Olvidaste tu contraseña o usuario?' para restablecerla de inmediato.",
                categories=LESSON_CATEGORIES,
            )
        else:
            remaining = 3 - user.failed_login_attempts
            db.session.commit()
            return render_template(
                "login.html",
                error=f"Usuario o contraseña incorrectos. Te quedan {remaining} intento(s) antes del bloqueo de cuenta.",
                categories=LESSON_CATEGORIES,
            )

    return render_template("login.html", categories=LESSON_CATEGORIES)


def send_recovery_email(to_email, username, code):
    """
    Envía correo con el nombre de usuario y el código de 6 dígitos.
    Si no hay SMTP configurado o falla el envío, registra en consola
    y retorna (False, error) para modo demostración.
    """
    mail_server = os.environ.get("MAIL_SERVER")
    mail_port = int(os.environ.get("MAIL_PORT", 587))
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_sender = os.environ.get("MAIL_DEFAULT_SENDER", mail_username or "no-reply@plataforma-educativa.edu")
    mail_use_tls = os.environ.get("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")

    subject = "Recuperación de cuenta — Plataforma Educativa Python & Java"
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 8px; background: #ffffff;">
        <h2 style="color: #4CAF50; text-align: center; margin-top: 0;">Recuperación de Cuenta</h2>
        <p style="color: #333; font-size: 15px;">Hola,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.5;">Hemos recibido una solicitud para recordar tu nombre de usuario y restablecer tu contraseña.</p>
        
        <div style="background: #f4f6f8; padding: 16px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4CAF50;">
            <p style="margin: 0 0 10px 0; font-size: 15px;">👤 <strong>Tu nombre de usuario es:</strong> <span style="font-size: 16px; color: #1e88e5; font-weight: bold;">{username}</span></p>
            <p style="margin: 0; font-size: 15px;">🔑 <strong>Código de verificación:</strong> <span style="font-size: 20px; font-weight: bold; letter-spacing: 4px; color: #2e7d32; display: block; margin-top: 6px; font-family: monospace;">{code}</span></p>
        </div>
        
        <p style="font-size: 13px; color: #777; line-height: 1.4;">Este código expirará en <strong>15 minutos</strong>. Si no solicitaste este cambio, puedes ignorar este correo de forma segura.</p>
    </div>
    """

    if not mail_server or not mail_username or not mail_password:
        print(f"[MODO DEMO RECUPERACIÓN] Correo: {to_email} | Usuario: {username} | Código: {code}", flush=True)
        return False, "SMTP no configurado"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = mail_sender
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
            if mail_use_tls:
                server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_sender, [to_email], msg.as_string())
        return True, None
    except Exception as e:
        print(f"[ERROR EMAIL] Error al enviar correo a {to_email}: {e}", flush=True)
        return False, str(e)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        teacher_code = request.form.get("teacher_code", "").strip()

        if not username or not email or not password:
            return render_template(
                "register.html",
                error="Todos los campos son requeridos (usuario, correo y contraseña).",
                categories=LESSON_CATEGORIES,
            )

        if role == "teacher" and (not TEACHER_SECRET_CODE or teacher_code != TEACHER_SECRET_CODE):
            return render_template(
                "register.html",
                error="Código de profesor incorrecto. Contacta al administrador.",
                categories=LESSON_CATEGORIES,
            )

        try:
            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first() if email else None
        except Exception as e:
            print(f"[ERROR in register query]: {e}", flush=True)
            db.session.rollback()
            try:
                db.create_all()
                existing_user = User.query.filter_by(username=username).first()
                existing_email = User.query.filter_by(email=email).first() if email else None
            except Exception as e2:
                print(f"[CRITICAL in register retry]: {e2}", flush=True)
                db.session.rollback()
                return render_template(
                    "register.html",
                    error="Error de conexión con la base de datos. Si estás en Vercel, verifica que tu DATABASE_URL esté configurada o revisa /api/db-status.",
                    categories=LESSON_CATEGORIES,
                )

        if existing_user:
            return render_template(
                "register.html",
                error="El nombre de usuario ya está en uso. Elige otro.",
                categories=LESSON_CATEGORIES,
            )

        if existing_email:
            return render_template(
                "register.html",
                error="Este correo electrónico ya está registrado. Si olvidaste tu clave, usa la opción de recuperar cuenta.",
                categories=LESSON_CATEGORIES,
            )

        try:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, email=email, password_hash=hashed_pw, role=role)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            return redirect(
                url_for("teacher_dashboard" if role == "teacher" else "dashboard")
            )
        except Exception as e:
            print(f"[ERROR in register commit]: {e}", flush=True)
            db.session.rollback()
            return render_template(
                "register.html",
                error="Error al guardar el usuario en la base de datos. Intenta de nuevo.",
                categories=LESSON_CATEGORIES,
            )

    return render_template("register.html", categories=LESSON_CATEGORIES)


@app.route("/recuperar", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            return render_template("forgot_password.html", error="Debes ingresar un correo electrónico.", categories=LESSON_CATEGORIES)

        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template(
                "forgot_password.html",
                error="No encontramos ninguna cuenta registrada con este correo electrónico.",
                email=email,
                categories=LESSON_CATEGORIES
            )

        # Generar código de 6 dígitos numéricos
        code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        # Marcar códigos anteriores no usados como usados
        PasswordResetCode.query.filter_by(user_id=user.id, used=False).update({"used": True})

        reset_record = PasswordResetCode(
            user_id=user.id,
            code=code,
            expires_at=expires_at,
            used=False
        )
        db.session.add(reset_record)
        db.session.commit()

        # Enviar correo (o simular en modo demo si no hay SMTP)
        sent, _ = send_recovery_email(user.email, user.username, code)
        session["recovery_email"] = user.email
        if not sent:
            session["demo_reset_code"] = code

        return redirect(url_for("reset_password", email=user.email))

    return render_template("forgot_password.html", categories=LESSON_CATEGORIES)


@app.route("/recuperar/verificar", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    email = request.args.get("email") or session.get("recovery_email", "")
    demo_code = session.get("demo_reset_code")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        code = request.form.get("code", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not email or not code or not new_password:
            return render_template(
                "reset_password.html",
                error="Todos los campos son obligatorios.",
                email=email,
                demo_code=demo_code,
                categories=LESSON_CATEGORIES
            )

        if len(new_password) < 4:
            return render_template(
                "reset_password.html",
                error="La contraseña debe tener al menos 4 caracteres.",
                email=email,
                demo_code=demo_code,
                categories=LESSON_CATEGORIES
            )

        if new_password != confirm_password:
            return render_template(
                "reset_password.html",
                error="Las contraseñas no coinciden.",
                email=email,
                demo_code=demo_code,
                categories=LESSON_CATEGORIES
            )

        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template(
                "reset_password.html",
                error="No se encontró usuario con ese correo electrónico.",
                email=email,
                categories=LESSON_CATEGORIES
            )

        reset_record = PasswordResetCode.query.filter_by(
            user_id=user.id,
            code=code,
            used=False
        ).order_by(PasswordResetCode.created_at.desc()).first()

        if not reset_record:
            return render_template(
                "reset_password.html",
                error="El código de verificación es inválido o ya fue utilizado.",
                email=email,
                demo_code=demo_code,
                categories=LESSON_CATEGORIES
            )

        # Verificar expiración (con soporte timezone)
        record_expiry = reset_record.expires_at
        if record_expiry.tzinfo is None:
            record_expiry = record_expiry.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        if record_expiry < now_utc:
            return render_template(
                "reset_password.html",
                error="El código de verificación ha expirado (válido 15 minutos). Solicita uno nuevo.",
                email=email,
                categories=LESSON_CATEGORIES
            )

        # Actualizar contraseña, desbloquear cuenta y marcar código como usado
        user.password_hash = generate_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        reset_record.used = True
        db.session.commit()

        # Limpiar datos de sesión
        session.pop("recovery_email", None)
        session.pop("demo_reset_code", None)

        return render_template(
            "login.html",
            success="¡Contraseña actualizada con éxito! Ya puedes iniciar sesión con tu usuario y nueva clave.",
            categories=LESSON_CATEGORIES
        )

    return render_template(
        "reset_password.html",
        email=email,
        demo_code=demo_code,
        categories=LESSON_CATEGORIES
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/profesor")
@login_required
def teacher_dashboard():
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))

    # Obtener todos los estudiantes y su progreso
    students = User.query.filter_by(role="student").all()
    student_stats = []
    
    # Métricas agregadas
    total_xp = 0
    total_completed = 0
    level_counts = {}

    for s in students:
        stats = get_progress_summary(s)
        lvl_info = get_level_info(stats["total_xp"])
        title = lvl_info["title"]
        
        # Accumulate level counts
        level_counts[title] = level_counts.get(title, 0) + 1
        total_xp += stats["total_xp"]
        total_completed += len(stats["completed_lessons"])
        
        student_stats.append(
            {
                "username": s.username,
                "total_xp": stats["total_xp"],
                "completed": len(stats["completed_lessons"]),
                "level": lvl_info["level"],
                "title": title,
                "id": s.id
            }
        )

    student_stats.sort(key=lambda x: x["total_xp"], reverse=True)

    metrics = {
        "total_students": len(students),
        "avg_xp": round(total_xp / len(students)) if students else 0,
        "total_completed": total_completed,
        "level_labels": list(level_counts.keys()),
        "level_data": list(level_counts.values())
    }

    return render_template(
        "teacher_dashboard.html", 
        students=student_stats, 
        metrics=metrics,
        categories=LESSON_CATEGORIES
    )

@app.route("/profesor/estudiante/<int:student_id>/eliminar", methods=["POST"])
@login_required
def teacher_delete_student(student_id):
    if current_user.role != "teacher":
        return jsonify({"success": False, "error": "No autorizado"}), 403
        
    student = db.session.get(User, student_id)
    if student and student.role == "student":
        db.session.delete(student)
        db.session.commit()
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404


# --- Exportar CSV ---
@app.route("/profesor/export/csv")
@login_required
def teacher_export_csv():
    if current_user.role != "teacher":
        return redirect(url_for("dashboard"))
        
    students = User.query.filter_by(role="student").all()
    
    si = StringIO()
    si.write('\ufeff')  # Agregamos BOM para que Excel detecte correctamente el UTF-8
    cw = csv.writer(si, delimiter=';')  # Usamos punto y coma que es el separador esperado por Excel en español
    cw.writerow(["Username", "Total_XP", "Lecciones_Completadas", "Nivel", "Racha_Actual", "Fecha_Registro"])
    
    for s in students:
        stats = get_progress_summary(s)
        lvl_info = get_level_info(stats["total_xp"])
        cw.writerow([
            s.username,
            stats["total_xp"],
            len(stats["completed_lessons"]),
            lvl_info["title"],
            stats["streak"],
            s.created_at.strftime("%Y-%m-%d")
        ])
        
    output = si.getvalue()
    si.close()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=reporte_estudiantes.csv"}
    )


# --- Tabla de posiciones ---
@app.route("/leaderboard")
def leaderboard():
    students = User.query.filter_by(role="student").all()
    board = []
    for s in students:
        summary = get_progress_summary(s)
        lvl_info = get_level_info(summary["total_xp"])
        board.append({
            "id": s.id,
            "username": s.username,
            "total_xp": summary["total_xp"],
            "level": lvl_info["level"],
            "completed": len(summary["completed_lessons"]),
            "streak": summary["streak"],
        })
    board.sort(key=lambda x: x["total_xp"], reverse=True)

    for i, entry in enumerate(board):
        entry["rank"] = i + 1

    current_uid = current_user.id if current_user.is_authenticated else None
    return render_template(
        "leaderboard.html",
        board=board,
        current_uid=current_uid,
        categories=LESSON_CATEGORIES,
        page="leaderboard",
    )


# --- Perfil de usuario ---
@app.route("/perfil")
@app.route("/perfil/<username>")
def profile(username=None):
    if username:
        user = User.query.filter_by(username=username).first_or_404()
    elif current_user.is_authenticated:
        user = current_user
    else:
        return redirect(url_for("login"))

    summary = get_progress_summary(user)
    level = get_level_info(summary["total_xp"])["level"]

    # Últimas lecciones completadas
    recent = (
        LessonProgress.query.filter_by(user_id=user.id, completed=True)
        .order_by(LessonProgress.completed_at.desc())
        .limit(10)
        .all()
    )

    # Quiz results
    quiz_results = (
        QuizResult.query.filter_by(user_id=user.id)
        .order_by(QuizResult.completed_at.desc())
        .limit(10)
        .all()
    )

    # Exercise stats
    total_exercises = ExerciseAttempt.query.filter_by(user_id=user.id).count()
    passed_exercises = ExerciseAttempt.query.filter_by(user_id=user.id, passed=True).count()

    return render_template(
        "profile.html",
        profile_user=user,
        summary=summary,
        level=level,
        recent=recent,
        quiz_results=quiz_results,
        total_exercises=total_exercises,
        passed_exercises=passed_exercises,
        categories=LESSON_CATEGORIES,
        page="profile",
    )


# --- Certificado ---
@app.route("/certificado/<section_id>")
@login_required
def certificate(section_id):
    user = current_user
    summary = get_progress_summary(user)

    # Find the category
    target_cat = None
    for cat in LESSON_CATEGORIES:
        if cat["id"] == section_id:
            target_cat = cat
            break

    if not target_cat:
        return redirect(url_for("dashboard"))

    # Get all lessons in this category
    cat_lessons = []
    for sec in target_cat["sections"]:
        for lesson in sec["lessons"]:
            cat_lessons.append(lesson["id"])

    # Check completion
    completed_in_cat = [lid for lid in cat_lessons if lid in summary["completed_lessons"]]
    is_complete = len(completed_in_cat) >= len(cat_lessons) and len(cat_lessons) > 0

    ui = load_ui_strings()
    cat_name = ui.get(target_cat["label_key"], section_id)

    return render_template(
        "certificate.html",
        user=user,
        category_name=cat_name,
        category_id=section_id,
        total_lessons=len(cat_lessons),
        completed_lessons=len(completed_in_cat),
        is_complete=is_complete,
        completion_date=datetime.now().strftime("%d de %B de %Y"),
        categories=LESSON_CATEGORIES,
    )


# --- Tema visual ---
@app.route("/api/theme", methods=["POST"])
def toggle_theme():
    data = request.get_json(silent=True) or {}
    theme = data.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"
    session["theme"] = theme
    return jsonify({"ok": True, "theme": theme})


@app.route("/configuracion", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        session["theme"] = theme if theme in ("light", "dark") else "light"
        return redirect(request.referrer or url_for("index"))

    return redirect(url_for("index"))


@app.route("/traductor")
def traductor():
    return render_template(
        "translator.html", categories=LESSON_CATEGORIES, page="translator"
    )


# --- Tutor IA ---

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


@app.route("/api/ai/tutor", methods=["POST"])
def api_ai_tutor():
    if not GEMINI_API_KEY:
        return jsonify(
            {"ok": False, "error": "API key no configurada. Configura GEMINI_API_KEY."}
        )

    data = request.get_json(silent=True) or {}
    user_code = data.get("code", "")
    lesson_id = data.get("lesson_id", "")
    question = data.get("question", "").strip()
    mode = data.get("mode", "chat" if question else "analyze")  # 'chat', 'analyze', 'hint'
    exercise_question = data.get("exercise_question", "")
    history = data.get("history", [])

    # Load lesson context
    lesson_data = get_lesson(lesson_id)
    lesson_title = lesson_data.get("title", lesson_id)
    lesson_intro = lesson_data.get("intro", "")

    history_context = ""
    if isinstance(history, list) and history:
        history_lines = []
        for h in history[-4:]:
            if isinstance(h, dict):
                role = "Estudiante" if h.get("role") == "user" else "Tutor IA"
                txt = h.get("text", "").strip()
                if txt:
                    history_lines.append(f"{role}: {txt}")
        if history_lines:
            history_context = "Historial reciente de la conversación:\n" + "\n".join(history_lines) + "\n\n"

    if mode == "hint":
        system_prompt = f"""Eres un tutor de programación amigable y pedagógico para estudiantes que aprenden Python y Java.
Estás ayudando con un ejercicio de la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS ESTRICTAS:
- NUNCA des la respuesta directa ni el código resuelto completo al ejercicio.
- Da pistas progresivas y conceptuales que guíen al estudiante para que lo resuelva por sí mismo.
- Usa analogías simples si es posible.
- Responde en español.
- Sé breve (máximo 3-4 oraciones).
- Usa emojis para ser más amigable."""
        user_message = f"Pregunta del ejercicio: {exercise_question}\n\nIntento/código del estudiante: {user_code}\n\nDuda del estudiante: {question if question else 'No entiendo cómo resolverlo'}"

    elif mode == "chat" or question:
        system_prompt = f"""Eres un tutor de programación inteligente, didáctico y amigable para estudiantes de Python y Java.
Estás en la lección "{lesson_title}".
Contexto de la lección: {lesson_intro}

REGLAS PRINCIPALES:
- Tu prioridad número uno es responder DIRECTA y CLARAMENTE a la PREGUNTA o DUDA planteada por el estudiante.
- Si el estudiante pregunta sobre conceptos, sintaxis o dudas específicas (por ejemplo: el uso de comas, comillas, llaves, f-strings, concatenación, print, tipos de variables, etc.), explícale el porqué con paciencia y dale ejemplos sencillos.
- NO te limites a felicitar el código del editor; concéntrate en resolver la duda del estudiante.
- Si hay código en el editor, úsalo como contexto solo si la pregunta se refiere a él.
- Responde en español de forma estructurada, pedagógica y fácil de entender."""

        context_code = f"\n\nCódigo actual en el editor (solo para contexto si aplica):\n```python\n{user_code}\n```" if user_code.strip() else ""
        user_message = f"{history_context}Pregunta del estudiante: {question}{context_code}"

    else:  # mode == "analyze"
        system_prompt = f"""Eres un analizador de código Python/Java para estudiantes.
Estás en la lección "{lesson_title}".

REGLAS:
- Analiza el código del estudiante y da feedback constructivo.
- Señala errores, mejoras de estilo y buenas prácticas de forma clara y pedagógica.
- Si el código está bien, felicita al estudiante y dale un consejo o tip de mejora.
- Responde en español.
- Sé breve y directo (máximo 4-5 oraciones).
- Usa emojis para ser más amigable."""
        user_message = f"Analiza este código:\n```python\n{user_code}\n```"

    try:
        resp = http_requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [
                    {"parts": [{"text": system_prompt + "\n\n" + user_message}]}
                ],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
            },
            timeout=25,
        )
        if resp.status_code == 429:
            return jsonify(
                {
                    "ok": False,
                    "error": "Límite de peticiones alcanzado (Error 429). Por favor, espera un minuto o verifica si tu API Key tiene cuota disponible.",
                }
            )

        resp.raise_for_status()
        result = resp.json()
        ai_text = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"ok": True, "response": ai_text})
    except http_requests.exceptions.Timeout:
        return jsonify(
            {
                "ok": False,
                "error": "La IA tardó demasiado en responder. Intenta de nuevo.",
            }
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error al conectar con la IA: {str(e)}"})

# --- Ejercicios y quizzes ---

@app.route("/ejercicios/<topic>")
def exercise_topic(topic):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
    
    exercises = lesson_data.get("exercises", [])
    user = get_current_user()
    completed_exercises = []
    
    if user and user.is_authenticated:
        attempts = ExerciseAttempt.query.filter_by(user_id=user.id, lesson_id=topic, passed=True).all()
        completed_exercises = [f"{a.lesson_id}-{a.exercise_id}" for a in attempts]
        
    return render_template(
        "exercise_hub.html",
        topic=topic,
        exercise_data=lesson_data,
        exercises=exercises,
        completed_exercises=completed_exercises,
        completed_count=len(completed_exercises),
        categories=LESSON_CATEGORIES,
        page="exercises"
    )

@app.route("/ejercicio/<topic>/<int:exercise_num>")
def exercise_page(topic, exercise_num):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
        
    exercises = lesson_data.get("exercises", [])
    if exercise_num < 1 or exercise_num > len(exercises):
        return redirect(url_for("exercise_topic", topic=topic))
        
    current_exercise = exercises[exercise_num - 1]
    
    return render_template(
        "exercise.html",
        topic=topic,
        exercise_data=lesson_data,
        current_exercise=current_exercise,
        exercise_num=exercise_num,
        total_exercises=len(exercises),
        categories=LESSON_CATEGORIES,
        page="exercises"
    )


@app.route("/quiz/<topic>")
def quiz(topic):
    quiz_data = load_quiz(topic)
    if not quiz_data:
        return redirect(url_for("index"))
        
    return render_template(
        "quiz.html",
        quiz_data=quiz_data,
        categories=LESSON_CATEGORIES,
        page="quiz"
    )


@app.route("/api/quiz/resultado", methods=["POST"])
def api_quiz_result():
    data = request.get_json(silent=True) or {}
    quiz_id = data.get("quiz_id")
    score = data.get("score", 0)
    total = data.get("total", 0)
    
    user = get_current_user()
    if user and quiz_id:
        result = QuizResult(user_id=user.id, quiz_id=quiz_id, score=score, total=total)
        db.session.add(result)
        db.session.commit()
        return jsonify({"ok": True})
    return jsonify({"ok": False})


@app.route("/ejemplos")
def examples():
    catalog = load_examples_catalog()
    return render_template(
        "examples.html",
        example_categories=catalog.get("categories", []),
        categories=LESSON_CATEGORIES,
        page="examples"
    )


@app.route("/ejemplo/<example_id>")
def example_detail(example_id):
    example = get_example_by_id(example_id)
    if not example:
        return redirect(url_for("examples"))
        
    return render_template(
        "example_detail.html",
        example=example,
        categories=LESSON_CATEGORIES,
        page="examples"
    )



@app.context_processor
def inject_globals():
    ui = load_ui_strings()
    return {
        "lang": "es",
        "theme": session.get("theme", "light"),
        "t": ui,
        "get_lesson": lambda lid: get_lesson(lid),
        "get_lesson_title": lambda lid: get_lesson_title(lid),
        "get_reference": lambda cat: get_reference(cat),
    }


# --- Evaluaciones por sección ---

# Maps section label_keys to their evaluation file IDs
SECTION_EVAL_MAP = {
    "cat_python_tutorial": "eval-python-tutorial",
    "cat_python_functions": "eval-python-functions",
    "cat_python_classes": "eval-python-classes",
    "cat_python_modules": "eval-python-modules",
    "cat_file_handling": "eval-file-handling",
    "cat_numpy": "eval-numpy",
    "cat_pandas": "eval-pandas",
    "cat_scipy": "eval-scipy",
    "cat_mysql": "eval-mysql",
    "cat_mongodb": "eval-mongodb",
}


def get_section_lessons(section_key):
    """Returns the list of lesson IDs for a given section label_key."""
    for cat in LESSON_CATEGORIES:
        for sec in cat["sections"]:
            if sec["label_key"] == section_key:
                return [lesson["id"] for lesson in sec["lessons"]
                        if not lesson.get("type")]  # Exclude quiz/practice/examples entries
    return []


def get_section_eval_status(user_id, section_key):
    """Check if a section evaluation is unlocked and its pass status."""
    lesson_ids = get_section_lessons(section_key)
    if not lesson_ids:
        return {"unlocked": False, "passed": False, "best_score": 0, "attempts": 0, "completion_pct": 0}

    # Count completed lessons
    completed = LessonProgress.query.filter(
        LessonProgress.user_id == user_id,
        LessonProgress.lesson_id.in_(lesson_ids),
        LessonProgress.completed == True
    ).count()

    completion_pct = round((completed / len(lesson_ids)) * 100) if lesson_ids else 0
    unlocked = completion_pct >= 80

    # Check best evaluation result
    best_eval = SectionEvaluation.query.filter_by(
        user_id=user_id, section_id=section_key
    ).order_by(SectionEvaluation.percentage.desc()).first()

    total_attempts = SectionEvaluation.query.filter_by(
        user_id=user_id, section_id=section_key
    ).count()

    return {
        "unlocked": unlocked,
        "passed": best_eval.passed if best_eval else False,
        "best_score": round(best_eval.percentage) if best_eval else 0,
        "attempts": total_attempts,
        "completion_pct": completion_pct,
        "completed_lessons": completed,
        "total_lessons": len(lesson_ids),
    }


def generate_adaptive_questions(section_key, user_id):
    """Generate an adaptive set of questions based on completed lessons."""
    eval_data = get_evaluation_for_section(section_key)
    if not eval_data:
        return [], eval_data

    lesson_questions = eval_data.get("lesson_questions", {})
    questions_per_eval = eval_data.get("questions_per_eval", 20)

    # Get completed lessons for this user in this section
    section_lessons = get_section_lessons(section_key)
    completed_records = LessonProgress.query.filter(
        LessonProgress.user_id == user_id,
        LessonProgress.lesson_id.in_(section_lessons),
        LessonProgress.completed == True
    ).all()
    completed_ids = {r.lesson_id for r in completed_records}

    # Collect questions only from completed lessons
    available = []
    for lesson_id in completed_ids:
        qs = lesson_questions.get(lesson_id, [])
        for q in qs:
            q_copy = dict(q)
            q_copy["source_lesson"] = lesson_id
            available.append(q_copy)

    # Select random subset
    num_questions = min(questions_per_eval, len(available))
    if num_questions == 0:
        return [], eval_data

    selected = random.sample(available, num_questions)
    random.shuffle(selected)
    return selected, eval_data


@app.route("/evaluacion/<section_key>")
@login_required
def evaluation_page(section_key):
    """Render the adaptive evaluation page for a section."""
    if section_key not in SECTION_EVAL_MAP:
        return redirect(url_for("dashboard"))

    user = current_user
    status = get_section_eval_status(user.id, section_key)

    if not status["unlocked"]:
        return redirect(url_for("dashboard"))

    questions, eval_data = generate_adaptive_questions(section_key, user.id)
    if not eval_data:
        return redirect(url_for("dashboard"))

    # Strip correct answers from questions sent to client (security)
    client_questions = []
    for q in questions:
        cq = {
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "difficulty": q.get("difficulty", "medium"),
            "source_lesson": q.get("source_lesson", ""),
        }
        if q["type"] == "multiple_choice":
            cq["options"] = q["options"]
        elif q["type"] == "complete_code":
            cq["code_template"] = q["code_template"]
        elif q["type"] == "true_false":
            pass  # No extra fields needed
        client_questions.append(cq)

    # Build answer key (stored in session for validation)
    answer_key = {}
    for q in questions:
        if q["type"] == "multiple_choice":
            answer_key[q["id"]] = {"correct": q["correct"], "explanation": q["explanation"]}
        elif q["type"] == "true_false":
            answer_key[q["id"]] = {"correct": q["correct"], "explanation": q["explanation"]}
        elif q["type"] == "complete_code":
            answer_key[q["id"]] = {"correct": q["correct_answer"], "explanation": q["explanation"]}

    session[f"eval_answers_{section_key}"] = answer_key
    session[f"eval_questions_{section_key}"] = [q["id"] for q in questions]

    # Get section display info
    ui = load_ui_strings()
    section_title = ui.get(section_key, section_key)

    # Time limit: 30s per question, capped at max 10 minutes (600s)
    raw_time = eval_data.get("time_per_question", 30) * len(client_questions)
    time_limit = min(600, raw_time)

    return render_template(
        "evaluation.html",
        section_key=section_key,
        section_title=section_title,
        eval_data=eval_data,
        questions=client_questions,
        questions_json=json.dumps(client_questions, ensure_ascii=False),
        time_limit=time_limit,
        status=status,
        passing_score=eval_data.get("passing_score", 70),
        categories=LESSON_CATEGORIES,
        page="evaluation",
    )


@app.route("/api/evaluacion/resultado", methods=["POST"])
@login_required
def api_evaluation_result():
    """Process and save evaluation results."""
    data = request.get_json(silent=True) or {}
    section_key = data.get("section_key", "")
    answers = data.get("answers", {})
    time_taken = data.get("time_taken", 0)

    if section_key not in SECTION_EVAL_MAP:
        return jsonify({"ok": False, "error": "Sección inválida"})

    # Get answer key from session
    answer_key = session.get(f"eval_answers_{section_key}", {})
    question_ids = session.get(f"eval_questions_{section_key}", [])

    if not answer_key:
        return jsonify({"ok": False, "error": "Sesión de evaluación expirada"})

    user = current_user
    score = 0
    total = len(question_ids)
    details = {}

    eval_data = get_evaluation_for_section(section_key)
    question_source_map = {}
    if eval_data:
        for lesson_id, qs in eval_data.get("lesson_questions", {}).items():
            for q in qs:
                question_source_map[q["id"]] = lesson_id

    for qid in question_ids:
        key_data = answer_key.get(qid, {})
        user_answer = answers.get(qid)
        correct_val = key_data.get("correct")
        source_lesson = question_source_map.get(qid, "")

        if source_lesson not in details:
            details[source_lesson] = {"correct": 0, "total": 0, "lesson_title": get_lesson_title(source_lesson)}

        details[source_lesson]["total"] += 1

        is_correct = False
        if isinstance(correct_val, bool):
            is_correct = (user_answer == correct_val)
        elif isinstance(correct_val, int):
            try:
                is_correct = (int(user_answer) == correct_val)
            except (ValueError, TypeError):
                is_correct = False
        elif isinstance(correct_val, str):
            is_correct = (str(user_answer).strip().lower() == correct_val.strip().lower())

        if is_correct:
            score += 1
            details[source_lesson]["correct"] += 1

    percentage = round((score / total) * 100, 1) if total > 0 else 0
    passed = percentage >= 70

    # Count previous attempts
    prev_attempts = SectionEvaluation.query.filter_by(
        user_id=user.id, section_id=section_key
    ).count()

    # Save result
    evaluation = SectionEvaluation(
        user_id=user.id,
        section_id=section_key,
        score=score,
        total=total,
        percentage=percentage,
        passed=passed,
        time_taken=time_taken,
        attempt_number=prev_attempts + 1,
        details_json=json.dumps(details, ensure_ascii=False),
    )
    db.session.add(evaluation)

    # Award XP if passed for first time
    xp_gained = 0
    if passed:
        first_pass = SectionEvaluation.query.filter_by(
            user_id=user.id, section_id=section_key, passed=True
        ).first()
        if not first_pass or first_pass.id is None:
            xp_gained = 100
            # Update a LessonProgress record for XP tracking
            lp = LessonProgress.query.filter_by(
                user_id=user.id, lesson_id=f"eval-{section_key}"
            ).first()
            if not lp:
                lp = LessonProgress(
                    user_id=user.id, lesson_id=f"eval-{section_key}",
                    completed=True, score=xp_gained, completed_at=datetime.now(timezone.utc)
                )
                db.session.add(lp)
            record_daily_activity(user.id)

    db.session.commit()

    # Clean up session
    session.pop(f"eval_answers_{section_key}", None)
    session.pop(f"eval_questions_{section_key}", None)

    return jsonify({
        "ok": True,
        "score": score,
        "total": total,
        "percentage": percentage,
        "passed": passed,
        "xp_gained": xp_gained,
        "attempt_number": prev_attempts + 1,
        "details": details,
    })


@app.route("/api/evaluacion/estado/<section_key>")
def api_evaluation_status(section_key):
    """Get the evaluation readiness status for a section."""
    if not current_user.is_authenticated:
        return jsonify({"unlocked": False, "passed": False})

    status = get_section_eval_status(current_user.id, section_key)
    return jsonify(status)


@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()


if __name__ == "__main__":
    app.run(debug=True, port=5000)

