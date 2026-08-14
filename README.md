# Py2Java Edu — Plataforma Web de Aprendizaje y Transpilación Interactiva (Python → Java)

> **Proyecto de Tesis de Grado**  
> Plataforma interactiva diseñada para facilitar la transición pedagógica del paradigma de programación dinámico (Python) al paradigma estructurado y fuertemente tipado (Java) mediante gamificación, aprendizaje adaptativo, evaluación diagnóstica y tutoría con Inteligencia Artificial.

---

## 🎯 Objetivos del Proyecto

1. **Facilitar la Curva de Aprendizaje:** Guiar a los estudiantes en la asimilación de conceptos de programación orientada a objetos (POO) y tipado estático en Java a partir de su experiencia previa en Python.
2. **Visualización y Mapeo Cognitivo:** Ofrecer un transpilador y visualizador AST de código interactivo que muestra las equivalencias estructurales y sintácticas en tiempo real.
3. **Gamificación y Motivación:** Incorporar sistema de experiencia (XP), niveles, rachas diarias, insignias de logros, tablas de clasificación (*Leaderboard*) y certificados de finalización descargables.
4. **Evaluación Adaptativa y Diagnóstica:** Cuestionarios temáticos (*Quizzes*), laboratorios de práctica con ejecución y validación de código (*Practice Labs*) y evaluaciones integrales por sección.
5. **Supervisión Docente:** Panel administrativo para instructores con métricas de rendimiento grupal, seguimiento individualizado y exportación de datos académicos en formato CSV.

---

## 🏗️ Arquitectura Técnica

* **Backend:** Python 3.11+ / Flask Framework
* **Bases de Datos:**
  * **Producción:** PostgreSQL (Vercel / Supabase / Neon)
  * **Desarrollo / Pruebas:** SQLite local con soporte de `memory`/`file`
* **ORM & Migraciones:** SQLAlchemy / Flask-SQLAlchemy
* **Autenticación y Seguridad:** Flask-Login, Werkzeug (cifrado con algoritmos Scrypt/PBKDF2)
* **Motor de Transpilación:** Módulos personalizados en `compiler/` (`analyzer.py`, `generator.py`, `environment.py`, `core.py`) basados en el AST nativo de Python
* **Frontend:** HTML5 semántico, CSS3 moderno (soporte de Modo Claro / Modo Oscuro, temas dinámicos), JavaScript ES6+ Vanilla
* **Tutor Inteligente:** Integración con API de Google Gemini para resolución de dudas en tiempo real

---

## 📂 Estructura del Repositorio

```text
├── compiler/              # Motor modular de transpilación Python -> Java
│   ├── analyzer.py        # Inferencia de tipos y pase 1 de análisis semántico
│   ├── generator.py       # Generador de código Java a partir del AST
│   ├── environment.py     # Manejo de ámbitos (scopes), tipos y variables
│   └── core.py            # Punto de entrada de la función translate()
├── content/               # 167+ Lecciones estructuradas en formato JSON
│   ├── py2java/           # Lecciones de sintaxis, POO, estructuras de datos
│   └── ...
├── data/                  # Evaluaciones, ejercicios, glosario y catálogo
│   ├── evaluations.json   # Banco de preguntas para evaluaciones adaptativas
│   ├── examples.json      # Catálogo de ejemplos comparativos Python vs Java
│   ├── glossary.json      # Glosario técnico bilingüe
│   ├── practice_problems.json # Laboratorios y retos de código
│   └── quizzes.json       # Cuestionarios por tema
├── static/                # Recursos estáticos
│   ├── css/               # Hojas de estilo modulares (style.css, evaluation.css, etc.)
│   └── js/                # Scripts de interacción (transpiler.js, ai-tutor.js, etc.)
├── templates/             # Plantillas Jinja2 (Dashboard, Lecciones, Quizzes, Certificados, etc.)
├── app.py                 # Servidor principal y definición de rutas / endpoints API
├── models.py              # Modelos de base de datos (User, LessonProgress, etc.)
├── content_loader.py      # Cargador y caché de contenido educativo
├── test_compiler.py       # Suite de pruebas del transpilador (81 tests unitarios)
├── test_system_audit.py   # Suite de auditoría y pruebas integrales E2E (9 tests)
└── requirements.txt       # Dependencias del proyecto
```

---

## 🚀 Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/JoseMiguel2005of/Tesis.git
cd Tesis
```

### 2. Crear y activar entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Variables de entorno (Opcional en desarrollo)
Crea un archivo `.env` en la raíz con:
```ini
SECRET_KEY=clave-secreta-de-desarrollo
TEACHER_SECRET_CODE=profesor2024
# DATABASE_URL=postgresql://... (Si no se especifica, usa SQLite automático)
# GEMINI_API_KEY=tu_api_key (Para activar el Tutor IA)
```

### 5. Iniciar la aplicación
```bash
python app.py
```
Abre en tu navegador: [http://localhost:5000](http://localhost:5000)

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto cuenta con suites de pruebas completas:

```bash
# 1. Pruebas unitarias del transpilador Python -> Java (81 pruebas)
python test_compiler.py

# 2. Pruebas de integración, seguridad y endpoints de la plataforma (9 pruebas E2E)
python test_system_audit.py
```

---

## 👥 Roles de Usuario

* **Estudiante (`student`):** Acceso al Roadmap de aprendizaje, lecciones interactivas, editor de código con transpilador, cuestionarios, labs de práctica, evaluaciones finales, leaderboard y certificados de finalización.
* **Profesor / Tutor (`teacher`):** Acceso al panel de control `/profesor`, visualización del avance global del curso, métricas de retención, distribución de niveles y descarga de reportes en CSV. (Registro mediante código de seguridad docente).

---

## 📄 Licencia

Desarrollado como proyecto de grado académico. Todos los derechos reservados © 2026.
