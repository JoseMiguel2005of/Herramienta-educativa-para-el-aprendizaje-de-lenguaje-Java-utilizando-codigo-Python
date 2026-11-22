"""
Cargador de contenido modular para Py2Java Edu.
Lee archivos JSON desde content/ y los expone al resto de la aplicación.
"""

import json
import os
import re
from functools import lru_cache

CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
LESSONS_DIR = os.path.join(CONTENT_DIR, "lessons")
SAFE_CONTENT_ID_RE = re.compile(r"^[a-z0-9\-]+$")

# Fuente única de verdad para los títulos de nivel (consumida en app.py, plantillas, JS y pdf_report.py)
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
    20: "Entidad Binaria Superior",
}


def get_level_title(level):
    """Devuelve el título oficial del nivel desde la fuente única LEVEL_TITLES."""
    try:
        lvl = int(level)
    except (TypeError, ValueError):
        lvl = 1
    if lvl >= 20:
        return LEVEL_TITLES[20]
    if lvl <= 1:
        return LEVEL_TITLES[1]
    return LEVEL_TITLES.get(lvl, LEVEL_TITLES[1])


def get_level_info(total_xp):
    """Calcula nivel y título oficial a partir del XP total."""
    try:
        xp = max(0, int(total_xp))
    except (TypeError, ValueError):
        xp = 0
    level = (xp // 100) + 1
    return {"level": level, "title": get_level_title(level)}


def _safe_content_json_path(base_dir, content_id):
    """Valida el ID contra ^[a-z0-9\\-]+$ y verifica commonpath para impedir Path Traversal."""
    if not isinstance(content_id, str) or not SAFE_CONTENT_ID_RE.fullmatch(content_id):
        return None
    base_real = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_real, f"{content_id}.json"))
    try:
        if os.path.commonpath([base_real, candidate]) != base_real:
            return None
    except ValueError:
        return None
    return candidate


def _load_json(path):
    """Carga un archivo JSON con encoding UTF-8."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_ui_strings():
    """Carga las cadenas de interfaz de usuario."""
    return _load_json(os.path.join(CONTENT_DIR, "ui.json"))


@lru_cache(maxsize=1)
def load_reference_data():
    """Carga todas las categorías de referencia teórica."""
    return _load_json(os.path.join(CONTENT_DIR, "reference.json"))


LESSON_ALIASES = {
    "sc-interpolate": "sc-interpolation",
    "sc-significance": "sc-sigtests",
    "sc-sparsematrix": "sc-sparsedata",
    "sc-spatial": "sc-spatialdata",
    "mongo-createcollection": "mongo-collection",
    "mongo-dropcollection": "mongo-drop",
}


@lru_cache(maxsize=256)
def load_lesson(lesson_id):
    """Carga una lección individual por su ID."""
    if not isinstance(lesson_id, str) or not SAFE_CONTENT_ID_RE.fullmatch(lesson_id):
        return None
    lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    path = _safe_content_json_path(LESSONS_DIR, lesson_id)
    if not path or not os.path.exists(path):
        return None
    return _load_json(path)


@lru_cache(maxsize=1)
def load_all_lesson_ids():
    """Devuelve la lista de todos los IDs de lecciones canónicas disponibles."""
    ids = []
    if os.path.isdir(LESSONS_DIR):
        for fname in sorted(os.listdir(LESSONS_DIR)):
            if fname.endswith(".json"):
                lid = fname[:-5]  # Remove .json
                if lid not in LESSON_ALIASES:
                    ids.append(lid)
    return ids


def get_lesson(lesson_id):
    """Obtiene los datos de una lección (compatible con el sistema anterior)."""
    data = load_lesson(lesson_id)
    if data is None:
        return {
            "title": lesson_id,
            "intro": "",
            "python_desc": "",
            "java_desc": "",
            "explanation": "",
            "code_mappings": [],
            "exercises": [],
        }
    return data


def get_lesson_title(lesson_id):
    """Obtiene solo el título de una lección."""
    data = load_lesson(lesson_id)
    if data:
        return data.get("title", lesson_id)
    # Fallback: buscar en UI strings por el patrón antiguo
    ui = load_ui_strings()
    key = f"lesson_{lesson_id}_title"
    return ui.get(key, lesson_id)


def get_reference(category):
    """Obtiene las filas de referencia para una categoría."""
    ref = load_reference_data()
    return ref.get(category, [])


# ===== QUIZ, EXAMPLES, PRACTICE LOADERS =====

QUIZZES_DIR = os.path.join(CONTENT_DIR, "quizzes")
EXAMPLES_DIR = os.path.join(CONTENT_DIR, "examples")
PRACTICE_DIR = os.path.join(CONTENT_DIR, "practice")


@lru_cache(maxsize=20)
def load_quiz(quiz_id):
    """Carga un quiz por su ID."""
    path = _safe_content_json_path(QUIZZES_DIR, quiz_id)
    if not path or not os.path.exists(path):
        return None
    return _load_json(path)


@lru_cache(maxsize=1)
def load_all_quizzes():
    """Devuelve lista de todos los quiz IDs disponibles."""
    ids = []
    if os.path.isdir(QUIZZES_DIR):
        for fname in sorted(os.listdir(QUIZZES_DIR)):
            if fname.endswith(".json"):
                ids.append(fname[:-5])
    return ids


@lru_cache(maxsize=1)
def load_examples_catalog():
    """Carga el catálogo completo de examples."""
    path = os.path.join(EXAMPLES_DIR, "examples-catalog.json")
    if not os.path.exists(path):
        return {"categories": []}
    return _load_json(path)


def get_example_by_id(example_id):
    """Busca un ejemplo individual por su ID en el catálogo devolviendo una copia segura (sin mutar caché)."""
    catalog = load_examples_catalog()
    for cat in catalog.get("categories", []):
        for ex in cat.get("examples", []):
            if ex["id"] == example_id:
                ex_copy = dict(ex)
                ex_copy["category"] = cat.get("title", "")
                ex_copy["related_lesson"] = cat.get("related_lesson", "")
                return ex_copy
    return None


@lru_cache(maxsize=1)
def load_practice_problems():
    """Carga todos los problemas de práctica."""
    path = os.path.join(PRACTICE_DIR, "practice-problems.json")
    if not os.path.exists(path):
        return {"problems": []}
    return _load_json(path)


def get_practice_problem(problem_id):
    """Obtiene un problema de práctica por su ID."""
    if not isinstance(problem_id, str) or not SAFE_CONTENT_ID_RE.fullmatch(problem_id):
        return None
    data = load_practice_problems()
    for p in data.get("problems", []):
        if p["id"] == problem_id:
            return p
    return None


@lru_cache(maxsize=1)
def get_valid_practice_ids():
    """Devuelve el conjunto inmutable de IDs válidos de problemas de práctica."""
    data = load_practice_problems()
    return frozenset(p["id"] for p in data.get("problems", []) if isinstance(p.get("id"), str))


@lru_cache(maxsize=1)
def get_valid_exercise_ids():
    """Devuelve el conjunto inmutable de todos los exercise_id válidos del currículo."""
    valid_ids = set()
    if os.path.isdir(LESSONS_DIR):
        for fname in sorted(os.listdir(LESSONS_DIR)):
            if not fname.endswith(".json"):
                continue
            lid = fname[:-5]
            data = load_lesson(lid)
            if not data:
                continue
            for idx, ex in enumerate(data.get("exercises", []), start=1):
                ex_id = ex.get("id")
                if isinstance(ex_id, str) and ex_id.strip():
                    valid_ids.add(ex_id.strip())
                else:
                    valid_ids.add(f"{lid}-{idx}")
    return frozenset(valid_ids)


def get_lesson_exercise(lesson_id, exercise_id):
    """Valida que lesson_id y exercise_id existan juntos en el currículo y devuelve (lesson_data, exercise)."""
    if not isinstance(lesson_id, str) or not isinstance(exercise_id, str):
        return None, None
    lesson_data = load_lesson(lesson_id)
    if not lesson_data:
        return None, None
    canonical_lesson_id = LESSON_ALIASES.get(lesson_id, lesson_id)
    for idx, ex in enumerate(lesson_data.get("exercises", []), start=1):
        ex_id = ex.get("id")
        if (ex_id and ex_id == exercise_id) or f"{canonical_lesson_id}-{idx}" == exercise_id:
            return lesson_data, ex
    return lesson_data, None


# ===== EVALUATION LOADERS =====

EVALUATIONS_DIR = os.path.join(CONTENT_DIR, "evaluations")


@lru_cache(maxsize=32)
def load_evaluation(eval_id):
    """Carga una evaluación por su ID."""
    path = _safe_content_json_path(EVALUATIONS_DIR, eval_id)
    if not path or not os.path.exists(path):
        return None
    return _load_json(path)


@lru_cache(maxsize=1)
def load_all_evaluations():
    """Devuelve lista de todos los IDs de evaluaciones disponibles."""
    ids = []
    if os.path.isdir(EVALUATIONS_DIR):
        for fname in sorted(os.listdir(EVALUATIONS_DIR)):
            if fname.endswith(".json"):
                ids.append(fname[:-5])
    return ids


def get_evaluation_for_section(section_key):
    """Obtiene la evaluación correspondiente a una sección del sidebar."""
    eval_ids = load_all_evaluations()
    for eid in eval_ids:
        data = load_evaluation(eid)
        if data and data.get("section_key") == section_key:
            return data
    return None


@lru_cache(maxsize=1)
def load_curriculum():
    """Carga el currículo de categorías y lecciones desde content/curriculum.json."""
    path = os.path.join(CONTENT_DIR, "curriculum.json")
    data = _load_json(path)
    if isinstance(data, dict) and isinstance(data.get("categories"), list):
        return data
    return {"categories": []}


def invalidate_cache():
    """Invalida todo el cache (útil si se editan JSONs en caliente)."""
    load_curriculum.cache_clear()
    load_ui_strings.cache_clear()
    load_reference_data.cache_clear()
    load_lesson.cache_clear()
    load_all_lesson_ids.cache_clear()
    load_quiz.cache_clear()
    load_all_quizzes.cache_clear()
    load_examples_catalog.cache_clear()
    load_practice_problems.cache_clear()
    get_valid_practice_ids.cache_clear()
    get_valid_exercise_ids.cache_clear()
    load_evaluation.cache_clear()
    load_all_evaluations.cache_clear()
    try:
        from search_index import invalidate_search_index
        invalidate_search_index()
    except Exception:
        pass



