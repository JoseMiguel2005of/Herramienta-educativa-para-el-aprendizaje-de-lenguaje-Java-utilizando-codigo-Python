TRANSLATIONS = {
    "es": {
        "site_title": "Py2Java Edu",



        "site_subtitle": "Herramienta educativa Python → Java",



        "nav_lessons": "Lecciones",



        "nav_reference": "Referencia teórica",



        "nav_home": "Inicio",



        "toggle_theme": "Cambiar tema",



        "toggle_lang": "English",



        "theme_light": "Modo diurno",



        "theme_dark": "Modo nocturno",



        "python_label": "Python",



        "java_label": "Java",



        "explanation_title": "Explicación",



        "try_editor": "Editor de práctica",



        "run_hint": "Escribe código Python a la izquierda. La traducción a Java aparece automáticamente a la derecha.",



        "translate_btn": "Traducir",



        "translating": "Traduciendo...",



        "java_output": "Salida Java",



        "translation_errors": "Errores de traducción",



        "translation_warnings": "Advertencias",



        "copy_code": "Copiar",



        "copied": "¡Copiado!",



        "lesson_hola-mundo_title": "Hola Mundo",



        "lesson_variables_title": "Variables",



        "lesson_condicionales_title": "Condicionales",



        "lesson_bucles_title": "Bucles",



        "cat_py2java": "Python → Java",



        "cat_java2py": "Java → Python",



        "cat_section_fundamentos": "Fundamentos",



        "cat_section_estructuras": "Estructuras de Datos",



        "cat_section_avanzado": "Avanzado",



        "cat_section_tutorial": "Tutorial",



        "cat_section_funciones": "Funciones",



        "cat_section_clases": "Clases y Objetos",



        "cat_section_modulos": "Módulos y Paquetes",



        "cat_section_archivos": "Manejo de Archivos",



        "lesson_listas_title": "Listas",



        "lesson_diccionarios_title": "Diccionarios",



        "lesson_clases_title": "Clases y Objetos",



        "lesson_excepciones_title": "Excepciones",



        "lesson_modulos_title": "Módulos",



        "lesson_j-listas_title": "Listas (J→P)",



        "lesson_j-diccionarios_title": "Diccionarios (J→P)",



        "lesson_j-clases_title": "Clases y Objetos (J→P)",



        "lesson_j-excepciones_title": "Excepciones (J→P)",



        "lesson_comentarios_title": "Comentarios",



        "lesson_tipos-datos_title": "Tipos de Datos",



        "lesson_cadenas_title": "Cadenas (Strings)",



        "lesson_operadores_title": "Operadores",



        "lesson_fechas_title": "Manejo de Fechas",



        "lesson_archivos_title": "Manejo de Archivos",



        "lesson_json_title": "Formato JSON",



        "lesson_tuplas_title": "Tuplas",



        "lesson_casting_title": "Casting (Conversión)",



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



        "lesson_sets_title": "Sets",



        "lesson_herencia_title": "Herencia",



        "lesson_j-comentarios_title": "Comentarios (J→P)",



        "lesson_j-tipos-datos_title": "Tipos de Datos (J→P)",



        "lesson_j-tuplas_title": "Tuplas (J→P)",



        "lesson_j-sets_title": "Sets (J→P)",



        "lesson_j-herencia_title": "Herencia (J→P)",



        "lesson_j-modulos_title": "Módulos (J→P)",




        "lesson_funciones_title": "Funciones",



        "lesson_j-hola-mundo_title": "Hola Mundo (J→P)",



        "lesson_j-variables_title": "Variables (J→P)",



        "lesson_j-condicionales_title": "Condicionales (J→P)",



        "lesson_j-bucles_title": "Bucles (J→P)",



        "lesson_j-funciones_title": "Funciones (J→P)",




        "ref_title": "Referencia teórica: Python vs Java",



        "ref_intro": (
            "Tabla comparativa de conceptos y funciones equivalentes entre Python y Java. "


            "Úsala como guía rápida al migrar código."


        ),
        "ref_cat_basico": "Conceptos básicos",



        "ref_cat_tipos": "Tipos de datos",



        "ref_cat_estructuras": "Estructuras de control",



        "ref_cat_funciones": "Funciones y métodos",



        "ref_cat_entrada_salida": "Entrada y salida",



        "ref_col_python": "Python",



        "ref_col_java": "Java",



        "ref_col_description": "Descripción",



        "footer_text": "Tesis de Ingeniería Informática — Herramienta educativa Python a Java",



        "lessons": {
            "hola-mundo": {
                "title": "Hola Mundo",



                "intro": (
                    "El programa «Hola Mundo» es el punto de partida tradicional al aprender un lenguaje. "


                    "En Python se escribe en una sola línea; en Java se requiere una estructura de clase "


                    "con el método <code>main</code>."


                ),
                "python_desc": (
                    "Python usa <code>print()</code> para mostrar texto en consola. "


                    "No necesita clase ni método principal."


                ),
                "java_desc": (
                    "Java exige una clase pública y el método <code>public static void main(String[] args)</code>. "

                    "La salida se hace con <code>System.out.println()</code>."


                ),
                "explanation": (
                    "<p><strong>Python</strong> es un lenguaje interpretado y de tipado dinámico. "


                    "Un script puede ejecutarse directamente sin declarar una clase.</p>"


                    "<p><strong>Java</strong> es compilado y orientado a objetos desde el inicio. "


                    "Todo programa debe vivir dentro de una clase, y la ejecución comienza en <code>main</code>.</p>"


                    "<p>Observa que en Java cada sentencia termina con punto y coma (<code>;</code>), "


                    "mientras que en Python el salto de línea basta.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-hm-1",



                        "question": "Traduce esta línea básica de Python a Java:",



                        "python_code": "print('Hola')",



                        "template_html": "System.out.<input type='text' class='exercise-input' data-answer='println' size='8'>('Hola');",



                        "hint": "En Java usamos println para imprimir en consola con salto de línea."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "hm-1",



                        "python": 'print("¡Hola, Mundo!")',
                        "java": (
                            'public class HolaMundo {\\n'
                            '    public static void main(String[] args) {\\n'
                            '        System.out.println("¡Hola, Mundo!");\n'
                            '    }\n'
                            '}'
                        ),
                        "explanation": "En Python la instrucción print es directa. En Java, debemos envolver todo en una clase pública y declarar el método principal (main)."



                    }
                ],
            },
            "variables": {
                "title": "Variables",



                "intro": (
                    "Las variables almacenan datos. Python infiere el tipo automáticamente; "


                    "en Java debes declarar el tipo explícitamente."


                ),
                "python_desc": (
                    "Se asigna con <code>=</code>. No hace falta declarar el tipo: "


                    "<code>nombre = \"Ana\"</code>, <code>edad = 20</code>."


                ),
                "java_desc": (
                    "Se declara el tipo antes del nombre: <code>String nombre = \"Ana\";</code>, "


                    "<code>int edad = 20;</code>."


                ),
                "explanation": (
                    "<p>En <strong>Python</strong>, <code>name = \"Ana\"</code> crea una variable de tipo cadena sin palabra clave.</p>"


                    "<p>En <strong>Java</strong>, <code>String name = \"Ana\";</code> exige el tipo <code>String</code> "


                    "(con S mayúscula, es una clase).</p>"


                    "<p>Los nombres de variables suelen usar <code>snake_case</code> en Python y <code>camelCase</code> en Java.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-var-1",



                        "question": "Declara una variable entera en Java equivalente a:",



                        "python_code": "edad = 20",



                        "template_html": "<input type='text' class='exercise-input' data-answer='int' size='4'> edad = 20;",



                        "hint": "Los números enteros sin decimales usan el tipo primitivo int."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "var-class",



                        "python": "",


                        "java": "public class Variables {\n    public static void main(String[] args) {",


                        "explanation": "Declaración estándar de clase y método main en Java. Python no lo requiere."



                    },
                    {
                        "id": "var-1",



                        "python": 'nombre = "Ana"',
                        "java": '        String nombre = "Ana";',
                        "explanation": "En Java, declaramos explícitamente el tipo 'String' para texto."



                    },
                    {
                        "id": "var-2",



                        "python": "edad = 20",



                        "java": "        int edad = 20;",



                        "explanation": "Declaramos el tipo primitivo 'int' para enteros."



                    },
                    {
                        "id": "var-3",



                        "python": "activo = True",



                        "java": "        boolean activo = true;",



                        "explanation": "El tipo lógico es 'boolean' (en minúscula) y los valores son true/false."



                    },
                    {
                        "id": "var-4",



                        "python": 'print(f"{nombre} tiene {edad} años")',
                        "java": '        System.out.println(nombre + " tiene " + edad + " años");',
                        "explanation": "En Java se usa el operador '+' para concatenar variables de texto y números."



                    },
                    {
                        "id": "var-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "Cierre de llaves en Java."



                    }
                ],
            },
            "operadores": {
                "title": "Operadores",



                "intro": "Los operadores se utilizan para realizar operaciones sobre variables y valores.",



                "python_desc": "Usa and, or, not para lógicos, y operadores aritméticos comunes.",



                "java_desc": "Usa &&, ||, ! para lógicos, y operadores aritméticos comunes.",



                "explanation": "La mayor diferencia radica en los operadores lógicos. En Python son palabras clave más legibles, mientras que en Java se utilizan símbolos booleanos tradicionales. Además, Java tiene operadores de incremento (++) y decremento (--) nativos, mientras que en Python se usa += 1.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "op-1",



                        "python": "x = 10\nx += 1\n\nif x > 5 and x < 15:\n    print('Rango válido')",



                        "java": "int x = 10;\nx++;\n\nif (x > 5 && x < 15) {\n    System.out.println(\"Rango válido\");\n}",


                        "explanation": "Se observan las diferencias entre 'and' / '&&' y el autoincremento."



                    }
                ]
            },
            "cadenas": {
                "title": "Cadenas de Texto (Strings)",



                "intro": "Los strings se utilizan para almacenar texto. Tanto en Python como en Java proporcionan muchos métodos nativos.",



                "python_desc": "Usa str. Soporta comillas simples y dobles.",



                "java_desc": "Usa la clase String. Solo soporta comillas dobles para texto.",



                "explanation": "En Python, los strings son matrices de bytes, por lo que puedes cortarlos usando particiones (slicing) como texto[0:5]. En Java, se requiere llamar a métodos como substring(0, 5).",


                "exercises": [],
                "code_mappings": [
                    {
                        "id": "str-1",



                        "python": "texto = \"Hola Mundo\"\nlongitud = len(texto)\nmayus = texto.upper()\nparte = texto[0:4]",


                        "java": "String texto = \"Hola Mundo\";\nint longitud = texto.length();\nString mayus = texto.toUpperCase();\nString parte = texto.substring(0, 4);",



                        "explanation": "len() vs .length() y particionado de arrays vs .substring()."



                    }
                ]
            },
            "condicionales": {
                "title": "Condicionales",



                "intro": (
                    "Las estructuras condicionales permiten ejecutar código según una condición. "


                    "La lógica es similar; cambian la sintaxis y la indentación."


                ),
                "python_desc": (
                    "Usa <code>if</code>, <code>elif</code> y <code>else</code>. "


                    "La indentación define los bloques."


                ),
                "java_desc": (
                    "Usa <code>if</code>, <code>else if</code> y <code>else</code>. "


                    "Los bloques van entre llaves <code>{ }</code>."

                ),
                "explanation": (
                    "<p>Python usa <strong>indentación</strong> (espacios o tabulaciones) para delimitar bloques.</p>"


                    "<p>Java usa <strong>llaves</strong> y no depende de la indentación (aunque conviene indentar para legibilidad).</p>"


                    "<p>La condición en ambos va entre paréntesis en Java; en Python los paréntesis son opcionales.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-cond-1",



                        "question": "Traduce la palabra reservada 'elif' a Java:",



                        "python_code": "elif x == 5:",



                        "template_html": "} <input type='text' class='exercise-input' data-answer='else if' size='8'> (x == 5) {",


                        "hint": "En Java se separan las palabras: 'else' y 'if'."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "cond-class",



                        "python": "",


                        "java": "public class Condicionales {\n    public static void main(String[] args) {",


                        "explanation": "Estructura principal de Java."



                    },
                    {
                        "id": "cond-1",



                        "python": "nota = 85",



                        "java": "        int nota = 85;",



                        "explanation": "Declaración de variable con su tipo."



                    },
                    {
                        "id": "cond-2",



                        "python": "if nota >= 90:\n    print(\"Excelente\")",



                        "java": "        if (nota >= 90) {\n            System.out.println(\"Excelente\");\n        }",


                        "explanation": "En Java, las condiciones van entre paréntesis '()' y los bloques usan llaves '{}'."


                    },
                    {
                        "id": "cond-3",



                        "python": "elif nota >= 70:\n    print(\"Aprobado\")",



                        "java": "        else if (nota >= 70) {\n            System.out.println(\"Aprobado\");\n        }",


                        "explanation": "Python usa 'elif', Java utiliza 'else if'."



                    },
                    {
                        "id": "cond-4",



                        "python": "else:\n    print(\"Reprobado\")",



                        "java": "        else {\n            System.out.println(\"Reprobado\");\n        }",


                        "explanation": "Caso por defecto. También encerrado en llaves en Java."



                    },
                    {
                        "id": "cond-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "Fin del main y la clase."



                    }
                ],
            },
            "bucles": {
                "title": "Bucles",



                "intro": (
                    "Los bucles repiten un bloque de código. Python ofrece <code>for</code> y <code>while</code>; "


                    "Java tiene estructuras equivalentes con sintaxis distinta."


                ),
                "python_desc": (
                    "<code>for i in range(5):</code> itera un número fijo de veces. "


                    "<code>while condicion:</code> repite mientras sea verdadera."


                ),
                "java_desc": (
                    "<code>for (int i = 0; i < 5; i++)</code> es el bucle clásico. "


                    "<code>while (condicion)</code> equivale al while de Python."


                ),
                "explanation": (
                    "<p>El bucle <code>for</code> de Python sobre <code>range(5)</code> genera 0, 1, 2, 3, 4.</p>"


                    "<p>En Java el <code>for</code> tradicional declara el contador, la condición y el incremento en una sola línea.</p>"


                    "<p>Ambos lenguajes permiten <code>break</code> (salir) y <code>continue</code> (siguiente iteración).</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-bucle-1",



                        "question": "Traduce este bucle for que itera 5 veces:",



                        "python_code": "for i in range(5):",



                        "template_html": "for (int i = 0; <input type='text' class='exercise-input' data-answer='i < 5' size='6'>; i++) {",


                        "hint": "La condición del medio debe hacer que el bucle siga mientras 'i' sea menor a 5."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "loop-class",



                        "python": "",


                        "java": "public class Bucles {\n    public static void main(String[] args) {",


                        "explanation": "Inicio en Java."



                    },
                    {
                        "id": "loop-1",



                        "python": "for i in range(5):\n    print(f\"Iteración {i}\")",


                        "java": "        for (int i = 0; i < 5; i++) {\n            System.out.println(\"Iteración \" + i);\n        }",


                        "explanation": "El bucle 'for' en Java necesita definir el tipo, la condición y el incremento todo junto (int i=0; i<5; i++)."



                    },
                    {
                        "id": "loop-2",



                        "python": "contador = 0",



                        "java": "\n        int contador = 0;",



                        "explanation": "Variable para el ciclo while."



                    },
                    {
                        "id": "loop-3",



                        "python": "while contador < 3:\n    print(f\"While: {contador}\")\n    contador += 1",


                        "java": "        while (contador < 3) {\n            System.out.println(\"While: \" + contador);\n            contador++;\n        }",


                        "explanation": "El 'while' funciona igual. En Java, podemos usar 'contador++' en lugar de 'contador += 1'."



                    },
                    {
                        "id": "loop-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "Cierre de la estructura."



                    }
                ],
            },
        
            "funciones": {
                "title": "Funciones",



                "intro": "Las funciones permiten reutilizar código. En Python se usa def, en Java se definen métodos dentro de clases.",



                "python_desc": "Usa def y no requiere declarar tipos de retorno.",



                "java_desc": "Requiere un tipo de retorno (o void) y modificadores de acceso.",



                "explanation": "<p>En Java los métodos deben pertenecer a una clase.</p>",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "func-1",



                        "python": "def saludar(nombre):\n    return f'Hola {nombre}'",


                        "java": "    public static String saludar(String nombre) {\n        return \"Hola \" + nombre;\n    }",


                        "explanation": "Java necesita tipo de retorno String y parámetro String."



                    }
                ]
            },
            "casting": {
                "title": "Casting (Conversión de Tipos)",



                "intro": "El casting es el proceso de forzar a que una variable sea tratada como un tipo de dato específico.",



                "python_desc": "Usa funciones de construcción como int(), float(), str().",



                "java_desc": "Usa paréntesis (tipo) para tipos primitivos, o métodos como Integer.parseInt().",



                "explanation": "En Python el casting se maneja como llamadas a funciones constructoras. En Java, se diferencia fuertemente entre tipos primitivos (donde se usa la sintaxis de prefijo entre paréntesis) y objetos (donde se usan métodos de conversión estáticos).",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "cast-1",



                        "python": "texto = \"10\"\nnumero = int(texto)\n\ndecimal = 5.8\nentero = int(decimal)",



                        "java": "String texto = \"10\";\nint numero = Integer.parseInt(texto);\n\ndouble decimal = 5.8;\nint entero = (int) decimal;",



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



                        "python": "es_mayor = True\n\nif 10 > 9:\n    print(es_mayor)",



                        "java": "boolean esMayor = true;\n\nif (10 > 9) {\n    System.out.println(esMayor);\n}",


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



                        "python": "nombre = input(\"¿Cuál es tu nombre? \")\nprint(\"Hola \" + nombre)",



                        "java": "import java.util.Scanner;\n\nScanner sc = new Scanner(System.in);\nSystem.out.print(\"¿Cuál es tu nombre? \");\nString nombre = sc.nextLine();\nSystem.out.println(\"Hola \" + nombre);",



                        "explanation": "La lectura por consola en Java es considerablemente más detallada (verbose)."



                    }
                ]
            },
            "formateo-cadenas": {
                "title": "Formateo de Cadenas",



                "intro": "Insertar valores variables dentro de cadenas de texto de forma legible.",



                "python_desc": "F-strings (ej. f\"Hola {nombre}\").",


                "java_desc": "String.format() o System.out.printf().",



                "explanation": "Las f-strings de Python 3.6+ revolucionaron la legibilidad al permitir inyectar variables directamente. Java depende de los comodines posicionales tipo C (%s, %d) o la concatenación pura.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "fmt-1",



                        "python": "precio = 49.99\ntexto = f\"El producto cuesta ${precio}\"\nprint(texto)",


                        "java": "double precio = 49.99;\nString texto = String.format(\"El producto cuesta $%.2f\", precio);\nSystem.out.println(texto);",



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



                        "python": "# Python no tiene arrays fijos, usa listas para todo\nautos = [\"Ford\", \"Volvo\", \"BMW\"]\nautos[0] = \"Toyota\"",


                        "java": "// Array de tamaño estático\nString[] autos = {\"Ford\", \"Volvo\", \"BMW\"};\nautos[0] = \"Toyota\";\n\n// Arrays sin datos inmediatos ocupan un tamaño exacto\nint[] numeros = new int[5];",


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



                        "python": "multiplicar = lambda a, b: a * b\nprint(multiplicar(5, 6))",



                        "java": "interface Operacion { int operar(int a, int b); }\n\n// Las Lambdas en Java necesitan interfaces funcionales\nOperacion multiplicar = (a, b) -> a * b;\nSystem.out.println(multiplicar.operar(5, 6));",


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



                        "python": "class Perro:\n    def sonido(self): print(\"Guau\")\n\nclass Gato:\n    def sonido(self): print(\"Miau\")\n\nfor animal in (Perro(), Gato()):\n    animal.sonido()",



                        "java": "interface Animal { void sonido(); }\nclass Perro implements Animal { public void sonido() { System.out.println(\"Guau\"); } }\nclass Gato implements Animal { public void sonido() { System.out.println(\"Miau\"); } }\n\nAnimal[] animales = {new Perro(), new Gato()};\nfor(Animal a : animales) { a.sonido(); }",


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



                        "python": "x = 300\n\ndef mi_funcion():\n    global x\n    x = 200\n\nmi_funcion()\nprint(x)",



                        "java": "public class MiClase {\n    static int x = 300;\n\n    static void miFuncion() {\n        x = 200;\n    }\n\n    public static void main(String[] args) {\n        miFuncion();\n        System.out.println(x);\n    }\n}",


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



                        "python": "import math\n\nraiz = math.sqrt(64)\npi = math.pi\nabsoluto = abs(-5)",



                        "java": "double raiz = Math.sqrt(64);\ndouble pi = Math.PI;\nint absoluto = Math.abs(-5);",



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



                        "python": "import re\n\ntexto = \"El sol sale\"\ncoincidencia = re.search(r\"(?i)sol\", texto)\nif coincidencia:\n    print(\"Encontrado\")",



                        "java": "import java.util.regex.*;\n\nString texto = \"El sol sale\";\nPattern pattern = Pattern.compile(\"(?i)sol\");\nMatcher matcher = pattern.matcher(texto);\nif (matcher.find()) {\n    System.out.println(\"Encontrado\");\n}",


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



                        "python": "# Instalación global:\npip install requests\n\n# Uso\nimport requests",



                        "java": "<!-- En el archivo pom.xml de Maven se añade: -->\n<dependency>\n    <groupId>com.google.code.gson</groupId>\n    <artifactId>gson</artifactId>\n    <version>2.8.6</version>\n</dependency>",



                        "explanation": "Esto representa un salto de paradigma importante: Java centraliza las dependencias en archivos del proyecto."



                    }
                ]
            },
            "j-hola-mundo": {
                "title": "Hola Mundo (Java a Python)",



                "intro": "Aprende a pasar de Java a Python. Python es más conciso y no requiere clases.",



                "python_desc": "print() directo, sin clases.",



                "java_desc": "Clase y método main obligatorios.",



                "explanation": "Python se ejecuta línea a línea.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-hm-1",



                        "python": "print('Hola, Mundo!')",



                        "java": "System.out.println('Hola, Mundo!');",



                        "explanation": "En Python, se omite el punto y coma y la clase."



                    }
                ]
            },
            "j-variables": {
                "title": "Variables (J→P)",



                "intro": "Python tiene tipado dinámico, no declaras int o String.",



                "python_desc": "No requiere tipo.",



                "java_desc": "Requiere declarar tipo explícito.",



                "explanation": "En Python el tipo se infiere en tiempo de ejecución.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-var-1",



                        "python": "edad = 20",



                        "java": "int edad = 20;",



                        "explanation": "Adiós a 'int' y al ';'"



                    }
                ]
            },
            "j-condicionales": {
                "title": "Condicionales (J→P)",



                "intro": "Python usa indentación en vez de llaves.",



                "python_desc": "if/elif/else y dos puntos.",



                "java_desc": "if/else if/else y llaves.",



                "explanation": "La indentación es obligatoria en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-cond-1",



                        "python": "if x > 5:\n    print('Mayor')",



                        "java": "if (x > 5) {\n    System.out.println('Mayor');\n}",


                        "explanation": "Paréntesis opcionales, sin llaves."



                    }
                ]
            },
            "j-bucles": {
                "title": "Bucles (J→P)",



                "intro": "Los bucles en Python suelen iterar sobre colecciones o rangos.",



                "python_desc": "for x in range(n):",



                "java_desc": "for(int i=0; i<n; i++)",



                "explanation": "range() es la forma idiomática en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-buc-1",



                        "python": "for i in range(5):\n    print(i)",



                        "java": "for(int i=0; i<5; i++) {\n    System.out.println(i);\n}",


                        "explanation": "range(5) genera 0..4"



                    }
                ]
            },
            "j-funciones": {
                "title": "Funciones (J→P)",



                "intro": "Python usa 'def' en vez de especificar modificadores de acceso.",



                "python_desc": "def y return sin tipo.",



                "java_desc": "public static tipo return.",



                "explanation": "Todo es más compacto en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-func-1",



                        "python": "def suma(a, b):\n    return a + b",



                        "java": "public int suma(int a, int b) {\n    return a + b;\n}",


                        "explanation": "Sin tipos en parámetros ni retorno."



                    }
                ]
            },

            "listas": {
                "title": "Listas / Arrays",



                "intro": "En Python, las listas son dinámicas y pueden contener múltiples tipos.",



                "python_desc": "Usa corchetes [] y crece dinámicamente.",


                "java_desc": "Usa ArrayList o arreglos fijos.",



                "explanation": "Los arreglos de Java tienen un tamaño fijo, las listas de Python no.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "list-1",



                        "python": "numeros = [1, 2, 3]\nnumeros.append(4)",


                        "java": "java.util.List<Integer> numeros = new java.util.ArrayList<>();\nnumeros.add(1);\nnumeros.add(2);\nnumeros.add(3);\nnumeros.add(4);",



                        "explanation": "En Java debes inicializar un ArrayList explícitamente."



                    }
                ]
            },
            "diccionarios": {
                "title": "Diccionarios / HashMaps",



                "intro": "Almacenan pares clave-valor.",



                "python_desc": "Se usa {} con clave: valor.",


                "java_desc": "Se usa HashMap.",



                "explanation": "Los diccionarios son estructuras nativas muy optimizadas en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "dict-1",



                        "python": "edades = {'Ana': 20}\nprint(edades['Ana'])",


                        "java": "java.util.Map<String, Integer> edades = new java.util.HashMap<>();\nedades.put(\"Ana\", 20);\nSystem.out.println(edades.get(\"Ana\"));",



                        "explanation": "Java requiere declarar tipos para la clave y el valor."



                    }
                ]
            },
            "clases": {
                "title": "Clases y Objetos",



                "intro": "Programación Orientada a Objetos.",



                "python_desc": "Se usa la palabra class y el parámetro self.",



                "java_desc": "Se usa class y modificadores de acceso.",



                "explanation": "En Python no existen los modificadores private/public nativos estrictos.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "class-1",



                        "python": "class Persona:\n    def __init__(self, nombre):\n        self.nombre = nombre",



                        "java": "public class Persona {\n    public String nombre;\n    public Persona(String nombre) {\n        this.nombre = nombre;\n    }\n}",


                        "explanation": "El constructor en Python es __init__, en Java tiene el mismo nombre de la clase."



                    }
                ]
            },
            "excepciones": {
                "title": "Excepciones",



                "intro": "Manejo de errores controlados.",



                "python_desc": "try / except / finally.",



                "java_desc": "try / catch / finally.",



                "explanation": "Python usa except en lugar de catch.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "exc-1",



                        "python": "try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    print('Error')",



                        "java": "try {\n    int x = 1 / 0;\n} catch (ArithmeticException e) {\n    System.out.println(\"Error\");\n}",


                        "explanation": "Diferentes nombres para los mismos tipos de excepciones básicas."



                    }
                ]
            },
            "modulos": {
                "title": "Módulos",



                "intro": "Importar librerías externas.",



                "python_desc": "import math",



                "java_desc": "import java.lang.Math;",



                "explanation": "En Python puedes importar módulos o funciones específicas con 'from module import X'.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "mod-1",



                        "python": "import math\nprint(math.pi)",



                        "java": "import java.lang.Math;\npublic class Program {\n    public static void main(String[] args) {\n        System.out.println(Math.PI);\n    }\n}",


                        "explanation": "En Java Math ya viene importado por defecto, pero el concepto es similar."



                    }
                ]
            },

            "comentarios": {
                "title": "Comentarios",



                "intro": "Explicar notas en el código.",



                "python_desc": "# Comentarios con almohadilla",



                "java_desc": "// Comentarios con doble slash",



                "explanation": "Usa # en Python y // o /* */ en Java para anotar el código sin ejecutarlo.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "comentarios-1",



                        "python": "x = 10  # este es un comentario",



                        "java": "int x = 10; // este es un comentario",



                        "explanation": "Los comentarios ayudan a que el código sea comprensible."



                    }
                ]
            },
            "tipos-datos": {
                "title": "Tipos de Datos",



                "intro": "Tipos como int, float, str y boolean.",



                "python_desc": "int, float, str, bool",



                "java_desc": "int, double, String, boolean",



                "explanation": "En Python los tipos se infieren dinámicamente; en Java se declaran estáticamente.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "tipos-datos-1",



                        "python": "entero = 5\ntexto = 'Hola'\nreal = 3.14",



                        "java": 'int entero = 5;\\nString texto = "Hola";\\ndouble real = 3.14;',
                        "explanation": "Tipos básicos se usan de forma similar, aunque en Java se declara el tipo explícitamente."



                    }
                ]
            },
            "fechas": {
                "title": "Fechas y Tiempo",



                "intro": "Manejar fechas es una tarea cotidiana para registros y bases de datos.",



                "python_desc": "Usa el módulo datetime.",



                "java_desc": "Usa el paquete java.time (LocalDate, LocalDateTime).",



                "explanation": "A partir de Java 8, se introdujo java.time que es muy similar a la filosofía de datetime de Python, abandonando las viejas y complejas clases Date o Calendar.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "date-1",



                        "python": "import datetime\n\nahora = datetime.datetime.now()\nprint(ahora.year)",



                        "java": "import java.time.LocalDateTime;\n\nLocalDateTime ahora = LocalDateTime.now();\nSystem.out.println(ahora.getYear());",



                        "explanation": "Ambos lenguajes ofrecen métodos descriptivos para extraer partes de la fecha."



                    }
                ]
            },
            "archivos": {
                "title": "Manejo de Archivos",



                "intro": "Leer y escribir archivos de disco duro de forma local.",



                "python_desc": "Función built-in open() y sentencias with.",



                "java_desc": "Clases de java.nio.file.* o FileWriter/Scanner.",



                "explanation": "Python hace que la lectura de archivos sea extremadamente concisa gracias al administrador de contexto 'with' (que cierra el archivo automáticamente). En Java, a menudo se usa la sintaxis de 'try-with-resources'.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "file-1",



                        "python": "with open('datos.txt', 'w') as f:\n    f.write('Hola, Archivo')",



                        "java": "try (java.io.FileWriter f = new java.io.FileWriter(\"datos.txt\")) {\n    f.write(\"Hola, Archivo\");\n} catch(Exception e) {\n    e.printStackTrace();\n}",


                        "explanation": "Ambas formas aseguran que el archivo se cierre después del bloque, evitando fugas de memoria."



                    }
                ]
            },
            "json": {
                "title": "Formato JSON",



                "intro": "JSON es el formato estándar para envío y recepción de datos por red.",



                "python_desc": "Módulo built-in json.",



                "java_desc": "Librerías de terceros (Gson, Jackson) o org.json.",



                "explanation": "A diferencia de Python que incluye la librería JSON de manera nativa en su estándar, Java históricamente ha dependido de librerías de terceros populares como Jackson o Gson para trabajar con este formato cómodamente.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "json-1",



                        "python": "import json\n\nobj = {'nombre': 'Ana', 'edad': 30}\njson_str = json.dumps(obj)\nprint(json_str)",


                        "java": "// Usando org.json (librería externa)\nimport org.json.JSONObject;\n\nJSONObject obj = new JSONObject();\nobj.put(\"nombre\", \"Ana\");\nobj.put(\"edad\", 30);\nSystem.out.println(obj.toString());",



                        "explanation": "En Python, los diccionarios y JSON son casi intercambiables de forma nativa."



                    }
                ]
            },
            "tuplas": {
                "title": "Tuplas",



                "intro": "Secuencias inmutables similares a listas.",



                "python_desc": "Tuplas con paréntesis ()",



                "java_desc": "Arrays o Listas inmutables usando Collections.unmodifiableList",



                "explanation": "Las tuplas no se pueden modificar después de crearse.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "tuplas-1",



                        "python": "coordenadas = (10, 20)",



                        "java": "List<Integer> coordenadas = Collections.unmodifiableList(Arrays.asList(10, 20));",



                        "explanation": "En Java no hay tuplas nativas, se usan listas inmutables o clases simples."



                    }
                ]
            },
            "sets": {
                "title": "Sets",



                "intro": "Colecciones sin orden y sin duplicados.",



                "python_desc": "set()",



                "java_desc": "HashSet<>",



                "explanation": "Los sets eliminan duplicados y no mantienen orden fijo.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "sets-1",



                        "python": "valores = {1, 2, 2, 3}",


                        "java": "Set<Integer> valores = new HashSet<>(Arrays.asList(1, 2, 2, 3));",



                        "explanation": "En ambos lenguajes el conjunto resulta en {1, 2, 3}."


                    }
                ]
            },
            "herencia": {
                "title": "Herencia",



                "intro": "Reutilizar la funcionalidad en clases derivadas.",



                "python_desc": "class Hija(Padre):",



                "java_desc": "class Hija extends Padre",



                "explanation": "Herencia permite especializar clases base en subclases.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "herencia-1",



                        "python": "class Animal:\n    pass\n\nclass Perro(Animal):\n    pass",



                        "java": "class Animal {}\nclass Perro extends Animal {}",


                        "explanation": "En Python se especifica la clase base entre paréntesis."



                    }
                ]
            },

            "j-listas": {
                "title": "Listas (J→P)",



                "intro": "Olvídate de ArrayList, usa listas nativas [].",


                "python_desc": "listas nativas.",



                "java_desc": "Arreglos fijos o ArrayList.",



                "explanation": "En Python puedes mezclar tipos en una misma lista.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-list-1",



                        "python": "arr = [1, 'Dos', 3.0]",


                        "java": "java.util.List<Object> arr = java.util.Arrays.asList(1, \"Dos\", 3.0);",



                        "explanation": "Sin restricciones de tipo estrictas."



                    }
                ]
            },
            "j-diccionarios": {
                "title": "Diccionarios (J→P)",



                "intro": "El HashMap se escribe directamente con llaves {}.",


                "python_desc": "{clave: valor}",


                "java_desc": "new HashMap<>()",



                "explanation": "Es la estructura de datos más utilizada en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-dict-1",



                        "python": "mapa = {'id': 1}",


                        "java": "java.util.Map<String, Integer> mapa = new java.util.HashMap<>();\nmapa.put(\"id\", 1);",



                        "explanation": "Se inicializa directamente con valores."



                    }
                ]
            },
            "j-clases": {
                "title": "Clases y Objetos (J→P)",



                "intro": "No hay public/private. El constructor se llama __init__.",



                "python_desc": "class y __init__.",



                "java_desc": "class y constructor homónimo.",



                "explanation": "Usa 'self' explícitamente en lugar del 'this' implícito.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-class-1",



                        "python": "class A:\n    def __init__(self):\n        pass",



                        "java": "public class A {\n    public A() {}\n}",


                        "explanation": "pass significa 'no hacer nada'."



                    }
                ]
            },
            "j-excepciones": {
                "title": "Excepciones (J→P)",



                "intro": "En lugar de catch, se usa except.",



                "python_desc": "try/except",



                "java_desc": "try/catch",



                "explanation": "No existen excepciones verificadas (checked exceptions) en Python.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-exc-1",



                        "python": "try:\n    pass\nexcept Exception as e:\n    print(e)",



                        "java": "try {\n} catch (Exception e) {\n    System.out.println(e);\n}",


                        "explanation": "La sintaxis es as en lugar de declarar el tipo y variable juntos."



                    }
                ]
            },
            "j-modulos": {
                "title": "Módulos (J→P)",



                "intro": "Archivos son módulos. Se usa import.",



                "python_desc": "import archivo",



                "java_desc": "import paquete.Clase;",



                "explanation": "Todo archivo .py puede ser importado directamente.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-mod-1",



                        "python": "import math",



                        "java": "import java.lang.Math;",



                        "explanation": "Simple y directo."



                    }
                ]
            }
        },
        "reference": {
            "basico": [
                {
                    "python": "No requiere clase",



                    "java": "public class MiClase { }",


                    "desc": "Java exige al menos una clase pública por archivo.",



                },
                {
                    "python": "# comentario",



                    "java": "// comentario",



                    "desc": "Comentarios de una línea.",



                },
                {
                    "python": '"""docstring"""',
                    "java": "/** Javadoc */",



                    "desc": "Documentación de código.",



                },
                {
                    "python": "pass",



                    "java": ";  o bloque vacío { }",


                    "desc": "Marcador de bloque vacío.",



                },
            ],
            "tipos": [
                {
                    "python": "int, float",



                    "java": "int, double, float",



                    "desc": "Números enteros y decimales.",



                },
                {
                    "python": "str",



                    "java": "String",



                    "desc": "Cadenas de texto.",



                },
                {
                    "python": "bool (True/False)",



                    "java": "boolean (true/false)",



                    "desc": "Valores lógicos.",



                },
                {
                    "python": "list",



                    "java": "ArrayList<T> o T[]",


                    "desc": "Listas y arreglos dinámicos.",



                },
                {
                    "python": "dict",



                    "java": "HashMap<K, V>",



                    "desc": "Estructuras clave-valor.",



                },
                {
                    "python": "None",



                    "java": "null",



                    "desc": "Ausencia de valor.",



                },
            ],
            "estructuras": [
                {
                    "python": "if / elif / else",



                    "java": "if / else if / else",



                    "desc": "Condicionales.",



                },
                {
                    "python": "for x in iterable:",



                    "java": "for (Tipo x : coleccion)",



                    "desc": "Bucle for-each.",



                },
                {
                    "python": "while cond:",



                    "java": "while (cond)",



                    "desc": "Bucle while.",



                },
                {
                    "python": "break / continue",



                    "java": "break / continue",



                    "desc": "Control de flujo en bucles.",



                },
            ],
            "funciones": [
                {
                    "python": "def nombre(params):",



                    "java": "Tipo nombre(Tipo param) { }",


                    "desc": "Definición de función/método.",



                },
                {
                    "python": "return valor",



                    "java": "return valor;",



                    "desc": "Devolver un resultado.",



                },
                {
                    "python": "lambda x: x * 2",



                    "java": "x -> x * 2",



                    "desc": "Funciones anónimas.",



                },
                {
                    "python": "len(lista)",



                    "java": "lista.size() o array.length",



                    "desc": "Longitud de colección.",



                },
            ],
            "entrada_salida": [
                {
                    "python": 'print("texto")',
                    "java": 'System.out.println("texto");',
                    "desc": "Salida por consola.",



                },
                {
                    "python": 'input("mensaje")',
                    "java": "Scanner + nextLine()",



                    "desc": "Entrada desde teclado.",



                },
                {
                    "python": "open('archivo.txt')",



                    "java": "Files.readAllLines(Paths.get(...))",



                    "desc": "Lectura de archivos.",



                },
                {
                    "python": "import modulo",



                    "java": "import paquete.Clase;",



                    "desc": "Importar dependencias.",



                },
            ],
        },
    },
    "en": {
        "site_title": "Py2Java Edu",



        "site_subtitle": "Educational tool Python → Java",



        "nav_lessons": "Lessons",



        "nav_reference": "Theory reference",



        "nav_home": "Home",



        "toggle_theme": "Toggle theme",



        "toggle_lang": "Español",



        "theme_light": "Light mode",



        "theme_dark": "Dark mode",



        "python_label": "Python",



        "java_label": "Java",



        "explanation_title": "Explanation",



        "try_editor": "Practice editor",



        "run_hint": "Write Python code on the left. The Java translation appears automatically on the right.",



        "translate_btn": "Translate",



        "translating": "Translating...",



        "java_output": "Java output",



        "translation_errors": "Translation errors",



        "translation_warnings": "Warnings",



        "copy_code": "Copy",



        "copied": "Copied!",



        "lesson_hola-mundo_title": "Hello World",



        "lesson_variables_title": "Variables",



        "lesson_condicionales_title": "Conditionals",



        "lesson_bucles_title": "Loops",



        "cat_py2java": "Python → Java",



        "cat_java2py": "Java → Python",



        "cat_section_fundamentos": "Fundamentals",



        "cat_section_estructuras": "Data Structures",



        "cat_section_avanzado": "Advanced",



        "cat_section_tutorial": "Tutorial",



        "cat_section_funciones": "Functions",



        "cat_section_clases": "Classes & Objects",



        "cat_section_modulos": "Modules",



        "cat_section_archivos": "File Handling",



        "lesson_listas_title": "Lists",



        "lesson_diccionarios_title": "Dictionaries",



        "lesson_clases_title": "Classes and Objects",



        "lesson_excepciones_title": "Exceptions",



        "lesson_modulos_title": "Modules",



        "lesson_j-listas_title": "Lists (J→P)",



        "lesson_j-diccionarios_title": "Dictionaries (J→P)",



        "lesson_j-clases_title": "Classes and Objects (J→P)",



        "lesson_j-excepciones_title": "Exceptions (J→P)",



        "lesson_comentarios_title": "Comments",



        "lesson_tipos-datos_title": "Data Types",



        "lesson_cadenas_title": "Strings",



        "lesson_operadores_title": "Operators",



        "lesson_fechas_title": "Dates & Time",



        "lesson_archivos_title": "File Handling",



        "lesson_json_title": "JSON Format",



        "lesson_tuplas_title": "Tuples",



        "lesson_casting_title": "Type Casting",



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



        "lesson_sets_title": "Sets",



        "lesson_herencia_title": "Inheritance",



        "lesson_j-comentarios_title": "Comments (J→P)",



        "lesson_j-tipos-datos_title": "Data Types (J→P)",



        "lesson_j-tuplas_title": "Tuples (J→P)",



        "lesson_j-sets_title": "Sets (J→P)",



        "lesson_j-herencia_title": "Inheritance (J→P)",



        "lesson_j-modulos_title": "Modules (J→P)",




        "lesson_funciones_title": "Functions",



        "lesson_j-hola-mundo_title": "Hello World (J→P)",



        "lesson_j-variables_title": "Variables (J→P)",



        "lesson_j-condicionales_title": "Conditionals (J→P)",



        "lesson_j-bucles_title": "Loops (J→P)",



        "lesson_j-funciones_title": "Functions (J→P)",




        "ref_title": "Theory reference: Python vs Java",



        "ref_intro": (
            "Comparative table of equivalent concepts and functions between Python and Java. "


            "Use it as a quick guide when migrating code."


        ),
        "ref_cat_basico": "Basic concepts",



        "ref_cat_tipos": "Data types",



        "ref_cat_estructuras": "Control structures",



        "ref_cat_funciones": "Functions and methods",



        "ref_cat_entrada_salida": "Input and output",



        "ref_col_python": "Python",



        "ref_col_java": "Java",



        "ref_col_description": "Description",



        "footer_text": "Computer Engineering Thesis — Educational Python to Java tool",



        "lessons": {
            "hola-mundo": {
                "title": "Hello World",



                "intro": (
                    "The «Hello World» program is the traditional starting point when learning a language. "


                    "In Python it is written in a single line; in Java you need a class structure "


                    "with the <code>main</code> method."


                ),
                "python_desc": (
                    "Python uses <code>print()</code> to display text on the console. "


                    "No class or main method is required."


                ),
                "java_desc": (
                    "Java requires a public class and the <code>public static void main(String[] args)</code> method. "

                    "Output is done with <code>System.out.println()</code>."


                ),
                "explanation": (
                    "<p><strong>Python</strong> is an interpreted language with dynamic typing. "


                    "A script can run directly without declaring a class.</p>"


                    "<p><strong>Java</strong> is compiled and object-oriented from the start. "


                    "Every program must live inside a class, and execution begins at <code>main</code>.</p>"


                    "<p>Note that in Java each statement ends with a semicolon (<code>;</code>), "


                    "while in Python a newline is enough.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-hm-1",



                        "question": "Traduce esta línea básica de Python a Java:",



                        "python_code": "print('Hola')",



                        "template_html": "System.out.<input type='text' class='exercise-input' data-answer='println' size='8'>('Hola');",



                        "hint": "En Java usamos println para imprimir en consola con salto de línea."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "hm-1",



                        "python": 'print("Hello, World!")',
                        "java": (
                            'public class HelloWorld {\\n'
                            '    public static void main(String[] args) {\\n'
                            '        System.out.println("Hello, World!");\\n'
                            '    }\\n'
                            '}'
                        ),
                        "explanation": "In Python, the print statement is direct. In Java, everything must be wrapped inside a public class and a main method."



                    }
                ],
            },
            "variables": {
                "title": "Variables",



                "intro": (
                    "Variables store data. Python infers the type automatically; "


                    "in Java you must declare the type explicitly."


                ),
                "python_desc": (
                    "Assign with <code>=</code>. No type declaration needed: "


                    '<code>name = "Ana"</code>, <code>age = 20</code>.'
                ),
                "java_desc": (
                    'Declare the type before the name: <code>String name = "Ana";</code>, '
                    "<code>int age = 20;</code>."


                ),
                "explanation": (
                    '<p>In <strong>Python</strong>, <code>name = "Ana"</code> creates a string variable without a keyword.</p>'
                    "<p>In <strong>Java</strong>, <code>String name = \"Ana\";</code> requires the <code>String</code> type "


                    "(capital S, it is a class).</p>"


                    "<p>Variable names often use <code>snake_case</code> in Python and <code>camelCase</code> in Java.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-var-1",



                        "question": "Declara una variable entera en Java equivalente a:",



                        "python_code": "edad = 20",



                        "template_html": "<input type='text' class='exercise-input' data-answer='int' size='4'> edad = 20;",



                        "hint": "Los números enteros sin decimales usan el tipo primitivo int."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "var-class",



                        "python": "",


                        "java": "public class Variables {\n    public static void main(String[] args) {",


                        "explanation": "Standard class and main method declaration in Java. Python doesn't require this."



                    },
                    {
                        "id": "var-1",



                        "python": 'name = "Ana"',
                        "java": '        String name = "Ana";',
                        "explanation": "In Java, we explicitly declare the 'String' type for text."



                    },
                    {
                        "id": "var-2",



                        "python": "age = 20",



                        "java": "        int age = 20;",



                        "explanation": "We declare the primitive type 'int' for integers."



                    },
                    {
                        "id": "var-3",



                        "python": "active = True",



                        "java": "        boolean active = true;",



                        "explanation": "The logical type is 'boolean' (lowercase) and values are true/false."



                    },
                    {
                        "id": "var-4",



                        "python": 'print(f"{name} is {age} years old")',
                        "java": '        System.out.println(name + " is " + age + " years old");',
                        "explanation": "In Java, the '+' operator is used to concatenate text and number variables."



                    },
                    {
                        "id": "var-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "Closing braces in Java."



                    }
                ],
            },
            "operadores": {
                "title": "Operators",



                "intro": "Operators are used to perform operations on variables and values.",



                "python_desc": "Uses and, or, not for logicals, and standard math operators.",



                "java_desc": "Uses &&, ||, ! for logicals, and standard math operators.",



                "explanation": "The biggest difference is in logical operators. Python uses readable keywords, while Java uses traditional boolean symbols. Also, Java has native increment (++) and decrement (--) operators, whereas Python relies on += 1.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "op-1",



                        "python": "x = 10\nx += 1\n\nif x > 5 and x < 15:\n    print('Valid range')",



                        "java": "int x = 10;\nx++;\n\nif (x > 5 && x < 15) {\n    System.out.println(\"Valid range\");\n}",


                        "explanation": "Notice the differences between 'and' / '&&' and autoincrementing."



                    }
                ]
            },
            "cadenas": {
                "title": "Strings",



                "intro": "Strings are used to store text. Both Python and Java provide many native methods.",



                "python_desc": "Uses str. Supports single and double quotes.",



                "java_desc": "Uses the String class. Only supports double quotes for text.",



                "explanation": "In Python, strings are arrays of bytes, so you can slice them easily like text[0:5]. In Java, you must call methods like substring(0, 5).",


                "exercises": [],
                "code_mappings": [
                    {
                        "id": "str-1",



                        "python": "text = \"Hello World\"\nlength = len(text)\nupper = text.upper()\npart = text[0:5]",


                        "java": "String text = \"Hello World\";\nint length = text.length();\nString upper = text.toUpperCase();\nString part = text.substring(0, 5);",



                        "explanation": "len() vs .length() and array slicing vs .substring()."



                    }
                ]
            },
            "condicionales": {
                "title": "Conditionals",



                "intro": (
                    "Conditional structures run code based on a condition. "


                    "The logic is similar; syntax and indentation differ."


                ),
                "python_desc": (
                    "Uses <code>if</code>, <code>elif</code>, and <code>else</code>. "


                    "Indentation defines blocks."


                ),
                "java_desc": (
                    "Uses <code>if</code>, <code>else if</code>, and <code>else</code>. "


                    "Blocks go inside braces <code>{ }</code>."

                ),
                "explanation": (
                    "<p>Python uses <strong>indentation</strong> (spaces or tabs) to delimit blocks.</p>"


                    "<p>Java uses <strong>braces</strong> and does not rely on indentation (though indenting helps readability).</p>"


                    "<p>The condition uses parentheses in Java; in Python parentheses are optional.</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-cond-1",



                        "question": "Traduce la palabra reservada 'elif' a Java:",



                        "python_code": "elif x == 5:",



                        "template_html": "} <input type='text' class='exercise-input' data-answer='else if' size='8'> (x == 5) {",


                        "hint": "En Java se separan las palabras: 'else' y 'if'."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "cond-class",



                        "python": "",


                        "java": "public class Conditionals {\n    public static void main(String[] args) {",


                        "explanation": "Main structure in Java."



                    },
                    {
                        "id": "cond-1",



                        "python": "score = 85",



                        "java": "        int score = 85;",



                        "explanation": "Variable declaration with its type."



                    },
                    {
                        "id": "cond-2",



                        "python": "if score >= 90:\n    print(\"Excellent\")",



                        "java": "        if (score >= 90) {\n            System.out.println(\"Excellent\");\n        }",


                        "explanation": "In Java, conditions go inside parentheses '()' and blocks use braces '{}'."


                    },
                    {
                        "id": "cond-3",



                        "python": "elif score >= 70:\n    print(\"Passed\")",



                        "java": "        else if (score >= 70) {\n            System.out.println(\"Passed\");\n        }",


                        "explanation": "Python uses 'elif', Java utilizes 'else if'."



                    },
                    {
                        "id": "cond-4",



                        "python": "else:\n    print(\"Failed\")",



                        "java": "        else {\n            System.out.println(\"Failed\");\n        }",


                        "explanation": "Default case. Also enclosed in braces in Java."



                    },
                    {
                        "id": "cond-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "End of main and class."



                    }
                ],
            },
            "bucles": {
                "title": "Loops",



                "intro": (
                    "Loops repeat a block of code. Python offers <code>for</code> and <code>while</code>; "


                    "Java has equivalent structures with different syntax."


                ),
                "python_desc": (
                    "<code>for i in range(5):</code> iterates a fixed number of times. "


                    "<code>while condition:</code> repeats while true."


                ),
                "java_desc": (
                    "<code>for (int i = 0; i < 5; i++)</code> is the classic loop. "


                    "<code>while (condition)</code> matches Python's while."


                ),
                "explanation": (
                    "<p>Python's <code>for</code> over <code>range(5)</code> yields 0, 1, 2, 3, 4.</p>"


                    "<p>Java's traditional <code>for</code> declares counter, condition, and increment on one line.</p>"


                    "<p>Both languages support <code>break</code> (exit) and <code>continue</code> (next iteration).</p>"


                ),
                "exercises": [
                    {
                        "id": "ex-bucle-1",



                        "question": "Traduce este bucle for que itera 5 veces:",



                        "python_code": "for i in range(5):",



                        "template_html": "for (int i = 0; <input type='text' class='exercise-input' data-answer='i < 5' size='6'>; i++) {",


                        "hint": "La condición del medio debe hacer que el bucle siga mientras 'i' sea menor a 5."



                    }
                ],
                "code_mappings": [
                    {
                        "id": "loop-class",



                        "python": "",


                        "java": "public class Loops {\n    public static void main(String[] args) {",


                        "explanation": "Java starting point."



                    },
                    {
                        "id": "loop-1",



                        "python": "for i in range(5):\n    print(f\"Iteration {i}\")",


                        "java": "        for (int i = 0; i < 5; i++) {\n            System.out.println(\"Iteration \" + i);\n        }",


                        "explanation": "The 'for' loop in Java needs to define the type, the condition, and the increment all together (int i=0; i<5; i++)."



                    },
                    {
                        "id": "loop-2",



                        "python": "counter = 0",



                        "java": "\n        int counter = 0;",



                        "explanation": "Variable for the while loop."



                    },
                    {
                        "id": "loop-3",



                        "python": "while counter < 3:\n    print(f\"While: {counter}\")\n    counter += 1",


                        "java": "        while (counter < 3) {\n            System.out.println(\"While: \" + counter);\n            counter++;\n        }",


                        "explanation": "The 'while' loop works the same way. In Java, we can use 'counter++' instead of 'counter += 1'."



                    },
                    {
                        "id": "loop-end",



                        "python": "",


                        "java": "    }\n}",


                        "explanation": "Closing the structure."



                    }
                ],
            },
        
            "funciones": {
                "title": "Functions",



                "intro": "Functions allow code reuse.",



                "python_desc": "Use def without return types.",



                "java_desc": "Requires return types and modifiers.",



                "explanation": "Java methods must be inside classes.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "func-1",



                        "python": "def greet(name):\n    return f'Hello {name}'",


                        "java": "    public static String greet(String name) {\n        return \"Hello \" + name;\n    }",


                        "explanation": "Java needs String type."



                    }
                ]
            },
            "casting": {
                "title": "Type Casting",



                "intro": "Casting is the process of forcing a variable to be treated as a specific data type.",



                "python_desc": "Uses constructor functions like int(), float(), str().",



                "java_desc": "Uses parentheses (type) for primitive types, or methods like Integer.parseInt().",



                "explanation": "In Python, casting is handled as calls to constructor functions. In Java, there is a strong distinction between primitive types (where parenthesis prefix syntax is used) and objects (where static conversion methods are used).",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "cast-1",



                        "python": "text = \"10\"\nnumber = int(text)\n\ndecimal = 5.8\ninteger = int(decimal)",



                        "java": "String text = \"10\";\nint number = Integer.parseInt(text);\n\ndouble decimal = 5.8;\nint integer = (int) decimal;",



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



                        "python": "is_greater = True\n\nif 10 > 9:\n    print(is_greater)",



                        "java": "boolean isGreater = true;\n\nif (10 > 9) {\n    System.out.println(isGreater);\n}",


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



                        "python": "name = input(\"What is your name? \")\nprint(\"Hello \" + name)",



                        "java": "import java.util.Scanner;\n\nScanner sc = new Scanner(System.in);\nSystem.out.print(\"What is your name? \");\nString name = sc.nextLine();\nSystem.out.println(\"Hello \" + name);",



                        "explanation": "Console reading in Java is considerably more verbose."



                    }
                ]
            },
            "formateo-cadenas": {
                "title": "String Formatting",



                "intro": "Inserting variable values inside text strings in a readable way.",



                "python_desc": "F-strings (e.g. f\"Hello {name}\").",


                "java_desc": "String.format() or System.out.printf().",



                "explanation": "Python 3.6+ f-strings revolutionized readability by allowing variables to be injected directly. Java relies on C-like positional wildcards (%s, %d) or pure concatenation.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "fmt-1",



                        "python": "price = 49.99\ntext = f\"The product costs ${price}\"\nprint(text)",


                        "java": "double price = 49.99;\nString text = String.format(\"The product costs $%.2f\", price);\nSystem.out.println(text);",



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



                        "python": "# Python has no fixed arrays, uses lists for everything\ncars = [\"Ford\", \"Volvo\", \"BMW\"]\ncars[0] = \"Toyota\"",


                        "java": "// Static size Array\nString[] cars = {\"Ford\", \"Volvo\", \"BMW\"};\ncars[0] = \"Toyota\";\n\n// Arrays without immediate data take an exact size\nint[] numbers = new int[5];",


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



                        "python": "multiply = lambda a, b: a * b\nprint(multiply(5, 6))",



                        "java": "interface Operation { int operate(int a, int b); }\n\n// Lambdas in Java need functional interfaces\nOperation multiply = (a, b) -> a * b;\nSystem.out.println(multiply.operate(5, 6));",


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



                        "python": "class Dog:\n    def sound(self): print(\"Woof\")\n\nclass Cat:\n    def sound(self): print(\"Meow\")\n\nfor animal in (Dog(), Cat()):\n    animal.sound()",



                        "java": "interface Animal { void sound(); }\nclass Dog implements Animal { public void sound() { System.out.println(\"Woof\"); } }\nclass Cat implements Animal { public void sound() { System.out.println(\"Meow\"); } }\n\nAnimal[] animals = {new Dog(), new Cat()};\nfor(Animal a : animals) { a.sound(); }",


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



                        "python": "x = 300\n\ndef my_function():\n    global x\n    x = 200\n\nmy_function()\nprint(x)",



                        "java": "public class MyClass {\n    static int x = 300;\n\n    static void myFunction() {\n        x = 200;\n    }\n\n    public static void main(String[] args) {\n        myFunction();\n        System.out.println(x);\n    }\n}",


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



                        "python": "import math\n\nroot = math.sqrt(64)\npi = math.pi\nabsolute = abs(-5)",



                        "java": "double root = Math.sqrt(64);\ndouble pi = Math.PI;\nint absolute = Math.abs(-5);",



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



                        "python": "import re\n\ntext = \"The sun rises\"\nmatch = re.search(r\"(?i)sun\", text)\nif match:\n    print(\"Found\")",



                        "java": "import java.util.regex.*;\n\nString text = \"The sun rises\";\nPattern pattern = Pattern.compile(\"(?i)sun\");\nMatcher matcher = pattern.matcher(text);\nif (matcher.find()) {\n    System.out.println(\"Found\");\n}",


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



                        "python": "# Global installation:\npip install requests\n\n# Usage\nimport requests",



                        "java": "<!-- In the Maven pom.xml file add: -->\n<dependency>\n    <groupId>com.google.code.gson</groupId>\n    <artifactId>gson</artifactId>\n    <version>2.8.6</version>\n</dependency>",



                        "explanation": "This represents a major paradigm shift: Java centralizes dependencies in project files."



                    }
                ]
            },
            "j-hola-mundo": {
                "title": "Hello World (J→P)",



                "intro": "Learn Java to Python.",



                "python_desc": "print() directly.",



                "java_desc": "Class and main method.",



                "explanation": "Python executes line by line.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-hm-1",



                        "python": "print('Hello, World!')",



                        "java": "System.out.println('Hello, World!');",



                        "explanation": "No semicolon or class."



                    }
                ]
            },
            "j-variables": {
                "title": "Variables (J→P)",



                "intro": "Python is dynamically typed.",



                "python_desc": "No type needed.",



                "java_desc": "Explicit type required.",



                "explanation": "Python infers types.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-var-1",



                        "python": "age = 20",



                        "java": "int age = 20;",



                        "explanation": "Goodbye 'int' and ';'"



                    }
                ]
            },
            "j-condicionales": {
                "title": "Conditionals (J→P)",



                "intro": "Python uses indentation.",



                "python_desc": "if/elif/else.",



                "java_desc": "if/else if/else.",



                "explanation": "Indentation is mandatory.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-cond-1",



                        "python": "if x > 5:\n    print('Greater')",



                        "java": "if (x > 5) {\n    System.out.println('Greater');\n}",


                        "explanation": "Optional parentheses."



                    }
                ]
            },
            "j-bucles": {
                "title": "Loops (J→P)",



                "intro": "Python loops over ranges.",



                "python_desc": "for x in range(n):",



                "java_desc": "for(int i=0; i<n; i++)",



                "explanation": "range() is idiomatic.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-buc-1",



                        "python": "for i in range(5):\n    print(i)",



                        "java": "for(int i=0; i<5; i++) {\n    System.out.println(i);\n}",


                        "explanation": "range(5) yields 0..4"



                    }
                ]
            },
            "j-funciones": {
                "title": "Functions (J→P)",



                "intro": "Python uses 'def'.",



                "python_desc": "def and return.",



                "java_desc": "public static type.",



                "explanation": "More compact.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-func-1",



                        "python": "def add(a, b):\n    return a + b",



                        "java": "public int add(int a, int b) {\n    return a + b;\n}",


                        "explanation": "No types."



                    }
                ]
            },


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



                        "python": "# This is a comment\nx = 5",



                        "java": "// This is a comment\nint x = 5;",



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



                        "python": "text = 'Hello'\nnum = 10",



                        "java": "String text = \"Hello\";\nint num = 10;",



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



                        "python": "s = {1, 2, 2}\nprint(s)",


                        "java": "java.util.Set<Integer> s = new java.util.HashSet<>();\ns.add(1);\ns.add(2);\nSystem.out.println(s);",



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



                        "python": "class Animal:\n    pass\nclass Dog(Animal):\n    pass",



                        "java": "class Animal {}\nclass Dog extends Animal {}",


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



                        "python": "numbers = [1, 2, 3]\nnumbers.append(4)",


                        "java": "java.util.List<Integer> numbers = new java.util.ArrayList<>();\nnumbers.add(1);\nnumbers.add(2);\nnumbers.add(3);\nnumbers.add(4);",



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



                        "python": "ages = {'Ana': 20}\nprint(ages['Ana'])",


                        "java": "java.util.Map<String, Integer> ages = new java.util.HashMap<>();\nages.put(\"Ana\", 20);\nSystem.out.println(ages.get(\"Ana\"));",



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



                        "python": "class Person:\n    def __init__(self, name):\n        self.name = name",



                        "java": "public class Person {\n    public String name;\n    public Person(String name) {\n        this.name = name;\n    }\n}",


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



                        "python": "try:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    print('Error')",



                        "java": "try {\n    int x = 1 / 0;\n} catch (ArithmeticException e) {\n    System.out.println(\"Error\");\n}",


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



                        "python": "import math\nprint(math.pi)",



                        "java": "import java.lang.Math;\npublic class Program {\n    public static void main(String[] args) {\n        System.out.println(Math.PI);\n    }\n}",


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


                        "java": "java.util.List<Object> arr = java.util.Arrays.asList(1, \"Two\", 3.0);",



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


                        "java": 'java.util.Map<String, Integer> map_obj = new java.util.HashMap<>();\\nmap_obj.put("id", 1);',
                        "explanation": "Initialized directly with values."



                    }
                ]
            },
            "fechas": {
                "title": "Dates and Time",



                "intro": "Handling dates is an everyday task for logs and databases.",



                "python_desc": "Uses the datetime module.",



                "java_desc": "Uses the java.time package (LocalDate, LocalDateTime).",



                "explanation": "Since Java 8, java.time was introduced which shares a very similar philosophy to Python's datetime, abandoning the old, complex Date or Calendar classes.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "date-1",



                        "python": "import datetime\n\nnow = datetime.datetime.now()\nprint(now.year)",



                        "java": "import java.time.LocalDateTime;\n\nLocalDateTime now = LocalDateTime.now();\nSystem.out.println(now.getYear());",



                        "explanation": "Both languages offer descriptive methods to extract date parts."



                    }
                ]
            },
            "archivos": {
                "title": "File Handling",



                "intro": "Read and write local hard drive files.",



                "python_desc": "Built-in open() function and with statements.",



                "java_desc": "java.nio.file.* classes or FileWriter/Scanner.",



                "explanation": "Python makes reading files extremely concise thanks to the 'with' context manager (which closes the file automatically). In Java, the 'try-with-resources' syntax is commonly used.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "file-1",



                        "python": "with open('data.txt', 'w') as f:\n    f.write('Hello, File')",



                        "java": "try (java.io.FileWriter f = new java.io.FileWriter(\"data.txt\")) {\n    f.write(\"Hello, File\");\n} catch(Exception e) {\n    e.printStackTrace();\n}",


                        "explanation": "Both approaches ensure the file is closed after the block, preventing memory leaks."



                    }
                ]
            },
            "json": {
                "title": "JSON Format",



                "intro": "JSON is the standard format for sending and receiving data over networks.",



                "python_desc": "Built-in json module.",



                "java_desc": "Third-party libraries (Gson, Jackson) or org.json.",



                "explanation": "Unlike Python, which includes the JSON library natively in its standard library, Java has historically relied on popular third-party libraries like Jackson or Gson to work with this format comfortably.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "json-1",



                        "python": "import json\n\nobj = {'name': 'Ana', 'age': 30}\njson_str = json.dumps(obj)\nprint(json_str)",


                        "java": "// Using org.json (external library)\nimport org.json.JSONObject;\n\nJSONObject obj = new JSONObject();\nobj.put(\"name\", \"Ana\");\nobj.put(\"age\", 30);\nSystem.out.println(obj.toString());",



                        "explanation": "In Python, dictionaries and JSON are almost natively interchangeable."



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



                        "python": "class A:\n    def __init__(self):\n        pass",



                        "java": "public class A {\n    public A() {}\n}",


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



                        "python": "try:\n    pass\nexcept Exception as e:\n    print(e)",



                        "java": "try {\n} catch (Exception e) {\n    System.out.println(e);\n}",


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
            },
            "j-comentarios": {
                "title": "Comments (J→P)",



                "intro": "In Java use // or /* */, in Python use #.",



                "python_desc": "# Single-line comments",



                "java_desc": "// Single-line comments",



                "explanation": "Comments are not executed and document the code.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-comentarios-1",



                        "python": "# This is a comment in Python",



                        "java": "// This is a comment in Java",



                        "explanation": "Java uses // for single-line comments."



                    }
                ]
            },
            "j-tipos-datos": {
                "title": "Data Types (J→P)",



                "intro": "Java types map to Python equivalents.",



                "python_desc": "int, float, str, bool",



                "java_desc": "int, double, String, boolean",



                "explanation": "Python infers types dynamically while Java declares them explicitly.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-tipos-datos-1",



                        "python": "numero = 5\ntexto = 'Hola'\nreal = 3.14",



                        "java": "int numero = 5;\nString texto = \"Hola\";\ndouble real = 3.14;",



                        "explanation": "Basic types are similar, but Python does not require explicit declarations."



                    }
                ]
            },
            "j-tuplas": {
                "title": "Tuples (J→P)",



                "intro": "Java does not have native tuples; Python does.",



                "python_desc": "Tuples with parentheses ()",



                "java_desc": "Immutable lists or simple classes",



                "explanation": "Python tuples are immutable and group related values together.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-tuplas-1",



                        "python": "coordinates = (10, 20)",



                        "java": "List<Integer> coordinates = Collections.unmodifiableList(Arrays.asList(10, 20));",



                        "explanation": "Java uses immutable collections for similar behavior."



                    }
                ]
            },
            "j-sets": {
                "title": "Sets (J→P)",



                "intro": "Duplicate-free collections in Java and Python.",



                "python_desc": "set()",



                "java_desc": "HashSet<>",



                "explanation": "Both languages use sets for unique values with no fixed order.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-sets-1",



                        "python": "values = {1, 2, 2, 3}",


                        "java": "Set<Integer> values = new HashSet<>(Arrays.asList(1, 2, 2, 3));",



                        "explanation": "The result is a collection of unique elements."



                    }
                ]
            },
            "j-herencia": {
                "title": "Inheritance (J→P)",



                "intro": "Subclasses inherit from base classes.",



                "python_desc": "class Child(Parent):",



                "java_desc": "class Child extends Parent",



                "explanation": "Inheritance allows reusing and specializing behavior in subclasses.",



                "exercises": [],
                "code_mappings": [
                    {
                        "id": "j-herencia-1",



                        "python": "class Animal:\n    pass\n\nclass Dog(Animal):\n    pass",



                        "java": "class Animal {}\nclass Dog extends Animal {}",


                        "explanation": "In Python the base class is specified in parentheses."



                    }
                ]
            },
        },
        "reference": {
            "basico": [
                {
                    "python": "No class required",



                    "java": "public class MyClass { }",


                    "desc": "Java requires at least one public class per file.",



                },
                {
                    "python": "# comment",



                    "java": "// comment",



                    "desc": "Single-line comments.",



                },
                {
                    "python": '"""docstring"""',
                    "java": "/** Javadoc */",



                    "desc": "Code documentation.",



                },
                {
                    "python": "pass",



                    "java": "; or empty block { }",


                    "desc": "Empty block placeholder.",



                },
            ],
            "tipos": [
                {
                    "python": "int, float",



                    "java": "int, double, float",



                    "desc": "Integer and decimal numbers.",



                },
                {
                    "python": "str",



                    "java": "String",



                    "desc": "Text strings.",



                },
                {
                    "python": "bool (True/False)",



                    "java": "boolean (true/false)",



                    "desc": "Boolean values.",



                },
                {
                    "python": "list",



                    "java": "ArrayList<T> or T[]",


                    "desc": "Lists and dynamic arrays.",



                },
                {
                    "python": "dict",



                    "java": "HashMap<K, V>",



                    "desc": "Key-value structures.",



                },
                {
                    "python": "None",



                    "java": "null",



                    "desc": "Absence of value.",



                },
            ],
            "estructuras": [
                {
                    "python": "if / elif / else",



                    "java": "if / else if / else",



                    "desc": "Conditionals.",



                },
                {
                    "python": "for x in iterable:",



                    "java": "for (Type x : collection)",



                    "desc": "For-each loop.",



                },
                {
                    "python": "while cond:",



                    "java": "while (cond)",



                    "desc": "While loop.",



                },
                {
                    "python": "break / continue",



                    "java": "break / continue",



                    "desc": "Loop flow control.",



                },
            ],
            "funciones": [
                {
                    "python": "def name(params):",



                    "java": "Type name(Type param) { }",


                    "desc": "Function/method definition.",



                },
                {
                    "python": "return value",



                    "java": "return value;",



                    "desc": "Return a result.",



                },
                {
                    "python": "lambda x: x * 2",



                    "java": "x -> x * 2",



                    "desc": "Anonymous functions.",



                },
                {
                    "python": "len(list)",



                    "java": "list.size() or array.length",



                    "desc": "Collection length.",



                },
            ],
            "entrada_salida": [
                {
                    "python": 'print("text")',
                    "java": 'System.out.println("text");',
                    "desc": "Console output.",



                },
                {
                    "python": 'input("message")',
                    "java": "Scanner + nextLine()",



                    "desc": "Keyboard input.",



                },
                {
                    "python": "open('file.txt')",



                    "java": "Files.readAllLines(Paths.get(...))",



                    "desc": "File reading.",



                },
                {
                    "python": "import module",



                    "java": "import package.Class;",



                    "desc": "Import dependencies.",



                },
            ],
        },
    },
}


def get_text(lang: str, key: str, default: str = "") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["es"]).get(key, default)


def get_lesson(lang: str, lesson_id: str) -> dict:
    return TRANSLATIONS.get(lang, TRANSLATIONS["es"])["lessons"].get(lesson_id, {})


def get_lesson_title(lang: str, lesson_id: str) -> str:
    key = f"lesson_{lesson_id.replace('-', '_')}_title"
    title = get_text(lang, key)
    if title:
        return title
    lesson = get_lesson(lang, lesson_id)
    return lesson.get("title", lesson_id)


def get_reference(lang: str, category: str) -> list:
    return TRANSLATIONS.get(lang, TRANSLATIONS["es"])["reference"].get(category, [])
