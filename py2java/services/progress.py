"""Progreso del estudiante: rachas, resúmenes y estadísticas agregadas."""

from datetime import timedelta

from sqlalchemy import distinct, false, func

from content_loader import get_valid_exercise_ids, get_valid_practice_ids
from models import (
    DailyStreak,
    ExerciseAttempt,
    LessonProgress,
    PracticeSubmission,
    SectionEvaluation,
    User,
    db,
)

from py2java.config import logger
from py2java.services.curriculum import _course_lesson_ids
from py2java.services.evaluation import SECTION_EVAL_MAP
from py2java.services.exercises import (
    XP_PER_EVALUATION,
    XP_PER_EXERCISE,
    XP_PER_LESSON,
    XP_PER_PRACTICE,
)
from py2java.services.timeutils import _get_app_today


def record_daily_activity(user_id):
    """Registra la actividad diaria del usuario en la zona horaria operativa para el cálculo de racha."""
    if not user_id:
        return
    today = _get_app_today()
    existing = DailyStreak.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        existing.lessons_completed = (existing.lessons_completed or 0) + 1
    else:
        streak_entry = DailyStreak(user_id=user_id, date=today, lessons_completed=1)
        db.session.add(streak_entry)


def _compute_streak_from_dates(dates, today):
    """Calcula la racha consecutiva dada una lista ordenada descendente de fechas únicas."""
    if not dates:
        return 0
    yesterday = today - timedelta(days=1)
    first_date = dates[0]
    if first_date != today and first_date != yesterday:
        return 0
    count = 1
    for i in range(1, len(dates)):
        if dates[i] == first_date - timedelta(days=i):
            count += 1
        else:
            break
    return count


def calculate_streak(user_id):
    """Calcula la racha de días consecutivos de actividad usando la zona horaria operativa."""
    if not user_id:
        return 0
    rows = (
        db.session.query(DailyStreak.date)
        .filter_by(user_id=user_id)
        .distinct()
        .order_by(DailyStreak.date.desc())
        .all()
    )
    return _compute_streak_from_dates([r[0] for r in rows], _get_app_today())


def _get_bulk_streaks(user_ids):
    """Calcula la racha actual para un conjunto acotado de IDs de usuario en una sola consulta."""
    if not user_ids:
        return {}
    rows = (
        db.session.query(DailyStreak.user_id, DailyStreak.date)
        .filter(DailyStreak.user_id.in_(user_ids))
        .distinct()
        .order_by(DailyStreak.user_id.asc(), DailyStreak.date.desc())
        .all()
    )
    dates_by_user = {}
    for uid, day in rows:
        dates_by_user.setdefault(uid, []).append(day)

    today = _get_app_today()
    return {
        uid: _compute_streak_from_dates(dates_by_user.get(uid, []), today)
        for uid in user_ids
    }


def _get_classroom_student_counts(section_ids=None):
    """Cuenta estudiantes por sección en una sola consulta agregada GROUP BY (elimina N+1)."""
    query = db.session.query(User.section_id, func.count(User.id)).filter(
        User.role == "student",
        User.section_id.isnot(None),
    )
    if section_ids is not None:
        if not section_ids:
            return {}
        query = query.filter(User.section_id.in_(section_ids))
    return {sec_id: int(cnt) for sec_id, cnt in query.group_by(User.section_id).all()}


def _build_student_stats_subqueries(user_ids_select=None):
    """Construye subconsultas GROUP BY por usuario para calcular XP y lecciones directamente en SQL."""
    course_ids = _course_lesson_ids()
    valid_exercise_ids = get_valid_exercise_ids()
    valid_practice_ids = get_valid_practice_ids()
    valid_eval_keys = set(SECTION_EVAL_MAP.keys())

    lp_q = db.session.query(
        LessonProgress.user_id.label("user_id"),
        func.count(distinct(LessonProgress.lesson_id)).label("completed_cnt"),
    ).filter(
        LessonProgress.completed.is_(True),
        LessonProgress.lesson_id.in_(course_ids) if course_ids else false(),
    )
    if user_ids_select is not None:
        lp_q = lp_q.filter(LessonProgress.user_id.in_(user_ids_select))
    lp_sub = lp_q.group_by(LessonProgress.user_id).subquery()

    ex_q = db.session.query(
        ExerciseAttempt.user_id.label("user_id"),
        func.count(distinct(ExerciseAttempt.exercise_id)).label("ex_cnt"),
    ).filter(
        ExerciseAttempt.passed.is_(True),
        ExerciseAttempt.exercise_id.in_(valid_exercise_ids) if valid_exercise_ids else false(),
    )
    if user_ids_select is not None:
        ex_q = ex_q.filter(ExerciseAttempt.user_id.in_(user_ids_select))
    ex_sub = ex_q.group_by(ExerciseAttempt.user_id).subquery()

    pr_q = db.session.query(
        PracticeSubmission.user_id.label("user_id"),
        func.count(distinct(PracticeSubmission.problem_id)).label("pr_cnt"),
    ).filter(
        PracticeSubmission.passed.is_(True),
        PracticeSubmission.problem_id.in_(valid_practice_ids) if valid_practice_ids else false(),
    )
    if user_ids_select is not None:
        pr_q = pr_q.filter(PracticeSubmission.user_id.in_(user_ids_select))
    pr_sub = pr_q.group_by(PracticeSubmission.user_id).subquery()

    ev_q = db.session.query(
        SectionEvaluation.user_id.label("user_id"),
        func.count(distinct(SectionEvaluation.section_id)).label("ev_cnt"),
    ).filter(
        SectionEvaluation.passed.is_(True),
        SectionEvaluation.section_id.in_(valid_eval_keys) if valid_eval_keys else false(),
    )
    if user_ids_select is not None:
        ev_q = ev_q.filter(SectionEvaluation.user_id.in_(user_ids_select))
    ev_sub = ev_q.group_by(SectionEvaluation.user_id).subquery()

    completed_expr = func.coalesce(lp_sub.c.completed_cnt, 0)
    total_xp_expr = (
        completed_expr * XP_PER_LESSON
        + func.coalesce(ex_sub.c.ex_cnt, 0) * XP_PER_EXERCISE
        + func.coalesce(pr_sub.c.pr_cnt, 0) * XP_PER_PRACTICE
        + func.coalesce(ev_sub.c.ev_cnt, 0) * XP_PER_EVALUATION
    )
    return lp_sub, ex_sub, pr_sub, ev_sub, completed_expr, total_xp_expr


def get_progress_summary(user):
    """Calcula lecciones completadas reales y XP total sumando únicamente desde las tablas reales."""
    if not user or not getattr(user, "id", None):
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}
    try:
        course_ids = _course_lesson_ids()
        valid_exercise_ids = get_valid_exercise_ids()
        valid_practice_ids = get_valid_practice_ids()
        valid_eval_keys = set(SECTION_EVAL_MAP.keys())

        progresses = LessonProgress.query.filter_by(user_id=user.id, completed=True).all()
        completed_set = {p.lesson_id for p in progresses if p.lesson_id in course_ids}

        passed_ex_rows = (
            db.session.query(ExerciseAttempt.exercise_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_ex_set = {r[0] for r in passed_ex_rows if r[0] in valid_exercise_ids}

        passed_pr_rows = (
            db.session.query(PracticeSubmission.problem_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_pr_set = {r[0] for r in passed_pr_rows if r[0] in valid_practice_ids}

        passed_ev_rows = (
            db.session.query(SectionEvaluation.section_id)
            .filter_by(user_id=user.id, passed=True)
            .distinct()
            .all()
        )
        passed_ev_set = {r[0] for r in passed_ev_rows if r[0] in valid_eval_keys}

        total_xp = (
            len(completed_set) * XP_PER_LESSON
            + len(passed_ex_set) * XP_PER_EXERCISE
            + len(passed_pr_set) * XP_PER_PRACTICE
            + len(passed_ev_set) * XP_PER_EVALUATION
        )
        streak = calculate_streak(user.id)
        return {
            "completed_lessons": sorted(completed_set),
            "total_xp": total_xp,
            "streak": streak,
        }
    except Exception as e:
        logger.warning("get_progress_summary error: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"completed_lessons": [], "total_xp": 0, "streak": 0}


def get_bulk_progress_summaries(users):
    """Calcula el resumen de progreso y XP real de múltiples usuarios desde las tablas reales."""
    user_ids = [u.id for u in users if getattr(u, "id", None)]
    if not user_ids:
        return {}

    result = {uid: {"completed_lessons": [], "total_xp": 0, "streak": 0} for uid in user_ids}
    try:
        course_ids = _course_lesson_ids()
        valid_exercise_ids = get_valid_exercise_ids()
        valid_practice_ids = get_valid_practice_ids()
        valid_eval_keys = set(SECTION_EVAL_MAP.keys())

        lessons_by_user = {uid: set() for uid in user_ids}
        ex_by_user = {uid: set() for uid in user_ids}
        pr_by_user = {uid: set() for uid in user_ids}
        ev_by_user = {uid: set() for uid in user_ids}

        all_progress = LessonProgress.query.filter(
            LessonProgress.user_id.in_(user_ids),
            LessonProgress.completed.is_(True),
        ).all()
        for p in all_progress:
            if p.lesson_id in course_ids:
                lessons_by_user[p.user_id].add(p.lesson_id)

        all_ex = (
            db.session.query(ExerciseAttempt.user_id, ExerciseAttempt.exercise_id)
            .filter(ExerciseAttempt.user_id.in_(user_ids), ExerciseAttempt.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, ex_id in all_ex:
            if ex_id in valid_exercise_ids:
                ex_by_user[uid].add(ex_id)

        all_pr = (
            db.session.query(PracticeSubmission.user_id, PracticeSubmission.problem_id)
            .filter(PracticeSubmission.user_id.in_(user_ids), PracticeSubmission.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, prob_id in all_pr:
            if prob_id in valid_practice_ids:
                pr_by_user[uid].add(prob_id)

        all_ev = (
            db.session.query(SectionEvaluation.user_id, SectionEvaluation.section_id)
            .filter(SectionEvaluation.user_id.in_(user_ids), SectionEvaluation.passed.is_(True))
            .distinct()
            .all()
        )
        for uid, sec_id in all_ev:
            if sec_id in valid_eval_keys:
                ev_by_user[uid].add(sec_id)

        streaks_map = _get_bulk_streaks(user_ids)
        for uid in user_ids:
            comp = lessons_by_user[uid]
            result[uid]["completed_lessons"] = sorted(comp)
            result[uid]["total_xp"] = (
                len(comp) * XP_PER_LESSON
                + len(ex_by_user[uid]) * XP_PER_EXERCISE
                + len(pr_by_user[uid]) * XP_PER_PRACTICE
                + len(ev_by_user[uid]) * XP_PER_EVALUATION
            )
            result[uid]["streak"] = streaks_map.get(uid, 0)
    except Exception as e:
        logger.warning("get_bulk_progress_summaries error: %s", e)
        db.session.rollback()

    return result
