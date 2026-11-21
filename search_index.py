from functools import lru_cache

from content_loader import get_lesson, load_all_lesson_ids


@lru_cache(maxsize=1)
def _build_search_index():
    """Preconstruye una sola vez en memoria el índice de búsqueda de todas las lecciones."""
    entries = []
    for lid in load_all_lesson_ids():
        lesson = get_lesson(lid)
        if not lesson:
            continue
        raw_title = lesson.get("title") or lid
        raw_intro = lesson.get("intro") or ""
        snippet = raw_intro[:100] + "..." if len(raw_intro) > 100 else raw_intro
        entries.append(
            (
                lid,
                raw_title,
                snippet,
                raw_title.lower(),
                raw_intro.lower(),
                (lesson.get("python_desc") or "").lower(),
                (lesson.get("java_desc") or "").lower(),
                (lesson.get("explanation") or "").lower(),
            )
        )
    return tuple(entries)


def invalidate_search_index():
    """Limpia el índice preconstruido cuando se invalida el caché de contenido."""
    _build_search_index.cache_clear()


def search_lessons(query):
    if not query or len(query.strip()) < 2:
        return []

    terms = [t for t in query.lower().split() if t]
    if not terms:
        return []

    results = []
    for lid, raw_title, snippet, title_l, intro_l, py_l, java_l, exp_l in _build_search_index():
        score = 0
        for term in terms:
            if term in title_l:
                score += 10
            if term in intro_l:
                score += 5
            if term in py_l or term in java_l:
                score += 2
            if term in exp_l:
                score += 1

        if score > 0:
            results.append(
                {
                    "id": lid,
                    "title": raw_title,
                    "snippet": snippet,
                    "score": score,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]
