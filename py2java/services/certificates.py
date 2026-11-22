"""Contexto y formato de certificados de finalización."""

from content_loader import load_ui_strings

from py2java.services.curriculum import LESSON_CATEGORIES, _category_course_lessons
from py2java.services.progress import get_progress_summary
from py2java.services.timeutils import _app_now


_SPANISH_MONTHS = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _format_spanish_date(dt):
    return f"{dt.day:02d} de {_SPANISH_MONTHS[dt.month]} de {dt.year}"


def _get_certificate_context(user, section_id):
    target_cat = None
    for cat in LESSON_CATEGORIES:
        if cat["id"] == section_id:
            target_cat = cat
            break
    if not target_cat:
        return None

    summary = get_progress_summary(user)
    completed_set = set(summary["completed_lessons"])
    cat_lessons = _category_course_lessons(target_cat)
    completed_in_cat = [lid for lid in cat_lessons if lid in completed_set]
    is_complete = len(completed_in_cat) >= len(cat_lessons) and len(cat_lessons) > 0

    ui = load_ui_strings()
    now = _app_now()
    return {
        "category_name": ui.get(target_cat["label_key"], section_id),
        "category_id": section_id,
        "total_lessons": len(cat_lessons),
        "completed_lessons": len(completed_in_cat),
        "is_complete": is_complete,
        "completion_date": _format_spanish_date(now),
        "completion_year": now.year,
        "site_title": ui.get("site_title", "Py2Java Edu"),
    }
