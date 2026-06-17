import unittest

from translator import translate


class TestTranslator(unittest.TestCase):
    def test_hello_world(self):
        result = translate('print("¡Hola, Mundo!")')
        self.assertEqual(result["errors"], [])
        self.assertIn('System.out.println("¡Hola, Mundo!");', result["java"])
        self.assertIn("public class Program", result["java"])

    def test_variables(self):
        code = (
            'nombre = "Ana"\n'
            "edad = 20\n"
            "activo = True\n"
            'print(f"{nombre} tiene {edad} años")'
        )
        result = translate(code)
        self.assertEqual(result["errors"], [])
        java = result["java"]
        self.assertIn('String nombre = "Ana";', java)
        self.assertIn("int edad = 20;", java)
        self.assertIn("boolean activo = true;", java)
        self.assertIn("System.out.println", java)

    def test_conditionals(self):
        code = (
            "nota = 85\n"
            "if nota >= 90:\n"
            '    print("Excelente")\n'
            "elif nota >= 70:\n"
            '    print("Aprobado")\n'
            "else:\n"
            '    print("Reprobado")'
        )
        result = translate(code)
        self.assertEqual(result["errors"], [])
        java = result["java"]
        self.assertIn("if (nota >= 90)", java)
        self.assertIn("} else if (nota >= 70)", java)
        self.assertIn('System.out.println("Aprobado");', java)

    def test_loops(self):
        code = (
            "for i in range(5):\n"
            '    print(f"Iteración {i}")\n'
            "\n"
            "contador = 0\n"
            "while contador < 3:\n"
            '    print(f"While: {contador}")\n'
            "    contador += 1"
        )
        result = translate(code)
        self.assertEqual(result["errors"], [])
        java = result["java"]
        self.assertIn("for (int i = 0; i < 5; i++)", java)
        self.assertIn("while (contador < 3)", java)
        self.assertIn("contador += 1;", java)

    def test_syntax_error(self):
        result = translate("if True\n    pass")
        self.assertTrue(result["errors"])
        self.assertEqual(result["java"], "")


if __name__ == "__main__":
    unittest.main()
