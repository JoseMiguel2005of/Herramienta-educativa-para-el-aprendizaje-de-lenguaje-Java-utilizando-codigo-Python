"""Currículo del curso: categorías, lecciones y navegación (datos en content/curriculum.json)."""

from content_loader import load_curriculum


_CURRICULUM = load_curriculum()
LESSON_CATEGORIES = _CURRICULUM["categories"]


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


# --- Exportar PDF ---
def _course_lesson_ids():
    """IDs de lecciones teóricas completables del curso (excluye quizzes, hubs, ex-* y ref-*)."""
    return {
        l["id"] for l in LESSONS
        if not l.get("type") and not l["id"].startswith(("ex-", "ref-"))
    }


def _category_course_lessons(cat):
    """Devuelve solo las lecciones teóricas completables de una categoría (sin quizzes, hubs, ex-* ni ref-*)."""
    lessons_out = []
    for sec in cat.get("sections", []):
        for lesson_item in sec.get("lessons", []):
            lid = lesson_item["id"]
            if not lesson_item.get("type") and not lid.startswith(("ex-", "ref-")):
                lessons_out.append(lid)
    return lessons_out
