# Py2Java Edu — Plataforma Educativa Interactiva Python → Java

Plataforma web educativa diseñada para el aprendizaje progresivo de **Python** y su transición hacia **Java**, con ejecución interactiva en navegador (Pyodide), traductor/transpilador **AST Python → Java**, evaluaciones adaptativas verificadas en servidor, gamificación anti-trampa, certificados con verificación pública criptográfica, accesibilidad **WCAG 2.1 AA** y paneles de gestión docente y de Super Admin.

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Funcionalidades por Rol](#funcionalidades-por-rol)
3. [Requisitos Previos](#requisitos-previos)
4. [Instalación Local](#instalación-local)
5. [Migraciones de Base de Datos (Alembic)](#migraciones-de-base-de-datos-alembic)
6. [Creación del Super Admin por CLI](#creación-del-super-admin-por-cli)
7. [Ejecución de Pruebas Automatizadas (`pytest`)](#ejecución-de-pruebas-automatizadas-pytest)
8. [Certificados Verificables](#certificados-verificables)
9. [Despliegue en Producción (Vercel + Supabase)](#despliegue-en-producción-vercel--supabase)
10. [Seguridad y Accesibilidad](#seguridad-y-accesibilidad)

---

## Arquitectura General

El proyecto adopta el patrón **Application Factory** (`py2java.create_app()`) con separación modular por Blueprints, servicios de dominio, contenido curricular en JSON y transpilador AST dedicado:

```text
Tesis/
├── app.py                     # Punto de entrada WSGI (exporta `app` para Vercel y CLI)
├── models.py                  # Modelos SQLAlchemy (UTC estandarizado, índices y UniqueConstraints)
├── content_loader.py          # Carga cacheada (@lru_cache) y validación estricta de IDs curriculares
├── pdf_report.py              # Generación de diplomas PDF y reportes docentes/globales (fpdf2)
├── translator.py              # Fachada del traductor Python → Java
├── compiler/                  # Compilador/Transpilador AST Python → Java
│   ├── analyzer.py            # Inferencia de tipos (int, double, boolean, String, ArrayList, HashMap, clases)
│   ├── environment.py         # Tabla de símbolos y ámbitos (scopes)
│   └── generator.py           # Generador de código Java compilable con `javac`
├── py2java/                   # Paquete modular de la aplicación Flask
│   ├── __init__.py            # Application Factory (`create_app`), cabeceras CSP/seguridad y error handlers
│   ├── config.py              # Configuración centralizada, pools SQLAlchemy y logging UTC
│   ├── extensions.py          # Extensiones (SQLAlchemy, Flask-Migrate, Flask-Login, CSRFProtect, Limiter)
│   ├── cli.py                 # Comandos CLI (`create-superadmin`, `bootstrap-superadmin`)
│   ├── blueprints/            # Rutas HTTP desacopladas por dominio
│   │   ├── auth.py            # Login, registro, recuperación OTP y configuración de cuenta (/cuenta)
│   │   ├── lessons.py         # Lecciones, glosario, búsqueda, perfil, certificado y verificación pública
│   │   ├── practice.py        # Laboratorio de práctica, traductor AST y envío de soluciones
│   │   ├── evaluations.py     # Evaluaciones finales y quizzes con sesiones en servidor
│   │   ├── teacher.py         # Panel docente, secciones, auditoría acotada, resultados y reportes CSV/PDF
│   │   ├── superadmin.py      # Panel Super Admin, alta de docentes, roles, desbloqueo y auditoría CSV
│   │   └── api.py             # API REST de progreso anti-trampa, XP, logros y Tutor IA (Gemini)
│   └── services/              # Lógica de negocio reutilizable (accounts, certificates, classrooms, curriculum, mail, progress, security, timeutils, validation)
├── content/                   # Currículo declarativo en JSON (lecciones, evaluaciones, práctica, glosario, UI)
├── migrations/                # Migraciones versionadas con Flask-Migrate / Alembic
├── templates/                 # Plantillas Jinja2 con diseño unificado y soporte WCAG 2.1 AA
├── static/                    # Hojas CSS modulares, JS de Pyodide/evaluaciones/a11y y Service Worker
├── tests/                     # Suite automatizada con pytest (seguridad, IDOR, evaluaciones, compilador, flujos)
├── vercel.json                # Configuración moderna de Vercel (Fluid Compute + CDN para /static/*)
├── requirements.txt           # Dependencias de producción con versiones exactas fijadas
├── requirements-dev.txt       # Dependencias de desarrollo y testing (`pytest`)
└── .env.example               # Plantilla documentada de variables de entorno
```

---

## Funcionalidades por Rol

| Rol | Capacidades Principales |
| :--- | :--- |
| **Estudiante** (`student`) | Ruta de aprendizaje guiada (Python, NumPy, Pandas, SciPy, MySQL, MongoDB, Java), ejecución de código Python en el navegador con **Pyodide**, traductor AST Python → Java, Laboratorio de Práctica con pistas y solución de referencia colapsables, **Tutor IA** con rate-limiting, evaluaciones adaptativas con temporizador en servidor, gamificación (XP, niveles, racha diaria y logros), perfil público/propio, configuración de cuenta (`/cuenta`: edición de correo, cambio de contraseña, historial de evaluaciones y auto-eliminación confirmada) y certificado HTML/PDF con verificación pública. |
| **Docente** (`teacher`) | Panel docente (`/profesor`), creación, edición de nombre y eliminación de secciones con código de invitación, inscripción y desvinculación de estudiantes sin suspender su cuenta global, consulta detallada de resultados de evaluaciones y quizzes por estudiante, suspensión/restauración con motivo obligatorio, bitácora de auditoría estrictamente acotada a sus propias acciones y secciones, y exportación de reportes CSV (con protección anti-fórmulas) y PDF. |
| **Super Admin** (`superadmin`) | Panel global (`/superadmin`), métricas globales de plataforma, creación directa de cuentas docentes (sin depender de código estático compartido), cambio de rol (`student` ↔ `teacher`), desbloqueo de cuentas suspendidas o limitadas por rate-limit, asignación/reasignación de secciones, suspensión/restauración de cualquier cuenta no-superadmin, filtrado avanzado y exportación completa de `AuditLog` a CSV, y reportes globales CSV/PDF. |

---

## Requisitos Previos

- **Python 3.11+** (probado en Python 3.12 / 3.13)
- **pip** y entorno virtual (`venv`)
- *(Opcional)* **PostgreSQL 15+** o cuenta en **Supabase** para producción
- *(Opcional)* **JDK (`javac`)** si deseas ejecutar las pruebas de compilación Java real en `tests/test_compiler.py`
- *(Opcional)* Clave de **Google Gemini** (`GEMINI_API_KEY`) para habilitar el Tutor IA

---

## Instalación Local

1. **Clonar el repositorio y entrar al directorio:**

   ```bash
   git clone <url-del-repositorio>
   cd Tesis
   ```

2. **Crear y activar un entorno virtual:**

   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar dependencias:**

   - Producción:
     ```bash
     pip install -r requirements.txt
     ```
   - Desarrollo y pruebas:
     ```bash
     pip install -r requirements-dev.txt
     ```

4. **Configurar variables de entorno:**

   ```bash
   cp .env.example .env
   ```
   Edita `.env` y define al menos `SECRET_KEY` (si omites `DATABASE_URL` en local, se utilizará SQLite en `database_v2.sqlite`).

5. **Aplicar migraciones de base de datos:**

   ```bash
   flask --app app db upgrade
   ```

6. **Iniciar el servidor de desarrollo:**

   ```bash
   python app.py
   ```
   La plataforma quedará disponible en `http://127.0.0.1:5000`.

---

## Migraciones de Base de Datos (Alembic)

La aplicación utiliza **Flask-Migrate (Alembic)** para evolucionar el esquema de forma controlada y reproducible (no se ejecuta DDL en caliente durante peticiones HTTP):

```bash
# Aplicar todas las migraciones pendientes (SQLite local o PostgreSQL/Supabase)
flask --app app db upgrade

# Consultar revisión actual de la base de datos
flask --app app db current

# Generar una nueva migración tras modificar models.py
flask --app app db migrate -m "descripcion_del_cambio"
```

---

## Creación del Super Admin por CLI

Puedes crear una cuenta de **Super Admin** de manera segura e interactiva desde la terminal (después de ejecutar `flask --app app db upgrade`):

```bash
flask --app app create-superadmin
```

Alternativamente, para despliegues automatizados, define `SUPERADMIN_USERNAME`, `SUPERADMIN_EMAIL` y `SUPERADMIN_PASSWORD` en el entorno y ejecuta:

```bash
flask --app app bootstrap-superadmin
```

---

## Ejecución de Pruebas Automatizadas (`pytest`)

La suite de pruebas está completamente aislada: utiliza bases de datos SQLite temporales limpias por test (`tmp_path`) y nunca modifica la base de datos de desarrollo ni la de producción.

```bash
python -m pytest
```

Cobertura de la suite:
- `tests/test_auth_security.py`: validaciones estrictas de registro (incluyendo confirmación de contraseña), login sin enumeración y con rate-limit, recuperación OTP con tope de 5 intentos y `ALLOW_DEMO_RESET=false`, CSRF en formularios y JSON, `/logout` solo `POST`, bloqueo de Open Redirect y Path Traversal, escape XSS y cabeceras CSP.
- `tests/test_rbac_idor.py`: aislamiento estricto multi-docente (IDOR), restricciones por rol y privacidad de códigos de sección.
- `tests/test_evaluations_progress.py`: sesiones de evaluación en servidor (`EvaluationSession`), caducidad, calificación completa, rechazo de IDs inexistentes y bloqueo anti-trampa de XP tras usar *"Ver Solución"*.
- `tests/test_exports.py`: neutralización anti-fórmulas en CSV (`=`, `+`, `-`, `@`) y generación válida de reportes PDF.
- `tests/test_compiler.py`: transpilador AST Python → Java y compilación real con `javac` (cuando el JDK está disponible).
- `tests/test_phase10_flows.py`: migración Alembic completa (incluyendo `issued_certificates`), certificados verificables (`IssuedCertificate` + `/certificado/verificar/<codigo>`), flujos de cuenta de estudiante (`/cuenta`), herramientas docentes (auditoría acotada, edición de sección, desvinculación sin suspensión, resultados detallados), administración Super Admin (alta docente, cambio de rol, desbloqueo, filtro/exportación de auditoría CSV) e infraestructura.

---

## Certificados Verificables

Cuando un estudiante completa el 100% de las lecciones del curso, el sistema emite y persiste un registro en `IssuedCertificate` con un código no predecible basado en **UUIDv4 + HMAC-SHA256** (`PY2J-XXXXXXXX-XXXXXXXX-XXXXXXXX`).

- El mismo código aparece tanto en el certificado HTML (`/certificado`) como en el PDF descargable (`/certificado/pdf`).
- Cualquier tercero o institución puede validar su autenticidad en la ruta pública:

  ```text
  GET /certificado/verificar/<codigo>
  ```

- La página de verificación muestra únicamente el estado de validez, nombre de usuario del titular, curso completado, total de lecciones y fecha de emisión, sin exponer datos privados (correo electrónico, contraseñas ni códigos de sección).

---

## Despliegue en Producción (Vercel + Supabase)

1. **Base de datos en Supabase (PostgreSQL):**
   - Crea un proyecto en Supabase y copia la cadena del **Transaction / Session Pooler** (`DATABASE_URL`) con `sslmode=require`.
   - Ejecuta las migraciones contra la base de producción antes de abrir tráfico:
     ```bash
     DATABASE_URL="postgresql://..." flask --app app db upgrade
     DATABASE_URL="postgresql://..." flask --app app create-superadmin
     ```

2. **Configuración en Vercel:**
   - El archivo `vercel.json` utiliza el esquema moderno de Vercel con **Fluid Compute** (`"fluid": true`), enrutando `/static/*` directamente desde la CDN con cabeceras de caché antes del fallback a `/app.py`, y configurando `/sw.js` con `Service-Worker-Allowed: /`.
   - Configura las variables de entorno en **Vercel Project Settings → Environment Variables**:
     - Obligatorias: `SECRET_KEY` (≥ 32 caracteres), `DATABASE_URL`
     - Recomendadas: `GEMINI_API_KEY`, `APP_TIMEZONE`, `RESEND_API_KEY` (o variables `MAIL_*`), `TEACHER_SECRET_CODE`, `RATELIMIT_STORAGE_URI` (Redis en producción multi-instancia)
     - Seguridad: `ALLOW_DEMO_RESET=false`, `FLASK_DEBUG=false`
   - Realiza el despliegue conectando el repositorio Git o ejecutando `vercel --prod`.

---

## Seguridad y Accesibilidad

- **Seguridad:** protección CSRF global (`Flask-WTF`), cookies `HttpOnly` + `SameSite=Lax` + `Secure` en producción, Content Security Policy con `nonce` por petición, `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, hashing de contraseñas con Werkzeug, rate-limiting en login/registro/recuperación/Tutor IA, neutralización de inyección de fórmulas en CSV y bitácora persistente `AuditLog`.
- **Accesibilidad (WCAG 2.1 AA):** navegación completa por teclado (incluyendo radios `.sr-only`, reordenamiento con botones *Subir/Bajar*, botones semánticos en ejercicios y modales con trampa de foco), soporte para `prefers-reduced-motion`, contraste validado en modo claro/oscuro/alto contraste, controles de tamaño de texto y fuente apta para dislexia, y estados de carga en formularios.
