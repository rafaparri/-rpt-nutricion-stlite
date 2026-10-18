# -*- coding: utf-8 -*-
"""
pdf_designs.py
--------------
Módulo encargado de generar los documentos PDF de RPT (Recetario e Informe
de Planificación) con una identidad visual profesional y coherente con el
logo de la marca.

No necesitas tocar este archivo para nada del día a día: la app principal
(app.py) simplemente llama a las funciones de aquí.
"""

import os
# --- Compatibilidad navegador (stlite/Pyodide): fpdf2 importa HTTPSHandler,
# que no existe en ese entorno. Se crea uno vacío; la app no descarga imágenes.
import urllib.request as _ur
for _n in ("HTTPSHandler", "HTTPHandler", "ProxyHandler"):
    if not hasattr(_ur, _n):
        setattr(_ur, _n, type(_n, (), {"__init__": lambda self, *a, **k: None}))
from datetime import datetime, date
from fpdf import FPDF
from nutricion import calcular_bmr

# ----------------------------------------------------------------------
# RUTAS Y CONSTANTES DE MARCA
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
FONT_DIR = os.path.join(BASE_DIR, "fonts")

FONT_REGULAR = os.path.join(FONT_DIR, "Poppins-Regular.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FONT_MEDIUM = os.path.join(FONT_DIR, "Poppins-Medium.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "Poppins-Italic.ttf")

# Azul corporativo (nueva paleta de marca)
BRAND_BLUE = (10, 42, 107)
BRAND_BLUE_DARK = (6, 27, 66)
BRAND_BLUE_SOFT = (232, 240, 252)      # fondo suave para tarjetas
BRAND_BLUE_PALE = (243, 247, 253)      # fondo muy suave (franjas de tabla)
INK = (28, 34, 48)                       # casi negro, neutro
GRAY_TEXT = (100, 107, 125)
WHITE = (255, 255, 255)
LINE_GRAY = (222, 227, 235)

# Colores de categoría (chips) - tonos pastel elegantes, no "de comic"
CATEGORY_COLORS = {
    "Alto en Hidratos": (252, 231, 205),
    "Alto en Proteína": (213, 235, 218),
    "Alto en Grasas": (233, 229, 222),
    "Ligero": (219, 231, 245),
    "Equilibrado": (245, 238, 210),
}
CATEGORY_TEXT_COLORS = {
    "Alto en Hidratos": (154, 91, 16),
    "Alto en Proteína": (35, 105, 55),
    "Alto en Grasas": (92, 85, 71),
    "Ligero": (35, 82, 130),
    "Equilibrado": (133, 108, 15),
}


def _safe(text):
    """Convierte cualquier valor a texto seguro para el PDF (evita errores
    si llegan números, None, etc.)."""
    if text is None:
        return ""
    return str(text)


# ----------------------------------------------------------------------
# CLASE BASE DE PDF CON CABECERA / PIE DE PÁGINA DE MARCA
# ----------------------------------------------------------------------
class RPTDocument(FPDF):
    """PDF con la identidad de marca RPT ya integrada (fuente, colores,
    cabecera y pie de página automáticos)."""

    def __init__(self, orientation="P", subtitle_doc="", *args, **kwargs):
        super().__init__(orientation=orientation, unit="mm", format="A4", *args, **kwargs)
        self.subtitle_doc = subtitle_doc
        self.set_auto_page_break(auto=True, margin=18)
        self._register_fonts()
        self.set_margins(12, 12, 12)

    def _register_fonts(self):
        if os.path.exists(FONT_REGULAR):
            self.add_font("Poppins", "", FONT_REGULAR)
            self.add_font("Poppins", "B", FONT_BOLD)
            self.add_font("Poppins", "I", FONT_ITALIC)
            self.font_family_name = "Poppins"
        else:
            # Red de seguridad por si algún día faltan las fuentes
            self.font_family_name = "Helvetica"

    def header(self):
        # Franja verde superior de marca
        band_h = 24
        self.set_fill_color(*BRAND_BLUE)
        self.rect(0, 0, self.w, band_h, "F")

        # Logo (versión sobre fondo blanco, se coloca en un pequeño
        # recuadro blanco redondeado a la izquierda para que resalte)
        if os.path.exists(LOGO_PATH):
            logo_size = 17
            self.set_fill_color(*WHITE)
            self.ellipse(9, (band_h - logo_size) / 2 - 1.5, logo_size + 3, logo_size + 3, "F")
            self.image(LOGO_PATH, x=10.5, y=(band_h - logo_size) / 2, w=logo_size, h=logo_size)
            text_x = 32
        else:
            text_x = 12

        self.set_xy(text_x, 4.5)
        self.set_text_color(*WHITE)
        self.set_font(self.font_family_name, "B", 14)
        self.cell(0, 7, "RPT  RAW POWER TRAINING", ln=1)
        self.set_xy(text_x, 12.5)
        self.set_font(self.font_family_name, "", 9.5)
        self.set_text_color(220, 235, 227)
        self.cell(0, 6, _safe(self.subtitle_doc), ln=1)

        self.set_y(band_h + 8)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*LINE_GRAY)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.set_font(self.font_family_name, "", 8)
        self.set_text_color(*GRAY_TEXT)
        self.set_y(-11)
        fecha = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 8, f"RPT · Generado el {fecha}", align="L")
        self.set_y(-11)
        self.cell(0, 8, f"Página {self.page_no()}", align="R")

    # ---------- utilidades de dibujo reutilizables ----------
    def section_title(self, text, size=12):
        self.set_font(self.font_family_name, "B", size)
        self.set_text_color(*BRAND_BLUE_DARK)
        self.cell(0, 8, _safe(text), ln=1)
        y = self.get_y() + 0.5
        self.set_draw_color(*BRAND_BLUE)
        self.set_line_width(0.6)
        self.line(self.l_margin, y, self.l_margin + 26, y)
        self.set_line_width(0.2)
        self.ln(4)
        self.set_text_color(*INK)

    def chip(self, text, x, y, fill_rgb, text_rgb, font_size=8, h=6, pad=3):
        self.set_font(self.font_family_name, "B", font_size)
        w = self.get_string_width(text) + pad * 2
        self.set_xy(x, y)
        self.set_fill_color(*fill_rgb)
        self.set_text_color(*text_rgb)
        self.cell(w, h, _safe(text), fill=True, align="C")
        self.set_text_color(*INK)
        return w


# ----------------------------------------------------------------------
# ANÁLISIS · funciones que generan el criterio del informe
# ----------------------------------------------------------------------
def _dias_hasta(fecha_competicion):
    """Devuelve los días que faltan hasta la fecha de competición (puede
    ser negativo si ya ha pasado). Admite date, datetime o texto ISO."""
    if fecha_competicion is None or fecha_competicion == "":
        return None
    if isinstance(fecha_competicion, datetime):
        fecha = fecha_competicion.date()
    elif isinstance(fecha_competicion, date):
        fecha = fecha_competicion
    else:
        try:
            fecha = datetime.strptime(str(fecha_competicion)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return (fecha - date.today()).days


def _texto_fase_por_dias(dias):
    """Traduce el tiempo restante en un consejo práctico y accionable."""
    if dias is None:
        return ("No se ha indicado fecha de competición, así que este informe "
                "se centra en mantener una base nutricional sólida y sostenible.")
    if dias < 0:
        return ("La fecha marcada ya ha pasado. Si ha habido competición, es un buen "
                "momento para revisar qué funcionó y reiniciar la planificación de cara "
                "al siguiente objetivo.")
    if dias == 0:
        return "¡Es hoy! Prioriza platos ligeros y de fácil digestión, bien conocidos, sin experimentos de última hora."
    if dias <= 3:
        return ("Últimos días: evita cualquier alimento o receta nueva, prioriza la digestión "
                "ligera, la hidratación y el descanso. No es momento de déficit ni de probar platos nuevos.")
    if dias <= 14:
        return ("Fase de puesta a punto (peaking): mantén el peso de categoría estable, evita "
                "cambios bruscos en la dieta y prioriza la recuperación entre sesiones.")
    if dias <= 28:
        return ("Recta final (3-4 semanas): buen momento para ir afinando el peso de categoría "
                "de forma progresiva y consolidar los platos que mejor te sientan antes de dejar "
                "de experimentar.")
    if dias <= 84:
        return ("Fase específica (1-3 meses): margen suficiente para ajustar composición corporal "
                "y probar variaciones del menú antes de fijar la estrategia final.")
    return ("Fase general: con más de 3 meses por delante hay margen amplio para trabajar "
            "volumen de entrenamiento y construir hábitos alimentarios sólidos sin prisa.")


def _generar_explicacion_semana(menu):
    """Construye un texto explicando el criterio nutricional usado para
    montar la semana, a partir de la intensidad real de cada día."""
    dias_alta = [d for d, v in menu.items() if v.get('intensidad') == 'Alta']
    dias_descanso = [d for d, v in menu.items() if v.get('intensidad') == 'Descanso']
    dias_media = [d for d, v in menu.items() if v.get('intensidad') == 'Media']

    partes = []
    if dias_alta:
        ejemplos = ", ".join(f"{menu[d]['almuerzo'].get('Plato','')} ({d})" for d in dias_alta[:2])
        plural = "días" if len(dias_alta) > 1 else "día"
        partes.append(
            f"Los {plural} de mayor exigencia física ({', '.join(dias_alta)}) incorporan platos "
            f"altos en hidratos como {ejemplos}, para maximizar el glucógeno disponible antes y "
            f"después del esfuerzo."
        )
    if dias_descanso:
        ejemplos = ", ".join(f"{menu[d]['cena'].get('Plato','')} ({d})" for d in dias_descanso[:2])
        plural = "días" if len(dias_descanso) > 1 else "día"
        partes.append(
            f"En los {plural} de descanso o técnica ({', '.join(dias_descanso)}) se priorizan "
            f"opciones ligeras o altas en proteína como {ejemplos}, para favorecer la recuperación "
            f"sin generar un superávit calórico innecesario."
        )
    if dias_media:
        partes.append(
            f"El resto de la semana ({', '.join(dias_media)}) mantiene un reparto equilibrado de "
            f"macronutrientes, sosteniendo el volumen general de entrenamiento sin comprometer la "
            f"composición corporal."
        )
    partes.append(
        "Estos criterios son orientativos y no una norma fija: cualquier plato se puede "
        "sustituir por otro de su misma categoría sin alterar el objetivo nutricional del día, "
        "o cambiar de categoría de forma consciente si buscas un efecto distinto (por ejemplo, "
        "más energía disponible para entrenar o un menor aporte calórico ese día)."
    )
    return " ".join(partes)


def _delta_texto(actual, objetivo):
    try:
        actual = float(actual)
        objetivo = float(objetivo)
    except (TypeError, ValueError):
        return "s/d"
    diff = objetivo - actual
    if abs(diff) < 0.05:
        return "Objetivo alcanzado"
    signo = "+" if diff > 0 else ""
    return f"{signo}{diff:.1f} kg por lograr"


def _kcal_total_dia(d):
    """Kcal totales reales de un día: almuerzo + cena más las kcal ya
    calculadas para desayuno, media mañana y merienda (si el menú viene
    de una versión antigua sin esos datos, se usa una estimación)."""
    return (
        d["almuerzo"].get("Kcal", 0) + d["cena"].get("Kcal", 0)
        + d.get("desayuno_kcal", 200) + d.get("media_manana_kcal", 150)
        + d.get("merienda_kcal", 150)
    )


# ----------------------------------------------------------------------
# PDF 1 · RECETARIO
# ----------------------------------------------------------------------
def generar_pdf_recetas(inventario_df, platos_nombres, output_path):
    """Genera un recetario en PDF con las recetas seleccionadas.

    inventario_df : DataFrame con toda la base de datos de platos
    platos_nombres: lista de nombres de platos a incluir
    output_path   : ruta donde se guardará el PDF
    """
    pdf = RPTDocument(orientation="P", subtitle_doc="Recetario de entrenamiento")
    pdf.add_page()

    pdf.set_font(pdf.font_family_name, "", 10.5)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.multi_cell(0, 5.5,
        "Selección de recetas preparada para acompañar tu planificación de "
        "entrenamiento. Cada ficha incluye macronutrientes, ingredientes y "
        "modo de preparación.")
    pdf.ln(4)

    for nombre in platos_nombres:
        filas = inventario_df[inventario_df["Plato"] == nombre]
        if filas.empty:
            continue
        plato = filas.iloc[0]

        # Reserva de espacio: si no cabe la ficha completa, salta de página
        if pdf.get_y() > pdf.h - 70:
            pdf.add_page()

        y_top = pdf.get_y()
        card_x = pdf.l_margin
        card_w = pdf.w - pdf.l_margin - pdf.r_margin

        # --- Cabecera de la ficha ---
        pdf.set_fill_color(*BRAND_BLUE_SOFT)
        pdf.rect(card_x, y_top, card_w, 12, "F")
        pdf.set_xy(card_x + 4, y_top + 1.5)
        pdf.set_font(pdf.font_family_name, "B", 13)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(card_w - 8, 9, _safe(plato["Plato"]).upper())

        pdf.set_y(y_top + 14)

        # --- Chips: apto para / categoría ---
        chip_x = card_x + 4
        chip_y = pdf.get_y()
        cat = plato.get("Categoria", "Equilibrado")
        fill = CATEGORY_COLORS.get(cat, (235, 235, 235))
        text_c = CATEGORY_TEXT_COLORS.get(cat, (90, 90, 90))
        w1 = pdf.chip(cat, chip_x, chip_y, fill, text_c)
        w2 = pdf.chip(f"Apto para: {plato.get('Utilizar_en', '')}",
                      chip_x + w1 + 3, chip_y, (236, 236, 236), (90, 90, 90))
        pdf.set_y(chip_y + 9)

        # --- Macros en línea ---
        pdf.set_x(card_x + 4)
        pdf.set_font(pdf.font_family_name, "B", 9.5)
        pdf.set_text_color(*INK)
        macro_txt = (f"{plato.get('Kcal', 0)} kcal    "
                     f"P {plato.get('Proteina_g', 0)} g    "
                     f"C {plato.get('Carbos_g', 0)} g    "
                     f"G {plato.get('Grasas_g', 0)} g")
        pdf.cell(0, 6, macro_txt, ln=1)
        pdf.ln(1)

        # --- Ingredientes ---
        pdf.set_x(card_x + 4)
        pdf.set_font(pdf.font_family_name, "B", 10)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(0, 6, "INGREDIENTES", ln=1)
        pdf.set_x(card_x + 4)
        pdf.set_font(pdf.font_family_name, "", 10)
        pdf.set_text_color(*INK)
        pdf.multi_cell(card_w - 8, 5.6, _safe(plato.get("Ingredientes", "")))
        pdf.ln(1.5)

        # --- Preparación ---
        pdf.set_x(card_x + 4)
        pdf.set_font(pdf.font_family_name, "B", 10)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(0, 6, "PREPARACIÓN", ln=1)
        pdf.set_x(card_x + 4)
        pdf.set_font(pdf.font_family_name, "", 10)
        pdf.set_text_color(*INK)
        pdf.multi_cell(card_w - 8, 5.6, _safe(plato.get("Preparacion", "")))

        # --- Borde de la ficha completo ---
        y_bottom = pdf.get_y() + 3
        pdf.set_draw_color(*LINE_GRAY)
        pdf.rect(card_x, y_top, card_w, y_bottom - y_top)
        pdf.set_y(y_bottom + 6)

    pdf.output(output_path)
    return output_path


# ----------------------------------------------------------------------
# PDF 2 · INFORME DE PLANIFICACIÓN PROFESIONAL
# ----------------------------------------------------------------------
def generar_informe_profesional(menu, perfil, output_path, historial=None, nota_reutilizacion=None):
    """Genera el informe de planificación semanal (apaisado A4), con
    secciones ampliadas para poder tomar decisiones sobre el menú con
    criterio: punto actual, tiempo hasta la competición, la planificación
    semanal, por qué se ha compuesto así la semana, y la evolución de kcal.

    menu     : dict {dia: {...}} tal como lo usa la app
    perfil   : dict con los datos del atleta
    historial: lista opcional de semanas generadas previamente, cada una
               como {'fecha': datetime, 'total_kcal': int, 'media_kcal': float}
    nota_reutilizacion: si el menú se ha cargado de otro atleta y se está
               reutilizando tal cual, un texto de aviso para incluir al
               final del informe.
    """
    historial = historial or []
    pdf = RPTDocument(orientation="L", subtitle_doc="Informe de planificación nutricional")
    pdf.add_page()

    # ================= PÁGINA 1: IDENTIDAD + PUNTO ACTUAL + TIEMPO =================
    pdf.set_font(pdf.font_family_name, "B", 16)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, _safe(perfil.get("nombre", "")), ln=1)
    pdf.set_font(pdf.font_family_name, "", 10.5)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(0, 6,
        f"Categoría: {perfil.get('categoria', '')}    ·    "
        f"Peso actual: {perfil.get('peso', '')} kg    ·    "
        f"Fase: {perfil.get('objetivo_fase', '')}", ln=1)
    pdf.ln(3)

    # ---------- PUNTO ACTUAL ----------
    pdf.section_title("PUNTO ACTUAL")
    card_x, card_y = pdf.l_margin, pdf.get_y()
    card_w = (pdf.w - pdf.l_margin - pdf.r_margin - 8) / 2
    card_h = 34
    pdf.set_fill_color(*BRAND_BLUE_SOFT)
    pdf.rect(card_x, card_y, card_w, card_h, "F")
    pdf.set_draw_color(*BRAND_BLUE)
    pdf.set_line_width(0.5)
    pdf.rect(card_x, card_y, card_w, card_h)
    pdf.set_line_width(0.2)

    marcas = [
        ("ARRANCADA", perfil.get("rm_arrancada", ""), perfil.get("obj_arrancada", "")),
        ("DOS TIEMPOS", perfil.get("rm_dos_tiempos", ""), perfil.get("obj_dos_tiempos", "")),
    ]
    sub_w = card_w / 2
    for i, (label, actual, objetivo) in enumerate(marcas):
        x = card_x + i * sub_w
        pdf.set_xy(x + 5, card_y + 4)
        pdf.set_font(pdf.font_family_name, "B", 8)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(sub_w - 8, 5, label)
        pdf.set_xy(x + 5, card_y + 10)
        pdf.set_font(pdf.font_family_name, "B", 14)
        pdf.set_text_color(*INK)
        pdf.cell(sub_w - 8, 8, f"{actual} kg  »  {objetivo} kg")
        pdf.set_xy(x + 5, card_y + 20)
        pdf.set_font(pdf.font_family_name, "", 8.5)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.cell(sub_w - 8, 5, _delta_texto(actual, objetivo))
        if i == 0:
            pdf.set_draw_color(*LINE_GRAY)
            pdf.line(x + sub_w, card_y + 4, x + sub_w, card_y + card_h - 4)

    pdf.set_xy(card_x + 5, card_y + card_h - 8)
    pdf.set_font(pdf.font_family_name, "", 7.5)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(card_w - 10, 4,
        f"SQ Frontal {perfil.get('rm_sentadilla_delantera','')} kg  ·  "
        f"SQ Trasera {perfil.get('rm_sentadilla_trasera','')} kg")

    # ---------- TIEMPO HASTA LA COMPETICIÓN (tarjeta hermana, a la derecha) ----------
    card2_x = card_x + card_w + 8
    pdf.set_fill_color(*BRAND_BLUE)
    pdf.rect(card2_x, card_y, card_w, card_h, "F")

    dias_restantes = _dias_hasta(perfil.get("fecha_competicion"))
    if dias_restantes is None:
        texto_dias = "Sin fecha"
        texto_semanas = ""
    elif dias_restantes < 0:
        texto_dias = "Ya pasada"
        texto_semanas = ""
    else:
        texto_dias = f"{dias_restantes} días"
        texto_semanas = f"({dias_restantes // 7} semanas)"

    pdf.set_xy(card2_x + 5, card_y + 4)
    pdf.set_font(pdf.font_family_name, "B", 8)
    pdf.set_text_color(220, 235, 227)
    pdf.cell(card_w - 10, 5, f"TIEMPO HASTA {_safe(perfil.get('competicion','LA COMPETICIÓN')).upper()}")
    pdf.set_xy(card2_x + 5, card_y + 10)
    pdf.set_font(pdf.font_family_name, "B", 20)
    pdf.set_text_color(*WHITE)
    pdf.cell(card_w - 10, 10, f"{texto_dias}  {texto_semanas}")
    pdf.set_xy(card2_x + 5, card_y + 22)
    pdf.set_font(pdf.font_family_name, "", 8.2)
    pdf.set_text_color(220, 235, 227)
    fecha_txt = _safe(perfil.get("fecha_competicion", ""))
    pdf.multi_cell(card_w - 10, 4.3, f"Fecha prevista: {fecha_txt}")

    pdf.set_y(card_y + card_h + 6)

    # ---------- Necesidades calóricas calculadas (transparencia del cálculo) ----------
    bmr_pdf = calcular_bmr(perfil.get("peso"), perfil.get("altura_cm"), perfil.get("edad"), perfil.get("sexo"))
    media_semana_pdf = None
    if menu:
        totales_dia = [_kcal_total_dia(d) for d in menu.values()]
        if totales_dia:
            media_semana_pdf = sum(totales_dia) / len(totales_dia)

    y_bmr = pdf.get_y()
    pdf.set_fill_color(*BRAND_BLUE_SOFT)
    pdf.rect(pdf.l_margin, y_bmr, pdf.w - pdf.l_margin - pdf.r_margin, 14, "F")
    pdf.set_xy(pdf.l_margin + 5, y_bmr + 2)
    pdf.set_font(pdf.font_family_name, "B", 8)
    pdf.set_text_color(*BRAND_BLUE_DARK)
    texto_bmr = f"METABOLISMO BASAL ≈ {round(bmr_pdf)} KCAL"
    if media_semana_pdf:
        texto_bmr += f"    ·    OBJETIVO MEDIO DE ESTA SEMANA ≈ {round(media_semana_pdf)} KCAL/DÍA"
    pdf.cell(0, 5, texto_bmr, ln=1)
    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font(pdf.font_family_name, "", 7.8)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(0, 4.5,
        "Calculado con la fórmula de Mifflin-St Jeor a partir de peso, altura, edad y sexo, "
        "y ajustado según la intensidad de cada día y la fase actual.")
    pdf.set_y(y_bmr + 14 + 4)

    # ---------- Consejo de fase (debajo de las dos tarjetas) ----------
    pdf.set_fill_color(*BRAND_BLUE_PALE)
    consejo = _texto_fase_por_dias(dias_restantes)
    y_consejo = pdf.get_y()
    pdf.rect(pdf.l_margin, y_consejo, pdf.w - pdf.l_margin - pdf.r_margin, 16, "F")
    pdf.set_xy(pdf.l_margin + 5, y_consejo + 2.5)
    pdf.set_font(pdf.font_family_name, "B", 8.5)
    pdf.set_text_color(*BRAND_BLUE_DARK)
    pdf.cell(0, 5, "CRITERIO PARA ESTA FASE", ln=1)
    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font(pdf.font_family_name, "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 10, 4.6, consejo)

    # ================= PÁGINA 2: PLANIFICACIÓN SEMANAL =================
    pdf.add_page()
    pdf.section_title("PLANIFICACIÓN SEMANAL")

    headers = ["DÍA", "DESAYUNO", "MEDIA MAÑANA", "ALMUERZO", "MERIENDA", "CENA", "KCAL"]
    anchos = [20, 34, 34, 60, 34, 60, 17]
    row_h = 23

    def draw_header_row():
        pdf.set_font(pdf.font_family_name, "B", 9)
        pdf.set_fill_color(*BRAND_BLUE)
        pdf.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            pdf.cell(anchos[i], 9, h, border=0, fill=True, align="C")
        pdf.ln()

    draw_header_row()

    dias = list(menu.items())
    for idx, (dia, d) in enumerate(dias):
        if pdf.get_y() + row_h > pdf.h - 20:
            pdf.add_page()
            pdf.section_title("PLANIFICACIÓN SEMANAL (continuación)")
            draw_header_row()

        fila_fill = BRAND_BLUE_PALE if idx % 2 == 0 else WHITE
        pdf.set_fill_color(*fila_fill)
        pdf.set_draw_color(*LINE_GRAY)

        pdf.set_font(pdf.font_family_name, "B", 9.5)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(anchos[0], row_h, _safe(dia).upper(), border="B", fill=True, align="C")

        _draw_texto_cell(pdf, anchos[1], row_h, d["desayuno"], fila_fill)
        _draw_texto_cell(pdf, anchos[2], row_h, d["media_manana"], fila_fill)

        _draw_menu_cell(pdf, anchos[3], row_h, d["almuerzo"], fila_fill)
        _draw_texto_cell(pdf, anchos[4], row_h, d["merienda"], fila_fill)
        _draw_menu_cell(pdf, anchos[5], row_h, d["cena"], fila_fill)

        kcal_total = _kcal_total_dia(d)
        pdf.set_font(pdf.font_family_name, "B", 10)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.cell(anchos[6], row_h, str(kcal_total), border="B", fill=True, align="C")
        pdf.ln()

    # ================= PÁGINA 3: CRITERIO + EVOLUCIÓN =================
    pdf.add_page()

    # ---------- Leyenda de categorías ----------
    pdf.set_font(pdf.font_family_name, "I", 8.5)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(0, 5, "Leyenda de categorías nutricionales:", ln=1)
    x = pdf.l_margin
    y = pdf.get_y()
    for cat, fill in CATEGORY_COLORS.items():
        w = pdf.chip(cat, x, y, fill, CATEGORY_TEXT_COLORS.get(cat, (80, 80, 80)), font_size=7.5, h=5.5, pad=2.5)
        x += w + 3
    pdf.set_y(y + 10)

    pdf.section_title("EXPLICACIÓN DEL POR QUÉ DE LA COMPOSICIÓN DE LA SEMANA")
    pdf.set_font(pdf.font_family_name, "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5.2, _generar_explicacion_semana(menu))
    pdf.ln(6)

    pdf.add_page()
    pdf.section_title("EVOLUCIÓN DE LOS MENÚS")
    _dibujar_evolucion(pdf, menu, historial)

    if nota_reutilizacion:
        pdf.ln(8)
        y_nota = pdf.get_y()
        pdf.set_fill_color(253, 236, 200)  # ambar suave, mismo tono que el aviso "kcal-warn" de la app
        pdf.rect(pdf.l_margin, y_nota, pdf.w - pdf.l_margin - pdf.r_margin, 22, "F")
        pdf.set_xy(pdf.l_margin + 5, y_nota + 3)
        pdf.set_font(pdf.font_family_name, "B", 9)
        pdf.set_text_color(146, 101, 11)
        pdf.cell(0, 5, "⚠ AVISO: MENÚ REUTILIZADO DE OTRO ATLETA", ln=1)
        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font(pdf.font_family_name, "", 8.8)
        pdf.set_text_color(*INK)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 10, 4.6, _safe(nota_reutilizacion))

    pdf.output(output_path)
    return output_path


def _dibujar_evolucion(pdf, menu, historial):
    """Dibuja dos gráficos sencillos: la evolución de kcal día a día de la
    semana actual, y (si hay datos) la evolución de la media diaria a lo
    largo de las semanas generadas anteriormente."""
    ancho_total = pdf.w - pdf.l_margin - pdf.r_margin

    # ---------- Gráfico 1: kcal por día de la semana actual ----------
    pdf.set_font(pdf.font_family_name, "B", 10)
    pdf.set_text_color(*BRAND_BLUE_DARK)
    pdf.cell(0, 6, "Kcal por día · semana actual", ln=1)
    pdf.ln(1)

    dias = list(menu.items())
    valores = [_kcal_total_dia(d) for _, d in dias]
    _grafico_barras(pdf, [dia[:3].upper() for dia, _ in dias], valores, ancho_total, alto=32)
    pdf.ln(8)

    # ---------- Gráfico 2: evolución entre semanas generadas ----------
    if pdf.get_y() + 45 > pdf.h - 20:
        pdf.add_page()
    pdf.set_font(pdf.font_family_name, "B", 10)
    pdf.set_text_color(*BRAND_BLUE_DARK)
    pdf.cell(0, 6, "Media diaria de kcal · semanas generadas", ln=1)
    pdf.ln(1)

    if historial and len(historial) >= 2:
        etiquetas = [f"S{i+1}" for i in range(len(historial))]
        medias = [round(h.get("media_kcal", 0)) for h in historial]
        _grafico_barras(pdf, etiquetas, medias, ancho_total, alto=32)
        pdf.ln(3)
        pdf.set_font(pdf.font_family_name, "", 8.5)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.multi_cell(ancho_total, 4.6,
            "Cada barra corresponde a una generación de menú semanal, en el orden en que se "
            "fueron creando. Úsalo para comprobar si la media calórica se mantiene estable o "
            "se está desviando de la fase actual, y ajusta los platos con ese criterio.")
    else:
        pdf.set_fill_color(*BRAND_BLUE_PALE)
        pdf.rect(pdf.l_margin, pdf.get_y(), ancho_total, 16, "F")
        pdf.set_xy(pdf.l_margin + 5, pdf.get_y() + 5)
        pdf.set_font(pdf.font_family_name, "", 9)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.cell(ancho_total - 10, 5,
            "Todavía no hay suficientes semanas generadas para mostrar una evolución. "
            "Este gráfico se irá completando cada vez que generes un nuevo menú semanal.")
        pdf.set_y(pdf.get_y() + 16)


def _grafico_barras(pdf, etiquetas, valores, ancho_total, alto=32):
    """Dibuja un gráfico de barras muy simple usando primitivas de fpdf2."""
    if not valores:
        return
    if pdf.get_y() + alto + 12 > pdf.h - 20:
        pdf.add_page()
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    n = len(valores)
    gap = 3
    bar_w = (ancho_total - gap * (n - 1)) / n
    max_val = max(valores) if max(valores) > 0 else 1

    pdf.set_draw_color(*LINE_GRAY)
    pdf.line(x0, y0 + alto, x0 + ancho_total, y0 + alto)

    for i, val in enumerate(valores):
        h = (val / max_val) * (alto - 10) if max_val else 0
        x = x0 + i * (bar_w + gap)
        y = y0 + alto - h
        pdf.set_fill_color(*BRAND_BLUE)
        pdf.rect(x, y, bar_w, h, "F")

        pdf.set_font(pdf.font_family_name, "B", 7)
        pdf.set_text_color(*BRAND_BLUE_DARK)
        pdf.set_xy(x, y - 5)
        pdf.cell(bar_w, 4, str(val), align="C")

        pdf.set_font(pdf.font_family_name, "", 7)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.set_xy(x, y0 + alto + 1.5)
        pdf.cell(bar_w, 4, _safe(etiquetas[i]), align="C")

    pdf.set_y(y0 + alto + 7)


def _acortar_con_elipsis(texto, limite):
    if len(texto) <= limite:
        return texto
    return texto[:limite - 1].rstrip() + "…"


def _draw_texto_cell(pdf, width, height, texto, fila_fill):
    """Dibuja una celda de texto simple (desayuno, media mañana, merienda)
    con salto de línea automático, en vez de cortar el texto sin más si
    no cabe en una sola línea. Se limita a 60 caracteres (con puntos
    suspensivos) solo como margen de seguridad ante nombres extremos, para
    que nunca llegue a solaparse con la fila siguiente."""
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*fila_fill)
    pdf.set_draw_color(*LINE_GRAY)
    pdf.cell(width, height, "", border="B", fill=True)

    pdf.set_xy(x + 2, y + 3)
    pdf.set_font(pdf.font_family_name, "", 8.0)
    pdf.set_text_color(*INK)
    pdf.multi_cell(width - 4, 3.8, _acortar_con_elipsis(_safe(texto), 60), align="C")

    pdf.set_xy(x + width, y)


def _draw_menu_cell(pdf, width, height, plato, fila_fill):
    """Dibuja una celda de la tabla con el nombre del plato y un pequeño
    indicador de color según su categoría nutricional."""
    x, y = pdf.get_x(), pdf.get_y()
    cat = plato.get("Categoria", "Equilibrado")
    color = CATEGORY_COLORS.get(cat, fila_fill)

    pdf.set_fill_color(*fila_fill)
    pdf.set_draw_color(*LINE_GRAY)
    pdf.cell(width, height, "", border="B", fill=True)

    # barra de color a la izquierda de la celda (indicador de categoría)
    pdf.set_fill_color(*color)
    pdf.rect(x, y + 2, 2.2, height - 4, "F")

    pdf.set_xy(x + 4, y + 3)
    pdf.set_font(pdf.font_family_name, "B", 8.6)
    pdf.set_text_color(35, 40, 38)
    nombre = _safe(plato.get("Plato", ""))
    pdf.multi_cell(width - 6, 4.2, _acortar_con_elipsis(nombre, 80), align="L")

    pdf.set_xy(x + 4, y + height - 6.5)
    pdf.set_font(pdf.font_family_name, "", 7)
    pdf.set_text_color(*GRAY_TEXT)
    pdf.cell(width - 6, 4, f"{plato.get('Kcal', 0)} kcal", align="L")

    pdf.set_xy(x + width, y)


# ----------------------------------------------------------------------
# PDF 3 · LISTA DE LA COMPRA
# ----------------------------------------------------------------------
def generar_pdf_lista_compra(lista_compra, output_path, subtitulo=""):
    """Genera un PDF con la lista de la compra consolidada de la semana,
    con casillas para ir marcando lo que ya se ha comprado.

    lista_compra: dict con 'principales' (lista de {'nombre','cantidad_texto'}),
                  'al_gusto' (lista de nombres) y 'fijos' (lista de nombres).
    """
    pdf = RPTDocument(orientation="P", subtitle_doc="Lista de la compra semanal")
    pdf.add_page()

    if subtitulo:
        pdf.set_font(pdf.font_family_name, "", 10.5)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.cell(0, 6, _safe(subtitulo), ln=1)
        pdf.ln(2)

    def _casilla(x, y, tamano=4.2):
        pdf.set_draw_color(*BRAND_BLUE)
        pdf.set_line_width(0.4)
        pdf.rect(x, y, tamano, tamano)
        pdf.set_line_width(0.2)

    principales = lista_compra.get("principales", [])
    if principales:
        pdf.section_title(f"PARA COMPRAR ({len(principales)})")
        col_w = (pdf.w - pdf.l_margin - pdf.r_margin - 8) / 2
        fila_h = 9
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        max_y = pdf.h - 20

        for i, item in enumerate(principales):
            columna = i % 2
            x = x0 + columna * (col_w + 8)
            if columna == 0 and i > 0:
                y0 += fila_h
            if y0 + fila_h > max_y:
                pdf.add_page()
                pdf.section_title("PARA COMPRAR (continuación)")
                y0 = pdf.get_y()

            _casilla(x, y0 + 1.8)
            pdf.set_xy(x + 7, y0)
            pdf.set_font(pdf.font_family_name, "B", 9.5)
            pdf.set_text_color(*INK)
            pdf.cell(col_w - 30, fila_h, _safe(item["nombre"])[:28])
            pdf.set_font(pdf.font_family_name, "", 9)
            pdf.set_text_color(*GRAY_TEXT)
            pdf.cell(22, fila_h, _safe(item["cantidad_texto"]), align="R")

        pdf.set_y(y0 + fila_h + 6)

    al_gusto = lista_compra.get("al_gusto", [])
    if al_gusto:
        pdf.section_title("AL GUSTO (revisa si ya tienes)")
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        for i, nombre in enumerate(al_gusto):
            x = x0 + (i % 3) * 60
            if i > 0 and i % 3 == 0:
                y0 += 8
            _casilla(x, y0 + 1.5, tamano=3.6)
            pdf.set_xy(x + 6, y0)
            pdf.set_font(pdf.font_family_name, "", 9.5)
            pdf.set_text_color(*INK)
            pdf.cell(52, 7, _safe(nombre))
        pdf.set_y(y0 + 12)

    fijos = lista_compra.get("fijos", [])
    if fijos:
        pdf.section_title("TAMBIÉN NECESITARÁS (desayunos y meriendas)")
        pdf.set_font(pdf.font_family_name, "", 9.5)
        pdf.set_text_color(*INK)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5.5, _safe(", ".join(fijos)))

    if not principales and not al_gusto and not fijos:
        pdf.set_font(pdf.font_family_name, "", 10)
        pdf.set_text_color(*GRAY_TEXT)
        pdf.cell(0, 8, "No se han encontrado ingredientes en el menú actual.", ln=1)

    pdf.output(output_path)
    return output_path
