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
