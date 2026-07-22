import os
import json
import random
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

import requests as http_requests
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from werkzeug.security import check_password_hash, generate_password_hash

from content_loader import (get_lesson, get_lesson_title, get_reference,
                            load_ui_strings, load_quiz, load_all_quizzes,
                            load_examples_catalog, get_example_by_id,
                            load_practice_problems, get_practice_problem,
                            get_evaluation_for_section, load_all_evaluations)
from models import (ExerciseAttempt, LessonProgress, User, QuizResult,
                    PracticeSubmission, DailyStreak, SectionEvaluation, db)
from search_index import search_lessons
from translator import translate

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tesis-python-java-educativo-fallback")

# Teacher registration secret code (4.10)
TEACHER_SECRET_CODE = os.environ.get("TEACHER_SECRET_CODE", "profesor2024")

# Database Configuration
database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "database_v2.sqlite"
    )
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()

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
    valid_ids = [lesson_item["id"] for lesson_item in LESSONS]
    if lesson_id not in valid_ids:
        lesson_id = "py-home"
    prev_lesson, next_lesson = get_lesson_neighbors(lesson_id)
    current_category = get_lesson_category(lesson_id)
    current_category_id = current_category["id"] if current_category else "py2java"

    # Prerequisite check (Sprint 3 — 2.10)
    prereq_warning = False
    prereq_lesson_id = None
    prereq_lesson_title = None
    if prev_lesson and lesson_id != "py-home":
        user = get_current_user()
        prev_completed = LessonProgress.query.filter_by(
            user_id=user.id, lesson_id=prev_lesson, completed=True
        ).first()
        if not prev_completed:
            prereq_warning = True
            prereq_lesson_id = prev_lesson
            prereq_lesson_title = get_lesson_title(prev_lesson) or prev_lesson

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


# ===== PRACTICE LAB (Sprint 5 — 2.3) =====
@app.route("/practica")
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
    if passed:
        # Give XP only if not previously completed
        prev_passed = PracticeSubmission.query.filter_by(user_id=user.id, problem_id=problem_id, passed=True).first()
        if not prev_passed:
            xp_gained = 50
            record_daily_activity(user.id)
            
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

# ===== GLOSSARY (Sprint 3 — 2.8) =====
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
    if current_user.is_authenticated:
        return current_user
    if "user_id" not in session:
        user = User(username=f"Estudiante_{os.urandom(3).hex()}", password_hash="")
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
    return User.query.get(session["user_id"])


@app.route("/api/progreso/ejercicio", methods=["POST"])
def api_ejercicio():
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id", "unknown")
    exercise_id = data.get("exercise_id", "unknown")
    passed = data.get("passed", False)

    user = get_current_user()
    if not user:
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
            lp.score += xp_gained

    # Record daily activity for streak (1.1)
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
    lp = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson_id).first()

    xp_gained = 0
    if not lp:
        lp = LessonProgress(user_id=user.id, lesson_id=lesson_id, completed=True, score=0, completed_at=datetime.utcnow())
        db.session.add(lp)
        xp_gained = 10
        lp.score += xp_gained
    elif not lp.completed:
        lp.completed = True
        lp.completed_at = datetime.utcnow()
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained

    # Record daily activity for streak (1.1)
    record_daily_activity(user.id)

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


def record_daily_activity(user_id):
    """Record that user was active today for streak tracking (1.1)."""
    today = date.today()
    existing = DailyStreak.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.lessons_completed += 1
    else:
        streak_entry = DailyStreak(user_id=user_id, date=today, lessons_completed=1)
        db.session.add(streak_entry)


def calculate_streak(user_id):
    """Calculate current consecutive day streak for a user (1.1)."""
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
    progresses = LessonProgress.query.filter_by(user_id=user.id).all()
    completed = [p.lesson_id for p in progresses if p.completed]
    total_xp = sum(p.score for p in progresses)
    streak = calculate_streak(user.id)
    return {"completed_lessons": completed, "total_xp": total_xp, "streak": streak}


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
def dashboard():
    user = get_current_user()
    summary = get_progress_summary(user)
    return render_template(
        "dashboard.html",
        user=user,
        summary=summary,
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        page="dashboard",
    )


@app.route("/roadmap")
def roadmap():
    user = get_current_user()
    summary = get_progress_summary(user)
    return render_template(
        "roadmap.html", categories=LESSON_CATEGORIES, summary=summary, page="roadmap"
    )


# --- RUTAS DE AUTENTICACIÓN (Fase 7) ---


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(
                url_for("teacher_dashboard" if user.role == "teacher" else "dashboard")
            )

        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos",
            categories=LESSON_CATEGORIES,
        )

    return render_template("login.html", categories=LESSON_CATEGORIES)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get(
            "role", "student"
        )
        teacher_code = request.form.get("teacher_code", "").strip()

        # Validate teacher code (4.10)
        if role == "teacher" and teacher_code != TEACHER_SECRET_CODE:
            return render_template(
                "register.html",
                error="Código de profesor incorrecto. Contacta al administrador.",
                categories=LESSON_CATEGORIES,
            )

        if User.query.filter_by(username=username).first():
            return render_template(
                "register.html",
                error="El usuario ya existe",
                categories=LESSON_CATEGORIES,
            )

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(
            url_for("teacher_dashboard" if role == "teacher" else "dashboard")
        )

    return render_template("register.html", categories=LESSON_CATEGORIES)


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
    
    # Aggregated metrics for dashboard (Sprint 4)
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

    # Sort students by XP descending
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
        
    student = User.query.get(student_id)
    if student and student.role == "student":
        db.session.delete(student)
        db.session.commit()
        return jsonify({"success": True})
        
    return jsonify({"success": False, "error": "Estudiante no encontrado"}), 404


# ===== CSV EXPORT (Sprint 4 — 4.7) =====
import csv
from io import StringIO
from flask import Response

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


# ===== LEADERBOARD (Sprint 2 — 1.2) =====
@app.route("/leaderboard")
def leaderboard():
    students = User.query.filter_by(role="student").all()
    board = []
    for s in students:
        summary = get_progress_summary(s)
        level = (summary["total_xp"] // 100) + 1
        board.append({
            "id": s.id,
            "username": s.username,
            "total_xp": summary["total_xp"],
            "level": level,
            "completed": len(summary["completed_lessons"]),
            "streak": summary["streak"],
        })
    board.sort(key=lambda x: x["total_xp"], reverse=True)

    # Assign rank
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


# ===== PROFILE (Sprint 2 — 1.6) =====
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
    level = (summary["total_xp"] // 100) + 1

    # Recent activity: last 10 completed lessons
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


# ===== CERTIFICATE (Sprint 2 — 1.10) =====
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


# ===== THEME TOGGLE (Sprint 2 — 1.9) =====
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


# --- AI TUTOR (Gemini API) ---

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
    question = data.get("question", "")
    mode = data.get("mode", "analyze")  # 'analyze' or 'hint'
    exercise_question = data.get("exercise_question", "")

    # Load lesson context
    lesson_data = get_lesson(lesson_id)
    lesson_title = lesson_data.get("title", lesson_id)
    lesson_intro = lesson_data.get("intro", "")

    if mode == "hint":
        system_prompt = f"""Eres un tutor de programación amigable para estudiantes que aprenden Python y Java.
Estás ayudando con un ejercicio de la lección \"{lesson_title}\".
Contexto de la lección: {lesson_intro}

REGLAS ESTRICTAS:
- NUNCA des la respuesta directa al ejercicio.
- Da pistas progresivas que guíen al estudiante.
- Usa analogías simples si es posible.
- Responde en español.
- Sé breve (máximo 3-4 oraciones).
- Usa emojis para ser más amigable."""
        user_message = f"Pregunta del ejercicio: {exercise_question}\n\nMi código/respuesta: {user_code}\n\nMi duda: {question if question else 'No entiendo cómo resolverlo'}"
    else:
        system_prompt = f"""Eres un analizador de código Python/Java para estudiantes.
Estás en la lección \"{lesson_title}\".

REGLAS:
- Analiza el código del estudiante y da feedback constructivo.
- Señala errores, mejoras de estilo y buenas prácticas.
- Responde en español.
- Sé breve y directo (máximo 5-6 oraciones).
- Usa emojis para ser más amigable.
- Si el código está bien, felicita al estudiante."""
        user_message = f"Analiza este código:\n```python\n{user_code}\n```\n{('Mi pregunta: ' + question) if question else ''}"

    try:
        resp = http_requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [
                    {"parts": [{"text": system_prompt + "\n\n" + user_message}]}
                ],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500},
            },
            timeout=15,
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

# --- W3SCHOOLS STYLE ROUTES ---

@app.route("/ejercicios/<topic>")
def exercise_topic(topic):
    lesson_data = get_lesson(topic)
    if not lesson_data:
        return redirect(url_for("index"))
    
    exercises = lesson_data.get("exercises", [])
    user = get_current_user()
    completed_exercises = []
    
    if user.is_authenticated:
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


# ===== ADAPTIVE SECTION EVALUATIONS =====

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
    details = {}  # Per-lesson breakdown

    for qid in question_ids:
        key_data = answer_key.get(qid, {})
        user_answer = answers.get(qid)
        correct_val = key_data.get("correct")

        # Determine source lesson from question ID pattern
        # Find the question's source lesson from the eval data
        eval_data = get_evaluation_for_section(section_key)
        source_lesson = ""
        if eval_data:
            for lesson_id, qs in eval_data.get("lesson_questions", {}).items():
                for q in qs:
                    if q["id"] == qid:
                        source_lesson = lesson_id
                        break

        if source_lesson not in details:
            details[source_lesson] = {"correct": 0, "total": 0, "lesson_title": get_lesson_title(source_lesson)}

        details[source_lesson]["total"] += 1

        is_correct = False
        if isinstance(correct_val, bool):
            # true/false question
            is_correct = (user_answer == correct_val)
        elif isinstance(correct_val, int):
            # multiple choice
            try:
                is_correct = (int(user_answer) == correct_val)
            except (ValueError, TypeError):
                is_correct = False
        elif isinstance(correct_val, str):
            # complete code
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
                    completed=True, score=xp_gained, completed_at=datetime.utcnow()
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)

