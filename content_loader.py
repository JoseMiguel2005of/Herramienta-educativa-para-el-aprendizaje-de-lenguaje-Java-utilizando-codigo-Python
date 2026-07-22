"""
Cargador de contenido modular para Py2Java Edu.
Lee archivos JSON desde content/ y los expone al resto de la aplicación.
"""

import json
import os
from functools import lru_cache

CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")
LESSONS_DIR = os.path.join(CONTENT_DIR, "lessons")


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


@lru_cache(maxsize=100)
def load_lesson(lesson_id):
    """Carga una lección individual por su ID."""
    path = os.path.join(LESSONS_DIR, f"{lesson_id}.json")
    if not os.path.exists(path):
        return None
    return _load_json(path)


@lru_cache(maxsize=1)
def load_all_lesson_ids():
    """Devuelve la lista de todos los IDs de lecciones disponibles."""
    ids = []
    if os.path.isdir(LESSONS_DIR):
        for fname in sorted(os.listdir(LESSONS_DIR)):
            if fname.endswith(".json"):
                ids.append(fname[:-5])  # Remove .json
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


def invalidate_cache():
    """Invalida todo el cache (útil si se editan JSONs en caliente)."""
    load_ui_strings.cache_clear()
    load_reference_data.cache_clear()
    load_lesson.cache_clear()
    load_all_lesson_ids.cache_clear()


# ===== QUIZ, EXAMPLES, PRACTICE LOADERS =====

QUIZZES_DIR = os.path.join(CONTENT_DIR, "quizzes")
EXAMPLES_DIR = os.path.join(CONTENT_DIR, "examples")
PRACTICE_DIR = os.path.join(CONTENT_DIR, "practice")


@lru_cache(maxsize=20)
def load_quiz(quiz_id):
    """Carga un quiz por su ID."""
    path = os.path.join(QUIZZES_DIR, f"{quiz_id}.json")
    if not os.path.exists(path):
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
    """Busca un ejemplo individual por su ID en el catálogo."""
    catalog = load_examples_catalog()
    for cat in catalog.get("categories", []):
        for ex in cat.get("examples", []):
            if ex["id"] == example_id:
                ex["category"] = cat.get("title", "")
                ex["related_lesson"] = cat.get("related_lesson", "")
                return ex
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
    data = load_practice_problems()
    for p in data.get("problems", []):
        if p["id"] == problem_id:
            return p
    return None


# ===== EVALUATION LOADERS =====

EVALUATIONS_DIR = os.path.join(CONTENT_DIR, "evaluations")


@lru_cache(maxsize=10)
def load_evaluation(eval_id):
    """Carga una evaluación por su ID."""
    path = os.path.join(EVALUATIONS_DIR, f"{eval_id}.json")
    if not os.path.exists(path):
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


