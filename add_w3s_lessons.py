import re

with open("translations.py", "r", encoding="utf-8") as f:
    content = f.read()

es_operadores_cadenas = """
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
                        "python": "x = 10\\nx += 1\\n\\nif x > 5 and x < 15:\\n    print('Rango válido')",
                        "java": "int x = 10;\\nx++;\\n\\nif (x > 5 && x < 15) {\\n    System.out.println(\\"Rango válido\\");\\n}",
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
                        "python": "texto = \\"Hola Mundo\\"\\nlongitud = len(texto)\\nmayus = texto.upper()\\nparte = texto[0:4]",
                        "java": "String texto = \\"Hola Mundo\\";\\nint longitud = texto.length();\\nString mayus = texto.toUpperCase();\\nString parte = texto.substring(0, 4);",
                        "explanation": "len() vs .length() y particionado de arrays vs .substring()."
                    }
                ]
            },"""

es_fechas_archivos_json = """
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
                        "python": "import datetime\\n\\nahora = datetime.datetime.now()\\nprint(ahora.year)",
                        "java": "import java.time.LocalDateTime;\\n\\nLocalDateTime ahora = LocalDateTime.now();\\nSystem.out.println(ahora.getYear());",
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
                        "python": "with open('datos.txt', 'w') as f:\\n    f.write('Hola, Archivo')",
                        "java": "try (java.io.FileWriter f = new java.io.FileWriter(\\"datos.txt\\")) {\\n    f.write(\\"Hola, Archivo\\");\\n} catch(Exception e) {\\n    e.printStackTrace();\\n}",
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
                        "python": "import json\\n\\nobj = {'nombre': 'Ana', 'edad': 30}\\njson_str = json.dumps(obj)\\nprint(json_str)",
                        "java": "// Usando org.json (librería externa)\\nimport org.json.JSONObject;\\n\\nJSONObject obj = new JSONObject();\\nobj.put(\\"nombre\\", \\"Ana\\");\\nobj.put(\\"edad\\", 30);\\nSystem.out.println(obj.toString());",
                        "explanation": "En Python, los diccionarios y JSON son casi intercambiables de forma nativa."
                    }
                ]
            },"""

en_operadores_cadenas = """
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
                        "python": "x = 10\\nx += 1\\n\\nif x > 5 and x < 15:\\n    print('Valid range')",
                        "java": "int x = 10;\\nx++;\\n\\nif (x > 5 && x < 15) {\\n    System.out.println(\\"Valid range\\");\\n}",
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
                        "python": "text = \\"Hello World\\"\\nlength = len(text)\\nupper = text.upper()\\npart = text[0:5]",
                        "java": "String text = \\"Hello World\\";\\nint length = text.length();\\nString upper = text.toUpperCase();\\nString part = text.substring(0, 5);",
                        "explanation": "len() vs .length() and array slicing vs .substring()."
                    }
                ]
            },"""

en_fechas_archivos_json = """
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
                        "python": "import datetime\\n\\nnow = datetime.datetime.now()\\nprint(now.year)",
                        "java": "import java.time.LocalDateTime;\\n\\nLocalDateTime now = LocalDateTime.now();\\nSystem.out.println(now.getYear());",
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
                        "python": "with open('data.txt', 'w') as f:\\n    f.write('Hello, File')",
                        "java": "try (java.io.FileWriter f = new java.io.FileWriter(\\"data.txt\\")) {\\n    f.write(\\"Hello, File\\");\\n} catch(Exception e) {\\n    e.printStackTrace();\\n}",
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
                        "python": "import json\\n\\nobj = {'name': 'Ana', 'age': 30}\\njson_str = json.dumps(obj)\\nprint(json_str)",
                        "java": "// Using org.json (external library)\\nimport org.json.JSONObject;\\n\\nJSONObject obj = new JSONObject();\\nobj.put(\\"name\\", \\"Ana\\");\\nobj.put(\\"age\\", 30);\\nSystem.out.println(obj.toString());",
                        "explanation": "In Python, dictionaries and JSON are almost natively interchangeable."
                    }
                ]
            },"""


def insert_before(content, lang_section, target_key, insertion):
    # Find the language section
    lang_idx = content.find(f'"{lang_section}": {{')
    if lang_idx == -1: return content
    
    # Find the target key inside the language section
    target_idx = content.find(f'"{target_key}": {{', lang_idx)
    if target_idx == -1: return content
    
    # Extract indentation
    start_of_line = content.rfind('\\n', 0, target_idx) + 1
    
    # Insert
    return content[:start_of_line] + insertion + content[start_of_line:]

def insert_after(content, lang_section, after_key, insertion):
    # Find the language section
    lang_idx = content.find(f'"{lang_section}": {{')
    if lang_idx == -1: return content
    
    # Find the target key
    target_idx = content.find(f'"{after_key}": {{', lang_idx)
    if target_idx == -1: return content
    
    # Find the end of this block
    # Count braces
    brace_count = 0
    in_str = False
    escape = False
    
    for i in range(target_idx, len(content)):
        c = content[i]
        if escape:
            escape = False
            continue
        if c == '\\\\':
            escape = True
            continue
        if c == '"' and not escape:
            in_str = not in_str
            continue
            
        if not in_str:
            if c == '{':
                brace_count += 1
            elif c == '}':
                brace_count -= 1
                if brace_count == 0:
                    # We found the end of the `after_key` dictionary block.
                    # It might be followed by a comma
                    end_idx = i + 1
                    if content[end_idx] == ',':
                        end_idx += 1
                    
                    # Insert right after this line
                    next_line_idx = content.find('\\n', end_idx)
                    if next_line_idx != -1:
                        next_line_idx += 1
                        return content[:next_line_idx] + insertion + content[next_line_idx:]
                    return content
    return content

def insert_after_key(content, lang, target_key, insertion):
    idx = content.find(f'"{lang}": {{')
    if idx == -1: return content
    target_idx = content.find(f'"{target_key}":', idx)
    if target_idx == -1: return content
    # Find the end of the line
    line_end = content.find('\\n', target_idx)
    if line_end != -1:
        return content[:line_end+1] + insertion + content[line_end+1:]
    return content

# Process ES lessons
content = insert_before(content, "es", "condicionales", es_operadores_cadenas)
content = insert_after(content, "es", "modulos", es_fechas_archivos_json)

# Process EN lessons
content = insert_before(content, "en", "condicionales", en_operadores_cadenas)
content = insert_after(content, "en", "modulos", en_fechas_archivos_json)

# Insert ES titles
es_titles = '''        "lesson_cadenas_title": "Cadenas (Strings)",
        "lesson_operadores_title": "Operadores",
        "lesson_fechas_title": "Manejo de Fechas",
        "lesson_archivos_title": "Manejo de Archivos",
        "lesson_json_title": "Formato JSON",
'''
content = insert_after_key(content, "es", "lesson_tipos-datos_title", es_titles)

# Insert EN titles
en_titles = '''        "lesson_cadenas_title": "Strings",
        "lesson_operadores_title": "Operators",
        "lesson_fechas_title": "Dates & Time",
        "lesson_archivos_title": "File Handling",
        "lesson_json_title": "JSON Format",
'''
content = insert_after_key(content, "en", "lesson_tipos-datos_title", en_titles)

with open("translations.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
