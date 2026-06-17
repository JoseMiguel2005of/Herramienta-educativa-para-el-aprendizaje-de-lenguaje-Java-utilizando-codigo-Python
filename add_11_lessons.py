import re

es_titles = """        "lesson_casting_title": "Casting (Conversión)",
        "lesson_booleanos_title": "Booleanos",
        "lesson_user-input_title": "Entrada de Usuario",
        "lesson_formateo-cadenas_title": "Formateo de Cadenas",
        "lesson_arreglos_title": "Arreglos (Arrays)",
        "lesson_lambdas_title": "Expresiones Lambda",
        "lesson_polimorfismo_title": "Polimorfismo",
        "lesson_scope_title": "Ámbito (Scope)",
        "lesson_math_title": "Matemáticas (Math)",
        "lesson_regex_title": "Expresiones Regulares",
        "lesson_paquetes_title": "Gestión de Paquetes",
"""

en_titles = """        "lesson_casting_title": "Type Casting",
        "lesson_booleanos_title": "Booleans",
        "lesson_user-input_title": "User Input",
        "lesson_formateo-cadenas_title": "String Formatting",
        "lesson_arreglos_title": "Arrays",
        "lesson_lambdas_title": "Lambda Expressions",
        "lesson_polimorfismo_title": "Polymorphism",
        "lesson_scope_title": "Scope",
        "lesson_math_title": "Math",
        "lesson_regex_title": "Regular Expressions",
        "lesson_paquetes_title": "Package Management",
"""

es_lessons = '''            "casting": {
                "title": "Casting (Conversión de Tipos)",
                "intro": "El casting es el proceso de forzar a que una variable sea tratada como un tipo de dato específico.",
                "python_desc": "Usa funciones de construcción como int(), float(), str().",
                "java_desc": "Usa paréntesis (tipo) para tipos primitivos, o métodos como Integer.parseInt().",
                "explanation": "En Python el casting se maneja como llamadas a funciones constructoras. En Java, se diferencia fuertemente entre tipos primitivos (donde se usa la sintaxis de prefijo entre paréntesis) y objetos (donde se usan métodos de conversión estáticos).",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "cast-1",
                        "python": "texto = \\"10\\"\\nnumero = int(texto)\\n\\ndecimal = 5.8\\nentero = int(decimal)",
                        "java": "String texto = \\"10\\";\\nint numero = Integer.parseInt(texto);\\n\\ndouble decimal = 5.8;\\nint entero = (int) decimal;",
                        "explanation": "Nota la diferencia entre convertir un String a número, y convertir de un tipo primitivo a otro primitivo (decimal a entero)."
                    }
                ]
            },
            "booleanos": {
                "title": "Booleanos",
                "intro": "Los booleanos representan uno de dos valores: verdadero o falso.",
                "python_desc": "Los valores son True y False (primera letra mayúscula).",
                "java_desc": "Los valores son true y false (todo en minúscula).",
                "explanation": "Mientras que en Python casi cualquier valor se evalúa como Booleano automáticamente en un if (ej. listas vacías son False), Java requiere explícitamente que la condición devuelva un valor boolean estricto.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "bool-1",
                        "python": "es_mayor = True\\n\\nif 10 > 9:\\n    print(es_mayor)",
                        "java": "boolean esMayor = true;\\n\\nif (10 > 9) {\\n    System.out.println(esMayor);\\n}",
                        "explanation": "Capitalización distinta y tipos estrictos en Java."
                    }
                ]
            },
            "user-input": {
                "title": "Entrada de Usuario",
                "intro": "Para que un programa sea interactivo, necesitamos poder capturar lo que el usuario escribe.",
                "python_desc": "Función input() nativa y simple.",
                "java_desc": "Requiere importar y usar la clase java.util.Scanner.",
                "explanation": "Python hace que la entrada de texto por consola sea trivial. En Java, debemos crear una instancia del Scanner conectada al System.in para leer los datos ingresados.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "input-1",
                        "python": "nombre = input(\\"¿Cuál es tu nombre? \\")\\nprint(\\"Hola \\" + nombre)",
                        "java": "import java.util.Scanner;\\n\\nScanner sc = new Scanner(System.in);\\nSystem.out.print(\\"¿Cuál es tu nombre? \\");\\nString nombre = sc.nextLine();\\nSystem.out.println(\\"Hola \\" + nombre);",
                        "explanation": "La lectura por consola en Java es considerablemente más detallada (verbose)."
                    }
                ]
            },
            "formateo-cadenas": {
                "title": "Formateo de Cadenas",
                "intro": "Insertar valores variables dentro de cadenas de texto de forma legible.",
                "python_desc": "F-strings (ej. f\\"Hola {nombre}\\").",
                "java_desc": "String.format() o System.out.printf().",
                "explanation": "Las f-strings de Python 3.6+ revolucionaron la legibilidad al permitir inyectar variables directamente. Java depende de los comodines posicionales tipo C (%s, %d) o la concatenación pura.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "fmt-1",
                        "python": "precio = 49.99\\ntexto = f\\"El producto cuesta ${precio}\\"\\nprint(texto)",
                        "java": "double precio = 49.99;\\nString texto = String.format(\\"El producto cuesta $%.2f\\", precio);\\nSystem.out.println(texto);",
                        "explanation": "String.format() en Java usa marcadores de posición estandarizados."
                    }
                ]
            },
            "arreglos": {
                "title": "Arreglos (Arrays)",
                "intro": "Las estructuras que agrupan elementos múltiples difieren fundamentalmente bajo el capó.",
                "python_desc": "Las 'listas' funcionan en la práctica como arreglos dinámicos.",
                "java_desc": "Tiene verdaderos Arrays primitivos (estáticos) y también ArrayList (dinámicos).",
                "explanation": "Python abstrae los arrays puros bajo el concepto dinámico de 'lista'. En Java, un Array primitivo tiene un tamaño fijo de memoria desde el momento de su creación que no puede cambiar.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "arr-1",
                        "python": "# Python no tiene arrays fijos, usa listas para todo\\nautos = [\\"Ford\\", \\"Volvo\\", \\"BMW\\"]\\nautos[0] = \\"Toyota\\"",
                        "java": "// Array de tamaño estático\\nString[] autos = {\\"Ford\\", \\"Volvo\\", \\"BMW\\"};\\nautos[0] = \\"Toyota\\";\\n\\n// Arrays sin datos inmediatos ocupan un tamaño exacto\\nint[] numeros = new int[5];",
                        "explanation": "Sintaxis de declaración de arrays fijos en Java."
                    }
                ]
            },
            "lambdas": {
                "title": "Expresiones Lambda",
                "intro": "Funciones anónimas o pequeñas funciones en una sola línea.",
                "python_desc": "Sintaxis lambda args: expresión.",
                "java_desc": "Sintaxis args -> expresión.",
                "explanation": "Ambos lenguajes ofrecen un modo conciso de definir funciones cortas para pasarlas como argumentos (por ejemplo a métodos de filtrado y mapeo).",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "lam-1",
                        "python": "multiplicar = lambda a, b: a * b\\nprint(multiplicar(5, 6))",
                        "java": "interface Operacion { int operar(int a, int b); }\\n\\n// Las Lambdas en Java necesitan interfaces funcionales\\nOperacion multiplicar = (a, b) -> a * b;\\nSystem.out.println(multiplicar.operar(5, 6));",
                        "explanation": "Java es fuertemente tipado, por lo que una lambda siempre requiere de una interfaz funcional como contrato."
                    }
                ]
            },
            "polimorfismo": {
                "title": "Polimorfismo",
                "intro": "Múltiples clases con métodos que se llaman de la misma manera, procesados de forma genérica.",
                "python_desc": "Duck typing (si camina como pato...).",
                "java_desc": "Herencia obligatoria e interfaces (@Override).",
                "explanation": "Python permite que cualquier objeto con el método correspondiente ejecute la acción. En Java, debemos obligar que todos hereden de una clase abstracta común o implementen la misma Interfaz.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "poli-1",
                        "python": "class Perro:\\n    def sonido(self): print(\\"Guau\\")\\n\\nclass Gato:\\n    def sonido(self): print(\\"Miau\\")\\n\\nfor animal in (Perro(), Gato()):\\n    animal.sonido()",
                        "java": "interface Animal { void sonido(); }\\nclass Perro implements Animal { public void sonido() { System.out.println(\\"Guau\\"); } }\\nclass Gato implements Animal { public void sonido() { System.out.println(\\"Miau\\"); } }\\n\\nAnimal[] animales = {new Perro(), new Gato()};\\nfor(Animal a : animales) { a.sonido(); }",
                        "explanation": "Duck Typing versus Polimorfismo basado en Interfaces."
                    }
                ]
            },
            "scope": {
                "title": "Ámbito (Scope)",
                "intro": "Determina desde dónde se pueden acceder las variables.",
                "python_desc": "Variables globales usando keyword 'global'.",
                "java_desc": "Ámbito restringido por bloques {}, clases y modificadores.",
                "explanation": "En Java no existen variables estrictamente 'globales' fuera de clases. El ámbito se controla a nivel de clase (public, private, static) y de bloque entre llaves.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "scp-1",
                        "python": "x = 300\\n\\ndef mi_funcion():\\n    global x\\n    x = 200\\n\\nmi_funcion()\\nprint(x)",
                        "java": "public class MiClase {\\n    static int x = 300;\\n\\n    static void miFuncion() {\\n        x = 200;\\n    }\\n\\n    public static void main(String[] args) {\\n        miFuncion();\\n        System.out.println(x);\\n    }\\n}",
                        "explanation": "Las 'variables globales' en Java generalmente se simulan mediante variables de clase 'static'."
                    }
                ]
            },
            "math": {
                "title": "Matemáticas (Math)",
                "intro": "Librerías incorporadas para tareas numéricas (raíz cuadrada, potencias, constantes).",
                "python_desc": "Módulo math (requiere importación).",
                "java_desc": "Clase estática Math nativa (sin importar).",
                "explanation": "Ambos lenguajes tienen funciones matemáticas estandarizadas. Java las incluye de forma nativa sin que importe ningún paquete extra.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "math-1",
                        "python": "import math\\n\\nraiz = math.sqrt(64)\\npi = math.pi\\nabsoluto = abs(-5)",
                        "java": "double raiz = Math.sqrt(64);\\ndouble pi = Math.PI;\\nint absoluto = Math.abs(-5);",
                        "explanation": "Math en Java es una clase incorporada globalmente de la que se acceden todos sus métodos estáticamente."
                    }
                ]
            },
            "regex": {
                "title": "Expresiones Regulares",
                "intro": "Permite encontrar patrones complejos dentro de cadenas de texto.",
                "python_desc": "Módulo re.",
                "java_desc": "Paquete java.util.regex (Pattern, Matcher).",
                "explanation": "Las expresiones regulares en sí utilizan la misma sintaxis base, pero el modo de aplicar la coincidencia es distinto en la API.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "reg-1",
                        "python": "import re\\n\\ntexto = \\"El sol sale\\"\\ncoincidencia = re.search(r\\"(?i)sol\\", texto)\\nif coincidencia:\\n    print(\\"Encontrado\\")",
                        "java": "import java.util.regex.*;\\n\\nString texto = \\"El sol sale\\";\\nPattern pattern = Pattern.compile(\\"(?i)sol\\");\\nMatcher matcher = pattern.matcher(texto);\\nif (matcher.find()) {\\n    System.out.println(\\"Encontrado\\");\\n}",
                        "explanation": "En Java siempre hay un flujo de 2 pasos: compilar el Pattern y utilizar un Matcher."
                    }
                ]
            },
            "paquetes": {
                "title": "Gestión de Paquetes",
                "intro": "El equivalente a importar librerías hechas por otros programadores.",
                "python_desc": "Pip (pip install paquete).",
                "java_desc": "Maven (pom.xml) o Gradle (build.gradle).",
                "explanation": "A diferencia de Python donde instalamos paquetes globalmente por comandos `pip`, Java es un lenguaje altamente estructurado que usa archivos de configuración (`pom.xml`) para que las dependencias de descargas automáticamente al construir (build) el proyecto entero.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "pkg-1",
                        "python": "# Instalación global:\\npip install requests\\n\\n# Uso\\nimport requests",
                        "java": "<!-- En el archivo pom.xml de Maven se añade: -->\\n<dependency>\\n    <groupId>com.google.code.gson</groupId>\\n    <artifactId>gson</artifactId>\\n    <version>2.8.6</version>\\n</dependency>",
                        "explanation": "Esto representa un salto de paradigma importante: Java centraliza las dependencias en archivos del proyecto."
                    }
                ]
            },
'''

en_lessons = '''            "casting": {
                "title": "Type Casting",
                "intro": "Casting is the process of forcing a variable to be treated as a specific data type.",
                "python_desc": "Uses constructor functions like int(), float(), str().",
                "java_desc": "Uses parentheses (type) for primitive types, or methods like Integer.parseInt().",
                "explanation": "In Python, casting is handled as calls to constructor functions. In Java, there is a strong distinction between primitive types (where parenthesis prefix syntax is used) and objects (where static conversion methods are used).",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "cast-1",
                        "python": "text = \\"10\\"\\nnumber = int(text)\\n\\ndecimal = 5.8\\ninteger = int(decimal)",
                        "java": "String text = \\"10\\";\\nint number = Integer.parseInt(text);\\n\\ndouble decimal = 5.8;\\nint integer = (int) decimal;",
                        "explanation": "Note the difference between converting a String to a number, and converting from one primitive type to another (decimal to integer)."
                    }
                ]
            },
            "booleanos": {
                "title": "Booleans",
                "intro": "Booleans represent one of two values: true or false.",
                "python_desc": "Values are True and False (first letter uppercase).",
                "java_desc": "Values are true and false (all lowercase).",
                "explanation": "While in Python almost any value is evaluated as a Boolean automatically in an if (e.g., empty lists are False), Java explicitly requires the condition to return a strict boolean value.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "bool-1",
                        "python": "is_greater = True\\n\\nif 10 > 9:\\n    print(is_greater)",
                        "java": "boolean isGreater = true;\\n\\nif (10 > 9) {\\n    System.out.println(isGreater);\\n}",
                        "explanation": "Different capitalization and strict typing in Java."
                    }
                ]
            },
            "user-input": {
                "title": "User Input",
                "intro": "To make a program interactive, we need to be able to capture what the user writes.",
                "python_desc": "Native and simple input() function.",
                "java_desc": "Requires importing and using the java.util.Scanner class.",
                "explanation": "Python makes reading console input trivial. In Java, we must create a Scanner instance connected to System.in to read the entered data.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "input-1",
                        "python": "name = input(\\"What is your name? \\")\\nprint(\\"Hello \\" + name)",
                        "java": "import java.util.Scanner;\\n\\nScanner sc = new Scanner(System.in);\\nSystem.out.print(\\"What is your name? \\");\\nString name = sc.nextLine();\\nSystem.out.println(\\"Hello \\" + name);",
                        "explanation": "Console reading in Java is considerably more verbose."
                    }
                ]
            },
            "formateo-cadenas": {
                "title": "String Formatting",
                "intro": "Inserting variable values inside text strings in a readable way.",
                "python_desc": "F-strings (e.g. f\\"Hello {name}\\").",
                "java_desc": "String.format() or System.out.printf().",
                "explanation": "Python 3.6+ f-strings revolutionized readability by allowing variables to be injected directly. Java relies on C-like positional wildcards (%s, %d) or pure concatenation.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "fmt-1",
                        "python": "price = 49.99\\ntext = f\\"The product costs ${price}\\"\\nprint(text)",
                        "java": "double price = 49.99;\\nString text = String.format(\\"The product costs $%.2f\\", price);\\nSystem.out.println(text);",
                        "explanation": "String.format() in Java uses standardized placeholders."
                    }
                ]
            },
            "arreglos": {
                "title": "Arrays",
                "intro": "Structures that group multiple elements differ fundamentally under the hood.",
                "python_desc": "'Lists' work in practice as dynamic arrays.",
                "java_desc": "Has true primitive (static) Arrays and also ArrayList (dynamic).",
                "explanation": "Python abstracts pure arrays under the dynamic concept of 'list'. In Java, a primitive Array has a fixed memory size from the moment of its creation that cannot change.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "arr-1",
                        "python": "# Python has no fixed arrays, uses lists for everything\\ncars = [\\"Ford\\", \\"Volvo\\", \\"BMW\\"]\\ncars[0] = \\"Toyota\\"",
                        "java": "// Static size Array\\nString[] cars = {\\"Ford\\", \\"Volvo\\", \\"BMW\\"};\\ncars[0] = \\"Toyota\\";\\n\\n// Arrays without immediate data take an exact size\\nint[] numbers = new int[5];",
                        "explanation": "Fixed array declaration syntax in Java."
                    }
                ]
            },
            "lambdas": {
                "title": "Lambda Expressions",
                "intro": "Anonymous functions or small functions in a single line.",
                "python_desc": "lambda args: expression syntax.",
                "java_desc": "args -> expression syntax.",
                "explanation": "Both languages offer a concise way to define short functions to pass them as arguments (e.g., to filtering and mapping methods).",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "lam-1",
                        "python": "multiply = lambda a, b: a * b\\nprint(multiply(5, 6))",
                        "java": "interface Operation { int operate(int a, int b); }\\n\\n// Lambdas in Java need functional interfaces\\nOperation multiply = (a, b) -> a * b;\\nSystem.out.println(multiply.operate(5, 6));",
                        "explanation": "Java is strongly typed, so a lambda always requires a functional interface as a contract."
                    }
                ]
            },
            "polimorfismo": {
                "title": "Polymorphism",
                "intro": "Multiple classes with methods that are called the same way, processed generically.",
                "python_desc": "Duck typing (if it walks like a duck...).",
                "java_desc": "Mandatory inheritance and interfaces (@Override).",
                "explanation": "Python allows any object with the corresponding method to execute the action. In Java, we must enforce that everyone inherits from a common abstract class or implements the same Interface.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "poli-1",
                        "python": "class Dog:\\n    def sound(self): print(\\"Woof\\")\\n\\nclass Cat:\\n    def sound(self): print(\\"Meow\\")\\n\\nfor animal in (Dog(), Cat()):\\n    animal.sound()",
                        "java": "interface Animal { void sound(); }\\nclass Dog implements Animal { public void sound() { System.out.println(\\"Woof\\"); } }\\nclass Cat implements Animal { public void sound() { System.out.println(\\"Meow\\"); } }\\n\\nAnimal[] animals = {new Dog(), new Cat()};\\nfor(Animal a : animals) { a.sound(); }",
                        "explanation": "Duck Typing versus Interface-based Polymorphism."
                    }
                ]
            },
            "scope": {
                "title": "Scope",
                "intro": "Determines from where variables can be accessed.",
                "python_desc": "Global variables using 'global' keyword.",
                "java_desc": "Scope restricted by {} blocks, classes and modifiers.",
                "explanation": "In Java there are no strictly 'global' variables outside classes. Scope is controlled at class level (public, private, static) and block level between curly braces.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "scp-1",
                        "python": "x = 300\\n\\ndef my_function():\\n    global x\\n    x = 200\\n\\nmy_function()\\nprint(x)",
                        "java": "public class MyClass {\\n    static int x = 300;\\n\\n    static void myFunction() {\\n        x = 200;\\n    }\\n\\n    public static void main(String[] args) {\\n        myFunction();\\n        System.out.println(x);\\n    }\\n}",
                        "explanation": "'Global variables' in Java are usually simulated using 'static' class variables."
                    }
                ]
            },
            "math": {
                "title": "Math",
                "intro": "Built-in libraries for numeric tasks (square root, powers, constants).",
                "python_desc": "math module (requires import).",
                "java_desc": "Native Math static class (no import).",
                "explanation": "Both languages have standardized math functions. Java includes them natively without importing any extra packages.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "math-1",
                        "python": "import math\\n\\nroot = math.sqrt(64)\\npi = math.pi\\nabsolute = abs(-5)",
                        "java": "double root = Math.sqrt(64);\\ndouble pi = Math.PI;\\nint absolute = Math.abs(-5);",
                        "explanation": "Math in Java is a globally built-in class from which all its methods are accessed statically."
                    }
                ]
            },
            "regex": {
                "title": "Regular Expressions",
                "intro": "Allows finding complex patterns inside text strings.",
                "python_desc": "re module.",
                "java_desc": "java.util.regex package (Pattern, Matcher).",
                "explanation": "Regular expressions themselves use the same base syntax, but the way matching is applied is different in the API.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "reg-1",
                        "python": "import re\\n\\ntext = \\"The sun rises\\"\\nmatch = re.search(r\\"(?i)sun\\", text)\\nif match:\\n    print(\\"Found\\")",
                        "java": "import java.util.regex.*;\\n\\nString text = \\"The sun rises\\";\\nPattern pattern = Pattern.compile(\\"(?i)sun\\");\\nMatcher matcher = pattern.matcher(text);\\nif (matcher.find()) {\\n    System.out.println(\\"Found\\");\\n}",
                        "explanation": "In Java there is always a 2-step flow: compile the Pattern and use a Matcher."
                    }
                ]
            },
            "paquetes": {
                "title": "Package Management",
                "intro": "The equivalent of importing libraries made by other programmers.",
                "python_desc": "Pip (pip install package).",
                "java_desc": "Maven (pom.xml) or Gradle (build.gradle).",
                "explanation": "Unlike Python where we install packages globally by `pip` commands, Java is a highly structured language that uses configuration files (`pom.xml`) so dependencies are automatically downloaded when building the entire project.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "pkg-1",
                        "python": "# Global installation:\\npip install requests\\n\\n# Usage\\nimport requests",
                        "java": "<!-- In the Maven pom.xml file add: -->\\n<dependency>\\n    <groupId>com.google.code.gson</groupId>\\n    <artifactId>gson</artifactId>\\n    <version>2.8.6</version>\\n</dependency>",
                        "explanation": "This represents a major paradigm shift: Java centralizes dependencies in project files."
                    }
                ]
            },
'''

with open('translations.py', 'r', encoding='utf-8') as f:
    content = f.read()

def insert_after_key_exact(content, lang, target_key, insertion):
    idx = content.find(f'"{lang}": {{')
    if idx == -1: return content
    target_idx = content.find(f'"{target_key}":', idx)
    if target_idx == -1: return content
    line_end = content.find('\\n', target_idx)
    if line_end != -1:
        return content[:line_end+1] + insertion + content[line_end+1:]
    return content

def insert_before_key_exact(content, lang, target_key, insertion):
    idx = content.find(f'"{lang}": {{')
    if idx == -1: return content
    
    # We want to find the exact target key inside the "lessons" block for the specific language
    # So we find the target key from idx
    target_idx = content.find(f'"{target_key}":', idx)
    if target_idx == -1: return content
    
    # Find the start of the line where target_key is
    line_start = content.rfind('\\n', 0, target_idx) + 1
    
    return content[:line_start] + insertion + content[line_start:]

# 1. Insert ES titles
content = insert_after_key_exact(content, 'es', 'lesson_tuplas_title', es_titles)
# 2. Insert EN titles
content = insert_after_key_exact(content, 'en', 'lesson_tuplas_title', en_titles)

# 3. Insert ES lessons BEFORE "j-hola-mundo"
content = insert_before_key_exact(content, 'es', 'j-hola-mundo', es_lessons)
# 4. Insert EN lessons BEFORE "j-hola-mundo"
content = insert_before_key_exact(content, 'en', 'j-hola-mundo', en_lessons)

with open('translations.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Successfully injected 11 new W3Schools-style lessons!')
