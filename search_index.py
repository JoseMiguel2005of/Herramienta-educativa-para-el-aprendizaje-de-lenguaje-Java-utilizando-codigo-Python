from content_loader import load_all_lesson_ids, get_lesson
import re

def search_lessons(query):
    if not query or len(query.strip()) < 2:
        return []
        
    query = query.lower()
    terms = [t for t in query.split() if t]
    
    lesson_ids = load_all_lesson_ids()
    results = []
    
    for lid in lesson_ids:
        lesson = get_lesson(lid)
        if not lesson:
            continue
            
        score = 0
        title = lesson.get("title", "").lower()
        intro = lesson.get("intro", "").lower()
        python_desc = lesson.get("python_desc", "").lower()
        java_desc = lesson.get("java_desc", "").lower()
        explanation = lesson.get("explanation", "").lower()
        
        # Simple scoring
        for term in terms:
            if term in title:
                score += 10
            if term in intro:
                score += 5
            if term in python_desc or term in java_desc:
                score += 2
            if term in explanation:
                score += 1
                
        if score > 0:
            # Generate a small snippet
            snippet = intro[:100] + "..." if len(intro) > 100 else intro
            
            results.append({
                "id": lid,
                "title": lesson.get("title"),
                "snippet": snippet,
                "score": score
            })
            
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10] # Return top 10
