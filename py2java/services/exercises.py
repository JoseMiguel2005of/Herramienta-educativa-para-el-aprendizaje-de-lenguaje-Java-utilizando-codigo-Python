"""Calificación de ejercicios y prácticas en servidor (XP, validación AST y respuestas)."""

import ast
import html
import re

from py2java.services.security import _DATA_ANSWER_EXTRACT_RE, _safe_int


XP_PER_LESSON = 10


XP_PER_EXERCISE = 25


XP_PER_PRACTICE = 50


XP_PER_EVALUATION = 100


MAX_PRACTICE_CODE_CHARS = 8000


SOLUTION_VIEWED_MARKER = "__SOLUTION_VIEWED__"


PASSED_AFTER_SOLUTION_MARKER = "__PASSED_AFTER_SOLUTION__"


def _normalize_answer_text(val):
    """Normaliza espacios en blanco preservando estrictamente mayúsculas y minúsculas (Python/Java)."""
    return re.sub(r"\s+", " ", str(val).strip())


def _is_trivial_function_body(body):
    """Devuelve True si el cuerpo de una función solo contiene pass, ... o docstrings."""
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            if stmt.value.value is Ellipsis or isinstance(stmt.value.value, str):
                continue
        return False
    return True


def _validate_practice_code_ast(problem, code):
    """Valida estáticamente (sin exec) que el código tenga sintaxis válida e implemente la función pedida."""
    if not isinstance(code, str):
        return False, "El código enviado es inválido."
    stripped = code.strip()
    if not stripped or len(code) > MAX_PRACTICE_CODE_CHARS:
        return False, f"El código debe tener entre 1 y {MAX_PRACTICE_CODE_CHARS} caracteres."

    starter = (problem.get("starter_code") or "").strip()
    if stripped == starter:
        return False, "Debes implementar tu solución antes de enviarla."

    try:
        user_tree = ast.parse(code)
    except SyntaxError:
        return False, "El código contiene errores de sintaxis Python."

    required_funcs = set()
    if starter:
        try:
            starter_tree = ast.parse(starter)
            for node in ast.walk(starter_tree):
                if isinstance(node, ast.FunctionDef):
                    required_funcs.add(node.name)
        except SyntaxError:
            pass

    if required_funcs:
        user_funcs = {
            node.name: node
            for node in ast.walk(user_tree)
            if isinstance(node, ast.FunctionDef)
        }
        for fname in required_funcs:
            fn_node = user_funcs.get(fname)
            if not fn_node or _is_trivial_function_body(fn_node.body):
                return False, f"Debes implementar el cuerpo de la función '{fname}'."

    return True, None


def _extract_exercise_blanks(ex, lang="python"):
    use_java = lang == "java" and bool(ex.get("template_html_java"))
    tpl = ex.get("template_html_java") if use_java else ex.get("template_html")
    if isinstance(tpl, str) and tpl:
        extracted = [
            html.unescape(m.group(1) if m.group(1) is not None else m.group(2))
            for m in _DATA_ANSWER_EXTRACT_RE.finditer(tpl)
        ]
        if extracted:
            return extracted
    ans = ex.get("answer_java") if use_java and ex.get("answer_java") is not None else ex.get("answer")
    if ans is not None:
        return [str(ans)]
    if ex.get("expected_output") is not None:
        return [str(ex["expected_output"])]
    return []


def _grade_exercise_submission(ex, lang, raw_answer, raw_answers, raw_actual_output=None):
    """Califica estrictamente en el servidor una respuesta de ejercicio del currículo."""
    ex_type = ex.get("type") or "fill-blank"
    use_java = lang == "java" and bool(
        ex.get("question_java") or ex.get("template_html_java") or ex.get("options_java")
    )
    explanation = (
        ex.get("explanation_java") or ex.get("explanation") or ""
        if use_java
        else ex.get("explanation") or ""
    )

    if ex_type == "multiple-choice":
        correct_raw = (
            ex.get("correct_java", ex.get("correct"))
            if (use_java and ex.get("options_java"))
            else ex.get("correct")
        )
        correct_idx = _safe_int(correct_raw, -1)
        if isinstance(raw_answer, bool) or raw_answer is None:
            selected_idx = -1
        else:
            selected_idx = _safe_int(raw_answer, -1)
        passed = correct_idx >= 0 and selected_idx == correct_idx
        return passed, {
            "type": "multiple-choice",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
            "selected_index": selected_idx,
            "correct_index": correct_idx if passed else None,
        }

    if ex_type == "reorder":
        lines = ex.get("lines") or []
        expected = list(range(len(lines)))
        if isinstance(raw_answers, list) and len(raw_answers) == len(expected):
            cleaned = []
            valid_list = True
            for item in raw_answers:
                if isinstance(item, bool):
                    valid_list = False
                    break
                val = _safe_int(item, -1)
                if val < 0:
                    valid_list = False
                    break
                cleaned.append(val)
            passed = valid_list and bool(expected) and cleaned == expected
        else:
            passed = False
        return passed, {
            "type": "reorder",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
        }

    if ex_type == "find-error":
        correct_line = _safe_int(ex.get("error_line", -1), -1)
        if isinstance(raw_answer, bool) or raw_answer is None:
            selected_line = -1
        else:
            selected_line = _safe_int(raw_answer, -1)
        passed = correct_line >= 0 and selected_line == correct_line
        return passed, {
            "type": "find-error",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
            "selected_line": selected_line,
            "correct_line": correct_line if passed else None,
        }

    # Ejercicio libre con expected_output (sin plantilla fill-blank ni opciones)
    has_template = bool(ex.get("template_html_java") if use_java else ex.get("template_html"))
    if not has_template and ex.get("expected_output") is not None:
        expected_out = str(ex["expected_output"])
        user_code = str(raw_answer or "").strip() if raw_answer is not None else ""
        if not user_code:
            passed = False
        else:
            norm_expected = _normalize_answer_text(expected_out)
            if _normalize_answer_text(user_code) == norm_expected:
                passed = True
            else:
                # Validar que el código Python tenga sintaxis válida y coincida con la salida real ejecutada en Pyodide
                passed = False
                if isinstance(raw_actual_output, str) and _normalize_answer_text(raw_actual_output) == norm_expected:
                    try:
                        parsed_tree = ast.parse(user_code)
                        if parsed_tree.body and not _is_trivial_function_body(parsed_tree.body):
                            passed = True
                    except SyntaxError:
                        passed = False
        return passed, {
            "type": "freeform",
            "explanation": explanation,
            "hint": ex.get("hint") or "",
        }

    # fill-blank
    expected_blanks = _extract_exercise_blanks(ex, "java" if use_java else "python")
    if isinstance(raw_answers, list):
        user_blanks = ["" if v is None else str(v) for v in raw_answers]
    elif raw_answer is not None:
        user_blanks = [str(raw_answer)]
    else:
        user_blanks = []

    input_results = []
    for idx, exp_val in enumerate(expected_blanks):
        u_val = user_blanks[idx] if idx < len(user_blanks) else ""
        input_results.append(_normalize_answer_text(u_val) == _normalize_answer_text(exp_val))

    passed = bool(expected_blanks) and len(user_blanks) == len(expected_blanks) and all(input_results)
    return passed, {
        "type": "fill-blank",
        "explanation": explanation,
        "hint": ex.get("hint") or "",
        "input_results": input_results,
    }


def _get_exercise_solution(ex, lang="python"):
    """Devuelve la solución de un ejercicio para el botón 'Ver Solución' (sin otorgar XP)."""
    ex_type = ex.get("type") or "fill-blank"
    use_java = lang == "java" and bool(
        ex.get("question_java") or ex.get("template_html_java") or ex.get("options_java")
    )
    explanation = (
        ex.get("explanation_java") or ex.get("explanation") or ""
        if use_java
        else ex.get("explanation") or ""
    )
    if ex_type == "multiple-choice":
        correct_raw = (
            ex.get("correct_java", ex.get("correct"))
            if (use_java and ex.get("options_java"))
            else ex.get("correct")
        )
        return {"type": "multiple-choice", "correct_index": _safe_int(correct_raw, -1), "explanation": explanation}
    if ex_type == "reorder":
        return {"type": "reorder", "order": list(range(len(ex.get("lines") or []))), "explanation": explanation}
    if ex_type == "find-error":
        return {"type": "find-error", "error_line": _safe_int(ex.get("error_line", -1), -1), "explanation": explanation}
    return {
        "type": "fill-blank",
        "answers": _extract_exercise_blanks(ex, "java" if use_java else "python"),
        "explanation": explanation,
    }
