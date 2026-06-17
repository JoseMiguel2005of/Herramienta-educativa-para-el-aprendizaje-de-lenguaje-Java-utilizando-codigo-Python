import pprint
from compiler import translate

code_examples = [
    "print('Hello World')",
    "x = 5\ny = x + 10\nprint(y)",
    "for i in range(5):\n    print(i)",
    "def saludar(nombre):\n    return 'Hola ' + nombre",
    "class Perro:\n    def __init__(self, nombre):\n        self.nombre = nombre\n    def ladrar(self):\n        print('Guau')",
    "lista = [1, 2, 3]\nlista.append(4)",
    "try:\n    x = 1 / 0\nexcept:\n    print('error')"
]

for code in code_examples:
    print(f"--- TRANSLATING ---\n{code}")
    result = translate(code)
    print(f"--- RESULT ---")
    print(result['java'])
    if result['errors']:
        print("ERRORS:", result['errors'])
    print("\n")
