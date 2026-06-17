with open('translations.py', 'r', encoding='utf-8') as f:
    content = f.read()

def insert_after_key_exact(content, lang, target_key, insertion):
    idx = content.find(f'"{lang}": {{')
    if idx == -1: return content
    target_idx = content.find(f'"{target_key}":', idx)
    if target_idx == -1: return content
    line_end = content.find('\n', target_idx)
    if line_end != -1:
        return content[:line_end+1] + insertion + content[line_end+1:]
    return content

es_titles = """        "lesson_cadenas_title": "Cadenas (Strings)",
        "lesson_operadores_title": "Operadores",
        "lesson_fechas_title": "Manejo de Fechas",
        "lesson_archivos_title": "Manejo de Archivos",
        "lesson_json_title": "Formato JSON",
"""

en_titles = """        "lesson_cadenas_title": "Strings",
        "lesson_operadores_title": "Operators",
        "lesson_fechas_title": "Dates & Time",
        "lesson_archivos_title": "File Handling",
        "lesson_json_title": "JSON Format",
"""

content = insert_after_key_exact(content, 'es', 'lesson_tipos-datos_title', es_titles)
content = insert_after_key_exact(content, 'en', 'lesson_tipos-datos_title', en_titles)

with open('translations.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Titles injected correctly!')
