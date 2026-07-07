"""
Comprehensive tests for the Python → Java transpiler.
Tests all supported patterns including complex ones.
"""
from compiler import translate

# ──────────────────────────────────────────────────────────
# Test cases: (description, python_code, should_not_error)
# ──────────────────────────────────────────────────────────

test_cases = [
    # ── BASICS ──
    ("Hello World",
     "print('Hello World')",
     True),

    ("Variables and arithmetic",
     "x = 5\ny = x + 10\nprint(y)",
     True),

    ("For loop with range",
     "for i in range(5):\n    print(i)",
     True),

    ("Function definition",
     "def saludar(nombre):\n    return 'Hola ' + nombre",
     True),

    ("Class with constructor",
     "class Perro:\n    def __init__(self, nombre):\n        self.nombre = nombre\n    def ladrar(self):\n        print('Guau')",
     True),

    ("List append",
     "lista = [1, 2, 3]\nlista.append(4)",
     True),

    ("Try/except",
     "try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    print('error')",
     True),

    # ── TUPLE UNPACKING ──
    ("Tuple unpacking simple",
     "a, b = 1, 2\nprint(a)\nprint(b)",
     True),

    ("Tuple unpacking triple",
     "x, y, z = 10, 20, 30",
     True),

    # ── LIST COMPREHENSION ──
    ("List comprehension simple",
     "squares = [x * x for x in range(10)]",
     True),

    ("List comprehension with filter",
     "evens = [x for x in range(20) if x % 2 == 0]",
     True),

    # ── TERNARY EXPRESSION ──
    ("Ternary expression",
     "x = 10\ny = 'positive' if x > 0 else 'negative'\nprint(y)",
     True),

    # ── CHAINED COMPARISON ──
    ("Chained comparison",
     "x = 5\nif 0 < x < 10:\n    print('in range')",
     True),

    # ── LAMBDA ──
    ("Lambda function",
     "double = lambda x: x * 2\nprint(double(5))",
     True),

    # ── SET LITERAL ──
    ("Set literal",
     "s = {1, 2, 3, 4, 5}",
     True),

    # ── DICT WITH DATA ──
    ("Dict with data",
     "d = {'name': 'Juan', 'age': 25}\nprint(d['name'])",
     True),

    # ── F-STRING ──
    ("F-string",
     "name = 'Carlos'\nage = 30\nprint(f'Me llamo {name} y tengo {age} años')",
     True),

    # ── STRING METHODS ──
    ("String methods",
     "msg = 'hello world'\nprint(msg.upper())\nprint(msg.lower())\nprint(msg.strip())\nprint(msg.replace('hello', 'hola'))\nprint(msg.startswith('hello'))",
     True),

    # ── LIST METHODS ──
    ("List methods",
     "nums = [3, 1, 4, 1, 5]\nnums.sort()\nnums.reverse()\nnums.insert(0, 99)\nlast = nums.pop()\nprint(nums)",
     True),

    # ── DICT METHODS ──
    ("Dict methods",
     "d = {'a': 1, 'b': 2}\nval = d.get('c', 0)\nprint(d.keys())\nprint(d.values())",
     True),

    # ── ENUMERATE ──
    ("Enumerate loop",
     "frutas = ['manzana', 'banana', 'cereza']\nfor i, fruta in enumerate(frutas):\n    print(i, fruta)",
     True),

    # ── NEGATIVE INDEXING ──
    ("Negative indexing",
     "nums = [10, 20, 30, 40, 50]\nprint(nums[-1])\nprint(nums[-2])",
     True),

    # ── WHILE TRUE ──
    ("While True with break",
     "while True:\n    x = 1\n    break",
     True),

    # ── NONE ──
    ("None literal",
     "x = None\nif x is None:\n    print('is none')",
     True),

    # ── FLOOR DIVISION ──
    ("Floor division",
     "x = 17 // 3\nprint(x)",
     True),

    # ── POWER ──
    ("Power operator",
     "x = 2 ** 10\nprint(x)",
     True),

    # ── ASSERT ──
    ("Assert statement",
     "x = 5\nassert x > 0, 'x must be positive'",
     True),

    # ── DELETE ──
    ("Delete statement",
     "x = 10\ndel x",
     True),

    # ── RAISE ──
    ("Raise exception",
     "def check(x):\n    if x < 0:\n        raise ValueError('negativo')\n    return x",
     True),

    # ── WITH STATEMENT ──
    ("With statement",
     "with open('file.txt') as f:\n    data = f.read()",
     True),

    # ── CLASS INHERITANCE ──
    ("Class inheritance",
     "class Animal:\n    def __init__(self, nombre):\n        self.nombre = nombre\n    def hablar(self):\n        pass\n\nclass Gato(Animal):\n    def hablar(self):\n        return 'Miau'",
     True),

    # ── COMPLEX COMBINED ──
    ("Complex: Fibonacci",
     """def fibonacci(n):
    a, b = 0, 1
    result = []
    for i in range(n):
        result.append(a)
        a, b = b, a + b
    return result

nums = fibonacci(10)
for n in nums:
    print(n)""",
     True),

    ("Complex: Bubble Sort",
     """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

nums = [64, 34, 25, 12, 22, 11, 90]
print(bubble_sort(nums))""",
     True),

    ("Complex: Class with multiple methods",
     """class Calculadora:
    def __init__(self):
        self.historial = []

    def sumar(self, a, b):
        resultado = a + b
        self.historial.append(resultado)
        return resultado

    def promedio(self):
        if len(self.historial) == 0:
            return 0
        total = 0
        for val in self.historial:
            total = total + val
        return total / len(self.historial)

calc = Calculadora()
calc.sumar(10, 20)
calc.sumar(5, 15)
print(calc.promedio())""",
     True),

    ("Complex: Dict comprehension-like pattern",
     """estudiantes = {'Ana': 90, 'Luis': 85, 'Maria': 95}
for nombre, nota in estudiantes.items():
    if nota >= 90:
        print(f'{nombre} aprobó con excelencia')
    else:
        print(f'{nombre} aprobó')""",
     True),

    # ── EDGE CASES ──
    ("Empty input", "", True),
    ("Just a comment (docstring)", "'This is a module docstring'", True),
    ("Multiple print with sep", "print('a', 'b', 'c')", True),
    ("Augmented assign", "x = 10\nx += 5\nx -= 2\nx *= 3", True),
    ("Boolean operators", "x = True and False\ny = True or False\nz = not x", True),
    ("String multiplication", "line = '-' * 40\nprint(line)", True),
    ("isinstance check", "x = 5\nprint(isinstance(x, int))", True),
]

# ──────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────

passed = 0
failed = 0
total = len(test_cases)

for desc, code, should_succeed in test_cases:
    result = translate(code)
    has_errors = len(result["errors"]) > 0

    if should_succeed and not has_errors:
        status = "[PASS]"
        passed += 1
    elif should_succeed and has_errors:
        status = "[FAIL]"
        failed += 1
    else:
        status = "[PASS] (expected errors)"
        passed += 1

    print(f"{status} | {desc}")
    if has_errors:
        for err in result["errors"]:
            print(f"       ERROR: {err}")
    if result["warnings"]:
        for w in result["warnings"]:
            print(f"       WARN: {w}")

    # Show generated code for failed or interesting cases
    if has_errors or desc.startswith("Complex"):
        print(f"  --- Generated Java ---")
        for line in result["java"].split("\n"):
            print(f"    {line}")
        print()

print(f"\n{'='*60}")
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("All tests passed!")
else:
    print(f"{failed} test(s) need attention.")
