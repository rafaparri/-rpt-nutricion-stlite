import streamlit as st
import pandas as pd
import os
import base64
from datetime import date, datetime

from pdf_designs import generar_pdf_recetas, generar_informe_profesional, generar_pdf_lista_compra
from recipe_import import procesar_docx_a_plato, estimar_macros, categorizar, generar_lista_compra
import data_store as ds
from nutricion import calcular_bmr, calcular_objetivo_dia, repartir_comidas, calcular_objetivo_macros, repartir_macros_comidas, calcular_objetivo_hidratacion
import entrenamiento as ent
import busqueda_recetas
import federacion as fed

# ------------------------------------------------------------------
# RUTAS (funcionan sin importar desde dónde se lance la aplicación)
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.png")
OUTPUT_DIR = os.path.join(BASE_DIR, "informes_generados")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BRAND_BLUE = "#4FC3F7"
BRAND_BLUE_DARK = "#F5F7FF"
BRAND_BLUE_SOFT = "#1B2158"
BRAND_BLUE_ACCENT = "#22D3EE"
BG_PAGE = "#0B0E2E"
BG_CARD_ALT = "#1E2358"
BORDE_OSCURO = "#2E3470"
TEXT_MUTED = "#9AA3D4"
ACCENT_GREEN = "#00E5A0"
ACCENT_RED = "#FF3B5C"
ACCENT_YELLOW = "#FFC53D"
ACCENT_CIAN = "#22D3EE"

# Colores de categoría (coherentes con los del PDF)
CATEGORIAS = ["Alto en Hidratos", "Alto en Proteína", "Alto en Grasas", "Ligero", "Equilibrado"]
OPCIONES_UTILIZAR_EN = ["Desayuno", "Almuerzo", "Cena", "Almuerzo, Cena", "Desayuno, Almuerzo, Cena"]
CAT_BG = {
    "Alto en Hidratos": "#3D2A12", "Alto en Proteína": "#0F3323", "Alto en Grasas": "#2E2A22",
    "Ligero": "#122A44", "Equilibrado": "#332C0E",
}
CAT_TEXT = {
    "Alto en Hidratos": "#FFB454", "Alto en Proteína": "#00E5A0", "Alto en Grasas": "#D8CBB0",
    "Ligero": "#5FA8FF", "Equilibrado": "#FFC53D",
}
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
OPCIONES_FASE = ["Bajar de peso", "Mantener categoría", "Subir de peso", "Ganar fuerza base", "Pico de forma competición"]

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(
    page_title="RPT | Planificador Nutricional",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🏋️",
    layout="wide",
    initial_sidebar_state="auto",
)

# ------------------------------------------------------------------
# ESTILO VISUAL DE MARCA (CSS)
# ------------------------------------------------------------------
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Fraunces:ital,wght@0,500;0,600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Manrope', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {BRAND_BLUE_DARK};
    }}

    /* Fondo general casi negro, con tarjetas oscuras que "flotan" gracias
       al contraste y a un brillo sutil de borde, estilo Whoop */
    [data-testid="stAppViewContainer"] > .main {{
        background-color: {BG_PAGE};
    }}
    [data-testid="stHeader"] {{
        background-color: transparent;
    }}
    .block-container {{
        padding-top: 1.1rem;
        max-width: 1180px;
    }}

    h1, h2, h3, h4 {{
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        color: {BRAND_BLUE_DARK};
        letter-spacing: -0.02em;
    }}
    p, span, label, .stMarkdown {{
        color: {BRAND_BLUE_DARK};
    }}

    .rpt-header {{
        background: linear-gradient(135deg, #1B2838 0%, {BG_PAGE} 100%);
        padding: 26px 32px;
        border-radius: 22px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 18px;
        border: 1px solid {BORDE_OSCURO};
        box-shadow: 0 10px 30px -8px rgba(0,0,0,0.6);
    }}
    .rpt-header h1 {{
        color: {ACCENT_CIAN};
        font-size: 27px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.01em;
    }}
    .rpt-header p {{
        color: {TEXT_MUTED};
        margin: 3px 0 0 0;
        font-size: 14px;
        font-weight: 500;
    }}

    /* ---- Tarjetas: superficie oscura con borde sutil y ligero brillo,
       esquinas redondeadas, como en apps de rendimiento premium ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 18px !important;
        border: 1px solid {BORDE_OSCURO} !important;
        box-shadow: 0 2px 14px -6px rgba(0,0,0,0.5);
        background-color: {BRAND_BLUE_SOFT};
    }}

    div[data-testid="stExpander"] {{
        border-radius: 16px !important;
        border: 1px solid {BORDE_OSCURO} !important;
        background-color: {BRAND_BLUE_SOFT};
        overflow: hidden;
    }}
    div[data-testid="stExpander"] summary {{
        font-weight: 600;
    }}

    /* ---- Botones ---- */
    .stButton>button, .stDownloadButton>button {{
        border-radius: 11px;
        font-weight: 600;
        transition: all 0.15s ease;
    }}
    .stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] {{
        background-color: {ACCENT_CIAN};
        color: #04140F;
        border: none;
        box-shadow: 0 4px 16px -3px rgba(34,211,238,0.45);
    }}
    .stButton>button[kind="primary"]:hover, .stDownloadButton>button[kind="primary"]:hover {{
        background-color: #17B8D4;
        box-shadow: 0 6px 20px -3px rgba(34,211,238,0.55);
        transform: translateY(-1px);
    }}
    .stButton>button[kind="secondary"] {{
        border-radius: 11px;
        border: 1px solid {BORDE_OSCURO};
        background-color: {BG_CARD_ALT};
        color: {BRAND_BLUE_DARK};
    }}

    section[data-testid="stSidebar"] {{
        background-color: #0B0D12;
        border-right: 1px solid {BORDE_OSCURO};
    }}

    /* ---- Barra de navegación inferior fija (solo iconos) ---- */
    .block-container {{
        padding-bottom: 92px;
    }}
    [class*="st-key-bottom_nav"] {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        background-color: {BRAND_BLUE_SOFT};
        border-top: 1px solid {BORDE_OSCURO};
        padding: 8px 12px calc(8px + env(safe-area-inset-bottom, 0px)) 12px;
        box-shadow: 0 -6px 24px -4px rgba(0,0,0,0.5);
    }}
    [class*="st-key-bottom_nav"] [data-testid="stMarkdownContainer"] {{
        display: none;
    }}
    [class*="st-key-bottom_nav"] [data-testid="stHorizontalBlock"] {{
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }}
    [class*="st-key-bottom_nav"] [data-testid="stColumn"] {{
        width: auto !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }}
    [class*="st-key-bottom_nav"] button {{
        height: 52px;
        border-radius: 14px;
        min-width: 0;
    }}
    [class*="st-key-bottom_nav"] button [data-testid="stIconMaterial"] {{
        font-size: 26px !important;
    }}
    [class*="st-key-bottom_nav"] button[kind="primary"] {{
        background-color: rgba(34,211,238,0.16);
        border: none;
        box-shadow: none;
    }}
    [class*="st-key-bottom_nav"] button[kind="primary"] [data-testid="stIconMaterial"] {{
        color: {ACCENT_CIAN} !important;
    }}
    [class*="st-key-bottom_nav"] button[kind="secondary"] {{
        background-color: transparent;
        border: none;
        box-shadow: none;
    }}
    [class*="st-key-bottom_nav"] button[kind="secondary"] [data-testid="stIconMaterial"] {{
        color: {TEXT_MUTED} !important;
    }}
    @media (min-width: 900px) {{
        [class*="st-key-bottom_nav"] {{
            left: 50%;
            right: auto;
            transform: translateX(-50%);
            width: min(480px, 90vw);
            bottom: 18px;
            border-radius: 20px;
            border: 1px solid {BORDE_OSCURO};
        }}
    }}

    .rpt-header-logo {{
        width: 64px;
        height: 64px;
        border-radius: 14px;
        background-color: #FFFFFF;
        padding: 6px;
        object-fit: contain;
        flex-shrink: 0;
        box-shadow: 0 4px 14px -3px rgba(0,0,0,0.4);
    }}

    /* ---- Efecto de "pulsado" en todos los botones: se hunden un poco
       al pulsarlos, como un botón físico ---- */
    .stButton>button, .stDownloadButton>button {{
        transform: translateY(0);
    }}
    .stButton>button:active, .stDownloadButton>button:active {{
        transform: scale(0.96) !important;
        filter: brightness(0.92);
        transition: transform 0.08s ease, filter 0.08s ease;
    }}

    /* ---- Navegación secundaria (BBDD / Subir platos), ahora en la
       barra lateral: discreta, porque son tareas de "una sola vez" ---- */
    [class*="st-key-navsec_"] button {{
        border-radius: 9px;
        font-weight: 500;
        font-size: 13px;
        justify-content: flex-start;
    }}
    [class*="st-key-navsec_"] button[kind="secondary"] {{
        background-color: transparent;
        border: 1px solid {BORDE_OSCURO};
        color: {TEXT_MUTED};
        box-shadow: none;
    }}
    [class*="st-key-navsec_"] button[kind="primary"] {{
        font-size: 13px;
    }}

    /* ---- Resumen semanal ---- */
    .week-stat {{
        background: linear-gradient(160deg, {BG_CARD_ALT} 0%, {BRAND_BLUE_SOFT} 100%);
        border-radius: 16px;
        padding: 16px 16px;
        text-align: center;
        border: 1px solid {BORDE_OSCURO};
    }}
    .week-stat .num {{
        font-size: 25px;
        font-weight: 800;
        color: {ACCENT_CIAN};
        letter-spacing: -0.02em;
    }}
    .week-stat .lbl {{
        font-size: 11.5px;
        color: {TEXT_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }}

    /* ---- Anillos de progreso de macros (estilo Whoop / Apple Health) ---- */
    /* ---- Anillo grande protagonista (estilo "Recovery Score" de Whoop),
       para el dato más importante de la semana ---- */
    .hero-ring-row {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
        padding: 10px 0 18px 0;
    }}
    .hero-ring-wrap {{
        position: relative;
        width: 172px;
        height: 172px;
        flex-shrink: 0;
    }}
    .hero-ring-wrap svg {{
        width: 172px;
        height: 172px;
        transform: rotate(-90deg);
    }}
    .hero-ring-bg {{
        fill: none;
        stroke: {BORDE_OSCURO};
        stroke-width: 14;
    }}
    .hero-ring-fg {{
        fill: none;
        stroke-width: 14;
        stroke-linecap: round;
        transition: stroke-dasharray 0.5s ease;
    }}
    .hero-ring-center {{
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}
    .hero-ring-pct {{
        font-size: 40px;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1;
    }}
    .hero-ring-lbl {{
        font-size: 11px;
        color: {TEXT_MUTED};
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }}
    .hero-ring-info {{
        min-width: 180px;
    }}
    .hero-ring-info .titulo {{
        font-size: 13px;
        color: {TEXT_MUTED};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-bottom: 4px;
    }}
    .hero-ring-info .valor {{
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.02em;
    }}
    .hero-ring-info .detalle {{
        font-size: 12.5px;
        color: {TEXT_MUTED};
        margin-top: 2px;
    }}

    .macro-rings {{
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 14px;
        padding: 6px 0 4px 0;
    }}
    .macro-ring-item {{
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 96px;
    }}
    .macro-ring-item svg {{
        width: 84px;
        height: 84px;
        transform: rotate(-90deg);
    }}
    .macro-ring-bg {{
        fill: none;
        stroke: {BORDE_OSCURO};
        stroke-width: 9;
    }}
    .macro-ring-fg {{
        fill: none;
        stroke-width: 9;
        stroke-linecap: round;
        transition: stroke-dasharray 0.4s ease;
    }}
    .macro-ring-wrap {{
        position: relative;
        width: 84px;
        height: 84px;
    }}
    .macro-ring-value {{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 800;
        color: {BRAND_BLUE_DARK};
    }}
    .macro-ring-label {{
        margin-top: 8px;
        font-size: 11.5px;
        font-weight: 700;
        color: {BRAND_BLUE_DARK};
        text-transform: uppercase;
        letter-spacing: 0.4px;
        text-align: center;
    }}
    .macro-ring-obj {{
        font-size: 10.5px;
        color: {TEXT_MUTED};
        font-weight: 500;
    }}

    /* ---- Tarjeta de día ---- */
    .day-title {{
        font-size: 17.5px;
        font-weight: 800;
        color: {BRAND_BLUE_DARK};
        margin: 0;
        letter-spacing: -0.01em;
    }}
    .day-sub {{
        font-size: 12px;
        color: {TEXT_MUTED};
        margin: 0;
        font-weight: 500;
    }}
    .day-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 12px;
    }}
    .day-kcal-block {{
        text-align: right;
    }}
    .day-badge-confirmado {{
        display: inline-block;
        background-color: #0F3323;
        color: {ACCENT_GREEN};
        font-size: 10.5px;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 10px;
        margin-left: 8px;
    }}
    .meal-confirmado-badge {{
        font-size: 12px;
    }}

    /* ---- Calendario semanal (celdas de día, clicables) ---- */
    .cal-day {{
        background-color: {BRAND_BLUE_SOFT};
        border: 1.5px solid {BORDE_OSCURO};
        border-radius: 14px;
        padding: 10px 4px 8px 4px;
        text-align: center;
        margin-bottom: 6px;
        transition: all 0.15s ease;
    }}
    .cal-day-activo {{
        border-color: {ACCENT_CIAN};
        background-color: #0E2530;
        box-shadow: 0 4px 16px -4px rgba(34,211,238,0.35);
    }}
    .cal-day-nombre {{
        font-size: 12px;
        font-weight: 800;
        color: {BRAND_BLUE_DARK};
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }}
    .cal-day-emoji {{
        font-size: 16px;
        margin: 3px 0;
    }}
    .cal-day-kcal {{
        font-size: 15px;
        font-weight: 800;
        letter-spacing: -0.02em;
    }}
    .cal-day-kcal.kcal-ok, .cal-day-kcal.kcal-warn, .cal-day-kcal.kcal-bad {{
        background-color: transparent;
        padding: 0;
        border-radius: 0;
    }}
    .cal-day-kcal-lbl {{
        font-size: 9px;
        color: {TEXT_MUTED};
        font-weight: 600;
        text-transform: uppercase;
        margin-top: -2px;
    }}

    .kcal-pill {{
        display: inline-block;
        padding: 6px 15px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 15px;
        white-space: nowrap;
        letter-spacing: -0.01em;
    }}
    .kcal-ok {{ background-color: #0F3323; color: {ACCENT_GREEN}; }}
    .kcal-warn {{ background-color: #3D2E0C; color: {ACCENT_YELLOW}; }}
    .kcal-bad {{ background-color: #3A0F18; color: {ACCENT_RED}; }}

    .meal-label {{
        font-size: 10.5px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: {TEXT_MUTED};
        font-weight: 700;
        margin-bottom: 2px;
    }}
    .fixed-meals-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
    }}
    .fixed-meal-chip {{
        flex: 1 1 110px;
        background-color: {BG_CARD_ALT};
        border: 1px solid {BORDE_OSCURO};
        border-radius: 12px;
        padding: 9px 12px;
        font-size: 12.5px;
        color: {BRAND_BLUE_DARK};
        font-weight: 500;
    }}
    .fixed-meal-chip .meal-label {{
        display: block;
        margin-bottom: 1px;
    }}
    .meal-card {{
        border-radius: 12px;
        padding: 10px 12px;
        border-left: 4px solid #ccc;
        background-color: {BG_CARD_ALT};
        min-height: 40px;
        margin-bottom: 6px;
    }}
    .meal-card .name {{
        font-weight: 700;
        font-size: 13.5px;
        color: {BRAND_BLUE_DARK};
    }}
    .cat-chip {{
        display: inline-block;
        font-size: 10.5px;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 10px;
        margin-top: 4px;
        letter-spacing: 0.2px;
    }}

    /* ---- Formularios e inputs: bordes redondeados y foco más suave ---- */
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    div[data-baseweb="select"] > div, div[data-baseweb="input"] {{
        border-radius: 11px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
        border-color: {ACCENT_CIAN} !important;
        box-shadow: 0 0 0 3px rgba(34,211,238,0.15) !important;
    }}
    .stRadio [role="radiogroup"] label, .stCheckbox label {{
        font-weight: 500;
    }}

    /* ---- Tablas de datos: cabecera con más peso, filas más aireadas ---- */
    div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid {BORDE_OSCURO};
    }}
    div[data-testid="stDataFrame"] [role="columnheader"] {{
        background-color: {BG_CARD_ALT} !important;
        font-weight: 700 !important;
        color: {BRAND_BLUE_DARK} !important;
    }}

    /* ---- Popovers y ventanas emergentes: mismo lenguaje que las tarjetas ---- */
    div[data-testid="stPopoverBody"] {{
        border-radius: 16px !important;
        border: 1px solid {BORDE_OSCURO} !important;
        box-shadow: 0 12px 36px -8px rgba(0,0,0,0.6) !important;
    }}
    div[role="dialog"] {{
        border-radius: 20px !important;
    }}

    /* ---- Avisos (success / info / warning / error): esquinas suaves ---- */
    div[data-testid="stAlertContentSuccess"], div[data-testid="stAlertContentInfo"],
    div[data-testid="stAlertContentWarning"], div[data-testid="stAlertContentError"],
    .stAlert {{
        border-radius: 14px !important;
    }}

    /* ---- Barra lateral ---- */
    section[data-testid="stSidebar"] .stButton>button {{
        border-radius: 11px;
    }}
    section[data-testid="stSidebar"] hr {{
        margin: 14px 0;
        border-color: {BORDE_OSCURO};
    }}

    /* ---- Separadores generales, más discretos ---- */
    hr {{
        border-color: {BORDE_OSCURO} !important;
    }}

    /* ---- Gráfico de barras de kcal semanal, envuelto en tarjeta oscura ---- */
    div[data-testid="stVegaLiteChart"] {{
        border-radius: 14px;
        overflow: hidden;
        padding: 6px;
        background-color: {BRAND_BLUE_SOFT};
    }}

    /* ---- Ajustes para pantallas de móvil ---- */
    @media (max-width: 640px) {{
        .rpt-header {{
            padding: 16px 18px;
            gap: 12px;
            border-radius: 18px;
        }}
        .rpt-header h1 {{
            font-size: 19px;
        }}
        .rpt-header p {{
            font-size: 12.5px;
        }}
        [class*="st-key-nav_"] button {{
            height: 52px;
            font-size: 13.5px;
        }}
        .day-title {{
            font-size: 16px;
        }}
        .kcal-pill {{
            font-size: 13px;
            padding: 4px 11px;
        }}
        .fixed-meal-chip {{
            flex: 1 1 42%;
            font-size: 12px;
        }}
        .week-stat .num {{
            font-size: 18px;
        }}
        .macro-ring-item {{
            min-width: 78px;
        }}
        .macro-ring-item svg, .macro-ring-wrap {{
            width: 68px;
            height: 68px;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# Colores de los anillos de macros (coherentes con lo que ya representa
# cada macronutriente en el resto de la app: proteína, carbohidratos, grasa;
# recalibrados para verse bien y muy saturados sobre fondo oscuro)
MACRO_RING_COLORES = {
    "proteina": "#FF3B5C",
    "carbos": "#FFC53D",
    "grasa": "#22D3EE",
}


def _anillo_macro_html(valor, objetivo, color, etiqueta):
    """Genera un anillo de progreso (SVG) estilo Apple Health para un
    macronutriente: cuánto se ha conseguido de media al día frente al
    objetivo calculado para el atleta. Todo en una sola línea sin sangría,
    porque en Markdown una línea indentada se interpreta como bloque de
    código y rompería el HTML de los anillos siguientes."""
    radio = 34
    circunferencia = 2 * 3.14159265 * radio
    pct = max(0.0, min(1.0, (valor / objetivo) if objetivo else 0.0))
    trazo = circunferencia * pct
    return (
        '<div class="macro-ring-item">'
        '<div class="macro-ring-wrap">'
        '<svg viewBox="0 0 84 84">'
        f'<circle class="macro-ring-bg" cx="42" cy="42" r="{radio}"></circle>'
        f'<circle class="macro-ring-fg" cx="42" cy="42" r="{radio}" stroke="{color}" '
        f'stroke-dasharray="{trazo:.1f} {circunferencia:.1f}"></circle>'
        '</svg>'
        f'<div class="macro-ring-value">{valor:.0f}g</div>'
        '</div>'
        f'<div class="macro-ring-label">{etiqueta}</div>'
        f'<div class="macro-ring-obj">objetivo {objetivo:.0f}g</div>'
        '</div>'
    )


def mostrar_grafica_tendencia(historial_semanas):
    """Gráfica de tendencia (estilo Whoop) de kcal y proteína media diaria
    a lo largo de las últimas semanas generadas para este atleta."""
    if not historial_semanas or len(historial_semanas) < 2:
        st.caption(
            "📈 En cuanto generes al menos dos semanas para este atleta, aquí verás la evolución de "
            "kcal y proteína media diaria semana a semana."
        )
        return
    filas = []
    for i, h in enumerate(historial_semanas):
        filas.append({
            "Semana": f"S{i + 1}",
            "Kcal media/día": round(h.get("media_kcal", 0)),
            "Proteína media/día (g)": round(h.get("media_proteina", 0)),
        })
    df_tendencia = pd.DataFrame(filas).set_index("Semana")
    st.markdown("**📈 Evolución semana a semana**")
    col_kcal, col_prot = st.columns(2)
    with col_kcal:
        st.caption("Kcal media diaria")
        st.line_chart(df_tendencia[["Kcal media/día"]], color=["#00E5A0"], height=180)
    with col_prot:
        st.caption("Proteína media diaria (g)")
        st.line_chart(df_tendencia[["Proteína media/día (g)"]], color=["#FF3B5C"], height=180)


CAMPO_MACRO = {"proteina": "Proteina_g", "carbos": "Carbos_g", "grasa": "Grasas_g"}
CATEGORIA_BUENA_MACRO = {"proteina": "Alto en Proteína", "carbos": "Alto en Hidratos", "grasa": "Ligero"}
NOMBRE_MACRO = {"proteina": "proteína", "carbos": "carbohidratos", "grasa": "grasas"}


def _analizar_macro_semana(macro_clave, es_deficit):
    """Analiza los platos REALES de la semana actual (almuerzo y cena de
    cada día) y prepara consejos concretos para acercar ese macro al
    objetivo: identifica qué comidas aportan menos (si hay déficit) o más
    (si hay exceso) de ese macro por caloría — es decir, cuáles "diluyen"
    o "cargan" más el resultado — y busca en tu propio inventario
    alternativas ya disponibles que mejorarían la cosa, sin usarlas ya en
    otro día de la misma semana."""
    campo = CAMPO_MACRO[macro_clave]
    comidas = []
    nombres_usados = set()
    for dia, datos_dia in st.session_state.datos_menu.items():
        for tipo in ['almuerzo', 'cena']:
            plato = datos_dia.get(tipo)
            if not plato or not plato.get('Kcal'):
                continue
            nombres_usados.add(plato['Plato'])
            densidad = plato.get(campo, 0) / plato['Kcal'] * 100
            comidas.append({'dia': dia, 'tipo': tipo, 'plato': plato, 'densidad': densidad})

    if not comidas:
        return [], []

    comidas.sort(key=lambda c: c['densidad'], reverse=not es_deficit)
    candidatos_cambio = comidas[:3]

    df = st.session_state.inventario
    if df.empty:
        return candidatos_cambio, []
    df_alt = df.copy()
    df_alt['_densidad'] = df_alt.apply(
        lambda r: (r.get(campo, 0) / r['Kcal'] * 100) if r.get('Kcal') else 0, axis=1,
    )
    if es_deficit:
        df_alt = df_alt[df_alt['Categoria'] == CATEGORIA_BUENA_MACRO[macro_clave]]
        df_alt = df_alt.sort_values('_densidad', ascending=False)
    else:
        df_alt = df_alt.sort_values('_densidad', ascending=True)
    df_alt = df_alt[~df_alt['Plato'].isin(nombres_usados)]
    sugerencias = df_alt.head(4).to_dict('records')
    return candidatos_cambio, sugerencias


def _mostrar_consejos_macro(macro_clave, media, objetivo, etiqueta_macro):
    """Panel de consejos concretos para ajustar un macro, mostrado al
    pulsar 'Ver consejos' bajo su anillo."""
    diferencia = media - objetivo
    es_deficit = diferencia < 0
    nombre_macro = NOMBRE_MACRO[macro_clave]
    if abs(diferencia) < max(objetivo * 0.03, 3):
        st.success(f"✅ Tu {nombre_macro} está prácticamente en el objetivo ({media:.0f} de {objetivo:.0f} g). No hace falta tocar nada.")
        return

    if es_deficit:
        st.warning(f"⚠️ Te faltan **{abs(diferencia):.0f} g de {nombre_macro}** de media al día ({media:.0f} de {objetivo:.0f} g objetivo).")
    else:
        st.warning(f"⚠️ Te sobran **{abs(diferencia):.0f} g de {nombre_macro}** de media al día ({media:.0f} de {objetivo:.0f} g objetivo).")

    candidatos, sugerencias = _analizar_macro_semana(macro_clave, es_deficit)
    if not candidatos:
        st.caption("Genera un menú primero para poder analizar tus comidas.")
        return

    verbo = "menos" if es_deficit else "más"
    st.markdown(f"**Estas comidas de tu semana son las que aportan {verbo} {nombre_macro} por caloría:**")
    for c in candidatos:
        plato = c['plato']
        st.markdown(
            f"- **{c['dia']} · {c['tipo']}**: {plato['Plato']} "
            f"({plato.get(CAMPO_MACRO[macro_clave], 0):.0f} g {nombre_macro} en {plato['Kcal']:.0f} kcal)"
        )

    if sugerencias:
        verbo2 = "más densos en" if es_deficit else "más ligeros de"
        st.markdown(f"**Podrías cambiar alguna de esas comidas por platos {verbo2} {nombre_macro} que ya tienes guardados:**")
        for s in sugerencias:
            st.markdown(
                f"- **{s['Plato']}** ({chip_categoria_html(s['Categoria'])} "
                f"{s.get(CAMPO_MACRO[macro_clave], 0):.0f} g {nombre_macro} / {s['Kcal']:.0f} kcal de referencia)",
                unsafe_allow_html=True,
            )
        st.caption(
            "Para aplicar el cambio, ve al día correspondiente en el calendario y pulsa '🔄 Cambiar' en esa "
            "comida — la ración se ajustará sola a las kcal que necesites."
        )
    else:
        st.caption(
            f"No tengo en tu base de datos ningún plato sin usar esta semana que ayude con esto. "
            f"Prueba a subir alguno nuevo con más {nombre_macro} desde 'Subir Mis Platos'."
        )


def mostrar_anillos_macros(prot_media, prot_obj, carb_media, carb_obj, grasa_media, grasa_obj):
    """Muestra los tres anillos de progreso de macros (proteína,
    carbohidratos, grasas) de la media diaria frente al objetivo, cada
    uno con un botón para ver consejos concretos de qué platos cambiar."""
    datos_anillos = [
        ("proteina", prot_media, prot_obj, "Proteína"),
        ("carbos", carb_media, carb_obj, "Carbohidratos"),
        ("grasa", grasa_media, grasa_obj, "Grasas"),
    ]
    cols = st.columns(3)
    for col, (clave, media, objetivo, etiqueta) in zip(cols, datos_anillos):
        with col:
            st.markdown(
                f'<div class="macro-rings">{_anillo_macro_html(media, objetivo, MACRO_RING_COLORES[clave], etiqueta)}</div>',
                unsafe_allow_html=True,
            )
            with st.popover("💡 Ver consejos", use_container_width=True):
                _mostrar_consejos_macro(clave, media, objetivo, etiqueta)


def mostrar_anillo_hero(kcal_media, kcal_objetivo, titulo="Cobertura calórica", etiqueta_detalle=None):
    """Anillo grande y protagonista (como el 'Recovery Score' de Whoop)
    con el dato más importante de la semana: qué porcentaje del objetivo
    calórico se está cubriendo de media. Verde si va bien encaminado,
    ámbar si hay una desviación moderada, rojo si es alta — el mismo
    criterio de color que ya se usa en el resto de la app."""
    pct = (kcal_media / kcal_objetivo * 100) if kcal_objetivo else 0
    pct_relleno = max(0, min(100, pct))
    radio = 80
    circunferencia = 2 * 3.14159265 * radio
    trazo = circunferencia * pct_relleno / 100
    desvio_pct = abs(pct - 100)
    if desvio_pct <= 5:
        color = ACCENT_GREEN
    elif desvio_pct <= 12:
        color = ACCENT_YELLOW
    else:
        color = ACCENT_RED
    detalle = etiqueta_detalle or f"{kcal_media:.0f} de {kcal_objetivo:.0f} kcal objetivo"
    html = (
        '<div class="hero-ring-row">'
        '<div class="hero-ring-wrap">'
        '<svg viewBox="0 0 200 200">'
        f'<circle class="hero-ring-bg" cx="100" cy="100" r="{radio}"></circle>'
        f'<circle class="hero-ring-fg" cx="100" cy="100" r="{radio}" stroke="{color}" '
        f'stroke-dasharray="{trazo:.1f} {circunferencia:.1f}"></circle>'
        '</svg>'
        f'<div class="hero-ring-center"><div class="hero-ring-pct" style="color:{color};">{pct:.0f}%</div>'
        '<div class="hero-ring-lbl">Cobertura</div></div>'
        '</div>'
        '<div class="hero-ring-info">'
        f'<div class="titulo">{titulo}</div>'
        f'<div class="valor" style="color:{color};">{pct:.0f}% del objetivo</div>'
        f'<div class="detalle">{detalle}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _logo_base64():
    if not os.path.exists(LOGO_PATH):
        return None
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


_LOGO_B64 = _logo_base64()
_logo_img_html = f'<img src="data:image/png;base64,{_LOGO_B64}" class="rpt-header-logo" alt="RPT" />' if _LOGO_B64 else ''

st.markdown(f"""
<div class="rpt-header">
    {_logo_img_html}
    <div>
        <h1>RPT · RAW POWER TRAINING</h1>
        <p>Planificador de menú y rendimiento deportivo</p>
    </div>
</div>
""", unsafe_allow_html=True)

SECCIONES_PRINCIPALES = [
    ('menu', 'Planificador de Menú', ':material/restaurant_menu:', 'Genera y ajusta el menú semanal'),
    ('atleta', 'Atleta', ':material/fitness_center:', 'Perfil, marcas y objetivos de cada atleta'),
    ('seguimiento', 'Seguimiento', ':material/monitoring:', 'El menú confirmado: qué se ha comido de verdad'),
]
SECCIONES_SECUNDARIAS = [
    ('gestion', 'Gestión de Base de Datos', ':material/database:'),
    ('subir', 'Subir Mis Platos', ':material/upload_file:'),
]


# ------------------------------------------------------------------
# INICIALIZACIÓN DE VARIABLES (ESTADO)
# ------------------------------------------------------------------
def _perfil_vacio():
    return {
        'nombre': '', 'peso': 0.0, 'altura_cm': 175, 'edad': 30, 'sexo': 'Hombre', 'categoria': '',
        'rm_arrancada': 0, 'rm_dos_tiempos': 0,
        'rm_sentadilla_delantera': 0, 'rm_sentadilla_trasera': 0,
        'obj_arrancada': 0, 'obj_dos_tiempos': 0,
        'objetivo_fase': 'Mantener categoría', 'competicion': '',
        'fecha_competicion': date.today(),
        'desayuno_semana_nombre': None, 'desayuno_finde_nombre': None,
    }


def _completar_perfil(perfil):
    """Rellena con valores por defecto los campos que falten (por ejemplo,
    atletas guardados antes de añadir altura/edad/sexo al formulario)."""
    base = _perfil_vacio()
    base.update({k: v for k, v in perfil.items() if v is not None})
    return base


def _firma_perfil(perfil):
    """Instantánea de los datos que influyen en el cálculo del menú. Se usa
    para detectar si el menú que se ve en pantalla se generó con otros
    datos (por ejemplo, si has cambiado de objetivo o de peso después)."""
    return {
        'nombre': perfil.get('nombre'),
        'objetivo_fase': perfil.get('objetivo_fase'),
        'peso': perfil.get('peso'),
        'altura_cm': perfil.get('altura_cm'),
        'edad': perfil.get('edad'),
        'sexo': perfil.get('sexo'),
    }


def _persistir_estado_actual():
    """Guarda en disco el estado 'de trabajo' del atleta actualmente
    seleccionado (su borrador en curso, o su menú confirmado activo), para
    poder recuperarlo tal cual al volver a él — incluso si se cierra la
    app o se sustituye por una versión nueva."""
    nombre = st.session_state.perfil.get('nombre', '')
    if not nombre:
        return
    ds.guardar_estado_actual(nombre, {
        "estado": st.session_state.get('estado_menu_actual', 'borrador'),
        "datos_menu": st.session_state.datos_menu,
        "menu_original": st.session_state.menu_original,
        "dias_confirmados": st.session_state.dias_confirmados,
        "objetivo_semanal_kcal": st.session_state.objetivo_semanal_kcal,
        "bmr_calculado": st.session_state.bmr_calculado,
        "intensidades_semana": st.session_state.intensidades_semana,
        "detalle_intensidades": st.session_state.detalle_intensidades,
        "entreno_nombre_archivo": st.session_state.entreno_nombre_archivo,
        "menu_confirmado_id": st.session_state.get('menu_confirmado_id'),
        "comidas_confirmadas": st.session_state.get('comidas_confirmadas', {}),
    })


def _cargar_o_reiniciar_menu_actual():
    """Se llama al cambiar de atleta (o al arrancar): cada atleta tiene su
    propio menú (borrador en curso o confirmado), así que al entrar en uno
    se recupera tal cual se dejó, en vez de partir siempre de cero."""
    nombre = st.session_state.perfil.get('nombre', '')
    estado_guardado = ds.cargar_estado_actual(nombre) if nombre else None

    if estado_guardado:
        st.session_state.datos_menu = estado_guardado.get('datos_menu', {})
        st.session_state.menu_original = estado_guardado.get('menu_original', {})
        st.session_state.dias_confirmados = estado_guardado.get('dias_confirmados', {})
        st.session_state.objetivo_semanal_kcal = estado_guardado.get('objetivo_semanal_kcal')
        st.session_state.bmr_calculado = estado_guardado.get('bmr_calculado')
        st.session_state.intensidades_semana = estado_guardado.get('intensidades_semana', {})
        st.session_state.detalle_intensidades = estado_guardado.get('detalle_intensidades', {})
        st.session_state.entreno_nombre_archivo = estado_guardado.get('entreno_nombre_archivo', '')
        st.session_state.estado_menu_actual = estado_guardado.get('estado', 'borrador')
        st.session_state.menu_confirmado_id = estado_guardado.get('menu_confirmado_id')
        st.session_state.comidas_confirmadas = estado_guardado.get('comidas_confirmadas', {})
        st.session_state.menu_generado_para = _firma_perfil(st.session_state.perfil)
    else:
        st.session_state.datos_menu = {}
        st.session_state.menu_original = {}
        st.session_state.dias_confirmados = {}
        st.session_state.objetivo_semanal_kcal = None
        st.session_state.bmr_calculado = None
        st.session_state.intensidades_semana = {}
        st.session_state.detalle_intensidades = {}
        st.session_state.entreno_nombre_archivo = ''
        st.session_state.estado_menu_actual = 'borrador'
        st.session_state.menu_confirmado_id = None
        st.session_state.comidas_confirmadas = {}
        st.session_state.menu_generado_para = None

    st.session_state.menu_cargado_de = None
    st.session_state.entreno_texto_ocr = ''
    st.session_state._entreno_excel_procesado = None
    st.session_state._entreno_imagen_procesada = None
    st.session_state.entreno_expander_abierto_inicialmente = not bool(st.session_state.intensidades_semana)
    st.session_state.historial_semanas = (
        ds.cargar_historial_semanas(nombre) if nombre else []
    ) or st.session_state.get('historial_por_atleta', {}).get(nombre, [])
    if nombre:
        st.session_state.setdefault('historial_por_atleta', {})[nombre] = st.session_state.historial_semanas


def _dibujar_detalle_dia(dia, datos):
    """Panel de edición completo de un día: comidas fijas, postres de
    almuerzo/cena, y almuerzo/cena. Es el mismo contenido para cualquier
    día, se llama con el que esté seleccionado en el calendario."""
    comidas_confirmadas = st.session_state.setdefault('comidas_confirmadas', {})

    def _badge_confirmado(clave_comida):
        return ' <span class="meal-confirmado-badge">✅</span>' if comidas_confirmadas.get(clave_comida) else ''

    st.markdown("**Comidas fijas y postres** _(pulsa 🔄 para cambiarlas, ✅ para confirmar que las has cumplido)_")
    m1, m2, m3 = st.columns(3)
    for col, tipo in [(m1, 'desayuno'), (m2, 'media_manana'), (m3, 'merienda')]:
        etiqueta = ETIQUETAS_COMIDA_FIJA[tipo]
        clave_comida = f"{dia}_{tipo}"
        col.markdown(
            f'<div class="fixed-meal-chip"><span class="meal-label">{etiqueta}</span>{_badge_confirmado(clave_comida)}<br>{datos[tipo]}'
            f'<div class="day-sub" style="margin-top:2px;">{datos.get(tipo + "_kcal", 0)} kcal</div></div>',
            unsafe_allow_html=True,
        )
        bc1, bc2 = col.columns(2)
        if bc1.button("🔄", key=f"btn_fijo_{dia}_{tipo}", use_container_width=True, help=f"Cambiar {etiqueta.lower()}"):
            dialog_editar_comida_fija(dia, tipo)
        if bc2.button("✅", key=f"btn_confirm_fijo_{dia}_{tipo}", use_container_width=True, help="Confirmar que lo has cumplido", type="primary" if comidas_confirmadas.get(clave_comida) else "secondary"):
            comidas_confirmadas[clave_comida] = not comidas_confirmadas.get(clave_comida)
            _persistir_estado_actual()
            st.rerun()

    p1, p2 = st.columns(2)
    for col, tipo in [(p1, 'postre_almuerzo'), (p2, 'postre_cena')]:
        etiqueta = ETIQUETAS_COMIDA_FIJA[tipo]
        clave_comida = f"{dia}_{tipo}"
        col.markdown(
            f'<div class="fixed-meal-chip"><span class="meal-label">{etiqueta}</span>{_badge_confirmado(clave_comida)}<br>{datos[tipo]}'
            f'<div class="day-sub" style="margin-top:2px;">{datos.get(tipo + "_kcal", 0)} kcal</div></div>',
            unsafe_allow_html=True,
        )
        bc1, bc2 = col.columns(2)
        if bc1.button("🔄", key=f"btn_fijo_{dia}_{tipo}", use_container_width=True, help=f"Cambiar {etiqueta.lower()}"):
            dialog_editar_comida_fija(dia, tipo)
        if bc2.button("✅", key=f"btn_confirm_fijo_{dia}_{tipo}", use_container_width=True, help="Confirmar que lo has cumplido", type="primary" if comidas_confirmadas.get(clave_comida) else "secondary"):
            comidas_confirmadas[clave_comida] = not comidas_confirmadas.get(clave_comida)
            _persistir_estado_actual()
            st.rerun()

    objetivo_agua = datos.get('objetivo_agua_l')
    if objetivo_agua:
        clave_agua = f"{dia}_hidratacion"
        col_agua, col_agua_btn = st.columns([4, 1])
        col_agua.markdown(
            f'<div class="fixed-meal-chip"><span class="meal-label">💧 Hidratación</span>{_badge_confirmado(clave_agua)}<br>'
            f'Objetivo del día: <b>{objetivo_agua} L</b> de agua'
            f'<div class="day-sub" style="margin-top:2px;">Orientativo — ajusta según sed y color de la orina</div></div>',
            unsafe_allow_html=True,
        )
        col_agua_btn.write("")
        col_agua_btn.write("")
        if col_agua_btn.button("✅", key=f"btn_confirm_{clave_agua}", use_container_width=True, help="Confirmar que has bebido lo suficiente hoy", type="primary" if comidas_confirmadas.get(clave_agua) else "secondary"):
            comidas_confirmadas[clave_agua] = not comidas_confirmadas.get(clave_agua)
            _persistir_estado_actual()
            st.rerun()

    st.markdown("**Almuerzo y cena**")
    col_alm, col_cen = st.columns(2)
    for col, tipo, etiqueta in [(col_alm, 'almuerzo', 'Almuerzo'), (col_cen, 'cena', 'Cena')]:
        plato_actual = datos[tipo]
        clave_comida = f"{dia}_{tipo}"
        col.markdown(f'<p class="meal-label">{etiqueta}{_badge_confirmado(clave_comida)}</p>', unsafe_allow_html=True)
        borde = CAT_TEXT.get(plato_actual['Categoria'], '#ccc')
        porcion_g = plato_actual.get('_porcion_g')
        linea_porcion = f' · ración de ≈{porcion_g:.0f} g' if porcion_g else ''
        col.markdown(
            f'<div class="meal-card" style="border-left-color:{borde};">'
            f'<div class="name">{plato_actual["Plato"]}</div>'
            f'{chip_categoria_html(plato_actual["Categoria"])}'
            f'<div class="day-sub" style="margin-top:3px;">{plato_actual["Kcal"]} kcal{linea_porcion}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        bcol1, bcol2, bcol3 = col.columns(3)
        if bcol1.button("🔄", key=f"btn_cambiar_{dia}_{tipo}", use_container_width=True, help="Cambiar el plato planeado"):
            dialog_sustituir(dia, tipo)
        if bcol2.button("📝", key=f"btn_real_{dia}_{tipo}", use_container_width=True, help="Registrar lo que has comido de verdad"):
            st.session_state.registro_paso = 'elegir'
            dialog_registrar_real(dia, tipo)
        if bcol3.button("✅", key=f"btn_confirm_{dia}_{tipo}", use_container_width=True, help="Confirmar que has cumplido lo planeado", type="primary" if comidas_confirmadas.get(clave_comida) else "secondary"):
            comidas_confirmadas[clave_comida] = not comidas_confirmadas.get(clave_comida)
            _persistir_estado_actual()
            st.rerun()


def _dibujar_tarjetas_dias_interactivas():
    """Calendario semanal: cada día es una celda compacta con su
    intensidad y sus kcal. Al pinchar en un día, se abre justo debajo su
    panel completo de edición (comidas fijas, postres, almuerzo y cena).
    Se usa tanto en el borrador (Planificador) como en el seguimiento del
    menú ya confirmado — en ambos casos es donde se hacen los ajustes
    reales."""
    dias_disponibles = list(st.session_state.datos_menu.keys())
    if st.session_state.get('dia_calendario_seleccionado') not in dias_disponibles:
        st.session_state.dia_calendario_seleccionado = dias_disponibles[0] if dias_disponibles else None

    cols = st.columns(len(dias_disponibles))
    for col, dia in zip(cols, dias_disponibles):
        datos = st.session_state.datos_menu[dia]
        k_actual = kcal_total_dia(datos)
        k_orig = st.session_state.menu_original[dia]['kcal']
        desvio = k_actual - k_orig
        if abs(desvio) <= 100:
            pill_class = "kcal-ok"
        elif abs(desvio) <= 250:
            pill_class = "kcal-warn"
        else:
            pill_class = "kcal-bad"
        confirmado = dia in st.session_state.dias_confirmados
        emoji_intensidad = {"Alta": "🔴", "Media": "🟡", "Descanso": "🟢"}.get(datos["intensidad"], "🟡")
        es_seleccionado = dia == st.session_state.dia_calendario_seleccionado

        with col:
            marca_check = ' <span style="color:#1F7A44;">✅</span>' if confirmado else ''
            st.markdown(
                f'<div class="cal-day{" cal-day-activo" if es_seleccionado else ""}">'
                f'<div class="cal-day-nombre">{dia[:3]}{marca_check}</div>'
                f'<div class="cal-day-emoji">{emoji_intensidad}</div>'
                f'<div class="cal-day-kcal {pill_class}">{k_actual}</div>'
                f'<div class="cal-day-kcal-lbl">kcal</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("Editar" if not es_seleccionado else "Editando", key=f"cal_dia_{dia}", use_container_width=True, type="primary" if es_seleccionado else "secondary"):
                st.session_state.dia_calendario_seleccionado = dia
                st.rerun()

    st.write("")
    dia_activo = st.session_state.dia_calendario_seleccionado
    if dia_activo:
        with st.container(border=True):
            datos_activo = st.session_state.datos_menu[dia_activo]
            st.markdown(f"#### {dia_activo}")
            st.caption(f"Intensidad: {datos_activo['intensidad']}")
            _dibujar_detalle_dia(dia_activo, datos_activo)


def _mostrar_menu_confirmado_bloqueado():
    """Se muestra en el Planificador cuando el atleta actual ya tiene un
    menú confirmado: resumen de solo lectura. Los cambios reales se hacen
    en 'Seguimiento Menú y Atleta'; aquí solo se puede consultar o
    empezar un menú nuevo."""
    st.header("Entrenamiento y Planificación")
    st.success(
        f"✅ **{st.session_state.perfil.get('nombre', 'Este atleta')} tiene un menú confirmado activo.** "
        "Para registrar lo que come de verdad o cambiar algún plato de esta semana, ve a "
        "**'📋 Seguimiento Menú y Atleta'**. Aquí, en el Planificador, solo puedes consultarlo o "
        "empezar uno nuevo."
    )

    if not st.session_state.datos_menu:
        st.info("No hay datos del menú confirmado para mostrar.")
    else:
        totales = {dia: kcal_total_dia(datos) for dia, datos in st.session_state.datos_menu.items()}
        media_semana = sum(totales.values()) / len(totales) if totales else 0
        r1, r2, r3 = st.columns(3)
        r1.markdown(f'<div class="week-stat"><div class="num">{sum(totales.values())}</div><div class="lbl">🔥 Kcal semana</div></div>', unsafe_allow_html=True)
        r2.markdown(f'<div class="week-stat"><div class="num">{media_semana:.0f}</div><div class="lbl">📊 Media diaria</div></div>', unsafe_allow_html=True)
        r3.markdown(f'<div class="week-stat"><div class="num">{len(totales)}</div><div class="lbl">📅 Días planificados</div></div>', unsafe_allow_html=True)
        st.write("")

        for dia, datos in st.session_state.datos_menu.items():
            k_actual = kcal_total_dia(datos)
            k_orig = st.session_state.menu_original.get(dia, {}).get('kcal', 0)
            desvio = k_actual - k_orig
            if abs(desvio) <= 100:
                pill_class = "kcal-ok"
            elif abs(desvio) <= 250:
                pill_class = "kcal-warn"
            else:
                pill_class = "kcal-bad"
            signo = "+" if desvio > 0 else ""
            emoji_intensidad = {"Alta": "🔴", "Media": "🟡", "Descanso": "🟢"}.get(datos["intensidad"], "🟡")
            with st.container(border=True):
                st.markdown(
                    f'<div class="day-header">'
                    f'<div><span class="day-title">{dia}</span>'
                    f'<p class="day-sub">{emoji_intensidad} Intensidad: {datos["intensidad"]}</p></div>'
                    f'<div class="day-kcal-block"><span class="kcal-pill {pill_class}">{k_actual} kcal</span>'
                    f'<p class="day-sub">{signo}{desvio} vs. objetivo</p></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    f'{datos["desayuno"]} · {datos["media_manana"]} · {datos["almuerzo"]["Plato"]} · '
                    f'{datos["merienda"]} · {datos["cena"]["Plato"]}'
                )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### 🆕 ¿Quieres planificar una semana nueva?")
        st.caption(
            "Esto no borra el menú confirmado (sigue disponible en 'Seguimiento Menú y Atleta' y en su "
            "histórico); simplemente libera el Planificador para generar uno nuevo, para este atleta o "
            "para otro."
        )
        if st.button("Empezar un menú nuevo", icon=":material/add_circle:", use_container_width=True, key="btn_empezar_nuevo"):
            nombre = st.session_state.perfil.get('nombre', '')
            ds.limpiar_estado_actual(nombre)
            _cargar_o_reiniciar_menu_actual()
            st.rerun()


def _mostrar_planificador_borrador():
    """Pantalla completa de generación y edición del menú en curso (borrador). Se muestra solo cuando el atleta actual NO tiene un menú confirmado activo."""
    st.header("Entrenamiento y Planificación")

    if 'entreno_expander_abierto_inicialmente' not in st.session_state:
        st.session_state.entreno_expander_abierto_inicialmente = not bool(st.session_state.get('intensidades_semana'))

    with st.expander("📋 Tabla de entrenamiento semanal", expanded=st.session_state.entreno_expander_abierto_inicialmente):
        st.caption(
            "Sube tu entrenamiento de esta semana (Excel, o una foto/captura de tu hoja) y la app "
            "calcula sola qué días son de intensidad alta, media o de descanso — no hace falta que "
            "lo indiques a mano. Siempre puedes corregir cualquier día abajo si algo no coincide."
        )
        modo_entreno = st.radio(
            "¿Cómo quieres subirlo?", ["Excel (.xlsx)", "Foto o captura (imagen)"],
            horizontal=True, key="modo_entreno",
        )

        if modo_entreno == "Excel (.xlsx)":
            col_plantilla, col_subida = st.columns([1, 2])
            with col_plantilla:
                try:
                    ruta_plantilla = os.path.join(OUTPUT_DIR, "Plantilla_Entrenamiento.xlsx")
                    ent.generar_plantilla_excel(ruta_plantilla)
                    with open(ruta_plantilla, "rb") as f:
                        st.download_button(
                            "📥 Descargar plantilla", data=f.read(),
                            file_name="Plantilla_Entrenamiento_RPT.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"No se pudo preparar la plantilla: {e}")

            archivo_entreno = col_subida.file_uploader("Sube tu entrenamiento (.xlsx)", type=['xlsx'], key="entreno_uploader")
            if archivo_entreno is not None:
                identidad_archivo = (archivo_entreno.name, archivo_entreno.size)
                if st.session_state.get('_entreno_excel_procesado') != identidad_archivo:
                    try:
                        intensidades, detalle, avisos_entreno = ent.leer_entrenamiento(archivo_entreno, st.session_state.perfil)
                        st.session_state.intensidades_semana = intensidades
                        st.session_state.detalle_intensidades = detalle
                        st.session_state.entreno_nombre_archivo = archivo_entreno.name
                        st.session_state._entreno_excel_procesado = identidad_archivo
                        for aviso in avisos_entreno:
                            st.warning(aviso)
                        st.success("Entrenamiento leído. Revisa abajo cómo se ha clasificado cada día antes de generar el menú.")
                    except ValueError as e:
                        st.error(str(e))

        else:
            st.caption(
                "Gratis y sin conexión (usa Tesseract OCR instalado en tu ordenador). Funciona mejor "
                "con capturas de pantalla nítidas o fotos rectas y bien iluminadas de texto impreso — "
                "con fotos borrosas, torcidas o letra manuscrita puede fallar u omitir algún día, así "
                "que revisa siempre el resultado abajo."
            )
            archivo_imagen = st.file_uploader(
                "Sube una foto o captura (.jpg, .png)", type=['jpg', 'jpeg', 'png'], key="entreno_uploader_imagen"
            )
            if archivo_imagen is not None:
                identidad_imagen = (archivo_imagen.name, archivo_imagen.size)
                if st.session_state.get('_entreno_imagen_procesada') != identidad_imagen:
                    if not ent.ocr_disponible():
                        st.error(
                            "No encuentro Tesseract OCR instalado en este ordenador. Es gratuito, pero hay "
                            "que instalarlo aparte del programa (no basta con lo que ya trae la app) — mira "
                            "el manual de instrucciones para ver cómo, según tu sistema operativo."
                        )
                    else:
                        try:
                            with st.spinner("Leyendo la imagen..."):
                                intensidades, detalle, avisos_entreno, texto_bruto = ent.leer_entrenamiento_imagen(archivo_imagen)
                            st.session_state.intensidades_semana = intensidades
                            st.session_state.detalle_intensidades = detalle
                            st.session_state.entreno_nombre_archivo = archivo_imagen.name
                            st.session_state.entreno_texto_ocr = texto_bruto
                            st.session_state._entreno_imagen_procesada = identidad_imagen
                            for aviso in avisos_entreno:
                                st.warning(aviso)
                            st.success("Imagen leída. Revisa con atención cómo se ha clasificado cada día antes de generar el menú — el OCR no es infalible.")
                        except ValueError as e:
                            st.error(str(e))

        if st.session_state.get('intensidades_semana'):
            st.caption(f"📄 Usando: **{st.session_state.get('entreno_nombre_archivo', '')}**")
            cols_dias = st.columns(7)
            opciones_intensidad = ["Alta", "Media", "Descanso"]
            for col, dia in zip(cols_dias, DIAS_SEMANA):
                intensidad_dia = st.session_state.intensidades_semana.get(dia, "Media")
                emoji = {"Alta": "🔴", "Media": "🟡", "Descanso": "🟢"}.get(intensidad_dia, "🟡")
                col.markdown(f"**{dia[:3]}**")
                with col.popover(f"{emoji} {intensidad_dia}", use_container_width=True):
                    st.caption(st.session_state.detalle_intensidades.get(dia, ""))
                    st.caption("¿No es correcto? Corrígelo aquí:")
                    for opcion, emoji_opcion in [("Alta", "🔴"), ("Media", "🟡"), ("Descanso", "🟢")]:
                        es_actual = opcion == intensidad_dia
                        if st.button(
                            f"{emoji_opcion} {opcion}", key=f"corr_{opcion}_{dia}", use_container_width=True,
                            type="primary" if es_actual else "secondary",
                        ):
                            if not es_actual:
                                st.session_state.intensidades_semana[dia] = opcion
                                st.session_state.detalle_intensidades[dia] = "Corregido a mano por ti."
                                st.rerun()
            st.caption("Pulsa sobre la intensidad de cualquier día para ver el detalle o corregirla a mano.")

            st.markdown("**📊 Necesidades según este entrenamiento**")
            st.caption(
                "Objetivo de kcal y macros para cada día, calculado a partir de tu perfil (peso, altura, "
                "edad, sexo, fase actual) y la intensidad de entrenamiento de ese día — antes incluso de "
                "generar el menú. Si corriges algún día arriba, este resumen se actualiza solo."
            )
            filas_resumen = []
            for dia in DIAS_SEMANA:
                intensidad_dia = st.session_state.intensidades_semana.get(dia, "Media")
                objetivo_dia, _, _ = calcular_objetivo_dia(st.session_state.perfil, intensidad_dia)
                macros_dia = calcular_objetivo_macros(st.session_state.perfil, objetivo_dia)
                filas_resumen.append({
                    "Día": dia,
                    "Intensidad": {"Alta": "🔴 Alta", "Media": "🟡 Media", "Descanso": "🟢 Descanso"}.get(intensidad_dia, intensidad_dia),
                    "Kcal": objetivo_dia,
                    "Proteína (g)": macros_dia["proteina_g"],
                    "Carbohidratos (g)": macros_dia["carbos_g"],
                    "Grasas (g)": macros_dia["grasa_g"],
                })
            df_resumen = pd.DataFrame(filas_resumen)
            st.dataframe(df_resumen, hide_index=True, use_container_width=True)

            total_kcal_semana = df_resumen["Kcal"].sum()
            media_kcal = total_kcal_semana / len(df_resumen)
            media_prot = df_resumen["Proteína (g)"].mean()
            media_carb = df_resumen["Carbohidratos (g)"].mean()
            media_grasa = df_resumen["Grasas (g)"].mean()
            st.caption(
                f"**Total semanal: {total_kcal_semana:.0f} kcal** · Media diaria: {media_kcal:.0f} kcal "
                f"({media_prot:.0f} g proteína, {media_carb:.0f} g carbohidratos, {media_grasa:.0f} g "
                "grasas, de media al día)."
            )

            if st.session_state.get('entreno_texto_ocr'):
                with st.expander("Ver el texto que ha leído el OCR (para comprobar si algo falló)"):
                    st.text(st.session_state.entreno_texto_ocr[:3000])
        else:
            st.info("Sin entrenamiento subido todavía: se usará un patrón orientativo (Miércoles fuerte, Martes y Viernes de descanso, resto medio) hasta que subas el tuyo.")

    with st.expander("🍳 Desayuno por defecto", expanded=False):
        st.caption(
            "Elige de tu base de datos qué desayuno usar entre semana y cuál el fin de semana. "
            "Si no eliges nada, se usa un cálculo genérico (puedes cambiarlo cada día igualmente con 🔄)."
        )
        nombres_platos = st.session_state.inventario['Plato'].tolist()
        opciones_desayuno = ["(cálculo genérico)"] + nombres_platos

        col_ds, col_df = st.columns(2)
        actual_semana = st.session_state.perfil.get('desayuno_semana_nombre')
        idx_semana = opciones_desayuno.index(actual_semana) if actual_semana in opciones_desayuno else 0
        elegido_semana = col_ds.selectbox("Entre semana (L-V)", opciones_desayuno, index=idx_semana, key="sel_desayuno_semana")
        st.session_state.perfil['desayuno_semana_nombre'] = None if elegido_semana == "(cálculo genérico)" else elegido_semana

        actual_finde = st.session_state.perfil.get('desayuno_finde_nombre')
        idx_finde = opciones_desayuno.index(actual_finde) if actual_finde in opciones_desayuno else 0
        elegido_finde = col_df.selectbox("Fin de semana (S-D)", opciones_desayuno, index=idx_finde, key="sel_desayuno_finde")
        st.session_state.perfil['desayuno_finde_nombre'] = None if elegido_finde == "(cálculo genérico)" else elegido_finde

        if st.session_state.perfil['desayuno_semana_nombre'] or st.session_state.perfil['desayuno_finde_nombre']:
            if st.button("💾 Recordar esta elección para este atleta", key="guardar_desayuno_defecto"):
                ds.guardar_atleta(st.session_state.perfil)
                st.success("Guardado. Se usará también la próxima vez que abras la app.")

    with st.expander("📂 Cargar un menú ya guardado (de este u otro atleta)", expanded=False):
        st.caption(
            "Los menús se guardan con un nombre elegido por ti y se pueden reutilizar para cualquier "
            "atleta — si es de otro atleta, la app recalcula automáticamente la cantidad de cada plato "
            "(como % de la receta original) según las necesidades de quien lo recibe. Después de "
            "cargarlo puedes seguir tocando lo que necesites."
        )
        menus_guardados = ds.cargar_menus_guardados()
        if not menus_guardados:
            st.info("Todavía no has guardado ningún menú. Genera uno abajo y guárdalo cuando lo tengas a tu gusto.")
        else:
            opciones_menu = list(menus_guardados.keys())
            elegido_menu = st.selectbox(
                "Menú guardado", opciones_menu,
                format_func=lambda n: f"{n} (de {menus_guardados[n].get('atleta_origen', '?')})",
                key="selector_menu_guardado",
            )
            col_cargar, col_borrar = st.columns(2)
            if col_cargar.button("📂 Cargar este menú", type="primary", use_container_width=True):
                datos = menus_guardados[elegido_menu]
                datos_menu_cargado = datos.get("datos_menu", {})
                atleta_origen_cargado = datos.get("atleta_origen", "")
                es_de_otro_atleta = (
                    atleta_origen_cargado and atleta_origen_cargado != st.session_state.perfil.get('nombre')
                )
                if es_de_otro_atleta and datos_menu_cargado:
                    datos_menu_cargado, menu_original_cargado = _recalcular_menu_para_perfil(
                        datos_menu_cargado, st.session_state.perfil,
                    )
                else:
                    menu_original_cargado = datos.get("menu_original", {})
                st.session_state.datos_menu = datos_menu_cargado
                st.session_state.menu_original = menu_original_cargado
                st.session_state.objetivo_semanal_kcal = (
                    sum(v['kcal'] for v in menu_original_cargado.values()) if es_de_otro_atleta
                    else datos.get("objetivo_semanal_kcal")
                )
                st.session_state.bmr_calculado = datos.get("bmr_calculado")
                st.session_state.dias_confirmados = {}
                st.session_state.menu_generado_para = _firma_perfil(st.session_state.perfil)
                st.session_state.menu_cargado_de = atleta_origen_cargado if es_de_otro_atleta else None
                if es_de_otro_atleta:
                    st.success(
                        f"Menú '{elegido_menu}' cargado y **recalculado** a las necesidades de "
                        f"{st.session_state.perfil.get('nombre', 'este atleta')} (mismos platos, "
                        "cantidades ajustadas)."
                    )
                else:
                    st.success(f"Menú '{elegido_menu}' cargado.")
                _persistir_estado_actual()
                st.rerun()
            if col_borrar.button("🗑️ Borrar este menú guardado", use_container_width=True):
                ds.eliminar_menu_guardado(elegido_menu)
                st.success(f"'{elegido_menu}' eliminado.")
                st.rerun()

    if st.session_state.menu_cargado_de:
        st.info(
            f"ℹ️ Este menú se generó originalmente para **{st.session_state.menu_cargado_de}**. Las "
            f"cantidades ya se han recalculado (como % de la receta original) para las necesidades de "
            f"**{st.session_state.perfil.get('nombre', 'este atleta')}** — mismos platos, ración ajustada."
        )

    if st.button("Generar Menú Semanal", icon=":material/auto_awesome:", type="primary"):
        bmr_actual = calcular_bmr(
            st.session_state.perfil.get('peso'), st.session_state.perfil.get('altura_cm'),
            st.session_state.perfil.get('edad'), st.session_state.perfil.get('sexo'),
        )
        intensidades_semana = st.session_state.get('intensidades_semana') or {}
        aviso_platos_faltantes = False
        for dia in DIAS_SEMANA:
            if dia in intensidades_semana:
                intensa = intensidades_semana[dia]
            else:
                intensa = "Alta" if dia == "Miércoles" else "Descanso" if dia in ["Martes", "Viernes"] else "Media"
            objetivo_dia, bmr_dia, tdee_dia = calcular_objetivo_dia(st.session_state.perfil, intensa)
            reparto = repartir_comidas(objetivo_dia)
            macros_dia = calcular_objetivo_macros(st.session_state.perfil, objetivo_dia)
            reparto_macros = repartir_macros_comidas(macros_dia)

            alm = seleccionar_plato(intensa, "Almuerzo", objetivo_kcal=reparto['almuerzo'], objetivo_macros=reparto_macros['almuerzo'])
            cen = seleccionar_plato(intensa, "Cena", objetivo_kcal=reparto['cena'], objetivo_macros=reparto_macros['cena'])
            if alm is None or cen is None:
                aviso_platos_faltantes = True
                continue
            datos_desayuno = _datos_desayuno(dia, reparto['desayuno'], reparto_macros['desayuno'])
            usar_yogur_hoy = DIAS_SEMANA.index(dia) % 2 == 0
            postre_almuerzo = _datos_postre(
                'postre_almuerzo', reparto['postre_almuerzo'], intensa, usar_yogur_hoy,
            )
            postre_cena = _datos_postre(
                'postre_cena', reparto['postre_cena'], intensa, not usar_yogur_hoy,
            )
            objetivo_agua = calcular_objetivo_hidratacion(st.session_state.perfil, intensa)
            st.session_state.datos_menu[dia] = {
                'intensidad': intensa,
                'objetivo_kcal': objetivo_dia,
                'objetivo_macros': macros_dia,
                'objetivo_agua_l': objetivo_agua,
                **datos_desayuno,
                'media_manana': 'Fruta de temporada', 'media_manana_kcal': reparto['media_manana'],
                'media_manana_proteina_g': reparto_macros['media_manana']['proteina_g'],
                'media_manana_carbos_g': reparto_macros['media_manana']['carbos_g'],
                'media_manana_grasa_g': reparto_macros['media_manana']['grasa_g'],
                'merienda': 'Muesli con yogur' if intensa == "Alta" else 'Fruta de temporada',
                'merienda_kcal': reparto['merienda'],
                'merienda_proteina_g': reparto_macros['merienda']['proteina_g'],
                'merienda_carbos_g': reparto_macros['merienda']['carbos_g'],
                'merienda_grasa_g': reparto_macros['merienda']['grasa_g'],
                **postre_almuerzo,
                **postre_cena,
                'almuerzo': alm, 'cena': cen,
            }
            st.session_state.menu_original[dia] = {'kcal': objetivo_dia}
        st.session_state.dias_confirmados = {}
        st.session_state.dia_calendario_seleccionado = DIAS_SEMANA[0] if st.session_state.datos_menu else None
        if aviso_platos_faltantes:
            st.warning("⚠️ No hay suficientes platos en el inventario para cubrir todas las comidas. Añade más platos en 'Subir Mis Platos'.")
        if st.session_state.datos_menu:
            totales_nuevos = {d: kcal_total_dia(v) for d, v in st.session_state.datos_menu.items()}
            st.session_state.objetivo_semanal_kcal = sum(
                st.session_state.menu_original[d]['kcal'] for d in st.session_state.datos_menu
            )
            st.session_state.bmr_calculado = round(bmr_actual)
            macros_totales_nuevos = [macros_total_dia(v) for v in st.session_state.datos_menu.values()]
            n_dias_nuevos = len(macros_totales_nuevos) or 1
            st.session_state.historial_semanas.append({
                'fecha': datetime.now(),
                'total_kcal': sum(totales_nuevos.values()),
                'media_kcal': sum(totales_nuevos.values()) / len(totales_nuevos),
                'media_proteina': sum(m['proteina_g'] for m in macros_totales_nuevos) / n_dias_nuevos,
                'media_carbos': sum(m['carbos_g'] for m in macros_totales_nuevos) / n_dias_nuevos,
                'media_grasa': sum(m['grasa_g'] for m in macros_totales_nuevos) / n_dias_nuevos,
            })
            st.session_state.historial_semanas = st.session_state.historial_semanas[-12:]
            st.session_state.setdefault('historial_por_atleta', {})[st.session_state.perfil.get('nombre', '')] = st.session_state.historial_semanas
            ds.guardar_historial_semanas(st.session_state.perfil.get('nombre', ''), st.session_state.historial_semanas)
            st.session_state.menu_generado_para = _firma_perfil(st.session_state.perfil)
            st.session_state.estado_menu_actual = 'borrador'
            st.session_state.menu_confirmado_id = None
            _persistir_estado_actual()
        st.rerun()

    if st.session_state.datos_menu and st.session_state.menu_generado_para:
        if _firma_perfil(st.session_state.perfil) != st.session_state.menu_generado_para:
            st.warning(
                "⚠️ Has cambiado datos del perfil (objetivo, peso, altura, edad o sexo) desde que se "
                "generó este menú. Las kcal que ves ya no son coherentes con el perfil actual — "
                "vuelve a pulsar **'Generar Menú Semanal'** para recalcularlo."
            )

    if st.session_state.get('bmr_calculado') and st.session_state.datos_menu:
        st.caption(
            f"📐 Calculado a partir de tu perfil: metabolismo basal ≈ **{st.session_state.bmr_calculado} kcal**. "
            "El objetivo de cada día ya tiene en cuenta tu peso, altura, edad, sexo, la intensidad de "
            "entrenamiento de ese día y tu fase actual (arriba, en la barra lateral)."
        )

    if st.session_state.datos_menu:
        # ---------------- Resumen semanal ----------------
        totales = {
            dia: kcal_total_dia(datos)
            for dia, datos in st.session_state.datos_menu.items()
        }
        media_semana = sum(totales.values()) / len(totales)

        r1, r2, r3 = st.columns(3)
        r1.markdown(f'<div class="week-stat"><div class="num">{sum(totales.values())}</div><div class="lbl">🔥 Kcal semana</div></div>', unsafe_allow_html=True)
        r2.markdown(f'<div class="week-stat"><div class="num">{media_semana:.0f}</div><div class="lbl">📊 Media diaria</div></div>', unsafe_allow_html=True)
        r3.markdown(f'<div class="week-stat"><div class="num">{len(totales)}</div><div class="lbl">📅 Días planificados</div></div>', unsafe_allow_html=True)

        macros_reales = [macros_total_dia(d) for d in st.session_state.datos_menu.values()]
        macros_objetivo = [d.get('objetivo_macros', {}) for d in st.session_state.datos_menu.values()]
        if macros_reales and macros_objetivo:
            n = len(macros_reales)
            prot_media = sum(m['proteina_g'] for m in macros_reales) / n
            carb_media = sum(m['carbos_g'] for m in macros_reales) / n
            grasa_media = sum(m['grasa_g'] for m in macros_reales) / n
            prot_obj = sum(m.get('proteina_g', 0) for m in macros_objetivo) / n
            carb_obj = sum(m.get('carbos_g', 0) for m in macros_objetivo) / n
            grasa_obj = sum(m.get('grasa_g', 0) for m in macros_objetivo) / n
            objetivo_kcal_medio = (
                sum(st.session_state.menu_original.get(d, {}).get('kcal', 0) for d in st.session_state.datos_menu) / n
            )
            st.write("")
            mostrar_anillo_hero(media_semana, objetivo_kcal_medio)
            mostrar_anillos_macros(prot_media, prot_obj, carb_media, carb_obj, grasa_media, grasa_obj)
            st.write("")

            deficit_kcal = objetivo_kcal_medio > 0 and media_semana < objetivo_kcal_medio * 0.85
            deficit_prot = prot_obj > 0 and prot_media < prot_obj * 0.85
            if deficit_kcal or deficit_prot:
                st.warning(
                    f"⚠️ **El resultado real se está quedando bastante por debajo del objetivo** "
                    f"({media_semana:.0f} de {objetivo_kcal_medio:.0f} kcal, {prot_media:.0f} de "
                    f"{prot_obj:.0f} g de proteína, de media al día). Esto casi siempre significa que "
                    "**a tu base de datos le faltan platos suficientemente grandes/calóricos** para tus "
                    "necesidades — la app solo puede elegir entre los platos que ya tienes guardados, no "
                    "se los inventa. Revisa en '⚙️ Gestión de Base de Datos' cuáles son tus platos más "
                    "pequeños (ordena la tabla por Kcal), y añade platos más completos o con más "
                    "cantidad de proteína desde '📄 Subir Mis Platos'."
                )

        st.write("")
        chart_df = pd.DataFrame({"Kcal": totales}).reindex(list(st.session_state.datos_menu.keys()))
        st.bar_chart(chart_df, color=BRAND_BLUE, height=160)
        st.write("")
        mostrar_grafica_tendencia(st.session_state.historial_semanas)
        st.write("")

        # ---------------- Tarjetas por día ----------------
        _dibujar_tarjetas_dias_interactivas()
        _persistir_estado_actual()

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### ✅ ¿Ya has ajustado el menú a tu gusto?")
            st.caption(
                f"Al confirmarlo, queda fijado como el plan real de esta semana para "
                f"**{st.session_state.perfil.get('nombre', 'este atleta')}**. A partir de ahí, los "
                "cambios reales (lo que de verdad come, o algún cambio de plato) se registran desde "
                "**'📋 Seguimiento Menú y Atleta'**, y aquí en el Planificador quedará bloqueado hasta "
                "que pulses 'Empezar un menú nuevo' — así puedes seguir generando menús para otros "
                "atletas sin perder de vista este."
            )
            nombre_semana_confirmar = st.text_input(
                "Nombre de esta semana (para tu histórico)",
                value=f"Semana del {date.today().strftime('%d-%m-%Y')}", key="nombre_semana_confirmar",
            )
            if st.button("CONFIRMAR MENÚ", icon=":material/check_circle:", type="primary", use_container_width=True, key="btn_confirmar_menu"):
                id_semana = ds.confirmar_menu(
                    st.session_state.perfil.get('nombre', 'Sin nombre'),
                    st.session_state.datos_menu, st.session_state.menu_original,
                    st.session_state.objetivo_semanal_kcal, st.session_state.bmr_calculado,
                    nombre_semana=nombre_semana_confirmar,
                )
                st.session_state.estado_menu_actual = 'confirmado'
                st.session_state.menu_confirmado_id = id_semana
                _persistir_estado_actual()
                st.success(
                    "Menú confirmado. Los cambios reales de esta semana ya se registran desde "
                    "'📋 Seguimiento Menú y Atleta'."
                )
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("💾 Guardar este menú para reutilizarlo después", expanded=False):
            st.caption(
                "Guárdalo con un nombre (por ejemplo 'Semana 1') para poder cargarlo tal cual más "
                "adelante, con este atleta o con cualquier otro."
            )
            sugerencia_nombre = f"Semana del {date.today().strftime('%d-%m-%Y')}"
            nombre_menu_guardar = st.text_input("Nombre para este menú", value=sugerencia_nombre, key="nombre_menu_guardar")
            if st.button("💾 Guardar menú", type="primary", key="btn_guardar_menu"):
                if not nombre_menu_guardar.strip():
                    st.error("Ponle un nombre al menú para poder guardarlo.")
                else:
                    ds.guardar_menu(
                        nombre_menu_guardar, st.session_state.perfil.get('nombre', 'Sin nombre'),
                        st.session_state.datos_menu, st.session_state.menu_original,
                        st.session_state.objetivo_semanal_kcal, st.session_state.bmr_calculado,
                    )
                    st.success(f"Menú guardado como '{nombre_menu_guardar}'. Podrás cargarlo desde 'Cargar un menú ya guardado', arriba.")

        st.markdown("<br>", unsafe_allow_html=True)
        try:
            ruta_informe = os.path.join(OUTPUT_DIR, "Informe_Planificacion.pdf")
            nota_reutilizacion = None
            if st.session_state.menu_cargado_de:
                nota_reutilizacion = (
                    f"Este menú se diseñó originalmente para {st.session_state.menu_cargado_de} y se ha "
                    f"reutilizado aquí para {st.session_state.perfil.get('nombre', 'este atleta')} tal "
                    "cual, sin recalcular el objetivo calórico ni de macronutrientes individual. "
                    "Revisa que las cantidades y el reparto sigan siendo adecuados para esta persona "
                    "antes de darlo por definitivo, especialmente si su peso, objetivo o intensidad de "
                    "entrenamiento son distintos."
                )
            generar_informe_profesional(
                st.session_state.datos_menu, st.session_state.perfil, ruta_informe,
                historial=st.session_state.historial_semanas,
                nota_reutilizacion=nota_reutilizacion,
            )
            with open(ruta_informe, "rb") as f:
                st.download_button(
                    "📥 Generar Informe Profesional PDF",
                    data=f.read(),
                    file_name="Informe_Planificacion_RPT.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"Error al generar informe: {e}")

        # ---------------- Lista de la compra ----------------
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛒 Lista de la compra de esta semana", expanded=False):
            st.caption(
                "Se calcula sumando los ingredientes de todos los almuerzos y cenas del menú "
                "actual (agrupando el mismo ingrediente aunque se repita en varios días). "
                "Desmarca lo que no quieras incluir en el PDF que descargues."
            )
            lista_compra = generar_lista_compra(st.session_state.datos_menu)

            if not lista_compra["principales"] and not lista_compra["al_gusto"]:
                st.info("No se han encontrado ingredientes en los platos de esta semana.")
            else:
                principales_seleccionados = []
                if lista_compra["principales"]:
                    st.markdown(f"**Para comprar ({len(lista_compra['principales'])}):**")
                    col_izq, col_der = st.columns(2)
                    for i, item in enumerate(lista_compra["principales"]):
                        columna = col_izq if i % 2 == 0 else col_der
                        clave_check = f"compra_check_{i}_{item['nombre']}"
                        marcado = columna.checkbox(
                            f"{item['nombre']} — {item['cantidad_texto']}",
                            value=True,
                            key=clave_check,
                        )
                        if marcado:
                            principales_seleccionados.append(item)

                if lista_compra["al_gusto"]:
                    st.markdown("**Al gusto (revisa si ya tienes):**")
                    st.write(", ".join(lista_compra["al_gusto"]))

                if lista_compra["fijos"]:
                    st.markdown("**También necesitarás (desayunos y meriendas):**")
                    st.write(", ".join(lista_compra["fijos"]))

                st.markdown("---")
                if not principales_seleccionados:
                    st.info("No has dejado ningún ingrediente marcado, así que no hay nada que descargar todavía.")
                else:
                    st.caption(f"Se incluirán {len(principales_seleccionados)} de {len(lista_compra['principales'])} ingredientes marcados en el PDF.")
                    try:
                        lista_compra_exportar = {
                            "principales": principales_seleccionados,
                            "al_gusto": lista_compra["al_gusto"],
                            "fijos": lista_compra["fijos"],
                        }
                        ruta_lista = os.path.join(OUTPUT_DIR, "Lista_Compra.pdf")
                        nombre_atleta = st.session_state.perfil.get('nombre', '').strip()
                        subtitulo_lista = f"Semana actual · {nombre_atleta}" if nombre_atleta else "Semana actual"
                        generar_pdf_lista_compra(lista_compra_exportar, ruta_lista, subtitulo=subtitulo_lista)
                        with open(ruta_lista, "rb") as f:
                            st.download_button(
                                "📥 Descargar Lista de la Compra en PDF",
                                data=f.read(),
                                file_name="Lista_Compra_RPT.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True,
                            )
                    except Exception as e:
                        st.error(f"Error al generar la lista de la compra: {e}")


if 'inventario' not in st.session_state:
    st.session_state.inventario = ds.cargar_inventario()

if 'perfil' not in st.session_state:
    _atletas_iniciales = ds.cargar_atletas()
    if _atletas_iniciales:
        _primer_nombre = list(_atletas_iniciales.keys())[0]
        st.session_state.perfil = _completar_perfil(_atletas_iniciales[_primer_nombre])
        st.session_state.atleta_seleccionado = _primer_nombre
    else:
        st.session_state.perfil = _perfil_vacio()
        st.session_state.atleta_seleccionado = "➕ Nuevo atleta..."
    _cargar_o_reiniciar_menu_actual()

if 'datos_menu' not in st.session_state: st.session_state.datos_menu = {}
if 'menu_original' not in st.session_state: st.session_state.menu_original = {}
if 'historial_semanas' not in st.session_state: st.session_state.historial_semanas = []
if 'historial_por_atleta' not in st.session_state: st.session_state.historial_por_atleta = {}
if 'menu_generado_para' not in st.session_state: st.session_state.menu_generado_para = None
if 'estado_menu_actual' not in st.session_state: st.session_state.estado_menu_actual = 'borrador'
if 'dia_calendario_seleccionado' not in st.session_state: st.session_state.dia_calendario_seleccionado = None
if 'comidas_confirmadas' not in st.session_state: st.session_state.comidas_confirmadas = {}
if 'menu_confirmado_id' not in st.session_state: st.session_state.menu_confirmado_id = None
if 'menu_cargado_de' not in st.session_state: st.session_state.menu_cargado_de = None
if 'intensidades_semana' not in st.session_state: st.session_state.intensidades_semana = {}
if 'detalle_intensidades' not in st.session_state: st.session_state.detalle_intensidades = {}
if 'entreno_nombre_archivo' not in st.session_state: st.session_state.entreno_nombre_archivo = ''
if 'entreno_texto_ocr' not in st.session_state: st.session_state.entreno_texto_ocr = ''
if '_entreno_excel_procesado' not in st.session_state: st.session_state._entreno_excel_procesado = None
if '_entreno_imagen_procesada' not in st.session_state: st.session_state._entreno_imagen_procesada = None
if 'resultados_mealdb' not in st.session_state: st.session_state.resultados_mealdb = []
if 'error_mealdb' not in st.session_state: st.session_state.error_mealdb = None
if 'docx_pendientes' not in st.session_state: st.session_state.docx_pendientes = {}
if 'docx_procesados' not in st.session_state: st.session_state.docx_procesados = set()
if 'docx_guardados' not in st.session_state: st.session_state.docx_guardados = []
if 'dias_confirmados' not in st.session_state: st.session_state.dias_confirmados = {}
if 'objetivo_semanal_kcal' not in st.session_state: st.session_state.objetivo_semanal_kcal = None
if 'seccion_activa' not in st.session_state: st.session_state.seccion_activa = 'menu'
if 'registro_paso' not in st.session_state: st.session_state.registro_paso = 'elegir'
if 'mostrar_resumen_cambios' not in st.session_state: st.session_state.mostrar_resumen_cambios = False


# ------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------------
PORCION_MIN_G = 100
PORCION_MAX_G = 1200


def _escalar_racion(plato_dict, objetivo_kcal):
    """Si el plato tiene registrado el peso de su ración de referencia,
    ajusta la cantidad servida (más o menos gramos de esa misma receta)
    para acercarse al objetivo de kcal de esa comida, escalando los
    macros proporcionalmente — en vez de servir siempre una ración fija
    pensada para una familia. Si no hay datos de peso (platos antiguos, o
    añadidos escribiendo las kcal a mano sin ingredientes), se sirve tal
    cual, como ración fija de siempre."""
    peso_ref = plato_dict.get('Peso_g')
    kcal_ref = plato_dict.get('Kcal')
    if not objetivo_kcal or not peso_ref or not kcal_ref or peso_ref <= 0 or kcal_ref <= 0:
        return plato_dict
    porcion_g = peso_ref * (objetivo_kcal / kcal_ref)
    porcion_g = max(PORCION_MIN_G, min(PORCION_MAX_G, porcion_g))
    factor = porcion_g / peso_ref
    plato_escalado = dict(plato_dict)
    plato_escalado['Kcal'] = round(kcal_ref * factor)
    plato_escalado['Proteina_g'] = round(plato_dict.get('Proteina_g', 0) * factor, 1)
    plato_escalado['Carbos_g'] = round(plato_dict.get('Carbos_g', 0) * factor, 1)
    plato_escalado['Grasas_g'] = round(plato_dict.get('Grasas_g', 0) * factor, 1)
    plato_escalado['Peso_g'] = round(porcion_g)
    plato_escalado['_porcion_g'] = round(porcion_g)
    plato_escalado['_factor_racion'] = factor
    return plato_escalado


def _recalcular_menu_para_perfil(datos_menu, perfil):
    """Cuando se carga un menú guardado originalmente para otro atleta (o
    para el mismo, pero con otro peso/objetivo), recalcula CADA comida
    como un porcentaje de la original: mantiene los mismos platos y el
    mismo reparto entre comidas, pero ajusta la cantidad sana de cada uno
    a las necesidades reales de este atleta — igual que ya se hace al
    generar un menú desde cero, reutilizando el mismo motor de ración
    ajustable (densidad calórica) que ya tienes."""
    nuevo_datos_menu = {}
    nuevo_menu_original = {}
    for dia, datos_dia in datos_menu.items():
        intensidad = datos_dia.get('intensidad', 'Media')
        objetivo_dia, _, _ = calcular_objetivo_dia(perfil, intensidad)
        macros_dia = calcular_objetivo_macros(perfil, objetivo_dia)
        reparto = repartir_comidas(objetivo_dia)
        reparto_macros = repartir_macros_comidas(macros_dia)

        nuevo_dia = dict(datos_dia)
        nuevo_dia['objetivo_kcal'] = objetivo_dia
        nuevo_dia['objetivo_macros'] = macros_dia
        nuevo_dia['objetivo_agua_l'] = calcular_objetivo_hidratacion(perfil, intensidad)

        for tipo_fijo in ['desayuno', 'media_manana', 'merienda', 'postre_almuerzo', 'postre_cena']:
            if tipo_fijo in reparto:
                nuevo_dia[f'{tipo_fijo}_kcal'] = reparto[tipo_fijo]
                nuevo_dia[f'{tipo_fijo}_proteina_g'] = reparto_macros[tipo_fijo]['proteina_g']
                nuevo_dia[f'{tipo_fijo}_carbos_g'] = reparto_macros[tipo_fijo]['carbos_g']
                nuevo_dia[f'{tipo_fijo}_grasa_g'] = reparto_macros[tipo_fijo]['grasa_g']

        nuevo_dia['almuerzo'] = _escalar_racion(dict(datos_dia.get('almuerzo', {})), reparto.get('almuerzo'))
        nuevo_dia['cena'] = _escalar_racion(dict(datos_dia.get('cena', {})), reparto.get('cena'))

        nuevo_datos_menu[dia] = nuevo_dia
        nuevo_menu_original[dia] = {'kcal': objetivo_dia}

    return nuevo_datos_menu, nuevo_menu_original


def seleccionar_plato(intensidad, comida_tipo, objetivo_kcal=None, objetivo_macros=None):
    df = st.session_state.inventario
    df = df[df['Utilizar_en'].str.contains(comida_tipo, case=False, na=False)]
    if intensidad == "Alta":
        opc = df[df['Categoria'] == 'Alto en Hidratos']
    elif intensidad == "Descanso":
        opc = df[df['Categoria'].isin(['Ligero', 'Alto en Proteína'])]
    else:
        opc = df
    if opc.empty:
        opc = df
    if opc.empty:
        return None
    if objetivo_kcal:
        # De entre las opciones válidas para esta intensidad, puntuamos cada
        # plato por lo bien que encaja con el objetivo de esa comida. Si el
        # plato tiene peso conocido (se puede escalar la ración), simulamos
        # cómo quedarían sus macros ya ajustado a las kcal objetivo — así
        # comparamos platos por si su PROPORCIÓN de proteína/carbos/grasa es
        # la adecuada, que es lo que de verdad importa cuando la cantidad
        # servida se puede ajustar (la proteína pesa más en la puntuación:
        # es la que menos margen de error admite para un atleta de fuerza).
        # Nos quedamos con las 3 mejores y elegimos una al azar entre ellas,
        # para no repetir siempre el mismo plato aunque sea el que mejor encaja.
        opc = opc.copy()
        if 'Peso_g' not in opc.columns:
            opc['Peso_g'] = 0.0
        opc['Peso_g'] = opc['Peso_g'].fillna(0.0)
        tiene_peso = (opc['Peso_g'] > 0) & (opc['Kcal'] > 0)

        d_kcal = (opc['Kcal'] - objetivo_kcal).abs() / max(objetivo_kcal, 1)
        d_kcal = d_kcal.where(~tiene_peso, 0.0)  # si se puede escalar, el ajuste de kcal es (casi) perfecto

        if objetivo_macros:
            factor_sim = (objetivo_kcal / opc['Kcal'].replace(0, 1)).where(tiene_peso, 1.0)
            prot_sim = opc['Proteina_g'] * factor_sim
            carb_sim = opc['Carbos_g'] * factor_sim
            grasa_sim = opc['Grasas_g'] * factor_sim
            d_prot = (prot_sim - objetivo_macros.get('proteina_g', 0)).abs() / max(objetivo_macros.get('proteina_g', 0), 1)
            d_carb = (carb_sim - objetivo_macros.get('carbos_g', 0)).abs() / max(objetivo_macros.get('carbos_g', 0), 1)
            d_grasa = (grasa_sim - objetivo_macros.get('grasa_g', 0)).abs() / max(objetivo_macros.get('grasa_g', 0), 1)
            opc['_dif'] = d_kcal * 0.40 + d_prot * 0.35 + d_carb * 0.15 + d_grasa * 0.10
        else:
            opc['_dif'] = d_kcal
        candidatas = opc.sort_values('_dif').head(3)
        elegido = candidatas.sample(1).iloc[0].drop('_dif').to_dict()
        return _escalar_racion(elegido, objetivo_kcal)
    return opc.sample(1).iloc[0].to_dict()


def kcal_total_dia(datos_dia):
    """Kcal totales reales de un día: almuerzo + cena (platos de verdad)
    más las kcal calculadas para desayuno, media mañana, merienda y los
    postres de almuerzo y cena (ya no un '+600' fijo e inventado)."""
    return (
        datos_dia['almuerzo'].get('Kcal', 0) + datos_dia['cena'].get('Kcal', 0)
        + datos_dia.get('desayuno_kcal', 0) + datos_dia.get('media_manana_kcal', 0)
        + datos_dia.get('merienda_kcal', 0)
        + datos_dia.get('postre_almuerzo_kcal', 0) + datos_dia.get('postre_cena_kcal', 0)
    )


# Datos reales del yogur griego natural (light) que usas — valores tal
# cual del etiquetado, por 100 g.
YOGUR_GRIEGO_KCAL_100G = 60
YOGUR_GRIEGO_PROT_100G = 5.8
YOGUR_GRIEGO_CARB_100G = 4.7
YOGUR_GRIEGO_GRASA_100G = 2.0

# Fruta de temporada media (estimación orientativa: manzana/naranja/pera...)
FRUTA_KCAL_100G = 55
FRUTA_PROT_100G = 0.6
FRUTA_CARB_100G = 13.0
FRUTA_GRASA_100G = 0.2


def _calcular_postre_componente(nombre, kcal_100g, prot_100g, carb_100g, grasa_100g, objetivo_kcal, peso_min, peso_max):
    objetivo_kcal = max(objetivo_kcal or 0, 40)
    gramos = max(peso_min, min(peso_max, objetivo_kcal / kcal_100g * 100))
    factor = gramos / 100
    return {
        'nombre': nombre, 'kcal': round(kcal_100g * factor),
        'proteina_g': round(prot_100g * factor, 1), 'carbos_g': round(carb_100g * factor, 1),
        'grasa_g': round(grasa_100g * factor, 1),
    }


def _datos_postre(clave_postre, objetivo_kcal_postre, intensidad, usar_yogur):
    """Genera el postre de almuerzo o cena: fruta de temporada, yogur
    griego natural (con los valores reales de tu etiqueta) o ambos a la
    vez. Alterna entre las dos opciones para que no se repita siempre lo
    mismo, y usa las dos combinadas en los días de entrenamiento fuerte
    (más proteína de recuperación)."""
    if intensidad == "Alta":
        kcal_yogur = (objetivo_kcal_postre or 0) * 0.55
        kcal_fruta = (objetivo_kcal_postre or 0) * 0.45
        yogur = _calcular_postre_componente(
            "yogur", YOGUR_GRIEGO_KCAL_100G, YOGUR_GRIEGO_PROT_100G, YOGUR_GRIEGO_CARB_100G, YOGUR_GRIEGO_GRASA_100G,
            kcal_yogur, 60, 250,
        )
        fruta = _calcular_postre_componente(
            "fruta", FRUTA_KCAL_100G, FRUTA_PROT_100G, FRUTA_CARB_100G, FRUTA_GRASA_100G, kcal_fruta, 80, 350,
        )
        nombre = "Yogur griego natural con fruta de temporada"
        kcal = yogur['kcal'] + fruta['kcal']
        prot = round(yogur['proteina_g'] + fruta['proteina_g'], 1)
        carb = round(yogur['carbos_g'] + fruta['carbos_g'], 1)
        grasa = round(yogur['grasa_g'] + fruta['grasa_g'], 1)
    elif usar_yogur:
        resultado = _calcular_postre_componente(
            "Yogur griego natural", YOGUR_GRIEGO_KCAL_100G, YOGUR_GRIEGO_PROT_100G,
            YOGUR_GRIEGO_CARB_100G, YOGUR_GRIEGO_GRASA_100G, objetivo_kcal_postre, 80, 300,
        )
        nombre, kcal, prot, carb, grasa = resultado['nombre'], resultado['kcal'], resultado['proteina_g'], resultado['carbos_g'], resultado['grasa_g']
    else:
        resultado = _calcular_postre_componente(
            "Fruta de temporada", FRUTA_KCAL_100G, FRUTA_PROT_100G, FRUTA_CARB_100G, FRUTA_GRASA_100G,
            objetivo_kcal_postre, 100, 400,
        )
        nombre, kcal, prot, carb, grasa = resultado['nombre'], resultado['kcal'], resultado['proteina_g'], resultado['carbos_g'], resultado['grasa_g']

    return {
        clave_postre: nombre, f'{clave_postre}_kcal': kcal,
        f'{clave_postre}_proteina_g': prot, f'{clave_postre}_carbos_g': carb,
        f'{clave_postre}_grasa_g': grasa,
    }


def _datos_desayuno(dia, reparto_kcal_desayuno, reparto_macros_desayuno):
    """Si el atleta tiene configurado un desayuno real (de su base de
    datos) para entre semana o fin de semana, lo usa tal cual (con sus
    kcal y macros reales). Si no, usa el cálculo genérico de siempre."""
    es_finde = dia in ("Sábado", "Domingo")
    campo = 'desayuno_finde_nombre' if es_finde else 'desayuno_semana_nombre'
    nombre_configurado = st.session_state.perfil.get(campo)
    if nombre_configurado:
        coincidencias = st.session_state.inventario[st.session_state.inventario['Plato'] == nombre_configurado]
        if not coincidencias.empty:
            fila = coincidencias.iloc[0]
            return {
                'desayuno': fila['Plato'], 'desayuno_kcal': int(fila['Kcal']),
                'desayuno_proteina_g': float(fila['Proteina_g']), 'desayuno_carbos_g': float(fila['Carbos_g']),
                'desayuno_grasa_g': float(fila['Grasas_g']),
            }
    nombre_generico = 'Tostadas' if es_finde else 'Porridge con huevos'
    return {
        'desayuno': nombre_generico, 'desayuno_kcal': reparto_kcal_desayuno,
        'desayuno_proteina_g': reparto_macros_desayuno['proteina_g'],
        'desayuno_carbos_g': reparto_macros_desayuno['carbos_g'],
        'desayuno_grasa_g': reparto_macros_desayuno['grasa_g'],
    }


def macros_total_dia(datos_dia):
    """Gramos totales reales de proteína / carbohidratos / grasa de un día:
    los de los platos de verdad (almuerzo y cena) más los ya calculados
    para desayuno, media mañana, merienda y los postres de almuerzo y cena."""
    prot = (
        datos_dia['almuerzo'].get('Proteina_g', 0) + datos_dia['cena'].get('Proteina_g', 0)
        + datos_dia.get('desayuno_proteina_g', 0) + datos_dia.get('media_manana_proteina_g', 0)
        + datos_dia.get('merienda_proteina_g', 0)
        + datos_dia.get('postre_almuerzo_proteina_g', 0) + datos_dia.get('postre_cena_proteina_g', 0)
    )
    carb = (
        datos_dia['almuerzo'].get('Carbos_g', 0) + datos_dia['cena'].get('Carbos_g', 0)
        + datos_dia.get('desayuno_carbos_g', 0) + datos_dia.get('media_manana_carbos_g', 0)
        + datos_dia.get('merienda_carbos_g', 0)
        + datos_dia.get('postre_almuerzo_carbos_g', 0) + datos_dia.get('postre_cena_carbos_g', 0)
    )
    grasa = (
        datos_dia['almuerzo'].get('Grasas_g', 0) + datos_dia['cena'].get('Grasas_g', 0)
        + datos_dia.get('desayuno_grasa_g', 0) + datos_dia.get('media_manana_grasa_g', 0)
        + datos_dia.get('merienda_grasa_g', 0)
        + datos_dia.get('postre_almuerzo_grasa_g', 0) + datos_dia.get('postre_cena_grasa_g', 0)
    )
    return {'proteina_g': round(prot, 1), 'carbos_g': round(carb, 1), 'grasa_g': round(grasa, 1)}


def chip_categoria_html(categoria):
    bg = CAT_BG.get(categoria, "#EEE")
    tx = CAT_TEXT.get(categoria, "#555")
    return f'<span class="cat-chip" style="background-color:{bg};color:{tx};">{categoria}</span>'


def persistir_inventario():
    ds.guardar_inventario(st.session_state.inventario)


def guardar_plato_en_inventario(fila_dict):
    """Añade un plato nuevo al inventario y lo persiste en disco."""
    columnas = ["Plato", "Categoria", "Kcal", "Proteina_g", "Carbos_g", "Grasas_g", "Peso_g", "Utilizar_en", "Ingredientes", "Preparacion"]
    fila_limpia = {c: fila_dict.get(c, "") for c in columnas}
    if not fila_limpia.get("Peso_g"):
        fila_limpia["Peso_g"] = 0.0
    nueva_fila = pd.DataFrame([fila_limpia])
    st.session_state.inventario = pd.concat([st.session_state.inventario, nueva_fila], ignore_index=True)
    persistir_inventario()


def recalcular_semana(dia_origen):
    """Tras confirmar lo que se ha comido realmente un día, reparte la
    diferencia de kcal entre los días restantes de la semana (los que
    todavía no se han confirmado), eligiendo para cada uno la alternativa
    disponible en el inventario que más se acerque al nuevo objetivo.
    Devuelve una lista de los cambios aplicados, para poder explicarlos."""
    objetivo_total = st.session_state.objetivo_semanal_kcal
    if not objetivo_total:
        return []

    dias_confirmados = st.session_state.dias_confirmados
    orden = [d for d in st.session_state.datos_menu.keys()]
    restantes = [d for d in orden if d not in dias_confirmados]
    if not restantes:
        return []

    kcal_confirmados = sum(
        kcal_total_dia(st.session_state.datos_menu[d])
        for d in dias_confirmados
    )
    objetivo_restante_total = objetivo_total - kcal_confirmados
    objetivo_por_dia = objetivo_restante_total / len(restantes)

    df = st.session_state.inventario
    cambios = []
    for d in restantes:
        datos_dia = st.session_state.datos_menu[d]
        kcal_actual_dia = kcal_total_dia(datos_dia)
        diferencia = objetivo_por_dia - kcal_actual_dia
        if abs(diferencia) < 60:
            continue

        for tipo_ajuste in ['cena', 'almuerzo']:
            plato_actual = datos_dia[tipo_ajuste]
            objetivo_plato = plato_actual['Kcal'] + diferencia
            comida_tipo = 'Cena' if tipo_ajuste == 'cena' else 'Almuerzo'
            candidatos = df[df['Utilizar_en'].str.contains(comida_tipo, case=False, na=False)]
            candidatos = candidatos[candidatos['Plato'] != plato_actual['Plato']]
            if candidatos.empty:
                continue
            candidatos = candidatos.copy()
            candidatos['dif'] = (candidatos['Kcal'] - objetivo_plato).abs()
            mejor = candidatos.sort_values('dif').iloc[0]
            if mejor['dif'] < abs(diferencia):
                nombre_antiguo, kcal_antiguo = plato_actual['Plato'], plato_actual['Kcal']
                st.session_state.datos_menu[d][tipo_ajuste] = mejor.drop('dif').to_dict()
                cambios.append({
                    'dia': d, 'tipo': tipo_ajuste,
                    'antes': nombre_antiguo, 'kcal_antes': kcal_antiguo,
                    'despues': mejor['Plato'], 'kcal_despues': mejor['Kcal'],
                })
                break
    return cambios


# Si se acaba de confirmar una comida real (desde dialog_registrar_real),
# esto se detecta aquí, en el nivel principal del script, para poder abrir
# después el resumen de cambios con normalidad (no puede hacerse dentro del
# propio bloque del botón, porque ese bloque solo se ejecuta en el instante
# del clic, no en el rerun donde el diálogo ya se ha cerrado).
if st.session_state.get('dia_recien_confirmado'):
    _dia_c = st.session_state.pop('dia_recien_confirmado')
    if _dia_c in st.session_state.datos_menu and _dia_c in st.session_state.menu_original:
        _k_actual_dia = kcal_total_dia(st.session_state.datos_menu[_dia_c])
        _k_orig = st.session_state.menu_original[_dia_c]['kcal']
        st.session_state['dia_origen_cambio'] = _dia_c
        st.session_state['desvio_origen_cambio'] = _k_actual_dia - _k_orig
        st.session_state['cambios_recalculo'] = recalcular_semana(_dia_c)
        st.session_state.mostrar_resumen_cambios = True


# ------------------------------------------------------------------
# VENTANA EMERGENTE · SUSTITUIR UN PLATO PLANEADO
# ------------------------------------------------------------------
@st.dialog("Cambiar plato", width="large")
def dialog_sustituir(dia, tipo):
    plato_actual = st.session_state.datos_menu[dia][tipo]
    comida_tipo = "Almuerzo" if tipo == "almuerzo" else "Cena"

    st.markdown(f"Sustituyendo **{plato_actual['Plato']}** en **{dia} · {comida_tipo.lower()}**")
    st.markdown(chip_categoria_html(plato_actual['Categoria']) + f"&nbsp;&nbsp;{plato_actual['Kcal']} kcal", unsafe_allow_html=True)
    st.divider()

    busqueda = st.text_input("Buscar por nombre", "", placeholder="Ej: pollo, arroz...")
    col_f1, col_f2 = st.columns(2)
    solo_misma_categoria = col_f1.checkbox("Solo misma categoría", value=False)
    solo_etiquetados = col_f2.checkbox(
        f"Solo platos marcados para {comida_tipo.lower()}", value=False,
        help="Si lo desmarcas (por defecto), se muestran TODOS tus platos, sin mirar la etiqueta 'Utilizar en'.",
    )

    df = st.session_state.inventario
    disponibles = df[df['Plato'] != plato_actual['Plato']]
    if solo_etiquetados:
        disponibles = disponibles[disponibles['Utilizar_en'].str.contains(comida_tipo, case=False, na=False)]
    if solo_misma_categoria:
        disponibles = disponibles[disponibles['Categoria'] == plato_actual['Categoria']]
    if busqueda:
        disponibles = disponibles[disponibles['Plato'].str.contains(busqueda, case=False, na=False)]

    st.caption(f"{len(disponibles)} de {len(df)} platos en tu base de datos encajan con estos filtros.")

    if disponibles.empty:
        st.info("No hay platos que encajen con estos filtros. Prueba a desmarcar alguna casilla o añade platos nuevos desde 'Subir Mis Platos'.")
    else:
        for idx, fila in disponibles.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{fila['Plato']}**")
                    st.markdown(
                        chip_categoria_html(fila['Categoria']) + f"&nbsp;&nbsp;{fila['Kcal']} kcal",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.write("")
                    if st.button("Elegir", key=f"choose_{dia}_{tipo}_{idx}", use_container_width=True):
                        objetivo_dia = st.session_state.datos_menu[dia].get('objetivo_kcal')
                        objetivo_comida = repartir_comidas(objetivo_dia).get(tipo) if objetivo_dia else None
                        st.session_state.datos_menu[dia][tipo] = _escalar_racion(fila.to_dict(), objetivo_comida)
                        st.rerun()

    st.divider()
    with st.expander("➕ No está en mi lista: añadir un plato nuevo y usarlo aquí mismo"):
        tab_manual, tab_word = st.tabs(["✏️ Describirlo", "📄 Subir desde Word"])

        with tab_manual:
            st.caption(
                "Descríbelo y lo calculo con el mismo motor que el resto de la app. Se guarda en tu "
                "base de datos (para poder usarlo también otro día) y se aplica aquí al momento."
            )
            nombre_nuevo = st.text_input("Nombre del plato", key=f"nuevo_nombre_{dia}_{tipo}")
            c_rac, c_util = st.columns(2)
            raciones_nuevo = c_rac.number_input("Raciones", min_value=1, value=4, key=f"nuevo_raciones_{dia}_{tipo}")
            c_util.text_input("Utilizar en", value=comida_tipo, disabled=True, key=f"nuevo_util_{dia}_{tipo}")
            ingredientes_nuevo = st.text_area(
                "Ingredientes (uno por línea, con cantidad si la sabes)", key=f"nuevo_ingr_{dia}_{tipo}",
                placeholder="200 gr merluza\n1 vaso de vino blanco\n2 patatas", height=100,
            )
            prep_nuevo = st.text_area("Preparación (opcional)", key=f"nuevo_prep_{dia}_{tipo}", height=70)

            if st.button("Calcular y usar ahora", type="primary", key=f"nuevo_calcular_{dia}_{tipo}"):
                if not nombre_nuevo.strip() or not ingredientes_nuevo.strip():
                    st.error("Necesito al menos el nombre y los ingredientes.")
                else:
                    lineas = [l for l in ingredientes_nuevo.split("\n") if l.strip()]
                    kcal_n, prot_n, carb_n, grasa_n, peso_n, no_rec_n = estimar_macros(lineas, raciones_nuevo)
                    categoria_n = categorizar(kcal_n, prot_n, carb_n, grasa_n)
                    nuevo_plato_dict = {
                        "Plato": nombre_nuevo.strip(), "Categoria": categoria_n, "Kcal": int(kcal_n),
                        "Proteina_g": float(prot_n), "Carbos_g": float(carb_n), "Grasas_g": float(grasa_n),
                        "Peso_g": float(peso_n), "Utilizar_en": comida_tipo, "Ingredientes": ", ".join(lineas),
                        "Preparacion": prep_nuevo,
                    }
                    if no_rec_n:
                        st.warning(f"No he reconocido: {', '.join(no_rec_n)}. La estimación puede no ser exacta; podrás corregirla luego en 'Gestión de Base de Datos'.")
                    similares_n = ds.buscar_platos_similares(nombre_nuevo, st.session_state.inventario)
                    if similares_n:
                        nombre_sim_n, ratio_sim_n = similares_n[0]
                        st.info(f"ℹ️ Ya tienes un plato parecido: **{nombre_sim_n}** ({ratio_sim_n*100:.0f}% de parecido). Se guardará igualmente como plato nuevo.")
                    guardar_plato_en_inventario(nuevo_plato_dict)
                    objetivo_dia_n = st.session_state.datos_menu[dia].get('objetivo_kcal')
                    objetivo_comida_n = repartir_comidas(objetivo_dia_n).get(tipo) if objetivo_dia_n else None
                    st.session_state.datos_menu[dia][tipo] = _escalar_racion(dict(nuevo_plato_dict), objetivo_comida_n)
                    st.success(f"'{nuevo_plato_dict['Plato']}' calculado, guardado y aplicado a {dia.lower()}.")
                    st.rerun()

        with tab_word:
            st.caption(
                "Sube una ficha de receta en Word (con ingredientes) y se calcula igual que en "
                "'📄 Subir Mis Platos': se guarda en tu base de datos y se aplica aquí al momento."
            )
            archivo_word = st.file_uploader("Documento Word (.docx)", type=["docx"], key=f"nuevo_word_{dia}_{tipo}")
            if archivo_word is not None:
                try:
                    plato_word = procesar_docx_a_plato(archivo_word)
                except Exception as e:
                    st.error(f"No se ha podido leer el documento: {e}")
                    plato_word = None
                if plato_word:
                    st.markdown(f"**{plato_word['Plato']}**")
                    st.markdown(
                        chip_categoria_html(plato_word['Categoria']) + f"&nbsp;&nbsp;{plato_word['Kcal']} kcal/ración",
                        unsafe_allow_html=True,
                    )
                    if plato_word.get('_ingredientes_no_reconocidos'):
                        st.warning(f"No he reconocido: {', '.join(plato_word['_ingredientes_no_reconocidos'])}. La estimación puede no ser exacta.")
                    plato_word['Utilizar_en'] = comida_tipo
                    if st.button("Guardar y usar ahora", type="primary", key=f"nuevo_word_usar_{dia}_{tipo}"):
                        plato_word_limpio = {k: v for k, v in plato_word.items() if not k.startswith("_")}
                        similares_w = ds.buscar_platos_similares(plato_word_limpio['Plato'], st.session_state.inventario)
                        if similares_w:
                            nombre_sim_w, ratio_sim_w = similares_w[0]
                            st.info(f"ℹ️ Ya tienes un plato parecido: **{nombre_sim_w}** ({ratio_sim_w*100:.0f}% de parecido). Se guardará igualmente como plato nuevo.")
                        guardar_plato_en_inventario(plato_word_limpio)
                        objetivo_dia_w = st.session_state.datos_menu[dia].get('objetivo_kcal')
                        objetivo_comida_w = repartir_comidas(objetivo_dia_w).get(tipo) if objetivo_dia_w else None
                        st.session_state.datos_menu[dia][tipo] = _escalar_racion(dict(plato_word_limpio), objetivo_comida_w)
                        st.success(f"'{plato_word_limpio['Plato']}' guardado y aplicado a {dia.lower()}.")
                        st.rerun()


# ------------------------------------------------------------------
# VENTANA EMERGENTE · CAMBIAR DESAYUNO / MEDIA MAÑANA / MERIENDA
# ------------------------------------------------------------------
ETIQUETAS_COMIDA_FIJA = {
    "desayuno": "Desayuno", "media_manana": "Media mañana", "merienda": "Merienda",
    "postre_almuerzo": "Postre (almuerzo)", "postre_cena": "Postre (cena)",
}


@st.dialog("Cambiar comida", width="large")
def dialog_editar_comida_fija(dia, tipo):
    etiqueta = ETIQUETAS_COMIDA_FIJA.get(tipo, tipo)
    datos_dia = st.session_state.datos_menu[dia]
    nombre_actual = datos_dia.get(tipo, "")
    kcal_actual = datos_dia.get(f"{tipo}_kcal", 0)

    st.markdown(f"Cambiando **{etiqueta.lower()}** del **{dia}** — ahora mismo: *{nombre_actual}* ({kcal_actual} kcal)")
    st.divider()

    modo = st.radio("¿Cómo quieres ponerlo?", ["Escribirlo libremente", "Elegir de mi lista de platos"], horizontal=True)

    if modo == "Escribirlo libremente":
        st.caption("Por ejemplo: 'Tostadas con tomate y aceite', 'Café con leche y bizcocho'... Ajusta las kcal a ojo o mantenlas.")
        nombre_nuevo = st.text_input("Nombre", value=nombre_actual)
        kcal_nuevo = st.number_input("Kcal aproximadas", value=int(kcal_actual), min_value=0, step=10)
        if st.button("Guardar", type="primary", use_container_width=True):
            factor = (kcal_nuevo / kcal_actual) if kcal_actual else 1.0
            st.session_state.datos_menu[dia][tipo] = nombre_nuevo
            st.session_state.datos_menu[dia][f"{tipo}_kcal"] = kcal_nuevo
            # Escalamos los macros que ya tenía proporcionalmente al nuevo kcal,
            # para no perder la coherencia con el objetivo del día.
            for macro in ("proteina_g", "carbos_g", "grasa_g"):
                clave = f"{tipo}_{macro}"
                st.session_state.datos_menu[dia][clave] = round(st.session_state.datos_menu[dia].get(clave, 0) * factor, 1)
            st.rerun()
    else:
        busqueda = st.text_input("Buscar en tu lista de platos", "")
        df = st.session_state.inventario
        disponibles = df
        if busqueda:
            disponibles = disponibles[disponibles['Plato'].str.contains(busqueda, case=False, na=False)]
        if disponibles.empty:
            st.info("No hay platos que coincidan con la búsqueda.")
        else:
            for idx, fila in disponibles.head(10).iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{fila['Plato']}**")
                        st.markdown(
                            chip_categoria_html(fila['Categoria']) + f"&nbsp;&nbsp;{fila['Kcal']} kcal",
                            unsafe_allow_html=True,
                        )
                    with c2:
                        st.write("")
                        if st.button("Elegir", key=f"choose_fijo_{dia}_{tipo}_{idx}", use_container_width=True):
                            st.session_state.datos_menu[dia][tipo] = fila['Plato']
                            st.session_state.datos_menu[dia][f"{tipo}_kcal"] = fila['Kcal']
                            st.session_state.datos_menu[dia][f"{tipo}_proteina_g"] = fila['Proteina_g']
                            st.session_state.datos_menu[dia][f"{tipo}_carbos_g"] = fila['Carbos_g']
                            st.session_state.datos_menu[dia][f"{tipo}_grasa_g"] = fila['Grasas_g']
                            st.rerun()


# ------------------------------------------------------------------
# VENTANA EMERGENTE · AVISO DE PLATO POSIBLEMENTE DUPLICADO
# ------------------------------------------------------------------
@st.dialog("⚠️ Posible plato duplicado")
def dialog_confirmar_duplicado():
    info = st.session_state.get('duplicado_pendiente')
    if not info:
        st.write("No hay ningún plato pendiente de confirmar.")
        return

    fila = info['fila']
    similares = info['similares']
    clave_docx = info.get('clave_docx_pendiente')
    nombre_similar, ratio = similares[0]

    st.warning(
        f"Ya tienes un plato parecido en tu base de datos: **{nombre_similar}** "
        f"({ratio*100:.0f}% de parecido con **{fila['Plato']}**)."
    )
    st.caption("¿Qué quieres hacer?")

    if st.button("➕ Guardar de todas formas, como plato nuevo", use_container_width=True):
        guardar_plato_en_inventario(fila)
        if clave_docx and clave_docx in st.session_state.docx_pendientes:
            del st.session_state.docx_pendientes[clave_docx]
        st.session_state.docx_guardados.append(fila['Plato'])
        st.session_state['duplicado_pendiente'] = None
        st.rerun()

    if st.button(f"🔁 Reemplazar '{nombre_similar}' por este plato nuevo", use_container_width=True):
        df = st.session_state.inventario
        st.session_state.inventario = df[df['Plato'] != nombre_similar].reset_index(drop=True)
        guardar_plato_en_inventario(fila)
        if clave_docx and clave_docx in st.session_state.docx_pendientes:
            del st.session_state.docx_pendientes[clave_docx]
        st.session_state.docx_guardados.append(fila['Plato'])
        st.session_state['duplicado_pendiente'] = None
        st.rerun()

    if st.button("❌ Cancelar, no guardar", use_container_width=True):
        st.session_state['duplicado_pendiente'] = None
        st.rerun()


# ------------------------------------------------------------------
# VENTANA EMERGENTE · REGISTRAR LO QUE SE HA COMIDO REALMENTE
# ------------------------------------------------------------------
@st.dialog("📝 Registrar lo que has comido", width="large")
def dialog_registrar_real(dia, tipo):
    plato_planeado = st.session_state.datos_menu[dia][tipo]
    comida_tipo = "Almuerzo" if tipo == "almuerzo" else "Cena"
    st.markdown(f"**{dia} · {comida_tipo}** — tenías planeado: *{plato_planeado['Plato']}* ({plato_planeado['Kcal']} kcal)")
    st.divider()

    paso = st.session_state.registro_paso

    if paso == 'elegir':
        if st.button("✅ Comí exactamente lo planeado", type="primary", use_container_width=True):
            st.session_state.dias_confirmados[dia] = True
            st.session_state['dia_recien_confirmado'] = dia
            st.rerun()

        st.write("¿O comiste otra cosa? Búscala en tu lista:")
        df = st.session_state.inventario
        disponibles = df
        busqueda = st.text_input("Buscar en tu lista de platos", "", key="busqueda_real")
        if busqueda:
            disponibles = disponibles[disponibles['Plato'].str.contains(busqueda, case=False, na=False)]
        st.caption(f"{len(disponibles)} de {len(df)} platos en tu base de datos.")
        for idx, fila in disponibles.head(15).iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{fila['Plato']}** — {fila['Kcal']} kcal")
                if c2.button("Elegir", key=f"real_choose_{dia}_{tipo}_{idx}", use_container_width=True):
                    st.session_state.datos_menu[dia][tipo] = fila.to_dict()
                    st.session_state.dias_confirmados[dia] = True
                    st.session_state['dia_recien_confirmado'] = dia
                    st.rerun()

        st.divider()
        if st.button("✍️ No está en mi lista, quiero describirlo", use_container_width=True):
            st.session_state.registro_paso = 'wizard'

    elif paso == 'wizard':
        st.write("Cuéntame el plato y calculo las calorías por ti, igual que con los documentos que subes:")
        nombre_w = st.text_input("Nombre del plato", key="wiz_nombre")
        raciones_w = st.number_input("¿Para cuántas raciones son esos ingredientes?", min_value=1, value=1, key="wiz_raciones")
        ingredientes_w = st.text_area(
            "Ingredientes (uno por línea, con cantidad si la sabes)", key="wiz_ingr",
            placeholder="150 gr merluza\n1 taza de arroz basmati\n1 cucharada de aceite de oliva",
            height=110,
        )
        preparacion_w = st.text_area("¿Cómo se preparó? (opcional, breve)", key="wiz_prep", height=70)

        cw1, cw2 = st.columns(2)
        if cw1.button("Calcular", type="primary", use_container_width=True):
            if not nombre_w.strip() or not ingredientes_w.strip():
                st.error("Necesito al menos el nombre y los ingredientes.")
            else:
                lineas = [l for l in ingredientes_w.split("\n") if l.strip()]
                kcal, prot, carb, grasa, peso, no_reconocidos = estimar_macros(lineas, raciones_w)
                categoria = categorizar(kcal, prot, carb, grasa)
                st.session_state['wizard_resultado'] = {
                    "Plato": nombre_w.strip(), "Categoria": categoria, "Kcal": int(kcal),
                    "Proteina_g": float(prot), "Carbos_g": float(carb), "Grasas_g": float(grasa),
                    "Peso_g": float(peso), "Utilizar_en": comida_tipo, "Ingredientes": ", ".join(lineas),
                    "Preparacion": preparacion_w,
                }
                st.session_state['wizard_no_reconocidos'] = no_reconocidos
                st.session_state.registro_paso = 'confirmar_wizard'
        if cw2.button("← Volver", use_container_width=True):
            st.session_state.registro_paso = 'elegir'

    elif paso == 'confirmar_wizard':
        nuevo_plato = st.session_state['wizard_resultado']
        no_reconocidos = st.session_state.get('wizard_no_reconocidos', [])
        st.success(f"He calculado: **{nuevo_plato['Plato']}** — {nuevo_plato['Kcal']} kcal · {nuevo_plato['Categoria']}")
        st.caption(f"Proteína {nuevo_plato['Proteina_g']} g · Carbohidratos {nuevo_plato['Carbos_g']} g · Grasas {nuevo_plato['Grasas_g']} g")
        if no_reconocidos:
            st.warning(f"No he reconocido estos ingredientes para el cálculo: {', '.join(no_reconocidos)}. La estimación puede no ser muy exacta.")

        guardar_en_bbdd = st.checkbox("Guardar también este plato en mi base de datos para futuras veces", value=True)

        if guardar_en_bbdd:
            similares = ds.buscar_platos_similares(nuevo_plato['Plato'], st.session_state.inventario)
            if similares:
                nombre_similar, ratio = similares[0]
                st.info(f"ℹ️ Ya tienes un plato parecido: **{nombre_similar}** ({ratio*100:.0f}% de parecido). Se guardará igualmente como plato nuevo si continúas.")

        if st.button("✅ Usar este plato como lo que he comido hoy", type="primary", use_container_width=True):
            if guardar_en_bbdd:
                guardar_plato_en_inventario(nuevo_plato)
                st.session_state.docx_guardados.append(nuevo_plato['Plato'])
            st.session_state.datos_menu[dia][tipo] = nuevo_plato
            st.session_state.dias_confirmados[dia] = True
            st.session_state.registro_paso = 'elegir'
            st.session_state['dia_recien_confirmado'] = dia
            st.rerun()


# ------------------------------------------------------------------
# VENTANA EMERGENTE · RESUMEN DE CAMBIOS TRAS RECALCULAR LA SEMANA
# ------------------------------------------------------------------
@st.dialog("📋 Cambios aplicados en la semana")
def dialog_resumen_cambios():
    cambios = st.session_state.get('cambios_recalculo', [])
    origen = st.session_state.get('dia_origen_cambio', '')
    desvio = st.session_state.get('desvio_origen_cambio', 0)

    if origen:
        if abs(desvio) < 30:
            st.markdown(f"Has registrado el cambio en **{origen}**, muy cerca de lo planeado (no ha hecho falta ajustar nada más).")
        else:
            signo = "un exceso de" if desvio > 0 else "un déficit de"
            st.markdown(f"Al registrar el cambio en **{origen}**, se ha generado {signo} **{abs(desvio):.0f} kcal** respecto al plan original de ese día.")

    if not cambios:
        st.info("No ha hecho falta tocar el resto de la semana: el desvío es pequeño, o no había en tu base de datos una alternativa mejor con la que compensarlo.")
    else:
        st.markdown(f"Para mantener el objetivo semanal, se han ajustado **{len(cambios)} comida(s)** en los días que quedaban por delante:")
        for c in cambios:
            diferencia = c['kcal_despues'] - c['kcal_antes']
            signo_c = "+" if diferencia > 0 else ""
            st.markdown(
                f"- **{c['dia']} · {c['tipo']}**: {c['antes']} ({c['kcal_antes']} kcal) → "
                f"**{c['despues']}** ({c['kcal_despues']} kcal, {signo_c}{diferencia:.0f} kcal)"
            )
        st.caption("Si no te convence alguno de estos cambios, puedes deshacerlo con el botón 'Cambiar' de esa comida, como siempre.")

    if st.button("Entendido", type="primary", use_container_width=True):
        st.session_state.mostrar_resumen_cambios = False
        st.session_state['cambios_recalculo'] = []
        st.rerun()


# --- BARRA LATERAL: ATLETA Y PERFIL ---
with st.sidebar:
    st.header("👤 Atleta")
    atletas_guardados = ds.cargar_atletas()
    nombres_atletas = list(atletas_guardados.keys())
    opciones_atleta = ["➕ Nuevo atleta..."] + nombres_atletas

    seleccion_previa = st.session_state.get('atleta_seleccionado', opciones_atleta[0])
    idx_default = opciones_atleta.index(seleccion_previa) if seleccion_previa in opciones_atleta else 0

    seleccion = st.selectbox("Atleta guardado", opciones_atleta, index=idx_default, key="selector_atleta")

    if seleccion != st.session_state.get('atleta_seleccionado'):
        st.session_state.atleta_seleccionado = seleccion
        if seleccion == "➕ Nuevo atleta...":
            st.session_state.perfil = _perfil_vacio()
        else:
            st.session_state.perfil = _completar_perfil(atletas_guardados[seleccion])
        _cargar_o_reiniciar_menu_actual()
        st.rerun()

    if seleccion in atletas_guardados:
        if st.button("Eliminar este atleta", icon=":material/delete:", use_container_width=True):
            ds.eliminar_atleta(seleccion)
            ds.limpiar_estado_actual(seleccion)
            st.session_state.atleta_seleccionado = "➕ Nuevo atleta..."
            st.session_state.perfil = _perfil_vacio()
            _cargar_o_reiniciar_menu_actual()
            st.success("Atleta eliminado.")
            st.rerun()

    estado_sidebar = st.session_state.get('estado_menu_actual', 'borrador')
    if seleccion in atletas_guardados and st.session_state.datos_menu:
        etiqueta_estado = "✅ Menú confirmado" if estado_sidebar == 'confirmado' else "📝 Borrador en curso"
        st.caption(etiqueta_estado)

    st.markdown("---")
    st.caption("GESTIÓN")
    for clave_sec, titulo_sec, icono_sec in SECCIONES_SECUNDARIAS:
        activo_sec = st.session_state.seccion_activa == clave_sec
        if st.button(
            titulo_sec, key=f"navsec_{clave_sec}", icon=icono_sec, use_container_width=True,
            type="primary" if activo_sec else "secondary",
        ):
            st.session_state.seccion_activa = clave_sec
            st.rerun()

# ------------------------------------------------------------------
# FORMULARIO DE PERFIL (contenido, se renderiza dentro de la pestaña Atleta)
# ------------------------------------------------------------------
def _renderizar_formulario_perfil():

    # ---- Sexo y categoría (reactivos: fuera del formulario, para poder
    # mostrar la lista de categorías correcta al instante) ----
    opciones_sexo = ["Hombre", "Mujer"]
    idx_sexo = opciones_sexo.index(st.session_state.perfil.get('sexo')) if st.session_state.perfil.get('sexo') in opciones_sexo else 0
    st.session_state.perfil['sexo'] = st.selectbox("Sexo", opciones_sexo, index=idx_sexo)

    vigencia = st.radio(
        "Categorías IWF", list(fed.CATEGORIAS_IWF.keys()), horizontal=True,
        help="La IWF cambia sus categorías de peso el 1 de agosto de 2026. Elige según la competición en la que vayas a pesarte.",
    )
    lista_categorias = fed.CATEGORIAS_IWF[vigencia][st.session_state.perfil['sexo']] + [fed.CATEGORIA_PERSONALIZADA]
    categoria_actual = st.session_state.perfil.get('categoria', '')
    idx_cat = lista_categorias.index(categoria_actual) if categoria_actual in lista_categorias else len(lista_categorias) - 1
    categoria_elegida = st.selectbox("Categoría de peso (IWF)", lista_categorias, index=idx_cat)
    if categoria_elegida == fed.CATEGORIA_PERSONALIZADA:
        st.session_state.perfil['categoria'] = st.text_input(
            "Especifica la categoría", value=categoria_actual if categoria_actual not in lista_categorias else ""
        )
    else:
        st.session_state.perfil['categoria'] = categoria_elegida

    # ---- Competición (reactiva: para autorrellenar la fecha oficial) ----
    opciones_competicion = list(fed.COMPETICIONES_OFICIALES.keys()) + [fed.COMPETICION_PERSONALIZADA]
    competicion_actual = st.session_state.perfil.get('competicion', '')
    idx_comp = opciones_competicion.index(competicion_actual) if competicion_actual in opciones_competicion else len(opciones_competicion) - 1
    competicion_elegida = st.selectbox("Competición", opciones_competicion, index=idx_comp)

    if competicion_elegida == fed.COMPETICION_PERSONALIZADA:
        st.session_state.perfil['competicion'] = st.text_input(
            "Nombre de la competición", value=competicion_actual if competicion_actual not in opciones_competicion else ""
        )
        fecha_por_defecto = st.session_state.perfil.get('fecha_competicion') or date.today()
    else:
        st.session_state.perfil['competicion'] = competicion_elegida
        datos_comp = fed.COMPETICIONES_OFICIALES[competicion_elegida]
        st.caption(f"📍 {datos_comp['sede']} — {datos_comp['nota']}")
        # Solo tomamos la fecha oficial cuando se acaba de elegir esta
        # competición; si luego el usuario la cambia a mano, se respeta.
        if st.session_state.get('_ultima_competicion_elegida') != competicion_elegida:
            st.session_state.perfil['fecha_competicion'] = datos_comp['fecha']
        fecha_por_defecto = st.session_state.perfil['fecha_competicion']
    st.session_state['_ultima_competicion_elegida'] = competicion_elegida

    st.session_state.perfil['fecha_competicion'] = st.date_input(
        "Fecha de la competición (puedes ajustarla)", value=fecha_por_defecto
    )

    with st.form("form_perfil"):
        st.session_state.perfil['nombre'] = st.text_input("Nombre de Usuario", value=st.session_state.perfil['nombre'])
        st.session_state.perfil['peso'] = st.number_input("Peso Corporal (kg)", value=float(st.session_state.perfil['peso']))

        st.markdown("**Datos para calcular tus necesidades calóricas**")
        d1, d2 = st.columns(2)
        st.session_state.perfil['altura_cm'] = d1.number_input("Altura (cm)", value=float(st.session_state.perfil.get('altura_cm', 175)), min_value=100.0, max_value=230.0)
        st.session_state.perfil['edad'] = d2.number_input("Edad", value=int(st.session_state.perfil.get('edad', 30)), min_value=14, max_value=90)
        st.caption("Con el sexo de arriba, se usan para calcular tu metabolismo basal (fórmula de Mifflin-St Jeor). No se comparten con nadie.")

        st.markdown("**Fuerza Máxima (RM)**")
        c1, c2 = st.columns(2)
        st.session_state.perfil['rm_arrancada'] = c1.number_input("Arrancada (kg)", value=st.session_state.perfil['rm_arrancada'])
        st.session_state.perfil['rm_dos_tiempos'] = c2.number_input("Dos Tiempos (kg)", value=st.session_state.perfil['rm_dos_tiempos'])
        c3, c4 = st.columns(2)
        st.session_state.perfil['rm_sentadilla_delantera'] = c3.number_input("SQ Frontal (kg)", value=st.session_state.perfil['rm_sentadilla_delantera'])
        st.session_state.perfil['rm_sentadilla_trasera'] = c4.number_input("SQ Trasera (kg)", value=st.session_state.perfil['rm_sentadilla_trasera'])

        st.markdown("**Objetivo actual**")
        idx_fase = OPCIONES_FASE.index(st.session_state.perfil['objetivo_fase']) if st.session_state.perfil.get('objetivo_fase') in OPCIONES_FASE else 1
        st.session_state.perfil['objetivo_fase'] = st.selectbox("Objetivo actual", OPCIONES_FASE, index=idx_fase)
        o1, o2 = st.columns(2)
        st.session_state.perfil['obj_arrancada'] = o1.number_input("Obj. Arrancada", value=st.session_state.perfil['obj_arrancada'])
        st.session_state.perfil['obj_dos_tiempos'] = o2.number_input("Obj. Dos Tiempos", value=st.session_state.perfil['obj_dos_tiempos'])

        guardado = st.form_submit_button("Guardar Perfil", icon=":material/save:", type="primary", use_container_width=True)
        if guardado:
            if not st.session_state.perfil['nombre'].strip():
                st.error("El atleta necesita un nombre para poder guardarlo.")
            else:
                ds.guardar_atleta(st.session_state.perfil)
                st.session_state.atleta_seleccionado = st.session_state.perfil['nombre']
                st.success(f"Perfil de {st.session_state.perfil['nombre']} guardado. Podrás recuperarlo desde el selector de arriba.")

# ------------------------------------------------------------------
# NAVEGACIÓN POR SECCIONES (barra fija inferior, solo iconos)
# ------------------------------------------------------------------
with st.container(key="bottom_nav"):
    nav_cols = st.columns(3)
    for col, (clave, titulo, icono, desc) in zip(nav_cols, SECCIONES_PRINCIPALES):
        activo = st.session_state.seccion_activa == clave
        with col:
            if st.button(titulo, key=f"nav_{clave}", icon=icono, use_container_width=True, type="primary" if activo else "secondary"):
                st.session_state.seccion_activa = clave
                st.rerun()

if st.session_state.mostrar_resumen_cambios:
    dialog_resumen_cambios()

# ====================================================================
# SECCIÓN: GESTIÓN DE BBDD Y RECETAS
# ====================================================================
if st.session_state.seccion_activa == 'gestion':
    st.header("Gestión de Platos e Inventario")

    if ds.hay_platos_ejemplo(st.session_state.inventario):
        col_aviso, col_boton = st.columns([3, 1])
        col_aviso.info(
            "📌 Todavía tienes platos de **ejemplo** en la base de datos (para poder probar la app). "
            "Bórralos cuando tengas cargados tus propios platos reales."
        )
        if col_boton.button("🧹 Borrar platos de ejemplo", use_container_width=True):
            st.session_state.inventario = ds.borrar_platos_ejemplo(st.session_state.inventario)
            persistir_inventario()
            st.success("Platos de ejemplo eliminados.")
            st.rerun()

    df_inv = st.session_state.inventario
    if not df_inv.empty:
        tiene_ingredientes = df_inv['Ingredientes'].astype(str).str.strip().ne("")
        tiene_peso = df_inv.get('Peso_g', pd.Series(dtype=float)).fillna(0) > 0
        platos_sin_peso = df_inv[tiene_ingredientes & ~tiene_peso]
        if not platos_sin_peso.empty:
            col_aviso2, col_boton2 = st.columns([3, 1])
            col_aviso2.warning(
                f"⚖️ **{len(platos_sin_peso)} plato(s) no tienen registrado el peso de la ración** "
                "(se guardaron antes de esta función, o se editó su fila a mano). Sin ese dato, la app "
                "los sirve siempre en una ración fija, sin poder ajustar la cantidad al objetivo de cada "
                "comida. Como sí tienen ingredientes guardados, puedo calcularlo por ti sin tocar sus "
                "kcal ni macros actuales."
            )
            if col_boton2.button("⚖️ Calcular el peso que falta", use_container_width=True):
                actualizados = 0
                avisos_peso = []
                for idx in platos_sin_peso.index:
                    ingredientes_str = df_inv.at[idx, 'Ingredientes']
                    lineas = [l.strip() for l in ingredientes_str.split(",") if l.strip()]
                    try:
                        _, _, _, _, peso_calc, no_rec = estimar_macros(lineas, 1)
                    except Exception:
                        continue
                    if peso_calc and peso_calc > 0:
                        st.session_state.inventario.at[idx, 'Peso_g'] = float(peso_calc)
                        actualizados += 1
                    if no_rec:
                        avisos_peso.append(f"{df_inv.at[idx, 'Plato']}: {', '.join(no_rec)}")
                persistir_inventario()
                st.success(f"Peso calculado para {actualizados} de {len(platos_sin_peso)} platos.")
                if avisos_peso:
                    st.caption("Algunos ingredientes no se reconocieron (el peso puede quedar algo corto en esos platos): " + " · ".join(avisos_peso[:5]))
                st.rerun()

    st.markdown("#### 🗑️ Eliminar platos")
    if st.session_state.inventario.empty:
        st.caption("Todavía no tienes ningún plato guardado.")
    else:
        nombres_platos = st.session_state.inventario['Plato'].tolist()
        col_sel, col_del = st.columns([3, 1])
        platos_a_borrar = col_sel.multiselect(
            "Elige uno o varios platos para eliminarlos de golpe", nombres_platos,
            key="platos_a_borrar_rapido", label_visibility="collapsed",
            placeholder="Elige uno o varios platos para eliminarlos de golpe",
        )
        col_del.write("")
        if col_del.button("Eliminar", icon=":material/delete_forever:", type="primary", use_container_width=True, disabled=not platos_a_borrar):
            st.session_state.inventario = st.session_state.inventario[~st.session_state.inventario['Plato'].isin(platos_a_borrar)].reset_index(drop=True)
            persistir_inventario()
            st.success(f"{len(platos_a_borrar)} plato(s) eliminado(s).")
            st.rerun()

    with st.expander("➕ Añadir un plato rápido (sin ingredientes, solo los números)", expanded=False):
        st.caption(
            "Para calcular las calorías a partir de ingredientes (con ajuste automático de ración), "
            "usa mejor '📄 Subir Mis Platos'. Esto es para cuando ya sabes las kcal/macros y solo "
            "quieres añadirlo directo a la lista."
        )
        with st.form("form_add_rapido", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nombre_rapido = c1.text_input("Nombre del plato")
            categoria_rapida = c2.selectbox("Categoría", CATEGORIAS)
            c3, c4, c5, c6 = st.columns(4)
            kcal_rapido = c3.number_input("Kcal", min_value=0, step=10)
            prot_rapido = c4.number_input("Proteína (g)", min_value=0.0, step=1.0)
            carb_rapido = c5.number_input("Carbohidratos (g)", min_value=0.0, step=1.0)
            grasa_rapido = c6.number_input("Grasas (g)", min_value=0.0, step=1.0)
            util_rapido = st.selectbox("Utilizar en", OPCIONES_UTILIZAR_EN, index=3)
            if st.form_submit_button("Añadir a la base de datos", icon=":material/add_circle:", type="primary", use_container_width=True):
                if not nombre_rapido.strip():
                    st.error("Ponle un nombre al plato.")
                else:
                    guardar_plato_en_inventario({
                        "Plato": nombre_rapido.strip(), "Categoria": categoria_rapida, "Kcal": kcal_rapido,
                        "Proteina_g": prot_rapido, "Carbos_g": carb_rapido, "Grasas_g": grasa_rapido,
                        "Peso_g": 0.0, "Utilizar_en": util_rapido, "Ingredientes": "", "Preparacion": "",
                    })
                    st.success(f"'{nombre_rapido.strip()}' añadido.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Tabla completa")
    st.write("Edita directamente la tabla para actualizar calorías, ingredientes o momentos de uso. Los cambios se guardan solos. También puedes borrar filas con la papelera que aparece a la izquierda al seleccionarlas.")
    editado = st.data_editor(st.session_state.inventario, num_rows="dynamic", use_container_width=True)
    if not editado.equals(st.session_state.inventario):
        st.session_state.inventario = editado
        persistir_inventario()

    st.markdown("---")
    st.subheader("Exportar Recetario Limpio")
    seleccionados = st.multiselect("Selecciona los platos para armar el PDF:", st.session_state.inventario['Plato'].tolist())
    if seleccionados:
        try:
            ruta_recetario = os.path.join(OUTPUT_DIR, "Recetario_Completo.pdf")
            generar_pdf_recetas(st.session_state.inventario, seleccionados, ruta_recetario)
            with open(ruta_recetario, "rb") as f:
                st.download_button(
                    "📥 Generar y Descargar Recetas en PDF",
                    data=f.read(),
                    file_name="Recetario_RPT.pdf",
                    mime="application/pdf",
                    type="primary",
                )
        except Exception as e:
            st.error(f"Error al generar PDF de recetas: {e}")

# ====================================================================
# SECCIÓN: SUBIR MIS PLATOS
# ====================================================================
elif st.session_state.seccion_activa == 'subir':
    st.header("📄 Subir Mis Platos")

    st.subheader("Añadir platos propios desde un documento Word (.docx)")
    st.caption(
        "Sube uno o varios archivos a la vez. Admite encabezados como "
        "**INGREDIENTES**, **PREPARACIÓN** (o ELABORACIÓN, INSTRUCCIONES, PASOS...) "
        "y **UTILIZAR EN**. A partir de los ingredientes, la app estima "
        "automáticamente las calorías, los macronutrientes y la categoría "
        "nutricional. Siempre podrás revisarlo y corregirlo antes de guardarlo."
    )
    archivos_docx = st.file_uploader(
        "Arrastra aquí uno o varios archivos .docx a la vez", type=["docx"],
        accept_multiple_files=True, key="docx_uploader",
    )

    if archivos_docx:
        nuevos = 0
        for archivo in archivos_docx:
            clave = archivo.name
            if clave not in st.session_state.docx_procesados:
                try:
                    plato = procesar_docx_a_plato(archivo)
                    nombres_ya_pendientes = [p['Plato'] for p in st.session_state.docx_pendientes.values()]
                    plato['_posible_duplicado'] = ds.buscar_platos_similares(
                        plato['Plato'], st.session_state.inventario, nombres_extra=nombres_ya_pendientes
                    )
                    st.session_state.docx_pendientes[clave] = plato
                    st.session_state.docx_procesados.add(clave)
                    nuevos += 1
                except Exception as e:
                    st.error(f"No se pudo leer '{clave}': {e}")
        if nuevos:
            st.toast(f"{nuevos} documento(s) leído(s) correctamente.", icon="📄")

    if st.session_state.docx_guardados:
        with st.container(border=True):
            st.markdown(f"**✅ Guardado en la base de datos ({len(st.session_state.docx_guardados)}):**")
            st.write(", ".join(st.session_state.docx_guardados))
            st.caption("Los verás en la sección 'Gestión de Base de Datos', dentro de la tabla de platos.")

    if st.session_state.docx_pendientes:
        st.markdown(f"**{len(st.session_state.docx_pendientes)} plato(s) pendiente(s) de revisar:**")

        pendientes_sin_conflicto = {k: v for k, v in st.session_state.docx_pendientes.items() if not v.get('_posible_duplicado')}
        pendientes_con_conflicto = {k: v for k, v in st.session_state.docx_pendientes.items() if v.get('_posible_duplicado')}

        col_masivo1, col_masivo2 = st.columns([1, 2])
        if col_masivo1.button(
            "✅ Guardar TODOS los pendientes", type="primary", use_container_width=True,
            help="Añade de golpe los platos sin conflicto de nombre. Los que tengan un posible duplicado se quedan pendientes para revisar uno a uno.",
        ):
            filas = []
            nombres_guardados = []
            for clave, plato in pendientes_sin_conflicto.items():
                filas.append({k: v for k, v in plato.items() if not k.startswith("_")})
                nombres_guardados.append(plato["Plato"])
                del st.session_state.docx_pendientes[clave]
            if filas:
                st.session_state.inventario = pd.concat(
                    [st.session_state.inventario, pd.DataFrame(filas)], ignore_index=True
                )
                persistir_inventario()
                st.session_state.docx_guardados.extend(nombres_guardados)
                st.success(f"Se han añadido {len(filas)} platos a la base de datos.")
            if pendientes_con_conflicto:
                st.warning(f"{len(pendientes_con_conflicto)} plato(s) tienen un posible duplicado y no se han guardado automáticamente. Revísalos abajo, uno a uno.")
            st.rerun()
        col_masivo2.caption(
            "Añade de golpe los que no tengan conflicto. Los de posible duplicado se quedan abajo para decidir uno a uno."
        )

        st.markdown("---")

        for clave in list(st.session_state.docx_pendientes.keys()):
            plato = st.session_state.docx_pendientes[clave]
            titulo_expander = f"📄 {clave} → {plato['Plato']}"
            if plato.get('_posible_duplicado'):
                titulo_expander += "  ⚠️ posible duplicado"
            if plato.get("_origen_ingles"):
                titulo_expander += "  🌐 en inglés"
            with st.expander(titulo_expander, expanded=False):
                if plato.get("_origen_ingles"):
                    st.info(
                        "🌐 Este plato viene de TheMealDB, en inglés. El nombre, los ingredientes y la "
                        "preparación se muestran tal cual — tradúcelos o ajústalos antes de guardar si quieres."
                    )
                if plato.get('_posible_duplicado'):
                    nombre_sim, ratio_sim = plato['_posible_duplicado'][0]
                    st.warning(f"Ya existe un plato parecido: **{nombre_sim}** ({ratio_sim*100:.0f}% de parecido).")
                if plato.get("_sin_ingredientes"):
                    st.error(
                        "No se ha detectado ningún ingrediente en este documento. Revisa que tenga un "
                        "apartado de INGREDIENTES, o añádelos a mano abajo antes de guardar."
                    )
                if plato.get("_pasos_reubicados"):
                    st.warning(
                        f"He movido {plato['_pasos_reubicados']} línea(s) desde 'ingredientes' a "
                        "'preparación' porque tenían toda la pinta de ser pasos de la receta, no "
                        "ingredientes. Revísalo abajo por si acaso."
                    )
                no_reconocidos = plato.get("_ingredientes_no_reconocidos", [])
                if no_reconocidos:
                    st.warning(
                        "No se han reconocido estos ingredientes para el cálculo de "
                        f"calorías (revisa los valores manualmente): {', '.join(no_reconocidos)}"
                    )
                kcal_doc = plato.get("_kcal_documento_por_racion")
                if kcal_doc:
                    diferencia = plato["Kcal"] - kcal_doc
                    st.warning(
                        f"📊 Tu documento indica **{kcal_doc:.0f} kcal/ración** en su propio estudio "
                        f"energético, y la app ha calculado **{plato['Kcal']} kcal/ración** a partir de "
                        f"los ingredientes ({'+' if diferencia > 0 else ''}{diferencia:.0f} kcal de diferencia). "
                        "Si te fías más de tu estudio, ajusta el campo 'Kcal' de abajo a mano antes de guardar."
                    )
                st.info(
                    f"Estimado a partir de {plato.get('_raciones_detectadas', '?')} raciones detectadas "
                    "en el documento. Ajusta lo que necesites antes de guardar."
                )

                col1, col2 = st.columns(2)
                nombre_edit = col1.text_input("Nombre del plato", value=plato["Plato"], key=f"nom_{clave}")
                categoria_edit = col2.selectbox(
                    "Categoría", CATEGORIAS,
                    index=CATEGORIAS.index(plato["Categoria"]) if plato["Categoria"] in CATEGORIAS else 0,
                    key=f"cat_{clave}",
                )

                col3, col4, col5, col6, col7 = st.columns(5)
                kcal_edit = col3.number_input("Kcal / ración", value=int(plato["Kcal"]), key=f"kcal_{clave}")
                prot_edit = col4.number_input("Proteína (g)", value=float(plato["Proteina_g"]), key=f"prot_{clave}")
                carb_edit = col5.number_input("Carbohidratos (g)", value=float(plato["Carbos_g"]), key=f"carb_{clave}")
                grasa_edit = col6.number_input("Grasas (g)", value=float(plato["Grasas_g"]), key=f"grasa_{clave}")
                peso_edit = col7.number_input(
                    "Peso ración (g)", value=float(plato.get("Peso_g", 0) or 0), key=f"peso_{clave}",
                    help="Peso de esta ración en gramos. Si lo rellenas, la app podrá ajustar la cantidad "
                         "servida (más o menos gramos) según lo que necesite cada comida, en vez de usar "
                         "siempre esta misma ración fija.",
                )

                util_edit = st.selectbox(
                    "Utilizar en", OPCIONES_UTILIZAR_EN,
                    index=OPCIONES_UTILIZAR_EN.index(plato["Utilizar_en"]) if plato["Utilizar_en"] in OPCIONES_UTILIZAR_EN else 3,
                    key=f"util_{clave}",
                )
                ingr_edit = st.text_area("Ingredientes", value=plato["Ingredientes"], key=f"ingr_{clave}")
                prep_edit = st.text_area("Preparación", value=plato["Preparacion"], key=f"prep_{clave}")

                bcol1, bcol2 = st.columns(2)
                if bcol1.button("✅ Guardar en la base de datos", key=f"save_{clave}", type="primary", use_container_width=True):
                    fila_dict = {
                        "Plato": nombre_edit, "Categoria": categoria_edit, "Kcal": kcal_edit,
                        "Proteina_g": prot_edit, "Carbos_g": carb_edit, "Grasas_g": grasa_edit,
                        "Peso_g": peso_edit, "Utilizar_en": util_edit, "Ingredientes": ingr_edit,
                        "Preparacion": prep_edit,
                    }
                    similares = ds.buscar_platos_similares(nombre_edit, st.session_state.inventario)
                    if similares:
                        st.session_state['duplicado_pendiente'] = {
                            'fila': fila_dict, 'similares': similares, 'clave_docx_pendiente': clave,
                        }
                        dialog_confirmar_duplicado()
                    else:
                        try:
                            guardar_plato_en_inventario(fila_dict)
                            st.session_state.docx_guardados.append(nombre_edit)
                            del st.session_state.docx_pendientes[clave]
                            st.success(f"'{nombre_edit}' añadido a la base de datos.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"No se pudo guardar el plato: {e}")
                if bcol2.button("🗑️ Descartar", key=f"discard_{clave}", use_container_width=True):
                    del st.session_state.docx_pendientes[clave]
                    st.rerun()

    st.markdown("---")

    # ----------------------------------------------------------
    # GENERAR PLATO A PARTIR DE INGREDIENTES (sin documento)
    # ----------------------------------------------------------
    with st.expander("🤖 Describir un plato y que la app calcule las calorías (sin documento)"):
        st.caption(
            "Útil para platos sueltos que no tienes en un .docx: dile el nombre, las raciones "
            "y los ingredientes, y calculo la estimación igual que con los documentos."
        )
        with st.form("form_wizard_plato"):
            gw1, gw2 = st.columns(2)
            gw_nombre = gw1.text_input("Nombre del plato")
            gw_raciones = gw2.number_input("Raciones", min_value=1, value=4)
            gw_util = st.selectbox("Utilizar en:", OPCIONES_UTILIZAR_EN, index=3)
            gw_ingredientes = st.text_area(
                "Ingredientes (uno por línea, con cantidad si la sabes)",
                placeholder="800 gr merluza\n1 vaso de vino blanco\n3 dientes de ajo\nperejil",
                height=120,
            )
            gw_prep = st.text_area("Preparación (opcional)")
            if st.form_submit_button("Calcular y revisar", type="primary"):
                if not gw_nombre.strip() or not gw_ingredientes.strip():
                    st.error("Necesito al menos el nombre y los ingredientes.")
                else:
                    lineas = [l for l in gw_ingredientes.split("\n") if l.strip()]
                    kcal, prot, carb, grasa, peso, no_rec = estimar_macros(lineas, gw_raciones)
                    categoria = categorizar(kcal, prot, carb, grasa)
                    nuevo_plato = {
                        "Plato": gw_nombre.strip(), "Categoria": categoria, "Kcal": int(kcal),
                        "Proteina_g": float(prot), "Carbos_g": float(carb), "Grasas_g": float(grasa),
                        "Peso_g": float(peso), "Utilizar_en": gw_util, "Ingredientes": ", ".join(lineas),
                        "Preparacion": gw_prep,
                        "_raciones_detectadas": gw_raciones, "_ingredientes_no_reconocidos": no_rec,
                    }
                    nuevo_plato['_posible_duplicado'] = ds.buscar_platos_similares(nuevo_plato['Plato'], st.session_state.inventario)
                    clave_gen = f"__generado_{len(st.session_state.docx_pendientes)}_{gw_nombre.strip()}"
                    st.session_state.docx_pendientes[clave_gen] = nuevo_plato
                    st.success("Calculado. Bájalo a revisar en la lista de pendientes de arriba.")
                    st.rerun()

    with st.expander("🌐 Buscar platos en internet (TheMealDB)"):
        st.caption(
            "Busca en TheMealDB, una base de datos de recetas gratuita y abierta (no hace falta "
            "registrarse ni tener ninguna clave). Está **en inglés**: al añadir un resultado, calculo "
            "las calorías igual que con el resto de platos, pero revisa y traduce lo que necesites "
            "antes de guardarlo."
        )
        col_busq, col_btn = st.columns([3, 1])
        consulta_receta = col_busq.text_input("Buscar plato (en inglés, ej: chicken, salmon, pasta...)", key="busqueda_mealdb")
        buscar_clic = col_btn.button("🔍 Buscar", use_container_width=True)

        if buscar_clic or st.session_state.get('resultados_mealdb'):
            if buscar_clic:
                with st.spinner("Buscando..."):
                    resultados, error_busqueda = busqueda_recetas.buscar_recetas(consulta_receta)
                st.session_state.resultados_mealdb = resultados
                st.session_state.error_mealdb = error_busqueda

            if st.session_state.get('error_mealdb'):
                st.error(st.session_state.error_mealdb)
            elif not st.session_state.get('resultados_mealdb'):
                st.info("Sin resultados para esa búsqueda. Prueba con otra palabra (en inglés).")
            else:
                st.caption(f"{len(st.session_state.resultados_mealdb)} resultado(s):")
                for resultado in st.session_state.resultados_mealdb[:10]:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([1, 3, 1])
                        if resultado.get('miniatura'):
                            c1.image(resultado['miniatura'], width=64)
                        c2.markdown(f"**{resultado['nombre']}**")
                        c2.caption(f"{resultado.get('categoria', '')} · {resultado.get('area', '')}")
                        if c3.button("➕ Añadir", key=f"mealdb_add_{resultado['id']}", use_container_width=True):
                            with st.spinner("Descargando receta..."):
                                receta, error_receta = busqueda_recetas.obtener_receta(resultado['id'])
                            if error_receta:
                                st.error(error_receta)
                            else:
                                kcal, prot, carb, grasa, peso, no_rec = estimar_macros(receta['ingredientes'], 4)
                                categoria = categorizar(kcal, prot, carb, grasa)
                                nuevo_plato = {
                                    "Plato": receta['nombre'], "Categoria": categoria, "Kcal": int(kcal),
                                    "Proteina_g": float(prot), "Carbos_g": float(carb), "Grasas_g": float(grasa),
                                    "Peso_g": float(peso), "Utilizar_en": "Almuerzo, Cena",
                                    "Ingredientes": ", ".join(receta['ingredientes']),
                                    "Preparacion": receta['preparacion'],
                                    "_raciones_detectadas": 4, "_ingredientes_no_reconocidos": no_rec,
                                    "_origen_ingles": True,
                                }
                                nuevo_plato['_posible_duplicado'] = ds.buscar_platos_similares(nuevo_plato['Plato'], st.session_state.inventario)
                                clave_mealdb = f"__mealdb_{resultado['id']}_{receta['nombre']}"
                                st.session_state.docx_pendientes[clave_mealdb] = nuevo_plato
                                st.success(f"'{receta['nombre']}' añadido a revisión (arriba). Recuerda que está en inglés.")
                                st.rerun()

    st.markdown("---")

    # ----------------------------------------------------------
    # ALTA MANUAL DE PLATO (con macros ya conocidos)
    # ----------------------------------------------------------
    with st.expander("✏️ Añadir un plato manualmente (ya sé sus calorías exactas)"):
        with st.form("form_nuevo_manual"):
            m1, m2 = st.columns(2)
            nm_nombre = m1.text_input("Nombre del Plato")
            nm_cat = m2.selectbox("Categoría", CATEGORIAS)
            m3, m4, m5, m6 = st.columns(4)
            nm_kcal = m3.number_input("Kcal", value=500)
            nm_prot = m4.number_input("Proteína (g)", value=20)
            nm_carb = m5.number_input("Carbohidratos (g)", value=40)
            nm_grasa = m6.number_input("Grasas (g)", value=10)
            nm_util = st.selectbox("Utilizar en:", OPCIONES_UTILIZAR_EN, index=3)
            nm_ingr = st.text_area("Ingredientes")
            nm_prep = st.text_area("Preparación")
            if st.form_submit_button("Guardar plato", type="primary"):
                if nm_nombre.strip() == "":
                    st.error("El plato necesita un nombre.")
                else:
                    fila_dict = {
                        'Plato': nm_nombre, 'Categoria': nm_cat, 'Kcal': nm_kcal,
                        'Proteina_g': nm_prot, 'Carbos_g': nm_carb, 'Grasas_g': nm_grasa,
                        'Utilizar_en': nm_util, 'Ingredientes': nm_ingr, 'Preparacion': nm_prep,
                    }
                    similares = ds.buscar_platos_similares(nm_nombre, st.session_state.inventario)
                    if similares:
                        st.session_state['duplicado_pendiente'] = {'fila': fila_dict, 'similares': similares, 'clave_docx_pendiente': None}
                        dialog_confirmar_duplicado()
                    else:
                        guardar_plato_en_inventario(fila_dict)
                        st.success(f"'{nm_nombre}' añadido a la base de datos.")
                        st.rerun()

# ====================================================================
# SECCIÓN: PLANIFICADOR
# ====================================================================
elif st.session_state.seccion_activa == 'menu':
    if st.session_state.estado_menu_actual == 'confirmado':
        _mostrar_menu_confirmado_bloqueado()
    else:
        _mostrar_planificador_borrador()

# ====================================================================
# SECCIÓN: ATLETA
# ====================================================================
elif st.session_state.seccion_activa == 'atleta':
    st.header("👤 Atleta")
    st.caption("Perfil, marcas y objetivos del atleta seleccionado en la barra lateral.")
    _renderizar_formulario_perfil()

    st.markdown("---")
    st.subheader("Todos tus atletas, de un vistazo")
    estados = ds.estado_atletas()
    if not estados:
        st.info("Todavía no tienes ningún atleta dado de alta. Rellena el formulario de arriba para crear el primero.")
    else:
        etiquetas_estado = {
            "confirmado": ("✅", "Menú confirmado activo"),
            "borrador": ("📝", "Borrador en curso"),
            "sin menú": ("⚪", "Sin menú todavía"),
        }
        for nombre_at, info in estados.items():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
                emoji_e, texto_e = etiquetas_estado.get(info['estado'], ("⚪", "Sin menú todavía"))
                c1.markdown(f"**{nombre_at}**" + ("  🔹 _seleccionado_" if nombre_at == st.session_state.perfil.get('nombre') else ""))
                c2.markdown(f"{emoji_e} {texto_e}")
                c3.caption(f"{info['semanas_confirmadas']} semana(s) en el histórico")
                if nombre_at != st.session_state.perfil.get('nombre'):
                    if c4.button("Ir a él", key=f"ir_a_{nombre_at}", use_container_width=True):
                        atletas_todos = ds.cargar_atletas()
                        st.session_state.atleta_seleccionado = nombre_at
                        st.session_state.perfil = _completar_perfil(atletas_todos[nombre_at])
                        _cargar_o_reiniciar_menu_actual()
                        st.rerun()

# ====================================================================
# SECCIÓN: SEGUIMIENTO MENÚ Y ATLETA
# ====================================================================
elif st.session_state.seccion_activa == 'seguimiento':
    st.header("📋 Seguimiento Menú y Atleta")
    nombre_actual = st.session_state.perfil.get('nombre', '')

    if not nombre_actual:
        st.info("Selecciona o crea un atleta primero, en la pestaña '👤 Atleta'.")
    elif st.session_state.estado_menu_actual != 'confirmado' or not st.session_state.datos_menu:
        st.info(
            f"**{nombre_actual}** todavía no tiene ningún menú confirmado activo. Ve a "
            "'📊 Planificador de Menú', ajusta el menú a tu gusto y pulsa **'✅ CONFIRMAR MENÚ'** "
            "para empezar aquí el seguimiento real de esta semana."
        )
    else:
        st.success(
            f"Menú confirmado activo de **{nombre_actual}**. Aquí registras lo que se come de verdad "
            "cada día, o cambias algún plato — sin que afecte al resto de la app."
        )

        totales = {dia: kcal_total_dia(datos) for dia, datos in st.session_state.datos_menu.items()}
        media_semana = sum(totales.values()) / len(totales) if totales else 0
        r1, r2, r3 = st.columns(3)
        r1.markdown(f'<div class="week-stat"><div class="num">{sum(totales.values())}</div><div class="lbl">🔥 Kcal semana</div></div>', unsafe_allow_html=True)
        r2.markdown(f'<div class="week-stat"><div class="num">{media_semana:.0f}</div><div class="lbl">📊 Media diaria</div></div>', unsafe_allow_html=True)
        r3.markdown(f'<div class="week-stat"><div class="num">{len(totales)}</div><div class="lbl">📅 Días planificados</div></div>', unsafe_allow_html=True)

        macros_reales = [macros_total_dia(d) for d in st.session_state.datos_menu.values()]
        macros_objetivo = [d.get('objetivo_macros', {}) for d in st.session_state.datos_menu.values()]
        if macros_reales and macros_objetivo:
            n = len(macros_reales)
            prot_media = sum(m['proteina_g'] for m in macros_reales) / n
            carb_media = sum(m['carbos_g'] for m in macros_reales) / n
            grasa_media = sum(m['grasa_g'] for m in macros_reales) / n
            prot_obj = sum(m.get('proteina_g', 0) for m in macros_objetivo) / n
            carb_obj = sum(m.get('carbos_g', 0) for m in macros_objetivo) / n
            grasa_obj = sum(m.get('grasa_g', 0) for m in macros_objetivo) / n
            objetivo_kcal_medio = (
                sum(st.session_state.menu_original.get(d, {}).get('kcal', 0) for d in st.session_state.datos_menu) / n
            )
            st.write("")
            mostrar_anillo_hero(media_semana, objetivo_kcal_medio)
            mostrar_anillos_macros(prot_media, prot_obj, carb_media, carb_obj, grasa_media, grasa_obj)
            st.write("")
            if (objetivo_kcal_medio > 0 and media_semana < objetivo_kcal_medio * 0.85) or (prot_obj > 0 and prot_media < prot_obj * 0.85):
                st.warning(
                    f"⚠️ Lo registrado esta semana se está quedando por debajo del objetivo "
                    f"({media_semana:.0f} de {objetivo_kcal_medio:.0f} kcal, {prot_media:.0f} de "
                    f"{prot_obj:.0f} g de proteína, de media al día)."
                )

        st.write("")
        chart_df = pd.DataFrame({"Kcal": totales}).reindex(list(st.session_state.datos_menu.keys()))
        st.bar_chart(chart_df, color=BRAND_BLUE, height=160)
        st.write("")
        mostrar_grafica_tendencia(st.session_state.historial_semanas)
        st.write("")

        _dibujar_tarjetas_dias_interactivas()
        _persistir_estado_actual()

        st.markdown("<br>", unsafe_allow_html=True)
        try:
            ruta_informe_seg = os.path.join(OUTPUT_DIR, "Informe_Seguimiento.pdf")
            generar_informe_profesional(
                st.session_state.datos_menu, st.session_state.perfil, ruta_informe_seg,
                historial=st.session_state.historial_semanas,
            )
            with open(ruta_informe_seg, "rb") as f:
                st.download_button(
                    "📥 Descargar informe de esta semana en PDF", data=f.read(),
                    file_name="Informe_Seguimiento_RPT.pdf", mime="application/pdf",
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"Error al generar informe: {e}")

    st.markdown("---")
    st.subheader("📚 Histórico de semanas confirmadas")
    if nombre_actual:
        historial_confirmados = ds.cargar_menus_confirmados(nombre_actual)
        if not historial_confirmados:
            st.caption("Todavía no hay semanas confirmadas en el histórico de este atleta.")
        else:
            for entrada in historial_confirmados:
                totales_hist = {dia: kcal_total_dia(datos) for dia, datos in entrada.get('datos_menu', {}).items()}
                media_hist = sum(totales_hist.values()) / len(totales_hist) if totales_hist else 0
                es_la_activa = entrada.get('id') == st.session_state.get('menu_confirmado_id')
                titulo_hist = f"{entrada.get('nombre_semana', 'Semana')} — confirmada el {entrada.get('fecha_confirmacion', '')[:10]}"
                if es_la_activa:
                    titulo_hist += "  ✅ (activa ahora mismo)"
                with st.expander(titulo_hist):
                    st.caption(f"Total: {sum(totales_hist.values())} kcal · Media diaria: {media_hist:.0f} kcal" if totales_hist else "Sin datos")
                    if not es_la_activa:
                        if st.button("🗑️ Eliminar del histórico", key=f"del_hist_{entrada.get('id')}"):
                            ds.eliminar_menu_confirmado(nombre_actual, entrada.get('id'))
                            st.rerun()
    else:
        st.caption("Selecciona un atleta para ver su histórico.")
