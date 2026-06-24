import os

import requests as http_requests
from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from werkzeug.security import check_password_hash, generate_password_hash

from content_loader import (get_lesson, get_lesson_title, get_reference,
                            load_ui_strings)
from models import ExerciseAttempt, LessonProgress, User, db
from search_index import search_lessons
from translator import translate

app = Flask(__name__)
app.secret_key = "tesis-python-java-educativo"

# Database Configuration
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
    return render_template(
        "lesson.html",
        categories=LESSON_CATEGORIES,
        lessons=LESSONS,
        current_lesson=lesson_id,
        current_category=current_category_id,
        prev_lesson=prev_lesson,
        next_lesson=next_lesson,
        page="lesson",
        role=session.get("role", "student"),
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
    data.get("lesson_id", "unknown")

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
        lp = LessonProgress(user_id=user.id, lesson_id=lesson_id, completed=True, score=0)
        db.session.add(lp)
        xp_gained = 10
        lp.score += xp_gained
    elif not lp.completed:
        lp.completed = True
        xp_gained = 10
        lp.score = (lp.score or 0) + xp_gained

    db.session.commit()
    return jsonify(
        {"ok": True, "xp_gained": xp_gained, "summary": get_progress_summary(user)}
    )


def get_progress_summary(user):
    progresses = LessonProgress.query.filter_by(user_id=user.id).all()
    completed = [p.lesson_id for p in progresses if p.completed]
    total_xp = sum(p.score for p in progresses)
    return {"completed_lessons": completed, "total_xp": total_xp}


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
        )  # Podría requerir código secreto para ser teacher en prod

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
    for s in students:
        stats = get_progress_summary(s)
        student_stats.append(
            {
                "username": s.username,
                "total_xp": stats["total_xp"],
                "completed": len(stats["completed_lessons"]),
            }
        )

    return render_template(
        "teacher_dashboard.html", students=student_stats, categories=LESSON_CATEGORIES
    )


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

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY", "AQ.Ab8RN6JX_BvWBYYh4CzXK6kvkDyqsNGCBME6wUvirs0UQtjoMA"
)
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
