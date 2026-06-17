import re

with open("translations.py", "r", encoding="utf-8") as f:
    content = f.read()

en_additions = """
            "comentarios": {
                "title": "Comments",
                "intro": "Comments explain the code and are ignored by the compiler/interpreter.",
                "python_desc": "Use # for single-line comments.",
                "java_desc": "Use // for single-line and /* */ for multi-line comments.",
                "explanation": "Both languages use comments to document logic.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "com-1",
                        "python": "# This is a comment\\nx = 5",
                        "java": "// This is a comment\\nint x = 5;",
                        "explanation": "Simple single-line comments."
                    }
                ]
            },
            "tipos-datos": {
                "title": "Data Types",
                "intro": "Types define what kind of data a variable holds.",
                "python_desc": "int, float, str, bool.",
                "java_desc": "int, double, String, boolean.",
                "explanation": "Java has primitive types and object types (like String).",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "td-1",
                        "python": "text = 'Hello'\\nnum = 10",
                        "java": "String text = \\"Hello\\";\\nint num = 10;",
                        "explanation": "Java requires explicit type declaration."
                    }
                ]
            },
            "tuplas": {
                "title": "Tuples",
                "intro": "Tuples are immutable collections.",
                "python_desc": "Created with parentheses ().",
                "java_desc": "Java doesn't have native tuples (often uses objects or arrays).",
                "explanation": "Since Java lacks native tuples, you usually create a custom class or use external libraries.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "tup-1",
                        "python": "point = (10, 20)",
                        "java": "int[] point = {10, 20}; // or a custom Point class",
                        "explanation": "Arrays or custom classes simulate tuples in Java."
                    }
                ]
            },
            "sets": {
                "title": "Sets",
                "intro": "Sets store unique elements.",
                "python_desc": "Created with {}.",
                "java_desc": "Uses HashSet.",
                "explanation": "Both languages prevent duplicate elements in a Set.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "set-1",
                        "python": "s = {1, 2, 2}\\nprint(s)",
                        "java": "java.util.Set<Integer> s = new java.util.HashSet<>();\\ns.add(1);\\ns.add(2);\\nSystem.out.println(s);",
                        "explanation": "Java uses the Set interface and HashSet implementation."
                    }
                ]
            },
            "herencia": {
                "title": "Inheritance",
                "intro": "Classes can inherit properties from other classes.",
                "python_desc": "class Child(Parent):",
                "java_desc": "class Child extends Parent",
                "explanation": "Python supports multiple inheritance; Java only supports single inheritance but allows multiple interfaces.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "her-1",
                        "python": "class Animal:\\n    pass\\nclass Dog(Animal):\\n    pass",
                        "java": "class Animal {}\\nclass Dog extends Animal {}",
                        "explanation": "'extends' is the Java keyword for inheritance."
                    }
                ]
            },
            "listas": {
                "title": "Lists / Arrays",
                "intro": "In Python, lists are dynamic and can hold multiple types.",
                "python_desc": "Uses brackets [] and grows dynamically.",
                "java_desc": "Uses ArrayList or fixed arrays.",
                "explanation": "Java arrays have a fixed size, Python lists do not.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "list-1",
                        "python": "numbers = [1, 2, 3]\\nnumbers.append(4)",
                        "java": "java.util.List<Integer> numbers = new java.util.ArrayList<>();\\nnumbers.add(1);\\nnumbers.add(2);\\nnumbers.add(3);\\nnumbers.add(4);",
                        "explanation": "In Java you must initialize an ArrayList explicitly."
                    }
                ]
            },
            "diccionarios": {
                "title": "Dictionaries / HashMaps",
                "intro": "They store key-value pairs.",
                "python_desc": "Uses {} with key: value.",
                "java_desc": "Uses HashMap.",
                "explanation": "Dictionaries are highly optimized native structures in Python.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "dict-1",
                        "python": "ages = {'Ana': 20}\\nprint(ages['Ana'])",
                        "java": "java.util.Map<String, Integer> ages = new java.util.HashMap<>();\\nages.put(\\"Ana\\", 20);\\nSystem.out.println(ages.get(\\"Ana\\"));",
                        "explanation": "Java requires declaring types for the key and the value."
                    }
                ]
            },
            "clases": {
                "title": "Classes and Objects",
                "intro": "Object Oriented Programming.",
                "python_desc": "Uses the 'class' keyword and the 'self' parameter.",
                "java_desc": "Uses 'class' and access modifiers.",
                "explanation": "Python does not have strict native private/public modifiers.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "class-1",
                        "python": "class Person:\\n    def __init__(self, name):\\n        self.name = name",
                        "java": "public class Person {\\n    public String name;\\n    public Person(String name) {\\n        this.name = name;\\n    }\\n}",
                        "explanation": "The constructor in Python is __init__, in Java it has the same name as the class."
                    }
                ]
            },
            "excepciones": {
                "title": "Exceptions",
                "intro": "Controlled error handling.",
                "python_desc": "try / except / finally.",
                "java_desc": "try / catch / finally.",
                "explanation": "Python uses except instead of catch.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "exc-1",
                        "python": "try:\\n    x = 1 / 0\\nexcept ZeroDivisionError:\\n    print('Error')",
                        "java": "try {\\n    int x = 1 / 0;\\n} catch (ArithmeticException e) {\\n    System.out.println(\\"Error\\");\\n}",
                        "explanation": "Different names for the same basic exception types."
                    }
                ]
            },
            "modulos": {
                "title": "Modules",
                "intro": "Import external libraries.",
                "python_desc": "import math",
                "java_desc": "import java.lang.Math;",
                "explanation": "In Python you can import modules or specific functions with 'from module import X'.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "mod-1",
                        "python": "import math\\nprint(math.pi)",
                        "java": "import java.lang.Math;\\npublic class Program {\\n    public static void main(String[] args) {\\n        System.out.println(Math.PI);\\n    }\\n}",
                        "explanation": "In Java Math is already imported by default, but the concept is similar."
                    }
                ]
            },
            "j-listas": {
                "title": "Lists (J→P)",
                "intro": "Forget ArrayList, use native lists [].",
                "python_desc": "native lists.",
                "java_desc": "Fixed arrays or ArrayList.",
                "explanation": "In Python you can mix types in the same list.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-list-1",
                        "python": "arr = [1, 'Two', 3.0]",
                        "java": "java.util.List<Object> arr = java.util.Arrays.asList(1, \\"Two\\", 3.0);",
                        "explanation": "No strict type restrictions."
                    }
                ]
            },
            "j-diccionarios": {
                "title": "Dictionaries (J→P)",
                "intro": "HashMap is written directly with braces {}.",
                "python_desc": "{key: value}",
                "java_desc": "new HashMap<>()",
                "explanation": "It is the most used data structure in Python.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-dict-1",
                        "python": "map_obj = {'id': 1}",
                        "java": "java.util.Map<String, Integer> map_obj = new java.util.HashMap<>();\\nmap_obj.put(\\"id\\", 1);",
                        "explanation": "Initialized directly with values."
                    }
                ]
            },
            "j-clases": {
                "title": "Classes and Objects (J→P)",
                "intro": "No public/private. The constructor is called __init__.",
                "python_desc": "class and __init__.",
                "java_desc": "class and homonymous constructor.",
                "explanation": "Use 'self' explicitly instead of implicit 'this'.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-class-1",
                        "python": "class A:\\n    def __init__(self):\\n        pass",
                        "java": "public class A {\\n    public A() {}\\n}",
                        "explanation": "'pass' means 'do nothing'."
                    }
                ]
            },
            "j-excepciones": {
                "title": "Exceptions (J→P)",
                "intro": "Instead of catch, except is used.",
                "python_desc": "try/except",
                "java_desc": "try/catch",
                "explanation": "There are no checked exceptions in Python.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-exc-1",
                        "python": "try:\\n    pass\\nexcept Exception as e:\\n    print(e)",
                        "java": "try {\\n} catch (Exception e) {\\n    System.out.println(e);\\n}",
                        "explanation": "The syntax is 'as' instead of declaring the type and variable together."
                    }
                ]
            },
            "j-modulos": {
                "title": "Modules (J→P)",
                "intro": "Files are modules. import is used.",
                "python_desc": "import file",
                "java_desc": "import package.Class;",
                "explanation": "Every .py file can be imported directly.",
                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-mod-1",
                        "python": "import math",
                        "java": "import java.lang.Math;",
                        "explanation": "Simple and direct."
                    }
                ]
            },"""

en_index = content.find('"en": {')
if en_index != -1:
    content_es = content[:en_index]
    content_en = content[en_index:]
    
    pattern = r'(\s*)"listas": \{.*?"j-modulos": \{.*?\}\n\s*\},'
    new_content_en, count = re.subn(pattern, en_additions, content_en, flags=re.DOTALL)
    if count > 0:
        with open("translations.py", "w", encoding="utf-8") as f:
            f.write(content_es + new_content_en)
        print("Éxito: reemplazos=", count)
    else:
        print("No se encontró el patrón en la sección EN.")
else:
    print("No se encontró la sección EN.")
