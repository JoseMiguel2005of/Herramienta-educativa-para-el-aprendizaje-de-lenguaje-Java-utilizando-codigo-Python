"""Evaluaciones finales por sección: desbloqueo, estado y generación adaptativa de preguntas."""

import random

from content_loader import get_evaluation_for_section
from models import LessonProgress, SectionEvaluation

from py2java.services.curriculum import LESSON_CATEGORIES


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
    """Returns the list of completable lesson IDs for a given section label_key."""
    for cat in LESSON_CATEGORIES:
        for sec in cat["sections"]:
            if sec["label_key"] == section_key:
                return [
                    lesson["id"] for lesson in sec["lessons"]
                    if not lesson.get("type") and not lesson["id"].startswith(("ex-", "ref-"))
                ]
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
    """Generate an adaptive set of questions based on completed lessons, with full section fallback."""
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

    # Collect questions from completed lessons first
    available = []
    for lesson_id in completed_ids:
        qs = lesson_questions.get(lesson_id, [])
        for q in qs:
            q_copy = dict(q)
            q_copy["source_lesson"] = lesson_id
            available.append(q_copy)

    # Fallback: si available quedó vacío, usar preguntas generales de toda la sección
    if not available:
        for lesson_id, qs in lesson_questions.items():
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


EVAL_NETWORK_GRACE_SECONDS = 30
