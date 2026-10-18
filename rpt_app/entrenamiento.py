# -*- coding: utf-8 -*-
"""
entrenamiento.py
-----------------
Lee la tabla de entrenamiento semanal y calcula la intensidad real de cada
día -Alta, Media o Descanso-, para que el reparto de calorías de la semana
se base en el entrenamiento real. Admite TRES formatos:

  1. El formato sencillo de la plantilla de RPT (columnas Día, Ejercicio,
     Series, Repeticiones, Peso), cruzando el peso planificado con las
     marcas (RM) del perfil.
  2. El formato típico de hojas de gimnasio/entrenador en Excel (columna
     'Día' con una letra por día, y una columna 'IMR' -Intensidad Media
     Relativa, ya calculada por la propia hoja-).
  3. Una FOTO o CAPTURA de esa misma hoja (JPG/PNG), leída con Tesseract
     OCR -software libre y gratuito que funciona en tu ordenador sin
     conexión a internet ni ningún coste-. Es menos fiable que subir el
     Excel directamente (una foto con mala luz, torcida o con letra
     manuscrita puede leerse mal), así que el resultado siempre se puede
     revisar y corregir a mano antes de generar el menú.

En los formatos de Excel, la fila de cabecera se busca entre las primeras
filas del archivo (no se asume que sea la primera), por si hay un título
encima de la tabla, como es habitual en estas plantillas.
"""

import re
import unicodedata
import os
import pandas as pd

try:
    import pytesseract
    from PIL import Image
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

# Rutas donde el instalador de Windows (UB-Mannheim) suele dejar Tesseract
# si al instalarlo no se marcó la opción de añadirlo al PATH del sistema.
_RUTAS_TESSERACT_WINDOWS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

MAPA_LETRA_DIA = {
    "l": "Lunes", "lu": "Lunes", "lun": "Lunes", "lunes": "Lunes",
    "m": "Martes", "ma": "Martes", "mar": "Martes", "martes": "Martes",
    "x": "Miércoles", "mi": "Miércoles", "mie": "Miércoles", "miercoles": "Miércoles", "w": "Miércoles",
    "j": "Jueves", "ju": "Jueves", "jue": "Jueves", "jueves": "Jueves",
    "v": "Viernes", "vi": "Viernes", "vie": "Viernes", "viernes": "Viernes",
    "s": "Sábado", "sa": "Sábado", "sab": "Sábado", "sabado": "Sábado",
    "d": "Domingo", "do": "Domingo", "dom": "Domingo", "domingo": "Domingo",
}

EJERCICIOS_RM = [
    (["arrancada", "snatch"], "rm_arrancada"),
    (["dos tiempos", "clean and jerk", "clean jerk", "clean & jerk", "cargada y jerk", "c&j"], "rm_dos_tiempos"),
    (["sentadilla frontal", "sentadilla delantera", "front squat"], "rm_sentadilla_delantera"),
    (["sentadilla trasera", "sentadilla espalda", "back squat", "sentadilla"], "rm_sentadilla_trasera"),
]

UMBRAL_ALTA_PCT = 0.85
UMBRAL_ALTA_VOLUMEN = 25
UMBRAL_DESCANSO_PCT = 0.65
UMBRAL_DESCANSO_VOLUMEN = 15
UMBRAL_VOLUMEN_SOLO_ACCESORIOS = 40

UMBRAL_IMR_ALTA = 0.72
UMBRAL_IMR_MEDIA = 0.35


def _normalizar(texto):
    texto = str(texto or "").lower().strip()
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _celda_coincide_exacta(valor, candidatos):
    """Compara el valor de una celda con un conjunto de candidatos por
    coincidencia EXACTA (no por subcadena). Evita falsos positivos como
    que 'MUNDIAL' se confunda con 'día' solo por contener esas letras."""
    return _normalizar(valor) in candidatos


def _indice_columna(fila_cabecera, candidatos):
    for idx, valor in enumerate(fila_cabecera):
        if _celda_coincide_exacta(valor, candidatos):
            return idx
    return None


def _localizar_fila_cabecera(df_crudo):
    """Recorre las primeras filas del archivo buscando la fila real de
    cabecera (con una celda exactamente 'Día'), por si hay una fila de
    título por encima de la tabla, como en las plantillas de gimnasios."""
    limite = min(8, len(df_crudo))
    for i in range(limite):
        fila = df_crudo.iloc[i].tolist()
        if _indice_columna(fila, {"dia"}) is not None:
            return i
    return None


def _identificar_campo_rm(nombre_ejercicio):
    normalizado = _normalizar(nombre_ejercicio)
    for palabras_clave, campo in EJERCICIOS_RM:
        for palabra in palabras_clave:
            if _normalizar(palabra) in normalizado:
                return campo
    return None


def _a_numero(valor):
    if valor is None:
        return 0.0
    texto = str(valor).strip().replace("%", "").replace(",", ".")
    if not texto or texto.lower() == "nan":
        return 0.0
    try:
        return float(texto)
    except ValueError:
        return 0.0


def generar_plantilla_excel(output_path):
    filas = [
        {"Día": "Lunes", "Ejercicio": "Arrancada", "Series": 6, "Repeticiones": 2, "Peso (kg)": 75},
        {"Día": "Lunes", "Ejercicio": "Sentadilla trasera", "Series": 4, "Repeticiones": 3, "Peso (kg)": 130},
        {"Día": "Martes", "Ejercicio": "Movilidad y técnica ligera", "Series": 3, "Repeticiones": 10, "Peso (kg)": 20},
        {"Día": "Miércoles", "Ejercicio": "Dos tiempos", "Series": 6, "Repeticiones": 1, "Peso (kg)": 105},
        {"Día": "Miércoles", "Ejercicio": "Sentadilla frontal", "Series": 5, "Repeticiones": 2, "Peso (kg)": 120},
        {"Día": "Jueves", "Ejercicio": "Arrancada", "Series": 5, "Repeticiones": 3, "Peso (kg)": 65},
        {"Día": "Viernes", "Ejercicio": "Descanso / movilidad", "Series": 1, "Repeticiones": 1, "Peso (kg)": 0},
        {"Día": "Sábado", "Ejercicio": "Dos tiempos", "Series": 5, "Repeticiones": 2, "Peso (kg)": 90},
        {"Día": "Sábado", "Ejercicio": "Sentadilla trasera", "Series": 4, "Repeticiones": 4, "Peso (kg)": 115},
        {"Día": "Domingo", "Ejercicio": "Descanso", "Series": 0, "Repeticiones": 0, "Peso (kg)": 0},
    ]
    df = pd.DataFrame(filas)
    df.to_excel(output_path, index=False, sheet_name="Entrenamiento")
    return output_path


def _clasificar_por_imr(valores_imr, valores_volumen):
    imr_max = max(valores_imr) if valores_imr else 0.0
    volumen_total = sum(valores_volumen) if valores_volumen else 0.0
    if imr_max <= 0 and volumen_total <= 0:
        return "Descanso", "Sin carga registrada ese día (0% IMR): se trata como descanso."
    if imr_max >= UMBRAL_IMR_ALTA:
        return "Alta", f"Pico de intensidad del día: {imr_max*100:.0f}% IMR (tonelaje {volumen_total:.0f})."
    if imr_max < UMBRAL_IMR_MEDIA:
        return "Descanso", f"Intensidad baja ese día: {imr_max*100:.0f}% IMR como máximo."
    return "Media", f"Pico de intensidad del día: {imr_max*100:.0f}% IMR (tonelaje {volumen_total:.0f})."


# ----------------------------------------------------------------------
# LECTURA DE UNA FOTO O CAPTURA (OCR con Tesseract, gratuito y local)
# ----------------------------------------------------------------------
_PALABRAS_DESCANSO_IMAGEN = ["crossfit", "rest", "descanso", "libre", "movilidad"]


def ocr_disponible():
    """Indica si Tesseract está instalado y accesible. Si no lo está, la
    app debe explicar cómo instalarlo en vez de fallar sin más."""
    if not OCR_DISPONIBLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        pass
    # en Windows, si no se añadió al PATH durante la instalación, probamos
    # las rutas donde lo deja el instalador habitual antes de rendirnos
    for ruta in _RUTAS_TESSERACT_WINDOWS:
        if os.path.exists(ruta):
            pytesseract.pytesseract.tesseract_cmd = ruta
            try:
                pytesseract.get_tesseract_version()
                return True
            except Exception:
                continue
    return False


def leer_entrenamiento_imagen(imagen_file):
    """Lee una foto o captura de la tabla de entrenamiento con OCR y
    calcula la intensidad de cada día, igual que con el Excel de hoja de
    gimnasio (buscando los porcentajes de IMR y las letras de cada día).

    Es un 'mejor esfuerzo': el reconocimiento de texto en una foto nunca es
    perfecto, así que devuelve también un aviso claro invitando a revisar
    el resultado, y una lista de líneas de texto en bruto reconocidas por
    si hace falta comprobar algo a mano.

    Devuelve (intensidades, detalle, avisos, texto_bruto).
    """
    if not OCR_DISPONIBLE:
        raise ValueError(
            "Esta instalación no tiene disponible la lectura de imágenes (falta el paquete "
            "'pytesseract'/'Pillow'). Revisa el manual de instrucciones para instalarlo."
        )
    if not ocr_disponible():
        raise ValueError(
            "No encuentro el programa Tesseract OCR instalado en este ordenador. Es gratuito, pero "
            "hay que instalarlo aparte (no basta con instalar los paquetes de Python). Consulta el "
            "manual de instrucciones para ver cómo instalarlo según tu sistema operativo."
        )

    try:
        imagen = Image.open(imagen_file)
    except Exception as e:
        raise ValueError(f"No se ha podido abrir la imagen. Detalle técnico: {e}")

    ancho_imagen, alto_imagen = imagen.size

    try:
        datos = pytesseract.image_to_data(imagen, lang="spa", output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        # si no está el paquete de idioma español, probamos con el inglés
        # (sigue reconociendo números y letras sueltas razonablemente bien)
        datos = pytesseract.image_to_data(imagen, output_type=pytesseract.Output.DICT)

    n = len(datos["text"])
    palabras = []
    for i in range(n):
        texto = (datos["text"][i] or "").strip()
        if not texto:
            continue
        palabras.append({
            "texto": texto,
            "x": datos["left"][i],
            "y": datos["top"][i],
            "conf": int(datos["conf"][i]) if str(datos["conf"][i]).lstrip("-").isdigit() else 0,
        })

    return interpretar_palabras_ocr(palabras, ancho_imagen, alto_imagen)


def interpretar_palabras_ocr(palabras, ancho_imagen, alto_imagen):
    """Convierte las palabras reconocidas por cualquier OCR (lista de dicts
    con texto, x, y, conf) en intensidades por día.
    Devuelve (intensidades, detalle, avisos, texto_bruto)."""
    texto_bruto = "\n".join(p["texto"] for p in palabras)

    # Columna izquierda (~5% del ancho): ahí van las letras de cada día en
    # este tipo de plantillas. Columna derecha (~90% del ancho): ahí suele
    # ir el % de IMR, el dato más fiable y el que de verdad usamos.
    limite_izquierda = ancho_imagen * 0.06
    limite_derecha = ancho_imagen * 0.85

    anclas_dia = []  # (y, nombre_dia)
    for p in palabras:
        if p["x"] > limite_izquierda:
            continue
        clave = _normalizar(p["texto"]).strip(" .:-")
        # nos quedamos solo con la primera letra reconocible (el OCR a
        # veces añade ruido, p.ej. 'XxX' en vez de 'X')
        clave_letra = clave[:1] if clave else ""
        if clave_letra in MAPA_LETRA_DIA and len(clave) <= 3:
            anclas_dia.append((p["y"], MAPA_LETRA_DIA[clave_letra]))

    porcentajes = []  # (y, valor 0-1)
    for p in palabras:
        if p["x"] < limite_derecha:
            continue
        m = re.match(r"^(\d+)[.,]?\d*\s*%$", p["texto"])
        if m:
            porcentajes.append((p["y"], int(m.group(1)) / 100))

    descansos_explicitos = []  # (y, 'Descanso') por CROSSFIT/REST/etc.
    for p in palabras:
        if _normalizar(p["texto"]) in _PALABRAS_DESCANSO_IMAGEN:
            descansos_explicitos.append(p["y"])

    anclas_dia.sort(key=lambda t: t[0])

    if not anclas_dia and not porcentajes:
        raise ValueError(
            "No he podido reconocer ninguna letra de día ni ningún porcentaje en la imagen. "
            "Prueba con una foto más nítida, mejor iluminada y lo más recta posible, o sube el "
            "Excel si lo tienes."
        )

    # Reconstruimos, en orden, qué días aparecen realmente en la imagen: se
    # asume el orden semanal habitual (L, M, X, J, V, S, D), empezando
    # siempre por Lunes aunque su letra no se haya reconocido bien.
    if anclas_dia:
        primer_dia_detectado = anclas_dia[0][1]
        idx_primero = DIAS_SEMANA.index(primer_dia_detectado)
    else:
        idx_primero = 0
    dias_presentes = DIAS_SEMANA[idx_primero:] if idx_primero > 0 else DIAS_SEMANA

    # Límites de cada bloque de día: el punto medio entre cada ancla y la
    # siguiente. Si faltan anclas (letras que el OCR no vio), el bloque de
    # ese día se reparte con sus vecinos lo mejor posible.
    if anclas_dia:
        y_anclas = [y for y, _ in anclas_dia]
        limites = [-1] + [
            (y_anclas[i] + y_anclas[i + 1]) / 2 for i in range(len(y_anclas) - 1)
        ] + [alto_imagen + 1]
    else:
        # sin ninguna letra reconocida: repartimos la imagen en franjas
        # iguales para los días de los que sí tenemos porcentaje
        limites = [-1] + [alto_imagen * (i + 1) / 7 for i in range(6)] + [alto_imagen + 1]
        anclas_dia = [(alto_imagen * i / 7, DIAS_SEMANA[i]) for i in range(7)]

    bloques = []  # (nombre_dia, y_inicio, y_fin)
    for i, (y, nombre) in enumerate(anclas_dia):
        bloques.append((nombre, limites[i], limites[i + 1]))

    intensidades, detalle = {}, {}
    dias_con_datos = set()
    for nombre_dia, y_ini, y_fin in bloques:
        valores_dia = [pct for (y, pct) in porcentajes if y_ini <= y < y_fin]
        hay_descanso_explicito = any(y_ini <= y < y_fin for y in descansos_explicitos)
        if hay_descanso_explicito and not valores_dia:
            intensidades[nombre_dia] = "Descanso"
            detalle[nombre_dia] = "Se ha reconocido texto de descanso/Crossfit ese día."
        else:
            intensidades[nombre_dia], detalle[nombre_dia] = _clasificar_por_imr(valores_dia, [])
        if valores_dia or hay_descanso_explicito:
            dias_con_datos.add(nombre_dia)

    avisos = ["🔎 Lectura por imagen (OCR): revisa cada día antes de generar el menú, puede tener errores."]
    dias_sin_datos = [d for d in DIAS_SEMANA if d not in intensidades]
    for d in dias_sin_datos:
        intensidades[d] = "Descanso"
        detalle[d] = "No se ha reconocido ningún dato para este día en la imagen: se deja como descanso por precaución. Revísalo a mano."
    dias_dudosos = [d for d in DIAS_SEMANA if d not in dias_con_datos]
    if dias_dudosos:
        avisos.append(
            "No se ha podido leer con confianza: " + ", ".join(dias_dudosos) +
            ". Corrige esos días a mano si hace falta."
        )

    return intensidades, detalle, avisos, texto_bruto




def _leer_formato_hoja_gimnasio(df_crudo, fila_cab, idx_dia, idx_imr):
    idx_volumen = _indice_columna(df_crudo.iloc[fila_cab].tolist(), {"to", "tonelaje"})
    filas_datos = df_crudo.iloc[fila_cab + 1:].copy()
    filas_datos["_dia"] = filas_datos[idx_dia].ffill()

    intensidades, detalle = {}, {}
    for dia_completo in DIAS_SEMANA:
        letras_dia = [l for l, nombre in MAPA_LETRA_DIA.items() if nombre == dia_completo]
        filas_dia = filas_datos[filas_datos["_dia"].apply(lambda v: _normalizar(v) in letras_dia)]
        if filas_dia.empty:
            intensidades[dia_completo] = "Descanso"
            detalle[dia_completo] = "No hay entrenamiento registrado ese día: se trata como descanso."
            continue

        valores_imr = [_a_numero(v) / (100 if _a_numero(v) > 1.5 else 1) for v in filas_dia[idx_imr].tolist()]
        valores_volumen = [_a_numero(v) for v in filas_dia[idx_volumen].tolist()] if idx_volumen is not None else []
        intensidades[dia_completo], detalle[dia_completo] = _clasificar_por_imr(valores_imr, valores_volumen)

    return intensidades, detalle, []


def _leer_formato_sencillo(df_crudo, fila_cab, idx_dia, perfil):
    cabecera = df_crudo.iloc[fila_cab].tolist()
    idx_ejercicio = _indice_columna(cabecera, {"ejercicio", "movimiento"})
    idx_series = _indice_columna(cabecera, {"series"})
    idx_reps = _indice_columna(cabecera, {"repeticiones", "reps"})
    idx_peso = _indice_columna(cabecera, {"peso", "peso (kg)", "kg", "carga"})

    filas_datos = df_crudo.iloc[fila_cab + 1:].copy()
    filas_datos["_dia"] = filas_datos[idx_dia].ffill()

    intensidades, detalle = {}, {}
    ejercicios_no_reconocidos = set()

    for dia in DIAS_SEMANA:
        filas_dia = filas_datos[filas_datos["_dia"].apply(lambda v: _normalizar(v) == _normalizar(dia))]
        if filas_dia.empty:
            intensidades[dia] = "Descanso"
            detalle[dia] = "No hay entrenamiento registrado ese día: se trata como descanso."
            continue

        porcentajes_ponderados = []
        volumen_total = 0.0
        for _, fila in filas_dia.iterrows():
            series = _a_numero(fila.iloc[idx_series]) if idx_series is not None else 1.0
            reps = _a_numero(fila.iloc[idx_reps]) if idx_reps is not None else 1.0
            peso = _a_numero(fila.iloc[idx_peso]) if idx_peso is not None else 0.0
            volumen = max(series, 0) * max(reps, 0)
            volumen_total += volumen

            nombre_ejercicio = str(fila.iloc[idx_ejercicio]) if idx_ejercicio is not None else ""
            campo_rm = _identificar_campo_rm(nombre_ejercicio)
            rm_atleta = perfil.get(campo_rm) if campo_rm else None
            if campo_rm and rm_atleta and float(rm_atleta) > 0 and peso > 0:
                pct = peso / float(rm_atleta)
                porcentajes_ponderados.extend([pct] * max(int(round(volumen)), 1))
            elif nombre_ejercicio.strip() and nombre_ejercicio.lower() != "nan" and not campo_rm:
                ejercicios_no_reconocidos.add(nombre_ejercicio.strip())

        if porcentajes_ponderados:
            media_pct = sum(porcentajes_ponderados) / len(porcentajes_ponderados)
            if media_pct >= UMBRAL_ALTA_PCT or volumen_total >= UMBRAL_ALTA_VOLUMEN:
                intensidades[dia] = "Alta"
            elif media_pct <= UMBRAL_DESCANSO_PCT and volumen_total < UMBRAL_DESCANSO_VOLUMEN:
                intensidades[dia] = "Descanso"
            else:
                intensidades[dia] = "Media"
            detalle[dia] = f"Carga media ≈ {media_pct*100:.0f}% de tu RM, volumen total {volumen_total:.0f}."
        else:
            intensidades[dia] = "Media" if volumen_total >= UMBRAL_VOLUMEN_SOLO_ACCESORIOS else "Descanso"
            detalle[dia] = f"Sin levantamientos con RM reconocido (volumen total {volumen_total:.0f})."

    avisos = []
    if ejercicios_no_reconocidos:
        avisos.append(
            "No he podido relacionar estos ejercicios con ninguna de tus marcas (RM) guardadas: "
            + ", ".join(sorted(ejercicios_no_reconocidos))
        )
    return intensidades, detalle, avisos


def leer_entrenamiento(file_like, perfil):
    """Lee el Excel de entrenamiento semanal (en cualquiera de los dos
    formatos admitidos) y devuelve (intensidades, detalle, avisos)."""
    try:
        df_crudo = pd.read_excel(file_like, header=None)
    except Exception as e:
        raise ValueError(
            "No se ha podido leer el archivo. Comprueba que es un Excel (.xlsx) válido. "
            f"Detalle técnico: {e}"
        )

    if df_crudo.empty:
        raise ValueError("El archivo está vacío.")

    fila_cab = _localizar_fila_cabecera(df_crudo)
    if fila_cab is None:
        raise ValueError(
            "No encuentro una columna 'Día' en el archivo (he mirado las primeras filas, por si "
            "hay un título encima de la tabla). Descarga la plantilla de ejemplo para ver la "
            "estructura exacta, o comprueba que tu Excel tenga una columna llamada 'Día'."
        )

    cabecera = df_crudo.iloc[fila_cab].tolist()
    idx_dia = _indice_columna(cabecera, {"dia"})
    idx_imr = _indice_columna(cabecera, {"imr", "intensidad", "%rm", "% rm"})

    if idx_imr is not None:
        return _leer_formato_hoja_gimnasio(df_crudo, fila_cab, idx_dia, idx_imr)
    return _leer_formato_sencillo(df_crudo, fila_cab, idx_dia, perfil)
