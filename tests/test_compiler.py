"""Pruebas unitarias y de compilación javac para el compilador Python -> Java."""

import re
import shutil
import subprocess

import pytest

from compiler import translate

HAS_JAVAC = shutil.which("javac") is not None
requires_javac = pytest.mark.skipif(not HAS_JAVAC, reason="javac no disponible en el entorno")


def _compile_java_with_javac(tmp_path, java_code, class_name="Program"):
    """Escribe el archivo .java con el nombre real de la clase pública y verifica compilación con javac."""
    match = re.search(r"public\s+class\s+([A-Za-z_][A-Za-z0-9_]*)", java_code)
    actual_class = match.group(1) if match else class_name
    java_file = tmp_path / f"{actual_class}.java"
    java_file.write_text(java_code, encoding="utf-8")
    proc = subprocess.run(
        ["javac", str(java_file)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"javac falló al compilar {actual_class}.java:\n"
        f"STDERR:\n{proc.stderr}\n\n"
        f"CÓDIGO GENERADO:\n{java_code}"
    )


# =====================================================================
# 1. Casos críticos del generador (compiler/generator.py)
# =====================================================================


def test_input_with_prompt_generates_valid_java_without_comma_operator():
    code = 'nombre = input("Ingresa tu nombre: ")\nprint(nombre)\n'
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]
    assert "import java.util.Scanner;" in java
    assert "scanner.nextLine()" in java
    assert 'System.out.print("Ingresa tu nombre: ")' in java
    # Java NO soporta el operador coma (System.out.print(...), scanner.nextLine())
    assert "(System.out.print(" not in java


def test_for_else_with_break_sets_flag_false_before_break():
    code = (
        "for i in range(5):\n"
        "    if i == 3:\n"
        "        break\n"
        "else:\n"
        '    print("no encontrado")\n'
    )
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]
    assert "boolean _loopCompleted1 = true;" in java
    assert "if (_loopCompleted1)" in java
    # Antes de break; debe marcarse _loopCompleted1 = false; para que else no se ejecute
    assert "_loopCompleted1 = false;" in java


def test_while_else_with_break_sets_flag_false_before_break():
    code = (
        "x = 0\n"
        "while x < 5:\n"
        "    if x == 2:\n"
        "        break\n"
        "    x += 1\n"
        "else:\n"
        '    print("terminado sin break")\n'
    )
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]
    assert "boolean _loopCompleted1 = true;" in java
    assert "if (_loopCompleted1)" in java
    assert "_loopCompleted1 = false;" in java


def test_list_count_uses_collections_frequency():
    code = "nums = [1, 2, 1, 3]\nc = nums.count(1)\nprint(c)\n"
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]
    assert "Collections.frequency(nums, 1)" in java
    assert "import java.util.Collections;" in java
    # No debe confundirse con String.count() usando .length() / .replace()
    assert "nums.replace(" not in java


def test_dict_pop_and_clear_use_map_semantics():
    code = (
        'd = {"a": 1, "b": 2}\n'
        'v1 = d.pop("a")\n'
        'v2 = d.pop("z", 0)\n'
        "d.clear()\n"
    )
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]
    assert 'd.remove("a")' in java
    assert "d.clear();" in java
    # dict.pop("z", 0) debe respetar el valor por defecto 0 (no ignorarlo cayendo en list.pop)
    assert "0" in java and ('containsKey("z")' in java or 'getOrDefault("z", 0)' in java or 'd.remove("z")' in java)
    # Si dict.pop se llama con valor por defecto, no debe perder el segundo argumento
    pop_default_lines = [ln for ln in java.splitlines() if "v2" in ln]
    assert pop_default_lines and "0" in pop_default_lines[0], (
        f"dict.pop('z', 0) ignoró el valor por defecto: {pop_default_lines}"
    )


def test_list_comprehension_with_external_variables_passes_scope():
    code = (
        "factor = 3\n"
        "nums = [1, 2, 3]\n"
        "scaled = [x * factor for x in nums]\n"
        "print(scaled)\n"
    )
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]

    # Si se extrae a un método auxiliar _listCompN, debe recibir las variables externas como parámetros
    helper_sig = re.search(r"public static\s+List<[^>]+>\s+_listComp\d+\(([^)]*)\)", java)
    if helper_sig:
        params_str = helper_sig.group(1)
        assert "factor" in params_str and "nums" in params_str, (
            f"El método auxiliar de list comprehension no recibe variables externas 'factor'/'nums': {helper_sig.group(0)}"
        )


def test_sum_any_all_with_generators_do_not_duplicate_helpers():
    code = (
        "s = sum(x for x in range(5))\n"
        "a = any(x > 3 for x in range(5))\n"
        "b = all(x >= 0 for x in range(5))\n"
        "print(s)\n"
        "print(a)\n"
        "print(b)\n"
    )
    res = translate(code)
    assert res["errors"] == []
    java = res["java"]

    # Debe haber exactamente 3 métodos _genExpr (uno por cada sum/any/all), sin duplicados huérfanos
    gen_defs = re.findall(r"public static\s+List<[^>]+>\s+(_genExpr\d+)\s*\(", java)
    assert len(gen_defs) == 3, (
        f"Se esperaban 3 métodos _genExpr (sin duplicar), se generaron {len(gen_defs)}: {gen_defs}"
    )
    assert ".sum()" in java
    assert ".anyMatch(" in java
    assert ".allMatch(" in java


@pytest.mark.parametrize(
    "snippet",
    [
        "x = abs()",
        "x = min()",
        "x = max()",
        "x = round()",
        "x = sum()",
        "x = type()",
        "x = chr()",
        "x = ord()",
        "x = hex()",
        "x = oct()",
        "x = bin()",
        "d = {}\nd.setdefault()",
        "s = {1}\ns.issubset()",
    ],
)
def test_zero_arg_calls_do_not_raise_index_error(snippet):
    res = translate(snippet)
    assert res["errors"] == [], f"Error inesperado para {snippet!r}: {res['errors']}"
    assert res["java"].strip() != ""


# =====================================================================
# 2. Validación de compilación real con javac (opcional si javac existe)
# =====================================================================


@requires_javac
def test_javac_compiles_basic_control_flow_and_functions(tmp_path):
    code = (
        "def sumar(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "total = 0\n"
        "for i in range(5):\n"
        "    if i % 2 == 0:\n"
        "        total += sumar(i, 1)\n"
        "print(total)\n"
    )
    res = translate(code, class_name="BasicCheck")
    assert res["errors"] == []
    _compile_java_with_javac(tmp_path, res["java"], class_name="BasicCheck")


@requires_javac
@pytest.mark.parametrize(
    "class_name, snippet",
    [
        ("InputPromptCheck", 'nombre = input("Tu nombre: ")\nprint(nombre)\n'),
        (
            "ForElseCheck",
            'for i in range(5):\n    if i == 2:\n        break\nelse:\n    print("done")\n',
        ),
        (
            "WhileElseCheck",
            "x = 0\nwhile x < 3:\n    if x == 1:\n        break\n    x += 1\nelse:\n    print(x)\n",
        ),
        ("ListCountCheck", "nums = [1, 2, 1]\nc = nums.count(1)\nprint(c)\n"),
        (
            "DictPopClearCheck",
            'd = {"a": 1, "b": 2}\nv = d.pop("a")\nd.clear()\nprint(v)\n',
        ),
        (
            "ListCompExternalCheck",
            "factor = 3\nnums = [1, 2, 3]\nres = [x * factor for x in nums]\nprint(res)\n",
        ),
        (
            "GeneratorBuiltinsCheck",
            "s = sum(x for x in range(5))\na = any(x > 2 for x in range(5))\nb = all(x >= 0 for x in range(5))\nprint(s)\nprint(a)\nprint(b)\n",
        ),
    ],
)
def test_javac_compiles_critical_compiler_patterns(tmp_path, class_name, snippet):
    res = translate(snippet, class_name=class_name)
    assert res["errors"] == [], f"Errores del compilador: {res['errors']}"
    _compile_java_with_javac(tmp_path, res["java"], class_name=class_name)
