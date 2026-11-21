"""
Generación del reporte PDF del Panel de Administrador.

Usa fpdf2 (Python puro, sin dependencias nativas) para que funcione igual en
local y en el entorno serverless de Vercel.
"""

from datetime import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

from content_loader import LEVEL_TITLES, get_level_title

# Paleta sobria, apta para impresión
COLOR_PRIMARY = (30, 58, 95)      # azul oscuro (encabezados)
COLOR_ACCENT = (55, 118, 171)     # azul Python
COLOR_ROW_ALT = (242, 245, 249)   # gris muy claro para filas alternas
COLOR_TEXT = (33, 37, 41)
COLOR_MUTED = (108, 117, 125)
COLOR_BORDER = (206, 212, 218)
COLOR_GOLD = (197, 155, 39)       # dorado discreto para diploma


def _latin1(text):
    """Las fuentes estándar de PDF usan Latin-1; normaliza símbolos frecuentes y reemplaza el resto."""
    s = str(text if text is not None else "")
    s = (
        s.replace("\u2192", "->")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return s.encode("latin-1", "replace").decode("latin-1")


class AdminReportPDF(FPDF):
    def __init__(self, site_title, generated_at, generated_by):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.site_title = site_title
        self.generated_at = generated_at
        self.generated_by = generated_by
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)
        self.set_title(f"Reporte de estudiantes - {site_title}")
        self.set_author(site_title)
        self.set_creator(site_title)

    def header(self):
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, self.w, 22, style="F")
        self.set_xy(15, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 6, _latin1(f"{self.site_title} - Reporte de Estudiantes"), new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(
            0, 5,
            _latin1(f"Generado el {self.generated_at.strftime('%d/%m/%Y %H:%M')} por {self.generated_by}"),
            new_x="LMARGIN", new_y="NEXT",
        )
        self.set_y(28)
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*COLOR_BORDER)
        self.set_text_color(*COLOR_TEXT)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*COLOR_BORDER)
        self.line(15, self.get_y() - 1, self.w - 15, self.get_y() - 1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_MUTED)
        self.cell(0, 6, _latin1(f"{self.site_title} - Reporte generado automáticamente"), align="L")
        self.cell(0, 6, f"Página {self.page_no()} de {{nb}}", align="R")

    # ---- bloques ----
    def section_title(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 8, _latin1(text), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*COLOR_ACCENT)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 60, self.get_y())
        self.set_line_width(0.2)
        self.set_draw_color(*COLOR_BORDER)
        self.ln(3)
        self.set_text_color(*COLOR_TEXT)

    def metric_cards(self, cards):
        """Dibuja tarjetas de métricas en una fila."""
        gap = 4
        n = len(cards)
        width = (self.w - 30 - gap * (n - 1)) / n
        height = 22
        y = self.get_y()
        for i, (label, value) in enumerate(cards):
            x = 15 + i * (width + gap)
            self.set_fill_color(*COLOR_ROW_ALT)
            self.set_draw_color(*COLOR_BORDER)
            self.rect(x, y, width, height, style="DF")
            self.set_fill_color(*COLOR_ACCENT)
            self.rect(x, y, 1.8, height, style="F")
            self.set_xy(x + 4, y + 3)
            self.set_font("Helvetica", "B", 15)
            self.set_text_color(*COLOR_PRIMARY)
            self.cell(width - 6, 9, _latin1(value))
            self.set_xy(x + 4, y + 13)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*COLOR_MUTED)
            self.cell(width - 6, 5, _latin1(label.upper()))
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*COLOR_BORDER)
        self.set_text_color(*COLOR_TEXT)
        self.set_y(y + height + 4)


def build_admin_report_pdf(students, metrics, site_title="Py2Java Edu", generated_by="Administrador"):
    """
    students: lista de dicts con username, level, title, total_xp, completed, progress_pct, streak
    metrics:  dict con total_students, avg_xp, total_completed, avg_progress_pct,
              total_course_lessons, active_streaks, level_distribution [(titulo, cantidad)]
    Devuelve los bytes del PDF.
    """
    pdf = AdminReportPDF(site_title, datetime.now(), generated_by)
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. Resumen general
    pdf.section_title("1. Resumen general de métricas")
    pdf.metric_cards([
        ("Estudiantes", str(metrics["total_students"])),
        ("XP promedio", f"{metrics['avg_xp']} XP"),
        ("Lecciones completas", str(metrics["total_completed"])),
        ("Progreso promedio", f"{metrics['avg_progress_pct']}%"),
    ])
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.multi_cell(
        0, 5,
        _latin1(
            f"El curso contiene {metrics['total_course_lessons']} lecciones. "
            f"Estudiantes con racha de estudio activa: {metrics['active_streaks']}. "
            "El progreso de cada estudiante se calcula como lecciones completadas / total de lecciones del curso."
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(*COLOR_TEXT)

    # 2. Distribución por nivel
    if metrics.get("level_distribution"):
        pdf.section_title("2. Distribución de estudiantes por nivel")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*COLOR_BORDER)
        heading = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=COLOR_PRIMARY)
        with pdf.table(
            col_widths=(110, 35, 35),
            text_align=("LEFT", "CENTER", "CENTER"),
            headings_style=heading,
            cell_fill_color=COLOR_ROW_ALT,
            cell_fill_mode="ROWS",
            borders_layout="HORIZONTAL_LINES",
            line_height=6,
            padding=1.5,
            width=180,
        ) as table:
            table.row(["Nivel / Título", "Estudiantes", "% del total"])
            total = max(1, metrics["total_students"])
            for title, count in metrics["level_distribution"]:
                table.row([_latin1(title), str(count), f"{round(count * 100 / total, 1)}%"])

    # 3. Detalle de estudiantes (encabezado repetido en cada página)
    if pdf.get_y() > 230:
        pdf.add_page()
    pdf.section_title("3. Detalle de estudiantes")
    if not students:
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "No hay estudiantes registrados.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(*COLOR_BORDER)
        heading = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=COLOR_PRIMARY)
        with pdf.table(
            col_widths=(8, 42, 52, 22, 36, 20),
            text_align=("CENTER", "LEFT", "LEFT", "RIGHT", "CENTER", "CENTER"),
            headings_style=heading,
            repeat_headings=1,
            cell_fill_color=COLOR_ROW_ALT,
            cell_fill_mode="ROWS",
            borders_layout="HORIZONTAL_LINES",
            line_height=6,
            padding=1.5,
            width=180,
        ) as table:
            table.row(["#", "Usuario", "Nivel", "XP total", "Progreso (lecciones)", "Racha"])
            for i, s in enumerate(students, start=1):
                lvl_title = s.get("title") or get_level_title(s.get("level", 1))
                table.row([
                    str(i),
                    _latin1(s["username"]),
                    _latin1(f"Lv.{s['level']} - {lvl_title}"),
                    f"{s['total_xp']} XP",
                    f"{s['completed']} / {metrics['total_course_lessons']} ({s['progress_pct']}%)",
                    f"{s['streak']} d",
                ])

    return bytes(pdf.output())


def build_certificate_pdf(
    username,
    category_name,
    category_id,
    user_id,
    total_lessons,
    completion_date,
    completion_year,
    site_title="Py2Java Edu",
):
    """
    Genera un certificado formal en PDF (A4 horizontal, 297 x 210 mm) para el estudiante.
    Devuelve los bytes del PDF.
    """
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_title(f"Certificado - {category_name} - {site_title}")
    pdf.set_author(site_title)
    pdf.set_creator(site_title)
    pdf.add_page()

    w, h = pdf.w, pdf.h  # 297 x 210 mm

    # Fondo suave marfil/blanco
    pdf.set_fill_color(252, 253, 255)
    pdf.rect(0, 0, w, h, style="F")

    # Banda superior e inferior sutil en el marco
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(2.2)
    pdf.rect(10, 10, w - 20, h - 20, style="D")

    pdf.set_draw_color(*COLOR_GOLD)
    pdf.set_line_width(0.6)
    pdf.rect(14, 14, w - 28, h - 28, style="D")

    # Esquinas decorativas
    corner = 10
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(1.2)
    for cx, cy, dx, dy in [
        (17, 17, corner, corner),
        (w - 17, 17, -corner, corner),
        (17, h - 17, corner, -corner),
        (w - 17, h - 17, -corner, -corner),
    ]:
        pdf.line(cx, cy, cx + dx, cy)
        pdf.line(cx, cy, cx, cy + dy)

    # Franja de cabecera institucional
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.rect(14, 14, w - 28, 22, style="F")
    pdf.set_xy(14, 18.5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(w - 28, 7, _latin1(site_title.upper()), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(210, 225, 240)
    pdf.cell(
        w - 28,
        5,
        _latin1("PLATAFORMA EDUCATIVA INTERACTIVA PYTHON -> JAVA"),
        align="C",
    )

    # Título del diploma
    pdf.set_xy(20, 46)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(w - 40, 11, _latin1("CERTIFICADO DE FINALIZACIÓN"), align="C")

    # Línea dorada decorativa
    pdf.set_draw_color(*COLOR_GOLD)
    pdf.set_line_width(0.9)
    pdf.line(w / 2 - 48, 60, w / 2 + 48, 60)

    # Texto de otorgamiento
    pdf.set_xy(20, 66)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(w - 40, 7, _latin1("Se certifica que"), align="C")

    # Nombre del estudiante
    pdf.set_xy(25, 76)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", "B", 30)
    pdf.cell(w - 50, 15, _latin1(username), align="C")

    # Subrayado fino bajo el nombre
    pdf.set_draw_color(*COLOR_BORDER)
    pdf.set_line_width(0.4)
    pdf.line(w / 2 - 75, 93, w / 2 + 75, 93)

    # Descripción del logro
    pdf.set_xy(30, 99)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(w - 60, 7, _latin1("ha completado satisfactoriamente el programa de formación"), align="C")

    # Módulo / categoría
    pdf.set_xy(30, 108)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.set_font("Helvetica", "B", 19)
    pdf.cell(w - 60, 10, _latin1(category_name), align="C")

    # Detalle de lecciones y fecha
    pdf.set_xy(30, 121)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.cell(
        w - 60,
        6,
        _latin1(f"Total acreditado: {total_lessons} lecciones completadas  |  Emitido el {completion_date}"),
        align="C",
    )

    # Sello central decorativo (círculo doble dorado/azul)
    cx, cy = w / 2, 154
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_draw_color(*COLOR_GOLD)
    pdf.set_line_width(1.2)
    pdf.circle(cx, cy, 13, style="DF")
    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.4)
    pdf.circle(cx, cy, 10.2, style="D")
    pdf.set_xy(cx - 10, cy - 4.5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(20, 4, "100%", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(cx - 10)
    pdf.set_font("Helvetica", "", 6)
    pdf.cell(20, 4, "APROBADO", align="C")

    # Firmas (izquierda y derecha)
    sig_y = 160
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(0.5)
    # Izquierda
    pdf.line(42, sig_y, 112, sig_y)
    pdf.set_xy(42, sig_y + 2)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(70, 5, _latin1(f"Plataforma {site_title}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(42)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(70, 4.5, _latin1("Dirección Académica"), align="C")

    # Derecha
    pdf.line(w - 112, sig_y, w - 42, sig_y)
    pdf.set_xy(w - 112, sig_y + 2)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(70, 5, _latin1("Coordinación del Curso"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(w - 112)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(70, 4.5, _latin1("Instructor / Administrador"), align="C")

    # Código de verificación al pie
    cert_code = f"CERT-{str(category_id).upper()}-{user_id}-{completion_year}"
    pdf.set_xy(20, h - 24)
    pdf.set_text_color(*COLOR_MUTED)
    pdf.set_font("Courier", "", 8)
    pdf.cell(w - 40, 5, _latin1(f"Código de verificación: {cert_code}"), align="C")

    return bytes(pdf.output())
