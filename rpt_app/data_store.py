# -*- coding: utf-8 -*-
"""
data_store.py
-------------
Persistencia local muy sencilla, basada en archivos JSON, para que la app
recuerde entre sesiones:
  - Los atletas dados de alta (perfil completo de cada uno).
  - La base de datos de platos (para que lo que subas hoy siga ahí mañana).
  - Los menús guardados (plantillas reutilizables) y los menús confirmados
    (el histórico real de cada atleta, semana a semana).

No requiere ningún servidor ni instalar una base de datos: todo se guarda
en archivos JSON dentro de una carpeta **independiente de la aplicación**
('RPT_Datos', al lado de la carpeta del programa, no dentro). Así, cuando
sustituyas la carpeta del programa por una versión nueva, tus atletas,
platos y menús confirmados no se pierden ni hay que volver a introducirlos.

Si existen datos de una instalación anterior en la ubicación antigua
(dentro de la propia carpeta del programa), se migran automáticamente la
primera vez que se arranca esta versión, para no perder nada.
"""

import os
import json
import shutil
import difflib
import pandas as pd
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpeta de datos independiente: al lado de la carpeta del programa
# (rpt_app), no dentro. 'os.path.dirname(BASE_DIR)' es la carpeta que
# contiene a rpt_app; ahí al lado creamos 'RPT_Datos'.
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "RPT_Datos")
DATA_DIR_ANTIGUA = os.path.join(BASE_DIR, "data")

def _carpeta_escribible(ruta):
    try:
        os.makedirs(ruta, exist_ok=True)
        prueba = os.path.join(ruta, ".escritura_ok")
        with open(prueba, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(prueba)
        return True
    except Exception:
        return False


# Red de seguridad (p. ej. en el navegador): si la carpeta preferida no se
# puede escribir, se usa una carpeta temporal para que la app no falle.
if not _carpeta_escribible(DATA_DIR):
    for _alt in ("/tmp/RPT_Datos", os.path.join(os.path.expanduser("~"), "RPT_Datos")):
        if _carpeta_escribible(_alt):
            DATA_DIR = _alt
            break


def _migrar_datos_antiguos():
    """Si hay datos de una instalación anterior (guardados dentro de la
    carpeta del programa, versiones previas a este cambio) y la carpeta
    independiente nueva todavía está vacía, los copiamos una sola vez para
    no perder atletas, platos ni menús ya guardados."""
    if not os.path.isdir(DATA_DIR_ANTIGUA):
        return
    hay_algo_nuevo = any(
        os.path.exists(os.path.join(DATA_DIR, nombre))
        for nombre in ("atletas.json", "platos.json")
    )
    if hay_algo_nuevo:
        return
    for nombre_archivo in os.listdir(DATA_DIR_ANTIGUA):
        origen = os.path.join(DATA_DIR_ANTIGUA, nombre_archivo)
        destino = os.path.join(DATA_DIR, nombre_archivo)
        if os.path.isfile(origen) and not os.path.exists(destino):
            try:
                shutil.copy2(origen, destino)
            except OSError:
                pass


_migrar_datos_antiguos()

ATLETAS_PATH = os.path.join(DATA_DIR, "atletas.json")
PLATOS_PATH = os.path.join(DATA_DIR, "platos.json")
MENUS_PATH = os.path.join(DATA_DIR, "menus_guardados.json")
MENUS_CONFIRMADOS_PATH = os.path.join(DATA_DIR, "menus_confirmados.json")
ESTADO_ACTUAL_PATH = os.path.join(DATA_DIR, "estado_actual_por_atleta.json")
HISTORIAL_SEMANAS_PATH = os.path.join(DATA_DIR, "historial_semanas_por_atleta.json")

# Nombres de los platos de ejemplo que se entregan para poder probar la
# app (macros calculados con el mismo motor que usa el resto del programa).
# Se guardan aparte para poder identificarlos y borrarlos de una vez desde
# 'Gestión de Base de Datos' en cuanto el usuario tenga sus propios platos.
NOMBRES_PLATOS_EJEMPLO = [
    "Pollo con arroz y brócoli", "Salmón al horno con quinoa", "Ternera con patatas asadas",
    "Merluza con puré y guisantes", "Pasta con atún y tomate", "Tortilla de patatas generosa",
    "Cocido completo", "Lentejas con chorizo", "Solomillo con boniato asado",
    "Garbanzos con espinacas y bacalao", "Arroz con pollo y verduras",
    "Ensalada de quinoa con pollo y aguacate", "Alubias blancas con costilla",
    "Bacalao con patatas y pimientos", "Cordero asado con boniato",
    "Sentadilla de gambas y arroz", "Tostas de jamón, queso y huevo",
    "Bowl de avena con plátano y nueces", "Yogur con muesli y fruta",
]


def hay_platos_ejemplo(df):
    """Indica si el inventario actual todavía contiene platos de ejemplo."""
    if df is None or df.empty:
        return False
    return df["Plato"].isin(NOMBRES_PLATOS_EJEMPLO).any()


def borrar_platos_ejemplo(df):
    """Devuelve el inventario sin los platos de ejemplo (no toca los que
    haya añadido el usuario, aunque coincidan por casualidad de categoría)."""
    if df is None or df.empty:
        return df
    return df[~df["Plato"].isin(NOMBRES_PLATOS_EJEMPLO)].reset_index(drop=True)


def _json_default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return str(o)


# ----------------------------------------------------------------------
# ATLETAS
# ----------------------------------------------------------------------
def cargar_atletas():
    """Devuelve un dict {nombre_atleta: perfil_dict} con todos los atletas
    guardados. Si no hay ninguno todavía, devuelve un dict vacío."""
    if not os.path.exists(ATLETAS_PATH):
        return {}
    try:
        with open(ATLETAS_PATH, "r", encoding="utf-8") as f:
            datos = json.load(f)
        # Las fechas se guardan como texto; las convertimos de vuelta si se puede
        for perfil in datos.values():
            fc = perfil.get("fecha_competicion")
            if fc:
                try:
                    perfil["fecha_competicion"] = datetime.strptime(fc[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    pass
        return datos
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_atleta(perfil):
    """Guarda (o actualiza si ya existe) un atleta, usando su nombre como
    identificador."""
    atletas = cargar_atletas()
    nombre = perfil.get("nombre", "").strip()
    if not nombre:
        return False
    atletas[nombre] = perfil
    with open(ATLETAS_PATH, "w", encoding="utf-8") as f:
        json.dump(atletas, f, ensure_ascii=False, indent=2, default=_json_default)
    return True


def eliminar_atleta(nombre):
    atletas = cargar_atletas()
    if nombre in atletas:
        del atletas[nombre]
        with open(ATLETAS_PATH, "w", encoding="utf-8") as f:
            json.dump(atletas, f, ensure_ascii=False, indent=2, default=_json_default)
        return True
    return False


# ----------------------------------------------------------------------
# BASE DE DATOS DE PLATOS
# ----------------------------------------------------------------------
COLUMNAS_INVENTARIO = ["Plato", "Categoria", "Kcal", "Proteina_g", "Carbos_g", "Grasas_g", "Peso_g", "Utilizar_en", "Ingredientes", "Preparacion"]


def _inventario_vacio():
    return pd.DataFrame(columns=COLUMNAS_INVENTARIO)


def cargar_inventario():
    """Devuelve el DataFrame de platos guardado en disco. La primera vez
    que se usa la app (no existe el archivo todavía) empieza vacío, listo
    para que cargues tus propios platos desde 'Subir Mis Platos'."""
    if not os.path.exists(PLATOS_PATH):
        df = _inventario_vacio()
        guardar_inventario(df)
        return df
    try:
        with open(PLATOS_PATH, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not datos:
            return _inventario_vacio()
        return pd.DataFrame(datos)
    except (json.JSONDecodeError, OSError):
        return _inventario_vacio()


def guardar_inventario(df):
    """Guarda el DataFrame completo de platos en disco."""
    registros = df.to_dict(orient="records")
    with open(PLATOS_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2, default=_json_default)


# ----------------------------------------------------------------------
# DETECCIÓN DE PLATOS SIMILARES (para avisar de posibles duplicados)
# ----------------------------------------------------------------------
def _normalizar_simple(texto):
    import unicodedata
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def buscar_platos_similares(nombre_nuevo, df, umbral=0.72, nombres_extra=None):
    """Compara 'nombre_nuevo' contra los platos ya existentes en el
    inventario (y opcionalmente contra una lista extra de nombres, por
    ejemplo otros platos pendientes de guardar en el mismo lote) y
    devuelve una lista de (nombre_existente, parecido 0-1) para aquellos
    que superen el umbral de similitud, ordenados de más a menos parecido."""
    objetivo = _normalizar_simple(nombre_nuevo)
    candidatos_nombres = []
    if df is not None and not df.empty:
        candidatos_nombres.extend(df["Plato"].astype(str).unique().tolist())
    if nombres_extra:
        candidatos_nombres.extend([n for n in nombres_extra if n])

    resultados = []
    vistos = set()
    for nombre_existente in candidatos_nombres:
        clave_vista = _normalizar_simple(nombre_existente)
        if clave_vista in vistos:
            continue
        vistos.add(clave_vista)

        candidato = clave_vista
        ratio = difflib.SequenceMatcher(None, objetivo, candidato).ratio()
        if objetivo in candidato or candidato in objetivo:
            ratio = max(ratio, 0.85)
        if ratio >= umbral:
            resultados.append((nombre_existente, ratio))
    resultados.sort(key=lambda x: -x[1])
    return resultados


# ----------------------------------------------------------------------
# MENÚS SEMANALES GUARDADOS (reutilizables entre atletas)
# ----------------------------------------------------------------------
def _limpiar_para_json(obj):
    """Convierte tipos de numpy/pandas (int64, float64...) y fechas a
    tipos nativos de Python, para poder guardarlos en JSON sin errores."""
    if isinstance(obj, dict):
        return {k: _limpiar_para_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_limpiar_para_json(v) for v in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if hasattr(obj, "item"):  # numpy.int64, numpy.float64, numpy.bool_...
        return obj.item()
    return obj


def cargar_menus_guardados():
    """Devuelve un dict {nombre_menu: {datos...}} con todos los menús
    semanales guardados, de cualquier atleta."""
    if not os.path.exists(MENUS_PATH):
        return {}
    try:
        with open(MENUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_menu(nombre_menu, atleta_origen, datos_menu, menu_original,
                  objetivo_semanal_kcal=None, bmr_calculado=None):
    """Guarda (o sobrescribe si ya existe) un menú semanal con un nombre
    elegido por el usuario, para poder reutilizarlo después con cualquier
    otro atleta tal cual, sin tener que volver a generarlo."""
    nombre_menu = (nombre_menu or "").strip()
    if not nombre_menu:
        return False
    menus = cargar_menus_guardados()
    menus[nombre_menu] = _limpiar_para_json({
        "atleta_origen": atleta_origen,
        "fecha_guardado": datetime.now().isoformat(),
        "datos_menu": datos_menu,
        "menu_original": menu_original,
        "objetivo_semanal_kcal": objetivo_semanal_kcal,
        "bmr_calculado": bmr_calculado,
    })
    with open(MENUS_PATH, "w", encoding="utf-8") as f:
        json.dump(menus, f, ensure_ascii=False, indent=2)
    return True


def eliminar_menu_guardado(nombre_menu):
    menus = cargar_menus_guardados()
    if nombre_menu in menus:
        del menus[nombre_menu]
        with open(MENUS_PATH, "w", encoding="utf-8") as f:
            json.dump(menus, f, ensure_ascii=False, indent=2)
        return True
    return False


# ----------------------------------------------------------------------
# MENÚS CONFIRMADOS (histórico real de cada atleta, semana a semana)
# ----------------------------------------------------------------------
def _cargar_todos_menus_confirmados():
    if not os.path.exists(MENUS_CONFIRMADOS_PATH):
        return {}
    try:
        with open(MENUS_CONFIRMADOS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _guardar_todos_menus_confirmados(datos):
    with open(MENUS_CONFIRMADOS_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def confirmar_menu(nombre_atleta, datos_menu, menu_original, objetivo_semanal_kcal,
                    bmr_calculado, nombre_semana=None):
    """Añade una nueva semana confirmada al histórico de este atleta (no
    sustituye a las anteriores: se guardan todas, para poder consultar
    semanas pasadas). Devuelve el id asignado a esta semana confirmada."""
    todos = _cargar_todos_menus_confirmados()
    lista_atleta = todos.get(nombre_atleta, [])
    id_semana = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_semana = (nombre_semana or f"Semana del {date.today().strftime('%d-%m-%Y')}").strip()
    entrada = _limpiar_para_json({
        "id": id_semana,
        "nombre_semana": nombre_semana,
        "fecha_confirmacion": datetime.now().isoformat(),
        "datos_menu": datos_menu,
        "menu_original": menu_original,
        "objetivo_semanal_kcal": objetivo_semanal_kcal,
        "bmr_calculado": bmr_calculado,
    })
    lista_atleta.insert(0, entrada)  # la más reciente primero
    todos[nombre_atleta] = lista_atleta
    _guardar_todos_menus_confirmados(todos)
    return id_semana


def cargar_menus_confirmados(nombre_atleta):
    """Histórico de semanas confirmadas de un atleta, más reciente primero."""
    return _cargar_todos_menus_confirmados().get(nombre_atleta, [])


def eliminar_menu_confirmado(nombre_atleta, id_semana):
    todos = _cargar_todos_menus_confirmados()
    lista_atleta = todos.get(nombre_atleta, [])
    nueva_lista = [e for e in lista_atleta if e.get("id") != id_semana]
    if len(nueva_lista) == len(lista_atleta):
        return False
    todos[nombre_atleta] = nueva_lista
    _guardar_todos_menus_confirmados(todos)
    return True


def estado_atletas():
    """Para la pestaña 'Atleta': un vistazo rápido de si cada atleta tiene
    un menú en borrador o confirmado ahora mismo, y cuántas semanas
    confirmadas tiene en su histórico."""
    estados = _cargar_todos_estados_actuales()
    confirmados = _cargar_todos_menus_confirmados()
    resultado = {}
    for nombre in cargar_atletas():
        estado_actual = estados.get(nombre, {})
        resultado[nombre] = {
            "estado": estado_actual.get("estado", "sin menú"),
            "semanas_confirmadas": len(confirmados.get(nombre, [])),
            "ultima_actualizacion": estado_actual.get("ultima_actualizacion"),
        }
    return resultado


# ----------------------------------------------------------------------
# ESTADO ACTUAL POR ATLETA (para poder cambiar de atleta y volver, sin
# perder en qué punto se había quedado cada uno — ni al cerrar la app)
# ----------------------------------------------------------------------
def _cargar_todos_estados_actuales():
    if not os.path.exists(ESTADO_ACTUAL_PATH):
        return {}
    try:
        with open(ESTADO_ACTUAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_estado_actual(nombre_atleta, estado_dict):
    """Guarda el estado 'de trabajo' actual de un atleta (su borrador o su
    menú confirmado activo, con todo lo necesario para reconstruir la
    pantalla tal cual se dejó)."""
    if not nombre_atleta:
        return
    todos = _cargar_todos_estados_actuales()
    estado_dict = dict(estado_dict)
    estado_dict["ultima_actualizacion"] = datetime.now().isoformat()
    todos[nombre_atleta] = _limpiar_para_json(estado_dict)
    with open(ESTADO_ACTUAL_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def cargar_estado_actual(nombre_atleta):
    """Devuelve el estado 'de trabajo' guardado de un atleta, o None si
    nunca se ha generado nada para él."""
    return _cargar_todos_estados_actuales().get(nombre_atleta)


def limpiar_estado_actual(nombre_atleta):
    todos = _cargar_todos_estados_actuales()
    if nombre_atleta in todos:
        del todos[nombre_atleta]
        with open(ESTADO_ACTUAL_PATH, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------
# HISTÓRICO DE SEMANAS GENERADAS (para las gráficas de tendencia)
# ----------------------------------------------------------------------
def _cargar_todo_historial_semanas():
    if not os.path.exists(HISTORIAL_SEMANAS_PATH):
        return {}
    try:
        with open(HISTORIAL_SEMANAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def cargar_historial_semanas(nombre_atleta):
    """Últimas semanas generadas para este atleta (hasta 12), con kcal y
    macros medios de cada una, para poder pintar gráficas de tendencia."""
    return _cargar_todo_historial_semanas().get(nombre_atleta, [])


def guardar_historial_semanas(nombre_atleta, historial):
    """Guarda el histórico de semanas de un atleta (ya recortado a las
    últimas 12) para que las gráficas de tendencia sobrevivan a cerrar la
    app o a sustituir la carpeta del programa."""
    if not nombre_atleta:
        return
    todos = _cargar_todo_historial_semanas()
    todos[nombre_atleta] = _limpiar_para_json(historial)
    with open(HISTORIAL_SEMANAS_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
