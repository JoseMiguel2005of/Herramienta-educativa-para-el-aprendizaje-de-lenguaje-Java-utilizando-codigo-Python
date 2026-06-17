from flask import Flask, jsonify, render_template, request, session, redirect, url_for


from translations import TRANSLATIONS, get_lesson, get_lesson_title, get_reference
from translator import translate

app = Flask(__name__)
app.secret_key = "tesis-python-java-educativo"

LESSON_CATEGORIES = [
    {
        "id": "py2java",
        "label_key": "cat_py2java",
        "icon": "",
        "color_class": "cat-python",
        "sections": [
            {
                "label_key": "cat_section_tutorial",
                "lessons": [
                    {"id": "hola-mundo",     "icon": ""},
                    {"id": "comentarios",    "icon": ""},
                    {"id": "variables",      "icon": ""},
                    {"id": "tipos-datos",    "icon": ""},
                    {"id": "casting",        "icon": ""},
                    {"id": "booleanos",      "icon": ""},
                    {"id": "operadores",     "icon": ""},
                    {"id": "cadenas",        "icon": ""},
                    {"id": "formateo-cadenas","icon": ""},
                    {"id": "user-input",     "icon": ""},
                    {"id": "condicionales",  "icon": ""},
                    {"id": "bucles",         "icon": ""},
                ]
            },
            {
                "label_key": "cat_section_funciones",
                "lessons": [
                    {"id": "funciones",      "icon": ""},
                    {"id": "lambdas",        "icon": ""},
                ]
            },
            {
                "label_key": "cat_section_estructuras",
                "lessons": [
                    {"id": "listas",         "icon": ""},
                    {"id": "tuplas",         "icon": ""},
                    {"id": "sets",           "icon": ""},
                    {"id": "diccionarios",   "icon": ""},
                    {"id": "arreglos",       "icon": ""},
                ]
            },
            {
                "label_key": "cat_section_clases",
                "lessons": [
                    {"id": "clases",         "icon": ""},
                    {"id": "herencia",       "icon": ""},
                    {"id": "polimorfismo",   "icon": ""},
                    {"id": "scope",          "icon": ""},
                ]
            },
            {
                "label_key": "cat_section_modulos",
                "lessons": [
                    {"id": "modulos",        "icon": ""},
                    {"id": "paquetes",       "icon": ""},
                    {"id": "fechas",         "icon": ""},
                    {"id": "math",           "icon": ""},
                    {"id": "regex",          "icon": ""},
                ]
            },
            {
                "label_key": "cat_section_archivos",
                "lessons": [
                    {"id": "excepciones",    "icon": ""},
                    {"id": "archivos",       "icon": ""},
                    {"id": "json",           "icon": ""},
                ]
            }
        ]
    },
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
        cat_lessons = [l for sec in cat["sections"] for l in sec["lessons"]]
        ids = [l["id"] for l in cat_lessons]
        if lesson_id in ids:
            idx = ids.index(lesson_id)
            prev_id = ids[idx - 1] if idx > 0 else None
            next_id = ids[idx + 1] if idx < len(ids) - 1 else None
            return prev_id, next_id
    return None, None


@app.route("/")
def index():
    return redirect(url_for("lesson", lesson_id="hola-mundo"))

@app.route("/leccion/<lesson_id>")
def lesson(lesson_id):
    valid_ids = [l["id"] for l in LESSONS]
    if lesson_id not in valid_ids:
        lesson_id = "hola-mundo"
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
        role=session.get("role", "student")
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
        role=session.get("role", "student")
    )

@app.route("/api/traducir", methods=["POST"])
def api_translate():
    data = request.get_json(silent=True) or {}
    python_code = data.get("code", "")
    class_name = data.get("class_name", "Program")
    lesson_id = data.get("lesson_id", "unknown")
    
    result = translate(python_code, class_name=class_name)
    
    return jsonify(result)

@app.route("/api/ejercicio", methods=["POST"])
def api_exercise():
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id", "unknown")
    passed = data.get("passed", False)
    
    # Podríamos guardar estadísticas aquí si tuviéramos BD
    return jsonify({"ok": True})


@app.route("/configuracion", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        lang = request.form.get("lang", "es")
        theme = request.form.get("theme", "light")
        session["lang"] = lang if lang in ("es", "en") else "es"
        session["theme"] = theme if theme in ("light", "dark") else "light"
        return redirect(request.referrer or url_for("index"))

    return redirect(url_for("index"))


@app.context_processor
def inject_globals():
    lang = session.get("lang", "es")
    return {
        "lang": lang,
        "theme": session.get("theme", "light"),
        "t": TRANSLATIONS.get(lang, TRANSLATIONS["es"]),
        "get_lesson": lambda lid: get_lesson(lang, lid),
        "get_lesson_title": lambda lid: get_lesson_title(lang, lid),
        "get_reference": lambda cat: get_reference(lang, cat),
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
