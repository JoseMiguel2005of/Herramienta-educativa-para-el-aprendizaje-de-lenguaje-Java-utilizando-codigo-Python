import ast
from typing import Dict, Any
from .environment import Environment
from .analyzer import Analyzer
from .generator import Generator

def translate(python_code: str, class_name: str = "Program") -> Dict[str, Any]:
    """
    Main entry point for translating Python code to Java.
    """
    code = python_code.strip()
    if not code:
        return {"java": "", "errors": [], "warnings": []}

    env = Environment()
    
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        env.error(f"Error de sintaxis en Python (línea {exc.lineno}): {exc.msg}")
        return {
            "java": "",
            "errors": env.errors,
            "warnings": env.warnings,
        }

    # Pass 1: Analysis & Type Inference
    try:
        analyzer = Analyzer(env)
        analyzer.analyze(tree)
    except Exception as exc:
        env.error(f"Error en fase de análisis: {str(exc)}")

    # Pass 2: Code Generation
    try:
        generator = Generator(env, class_name=class_name)
        java_code = generator.generate(tree)
        return {
            "java": java_code,
            "errors": env.errors,
            "warnings": env.warnings,
        }
    except Exception as exc:
        env.error(f"Error en fase de generación: {str(exc)}")
        return {"java": "", "errors": env.errors, "warnings": env.warnings}
