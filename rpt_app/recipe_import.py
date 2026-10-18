# -*- coding: utf-8 -*-
"""
recipe_import.py
-----------------
Lee documentos .docx con la estructura que usa RPT para sus fichas de
platos (NOMBRE (X raciones) / INGREDIENTES: / PREPARACIÓN / UTILIZAR EN:)
y estima automáticamente sus calorías y macronutrientes a partir de los
ingredientes, para poder añadirlos a la base de datos con un clic.

La estimación es aproximada (se basa en tablas nutricionales generales
por cada 100 g). Siempre se muestra al usuario antes de guardar, para que
pueda corregirla a mano si lo desea.
"""

import re
import unicodedata
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

# ----------------------------------------------------------------------
# TABLA NUTRICIONAL APROXIMADA (por 100 g de parte comestible)
# kcal, proteína (g), carbohidratos (g), grasa (g), peso medio de 1 unidad (g)
# ----------------------------------------------------------------------
FOOD_DB = {
    "berenjena":            (25, 1.0, 6.0, 0.2, 250),
    "calabacin":             (17, 1.2, 3.1, 0.3, 200),
    "calabaza":              (26, 1.0, 7.0, 0.1, 300),
    "cebolla":                (40, 1.1, 9.0, 0.1, 150),
    "puerro":                (61, 1.5, 14.0, 0.3, 150),
    "pimiento rojo":          (31, 1.0, 6.0, 0.3, 150),
    "pimiento verde":         (20, 0.9, 4.6, 0.2, 120),
    "pimiento":               (25, 1.0, 5.0, 0.3, 130),
    "tomate triturado":       (32, 1.6, 5.0, 0.3, 100),
    "tomate":                 (18, 0.9, 3.9, 0.2, 120),
    "zanahoria":              (41, 0.9, 10.0, 0.2, 80),
    "patata":                 (77, 2.0, 17.0, 0.1, 150),
    "boniato":                (86, 1.6, 20.0, 0.1, 200),
    "lechuga":                (15, 1.4, 2.9, 0.2, 100),
    "espinaca":               (23, 2.9, 3.6, 0.4, 100),
    "brocoli":                (34, 2.8, 7.0, 0.4, 300),
    "coliflor":               (25, 1.9, 5.0, 0.3, 400),
    "champinon":              (22, 3.1, 3.3, 0.3, 100),
    "ajo":                    (149, 6.4, 33.0, 0.5, 5),
    "vino blanco":            (82, 0.1, 2.6, 0.0, 30),
    "vino":                   (85, 0.1, 2.6, 0.0, 30),
    "arroz basmati":          (350, 7.0, 78.0, 0.6, 185),
    "arroz":                  (350, 7.0, 78.0, 0.6, 185),
    "pasta":                  (350, 12.0, 71.0, 1.5, 100),
    "quinoa":                 (120, 4.4, 21.0, 1.9, 185),
    "avena":                  (389, 17.0, 66.0, 7.0, 90),
    "pan":                    (265, 9.0, 49.0, 3.2, 40),
    "huevo":                  (155, 13.0, 1.1, 11.0, 55),
    "garbanzo":               (164, 8.9, 27.0, 2.6, 200),
    "lenteja":                (116, 9.0, 20.0, 0.4, 200),
    "calamar":                (92, 15.0, 3.1, 1.4, 200),
    "carne de puchero":       (250, 26.0, 0.0, 17.0, 200),
    "ternera":                (250, 26.0, 0.0, 17.0, 200),
    "carne picada":           (170, 20.0, 0.0, 10.0, 150),
    "maiz":                   (86, 3.2, 19.0, 1.2, 100),
    "pechuga de pollo":       (165, 31.0, 0.0, 3.6, 150),
    "pollo":                  (200, 27.0, 0.0, 10.0, 150),
    "sardina":                (210, 20.0, 0.0, 14.0, 120),
    "atun":                   (130, 26.0, 0.0, 3.0, 80),
    "salmon":                 (208, 20.0, 0.0, 13.0, 150),
    "merluza":                (86, 17.0, 0.0, 1.5, 150),
    "jamon":                  (241, 31.0, 0.0, 13.0, 30),
    "aceite de oliva":        (884, 0.0, 0.0, 100.0, 13),
    "aceite":                 (884, 0.0, 0.0, 100.0, 13),
    "leche":                  (61, 3.2, 4.8, 3.3, 200),
    "yogur":                  (61, 3.5, 4.7, 3.3, 125),
    "yogur griego":           (60, 5.8, 4.7, 2.0, 125),
    "queso":                  (350, 25.0, 1.5, 27.0, 30),
    "platano":                (89, 1.1, 23.0, 0.3, 120),
    "manzana":                (52, 0.3, 14.0, 0.2, 150),
    "naranja":                (47, 0.9, 12.0, 0.1, 150),
    "fresa":                  (32, 0.7, 7.7, 0.3, 15),
    "almendra":               (579, 21.0, 22.0, 50.0, 1),
    "nuez":                   (654, 15.0, 14.0, 65.0, 5),
    "miel":                   (304, 0.3, 82.0, 0.0, 20),
    "azucar":                 (387, 0.0, 100.0, 0.0, 5),
    "azucar moreno":          (380, 0.0, 98.0, 0.0, 5),
    "salsa de soja":          (53, 8.0, 5.0, 0.0, 15),
    "maicena":                (355, 0.3, 87.0, 0.1, 10),
    "jengibre":               (80, 1.8, 18.0, 0.8, 10),
    "vinagre":                (18, 0.0, 0.9, 0.0, 15),
    "ketchup":                (101, 1.0, 24.0, 0.2, 15),
    "mostaza":                (66, 4.4, 5.3, 3.3, 5),
    "levadura":               (325, 41.0, 41.0, 7.6, 5),
    "canela":                 (247, 4.0, 81.0, 1.2, 3),
    "costilla de cerdo":      (277, 17.0, 0.0, 23.0, 250),
    "costilla":               (277, 17.0, 0.0, 23.0, 250),
    "cordero":                (294, 25.0, 0.0, 21.0, 200),
    "conejo":                 (173, 29.0, 0.0, 6.0, 200),
    "chorizo":                (455, 24.0, 2.0, 38.0, 25),
    "morcilla":               (379, 15.0, 19.0, 29.0, 25),
    "panceta":                (518, 9.0, 0.0, 53.0, 30),
    "tocino":                 (815, 2.0, 0.0, 88.0, 30),
    "hueso de jamon":         (200, 15.0, 0.0, 15.0, 100),
    "hueso":                  (150, 10.0, 0.0, 12.0, 100),
    "punta de jamon":         (280, 20.0, 0.0, 22.0, 60),
    "gallina":                (215, 20.0, 0.0, 15.0, 200),
    "repollo":                (25, 1.3, 5.8, 0.1, 200),
    "col":                    (25, 1.3, 5.8, 0.1, 200),
    "fideo":                  (350, 12.0, 71.0, 1.5, 30),
    "fideos":                 (350, 12.0, 71.0, 1.5, 30),
    "solomillo":              (143, 21.0, 0.0, 6.0, 200),
    "bacalao":                (82, 18.0, 0.0, 0.7, 150),
    "gamba":                  (85, 20.0, 0.0, 0.5, 15),
    "mejillon":               (86, 12.0, 4.0, 2.2, 15),
    "alubia":                 (127, 8.7, 23.0, 0.5, 200),
    "judia blanca":           (127, 8.7, 23.0, 0.5, 200),
    "guisante":               (81, 5.4, 14.0, 0.4, 150),
    "acelga":                 (19, 1.8, 3.7, 0.2, 100),
    "apio":                   (16, 0.7, 3.0, 0.2, 60),
    "endivia":                (17, 1.3, 3.4, 0.2, 100),
    "pepino":                 (15, 0.7, 3.6, 0.1, 200),
    "aguacate":               (160, 2.0, 8.5, 15.0, 200),
    "coco":                   (354, 3.3, 15.0, 33.0, 100),
}

# Palabras que no aportan calorías relevantes -> se ignoran en el cálculo
INGREDIENTES_IGNORAR = [
    "sal", "pimienta", "especias", "especia", "agua", "hielo", "laurel",
    "guindilla", "oregano", "comino", "perejil", "cilantro",
    "perejil", "organo", "pimenton", "colorante", "opcional", "opcionales",
    # inglés
    "salt", "water", "ice", "optional", "spices", "seasoning",
]

# Conversión de unidades de cocina a gramos/mililitros aproximados
# (incluye equivalentes en inglés, para poder interpretar recetas que
# vengan de fuentes en ese idioma, como la búsqueda en internet).
UNIDADES_GRAMOS = {
    "g": 1, "gr": 1, "grs": 1, "gramo": 1, "gramos": 1,
    "kg": 1000, "kilo": 1000, "kilos": 1000,
    "ml": 1, "l": 1000, "litro": 1000, "litros": 1000,
    "taza": 200, "tazas": 200,
    "cucharada": 13, "cucharadas": 13,
    "cucharadita": 5, "cucharaditas": 5,
    "sopera": 15, "soperas": 15, "postre": 8, "puñado": 30, "punado": 30,
    "diente": 5, "dientes": 5,
    "dedo": 30, "dedos": 30,
    "lata": 120, "latas": 120,
    "vaso": 200, "vasos": 200,
    "pizca": 1, "pizcas": 1,
    # --- inglés ---
    "cup": 200, "cups": 200,
    "tbsp": 13, "tbsps": 13, "tablespoon": 13, "tablespoons": 13,
    "tsp": 5, "tsps": 5, "teaspoon": 5, "teaspoons": 5,
    "oz": 28, "ounce": 28, "ounces": 28,
    "lb": 454, "lbs": 454, "pound": 454, "pounds": 454,
    "clove": 5, "cloves": 5,
    "can": 120, "cans": 120,
    "pinch": 1, "pinches": 1,
}

# Traducción aproximada de nombres de ingredientes en inglés a la clave en
# español que ya conoce el motor de cálculo (FOOD_DB). Solo hace falta
# tener las palabras clave más habituales: la búsqueda por palabras ya
# permite variantes ("chicken breast", "chicken thighs"...).
ALIAS_INGLES = {
    "chicken": "pollo", "chicken breast": "pechuga de pollo",
    "beef": "ternera", "steak": "solomillo", "sirloin": "solomillo",
    "pork": "costilla de cerdo", "pork chop": "costilla de cerdo",
    "bacon": "panceta", "ham": "jamon", "lamb": "cordero", "rabbit": "conejo",
    "salmon": "salmon", "tuna": "atun", "cod": "bacalao", "hake": "merluza",
    "shrimp": "gamba", "prawn": "gamba", "prawns": "gamba", "mussel": "mejillon", "mussels": "mejillon", "squid": "calamar",
    "egg": "huevo", "eggs": "huevo",
    "rice": "arroz", "basmati rice": "arroz basmati", "pasta": "pasta", "spaghetti": "pasta",
    "potato": "patata", "potatoes": "patata", "sweet potato": "boniato",
    "quinoa": "quinoa", "oats": "avena", "oatmeal": "avena", "bread": "pan",
    "chickpeas": "garbanzo", "lentils": "lenteja", "beans": "alubia", "white beans": "judia blanca",
    "peas": "guisante",
    "onion": "cebolla", "garlic": "ajo", "leek": "puerro",
    "tomato": "tomate", "tomatoes": "tomate", "chopped tomatoes": "tomate triturado",
    "carrot": "zanahoria", "carrots": "zanahoria", "pepper": "pimiento", "bell pepper": "pimiento",
    "red pepper": "pimiento rojo", "green pepper": "pimiento verde",
    "aubergine": "berenjena", "eggplant": "berenjena", "courgette": "calabacin", "zucchini": "calabacin",
    "pumpkin": "calabaza", "broccoli": "brocoli", "cauliflower": "coliflor", "mushroom": "champinon", "mushrooms": "champinon",
    "spinach": "espinaca", "lettuce": "lechuga", "cucumber": "pepino", "celery": "apio", "avocado": "aguacate",
    "olive oil": "aceite de oliva", "oil": "aceite", "butter": "queso",
    "milk": "leche", "yogurt": "yogur", "cheese": "queso",
    "banana": "platano", "apple": "manzana", "orange": "naranja", "strawberry": "fresa", "strawberries": "fresa",
    "almond": "almendra", "almonds": "almendra", "walnut": "nuez", "walnuts": "nuez", "coconut": "coco",
    "honey": "miel", "sugar": "azucar", "brown sugar": "azucar moreno",
    "soy sauce": "salsa de soja", "cornstarch": "maicena", "corn starch": "maicena",
    "ginger": "jengibre", "vinegar": "vinagre", "ketchup": "ketchup", "mustard": "mostaza",
    "yeast": "levadura", "cinnamon": "canela",
    "white wine": "vino blanco", "wine": "vino",
    "chorizo": "chorizo", "cabbage": "repollo", "noodles": "fideos", "hen": "gallina",
}

RACIONES_POR_DEFECTO = 4

# Verbos habituales en pasos de preparación (en varias formas y personas).
# Se usan para detectar, línea a línea, si algo que se ha colado en la
# lista de ingredientes en realidad es un paso de la receta.
_VERBOS_PREPARACION = {
    "cocer", "cocemos", "cuece", "cocinar", "cocinamos", "cocina",
    "hornear", "horneamos", "hornea", "freir", "freír", "freimos", "freímos", "frie", "fríe",
    "saltear", "salteamos", "saltea", "dorar", "doramos", "dora",
    "rehogar", "rehogamos", "rehoga", "sofreir", "sofreír", "sofreimos", "sofreímos", "sofrie", "sofríe",
    "mezclar", "mezclamos", "mezcla", "batir", "batimos", "bate",
    "remover", "removemos", "remueve", "triturar", "trituramos", "tritura",
    "picar", "picamos", "pica", "cortar", "cortamos", "corta",
    "trocear", "troceamos", "trocea", "pelar", "pelamos", "pela",
    "lavar", "lavamos", "lava", "escurrir", "escurrimos", "escurre",
    "reservar", "reservamos", "reserva", "anadir", "anadimos", "anade",
    "agregar", "agregamos", "agrega", "incorporar", "incorporamos", "incorpora",
    "servir", "servimos", "sirve", "dejar", "dejamos", "deja",
    "tapar", "tapamos", "tapa", "destapar", "calentar", "calentamos", "calienta",
    "enfriar", "enfriamos", "enfria", "enfría", "reducir", "reducimos", "reduce",
    "hervir", "hervimos", "hierve", "montar", "montamos", "monta",
    "verter", "vertemos", "vierte", "colar", "colamos", "cuela",
    "precalentar", "precalentamos", "precalienta", "disponer", "disponemos", "dispon",
    "colocar", "colocamos", "coloca", "retirar", "retiramos", "retira",
    "apagar", "apagamos", "apaga", "cubrir", "cubrimos", "cubre",
    "untar", "untamos", "unta", "amasar", "amasamos", "amasa",
    "espolvorear", "espolvoreamos", "removiendo", "cociendo", "cocinando",
}


def _parece_paso_preparacion(linea):
    """Heurística de seguridad: decide si una línea que se ha clasificado
    como 'ingrediente' en realidad tiene toda la pinta de ser un paso de
    la preparación (por ejemplo, si el lector no ha encontrado bien los
    encabezados del documento). No es infalible, pero evita que frases
    largas de instrucciones acaben mezcladas con los ingredientes."""
    texto = linea.strip()
    if not texto:
        return False
    normalizado = _normalizar(texto)
    palabras = normalizado.split()
    if not palabras:
        return False

    # Si empieza directamente por una cantidad ("200 gr...", "1 cebolla"),
    # es casi seguro un ingrediente de verdad, aunque la frase sea larga.
    if re.match(r"^\d", palabras[0]):
        return False

    # Si empieza directamente por un verbo de preparación ("Servimos...",
    # "Dejar reposar...", "Removemos..."), es casi seguro un paso, aunque
    # la frase sea corta.
    primera = palabras[0]
    if primera in _VERBOS_PREPARACION or _stem(primera) in _VERBOS_PREPARACION:
        return True

    hay_verbo = any(_stem(p) in _VERBOS_PREPARACION or p in _VERBOS_PREPARACION for p in palabras)
    if hay_verbo and len(palabras) >= 5:
        return True
    if len(palabras) >= 16:  # frase demasiado larga para ser un solo ingrediente
        return True
    return False


def _normalizar(texto):
    """minúsculas, sin tildes, sin espacios sobrantes."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _stem(palabra):
    """Quita plurales sencillos para poder comparar 'pimientos' con 'pimiento'."""
    if len(palabra) > 4 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 3 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


_PALABRAS_VACIAS = {"de", "del", "en", "con", "al", "a", "y", "el", "la", "los", "las", "un", "una", "unos", "unas"}


def _traducir_ingles_parcial(texto_normalizado):
    """Si el texto contiene alguna palabra o frase en inglés conocida (de
    ALIAS_INGLES), la sustituye por su equivalente en español antes de
    intentar el emparejamiento normal. Prueba primero los alias más largos,
    para no perder 'chicken breast' sustituyendo antes solo 'chicken'."""
    resultado = texto_normalizado
    for alias in sorted(ALIAS_INGLES, key=len, reverse=True):
        alias_norm = _normalizar(alias)
        if alias_norm and alias_norm in resultado:
            resultado = resultado.replace(alias_norm, _normalizar(ALIAS_INGLES[alias]))
    return resultado


def _buscar_ingrediente(nombre_normalizado):
    """Busca la mejor coincidencia dentro de FOOD_DB para un texto de
    ingrediente ya normalizado. Devuelve la clave encontrada o None.

    Prioriza SIEMPRE que la coincidencia incluya la primera palabra con
    contenido del texto (el ingrediente principal), para no confundir por
    ejemplo 'sardinas en aceite de oliva' con 'aceite de oliva' solo porque
    esa clave tiene más palabras coincidentes en total."""
    nombre_normalizado = _traducir_ingles_parcial(nombre_normalizado)
    palabras_ing_todas = [_stem(w) for w in nombre_normalizado.split()]
    palabras_ing = [w for w in palabras_ing_todas if w not in _PALABRAS_VACIAS] or palabras_ing_todas
    primera_palabra = palabras_ing[0]

    mejor_clave = None
    mejor_puntuacion = 0
    mejor_es_principal = False

    for clave in FOOD_DB:
        palabras_clave = [_stem(w) for w in clave.split() if w not in _PALABRAS_VACIAS]
        if not palabras_clave:
            continue
        coincidencias = sum(
            1 for pk in palabras_clave
            if any(pk == pi or pk in pi or pi in pk for pi in palabras_ing)
        )
        if coincidencias != len(palabras_clave):
            continue  # solo nos interesan coincidencias completas de la clave

        es_principal = any(
            pk == primera_palabra or pk in primera_palabra or primera_palabra in pk
            for pk in palabras_clave
        )

        if es_principal and not mejor_es_principal:
            mejor_clave, mejor_puntuacion, mejor_es_principal = clave, coincidencias, True
        elif es_principal == mejor_es_principal and coincidencias > mejor_puntuacion:
            mejor_clave, mejor_puntuacion = clave, coincidencias
    return mejor_clave


def _es_ignorable(nombre_normalizado):
    """Compara PALABRA A PALABRA (no por subcadena) para no confundir
    ingredientes como 'aguacate', 'salmón' o 'ensalada' con las palabras
    de relleno 'agua' o 'sal' solo porque las contienen como texto."""
    palabras_stem = {_stem(w) for w in nombre_normalizado.split()}
    ignorables_stem = {_stem(p) for p in INGREDIENTES_IGNORAR}
    return bool(palabras_stem & ignorables_stem)


def _convertir_fracciones(texto):
    """Convierte fracciones tipo '3/4' o '1 1/2' (formato habitual en
    recetas en inglés, como las de la búsqueda en internet) a un número
    decimal, para poder interpretar la cantidad igual que las demás."""
    m = re.match(r"^(\d+)\s+(\d+)/(\d+)(.*)$", texto)
    if m:
        entero, num, den, resto = m.groups()
        valor = int(entero) + int(num) / int(den)
        return f"{valor:.3f}".rstrip("0").rstrip(".") + resto
    m = re.match(r"^(\d+)/(\d+)(.*)$", texto)
    if m:
        num, den, resto = m.groups()
        valor = int(num) / int(den)
        return f"{valor:.3f}".rstrip("0").rstrip(".") + resto
    return texto


NUMEROS_TEXTO = [
    ("un par de", "2"), ("una docena de", "12"), ("media docena de", "6"),
    ("un par", "2"), ("una docena", "12"), ("media docena", "6"),
    ("medio", "0.5"), ("media", "0.5"),
    ("una", "1"), ("un", "1"), ("uno", "1"),
    ("dos", "2"), ("tres", "3"), ("cuatro", "4"), ("cinco", "5"),
    ("seis", "6"), ("siete", "7"), ("ocho", "8"), ("nueve", "9"), ("diez", "10"),
]


def _convertir_numero_texto(texto):
    """Convierte cantidades escritas en texto ('medio kilo de patatas',
    'una cebolla', 'un par de huevos') al formato numérico que ya sabe
    interpretar el resto del analizador. Prueba primero las frases más
    largas, para no confundir 'un par de' con solo 'un'."""
    texto_norm = texto.lower().strip()
    for frase, valor in NUMEROS_TEXTO:
        if texto_norm == frase or texto_norm.startswith(frase + " "):
            resto = texto[len(frase):]
            return valor + resto
    return texto


def parse_ingrediente(linea):
    """Convierte una línea de ingrediente ('- 200 GR TOMATE TRITURADO') en
    (cantidad, unidad_o_None, nombre_resto)."""
    texto = linea.strip()
    texto = re.sub(r"^[-•*]\s*", "", texto)  # quita viñetas
    texto = _convertir_numero_texto(texto.strip())
    texto = _convertir_fracciones(texto.strip())
    match = re.match(r"^(\d+[.,]?\d*)\s*([a-zA-Záéíóúñ]*)\s*(?:de\s+)?(.*)$", texto)
    if not match:
        return None, None, texto
    cantidad_str, unidad, resto = match.groups()
    cantidad = float(cantidad_str.replace(",", "."))
    unidad = unidad.lower().strip()
    if unidad not in UNIDADES_GRAMOS:
        # lo que se interpretó como "unidad" en realidad es parte del nombre
        resto = (unidad + " " + resto).strip()
        unidad = None
    else:
        # 'cucharadas soperas de maíz', 'puñado generoso de carne'...
        resto = re.sub(r"^(?:soperas?|generos[oa]s?|colmad[oa]s?|rasas?|grandes?|peque[ñn][oa]s?)\s+(?:de\s+)?", "", resto.strip(), flags=re.I)
    return cantidad, unidad, resto.strip()


def _gramos_indicados(linea):
    """Si la línea indica un peso ('aprox. 120-150 g', '200 g'), lo devuelve
    (media del rango); si no, None. Sirve para no perder el peso de un
    ingrediente que no está en la tabla nutricional."""
    m = re.search(r"(\d+[.,]?\d*)\s*(?:-|–|a)\s*(\d+[.,]?\d*)\s*(?:g|gr|grs|gramos)\b", linea, re.I)
    if m:
        a, b = (float(x.replace(",", ".")) for x in m.groups())
        return (a + b) / 2
    m = re.search(r"(\d+[.,]?\d*)\s*(?:g|gr|grs|gramos)\b", linea, re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def estimar_macros(lineas_ingredientes, raciones):
    """Devuelve (kcal, proteina_g, carbos_g, grasa_g, peso_g, no_reconocidos)
    para UNA ración (la receta completa dividida entre 'raciones'). El
    peso_g es el peso en gramos de esa misma ración — se usa después para
    poder escalarla (servir más o menos cantidad) según lo que necesite
    cada comida, en vez de quedarse siempre con una ración fija."""
    raciones = raciones or RACIONES_POR_DEFECTO
    total_kcal = total_prot = total_carb = total_grasa = total_gramos = 0.0
    no_reconocidos = []

    for linea in lineas_ingredientes:
        if not linea.strip():
            continue
        cantidad, unidad, nombre = parse_ingrediente(linea)
        nombre_norm = _normalizar(nombre)

        if not nombre_norm or _es_ignorable(nombre_norm):
            continue

        clave = _buscar_ingrediente(nombre_norm)
        if clave is None:
            no_reconocidos.append(nombre.strip().capitalize())
            g_ind = _gramos_indicados(linea)
            if g_ind:
                total_gramos += g_ind
            continue

        kcal100, prot100, carb100, grasa100, peso_unidad = FOOD_DB[clave]

        if cantidad is None:
            cantidad = 1
        if unidad and unidad in UNIDADES_GRAMOS:
            gramos = cantidad * UNIDADES_GRAMOS[unidad]
        else:
            # sin unidad -> viene en "unidades" (ej. "1 berenjena", "5 huevos")
            gramos = cantidad * peso_unidad
            if "grande" in nombre_norm:
                gramos *= 1.3
            elif "pequen" in nombre_norm:
                gramos *= 0.7

        # si la línea trae un peso aproximado explícito ('aprox. 120-150 g'),
        # se usa en vez de la estimación por unidad ('un puñado')
        if re.search(r"aprox", linea, re.I):
            g_ind = _gramos_indicados(linea)
            if g_ind:
                gramos = g_ind

        factor = gramos / 100.0
        total_kcal += kcal100 * factor
        total_prot += prot100 * factor
        total_carb += carb100 * factor
        total_grasa += grasa100 * factor
        total_gramos += gramos

    return (
        round(total_kcal / raciones),
        round(total_prot / raciones, 1),
        round(total_carb / raciones, 1),
        round(total_grasa / raciones, 1),
        round(total_gramos / raciones),
        no_reconocidos,
    )


def categorizar(kcal, prot, carb, grasa):
    """Asigna una de las categorías nutricionales ya usadas en RPT según
    el reparto de macronutrientes."""
    kcal_prot = prot * 4
    kcal_carb = carb * 4
    kcal_grasa = grasa * 9
    kcal_macros = max(kcal_prot + kcal_carb + kcal_grasa, 1)

    if kcal < 300:
        return "Ligero"
    if kcal_prot / kcal_macros >= 0.35:
        return "Alto en Proteína"
    if kcal_carb / kcal_macros >= 0.55:
        return "Alto en Hidratos"
    if kcal_grasa / kcal_macros >= 0.40:
        return "Alto en Grasas"
    return "Equilibrado"


def _detectar_seccion(linea_normalizada):
    """Identifica si una línea es un encabezado de sección (INGREDIENTES,
    PREPARACIÓN, UTILIZAR EN...), admitiendo sinónimos habituales y sin
    depender de tildes ni mayúsculas exactas. Devuelve el nombre de la
    sección detectada, o None si la línea no es un encabezado."""
    # Una línea de encabezado real es corta (no una frase de la receta)
    if len(linea_normalizada) > 45:
        return None

    if linea_normalizada.startswith("INGREDIENTE"):
        return "ingredientes"

    prefijos_preparacion = [
        "PREPARACION", "ELABORACION", "MODO DE PREPARACION", "MODO DE EMPLEO",
        "INSTRUCCIONES", "PASOS", "COMO SE HACE", "ELABORA", "PROCEDIMIENTO",
    ]
    for pref in prefijos_preparacion:
        if linea_normalizada.startswith(pref):
            return "preparacion"

    prefijos_utilizar = ["UTILIZAR EN", "APTO PARA", "MOMENTO DEL DIA", "USAR EN"]
    for pref in prefijos_utilizar:
        if linea_normalizada.startswith(pref):
            return "utilizar_en"

    # "Clase de plato" (plato principal / guarnición / postre...) no es un
    # dato que usemos, pero SÍ es un encabezado de sección real: si no lo
    # reconocemos como tal, su contenido se cuela dentro de la sección
    # anterior (normalmente "Utilizar en"), ensuciando esa etiqueta.
    if linea_normalizada.startswith("CLASE DE PLATO"):
        return "descartado"

    prefijos_estudio = [
        "ESTUDIO ENERGETICO", "INFORMACION NUTRICIONAL", "VALOR NUTRICIONAL",
        "APORTE CALORICO", "APORTE NUTRICIONAL", "DATOS NUTRICIONALES",
        "ANALISIS NUTRICIONAL", "VALORES NUTRICIONALES", "COMPOSICION NUTRICIONAL",
    ]
    for pref in prefijos_estudio:
        if linea_normalizada.startswith(pref):
            return "estudio_energetico"

    return None


def _iter_bloques(documento):
    """Recorre el documento en el ORDEN REAL en que aparecen los párrafos y
    las tablas. python-docx normalmente los expone en dos listas separadas
    (document.paragraphs y document.tables) que no reflejan el orden real
    ni permiten saber qué iba primero; aquí se leen directamente del XML
    para no perder ese orden."""
    body = documento.element.body
    for hijo in body.iterchildren():
        if hijo.tag == qn('w:p'):
            yield Paragraph(hijo, documento)
        elif hijo.tag == qn('w:tbl'):
            yield Table(hijo, documento)


def _lineas_de_tabla(tabla):
    """Convierte una tabla de Word en líneas de texto para el mismo lector
    de secciones que se usa con párrafos normales. Las fichas de receta
    muchas veces ponen los ingredientes en una tabla de 2 columnas
    (cantidad | ingrediente): en ese caso se unen ambas celdas en una sola
    línea por fila. Si una fila tiene una sola celda con contenido (por
    ejemplo, un encabezado de sección o un párrafo largo), se conserva tal
    cual, respetando también sus saltos de línea internos."""
    lineas = []
    for fila in tabla.rows:
        vistas = set()
        celdas_texto = []
        for celda in fila.cells:
            marca = id(celda._tc)
            if marca in vistas:  # celdas combinadas: no repetir contenido
                continue
            vistas.add(marca)
            texto_celda = celda.text.strip()
            if texto_celda:
                celdas_texto.append(texto_celda)

        if not celdas_texto:
            continue
        elif len(celdas_texto) == 1:
            lineas.extend(celdas_texto[0].split("\n"))
        else:
            lineas.append(" ".join(celdas_texto))
    return lineas


def _extraer_lineas_documento(documento):
    """Devuelve la lista completa de líneas de texto del documento, mezclando
    párrafos sueltos y tablas en el orden en que aparecen de verdad."""
    lineas = []
    for bloque in _iter_bloques(documento):
        if isinstance(bloque, Paragraph):
            texto = bloque.text.strip()
            if texto:
                lineas.append(texto)
        elif isinstance(bloque, Table):
            lineas.extend(_lineas_de_tabla(bloque))
            # Añadimos también las tablas anidadas dentro de celdas, por si
            # la estructura tiene una tabla dentro de otra tabla
            for fila in bloque.rows:
                for celda in fila.cells:
                    for subtabla in celda.tables:
                        lineas.extend(_lineas_de_tabla(subtabla))
    return lineas


def _extraer_kcal_declarado(lineas_estudio):
    """Busca un número de kcal mencionado en el apartado de estudio
    energético del documento (si lo hay), solo para poder mostrar una
    comparación informativa al usuario junto al cálculo de la app."""
    texto = " ".join(lineas_estudio)
    m = re.search(r"(\d[\d.,]*)\s*k?cal", texto, re.IGNORECASE)
    if not m:
        return None
    numero = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(numero)
    except ValueError:
        return None


def _a_numero_es(texto):
    try:
        return float(texto.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _extraer_macros_declarados(lineas_estudio):
    """Busca en el apartado de estudio energético del documento (texto o
    tabla, ya convertida a líneas) los valores nutricionales que el
    propio documento declara: kcal, proteína, carbohidratos y grasas por
    ración. Cuando el documento los da de forma clara y completa, son más
    fiables que estimarlos a partir de los ingredientes (que dependen de
    que cada línea de ingrediente esté bien formada, con la cantidad en
    el sitio esperado) — así que se usan como valor principal cuando
    están disponibles los cuatro datos. También intenta rescatar el
    nombre del plato, por si solo aparece como fila suelta de una tabla
    (algo habitual cuando la ficha no tiene un título de documento aparte).
    Devuelve (macros_dict, nombre_o_None)."""
    resultado = {}
    nombre_tabla = None

    m_kcal = re.search(r"(\d[\d.,]*)\s*k?cal", " ".join(lineas_estudio), re.IGNORECASE)
    if m_kcal:
        numero = _a_numero_es(m_kcal.group(1))
        if numero:
            resultado["kcal"] = numero

    patrones = {
        "proteina_g": r"prote[ií]nas?\D{0,15}?(\d[\d.,]*)\s*g",
        "carbos_g": r"(?:hidratos de carbono|carbohidratos)\D{0,15}?(\d[\d.,]*)\s*g",
        "grasa_g": r"grasas?\D{0,15}?(\d[\d.,]*)\s*g",
    }
    for clave, patron in patrones.items():
        m = re.search(patron, " ".join(lineas_estudio), re.IGNORECASE)
        if m:
            numero = _a_numero_es(m.group(1))
            if numero is not None:
                resultado[clave] = numero

    # Si alguna línea suelta no contiene ningún dato numérico y tiene
    # pinta de título (corta, sin dos puntos, varias palabras en
    # mayúsculas), es probable que sea el nombre del plato colado como
    # fila de tabla (p.ej. la primera fila de la tabla de nutrientes).
    for linea in lineas_estudio:
        if re.search(r"\d", linea) or ":" in linea or len(linea) > 60:
            continue
        palabras_mayus = sum(1 for palabra in linea.split() if palabra.isupper() and len(palabra) > 2)
        if palabras_mayus >= 2:
            nombre_tabla = linea.strip().title()
            break

    return resultado, nombre_tabla


def parse_docx(file_like):
    """Lee un .docx con la estructura estándar de fichas RPT y devuelve un
    diccionario con nombre, raciones, ingredientes (lista), preparación
    (texto) y utilizar_en (texto tipo 'Almuerzo, Cena').

    Es tolerante con: sinónimos de los encabezados (ELABORACIÓN, PASOS...),
    encabezados que llevan el primer contenido pegado en la misma línea
    (ej. 'PREPARACIÓN: Doramos las costillas...'), líneas partidas con
    Mayús+Intro dentro de un mismo párrafo, viñetas o numeración, y también
    tablas (ingredientes en una tabla de 2 columnas, por ejemplo)."""
    documento = docx.Document(file_like)
    parrafos = _extraer_lineas_documento(documento)

    nombre = "Plato sin nombre"
    raciones = RACIONES_POR_DEFECTO
    listas = {"ingredientes": [], "preparacion": [], "utilizar_en": [], "estudio_energetico": []}
    seccion = None
    titulo_detectado = False
    algun_encabezado_detectado = False
    lineas_sin_seccion = []  # respaldo, por si el documento no tiene encabezados

    def _agregar(seccion_destino, texto):
        if seccion_destino not in listas:
            return
        fragmentos = texto.split("\n")
        if seccion_destino == "ingredientes":
            # Los ingredientes a veces vienen todos en una sola línea
            # separados por comas, en vez de uno por línea/viñeta.
            expandido = []
            for frag in fragmentos:
                expandido.extend(frag.split(","))
            fragmentos = expandido
        for sub in fragmentos:
            sub = re.sub(r"^[\s\-•*\u2022]+", "", sub).strip()
            sub = re.sub(r"^\d+[\.\)]\s*", "", sub)  # quita numeración "1. " / "1) "
            if sub:
                listas[seccion_destino].append(sub)

    for linea in parrafos:
        limpio = linea.strip()
        if not limpio:
            continue

        normalizado = _normalizar(limpio).upper()

        # La primera línea con contenido real debería ser el título del
        # plato — salvo que el documento no tenga título propio y empiece
        # directamente por un encabezado de sección (p.ej. "INGREDIENTES
        # (PARA 1 PERSONA):"), en cuyo caso NO la tratamos como título:
        # dejamos que caiga en la detección de sección normal, más abajo.
        if not titulo_detectado:
            cabecera_titulo, _, _ = limpio.partition(":")
            es_seccion_ya = _detectar_seccion(_normalizar(cabecera_titulo).upper()) or _detectar_seccion(normalizado)
            titulo_detectado = True
            if not es_seccion_ya:
                match = re.search(r"\(?\s*(\d+)\s*(?:raci|persona)", limpio, re.IGNORECASE)
                if match:
                    raciones = int(match.group(1))
                nombre = re.sub(r"\(.*(?:raci|persona).*\)", "", limpio, flags=re.IGNORECASE).strip()
                nombre = nombre.title() if nombre else "Plato sin nombre"
                continue

        # ¿Es esta línea un encabezado de sección? (puede llevar contenido pegado tras ":")
        cabecera, _, resto = limpio.partition(":")
        cabecera_norm = _normalizar(cabecera).upper()
        nueva_seccion = _detectar_seccion(cabecera_norm) or _detectar_seccion(normalizado)

        if nueva_seccion:
            seccion = nueva_seccion
            algun_encabezado_detectado = True
            if nueva_seccion == "ingredientes":
                match_rac = re.search(r"\(?\s*(\d+)\s*(?:raci|persona)", limpio, re.IGNORECASE)
                if match_rac:
                    raciones = int(match_rac.group(1))
            if resto.strip():
                _agregar(seccion, resto)
            continue

        if seccion in listas:
            _agregar(seccion, limpio)
        else:
            lineas_sin_seccion.append(limpio)

    # Modo de respaldo: si el documento no tenía NINGÚN encabezado de
    # sección reconocible, no hay forma de saber por título dónde
    # empiezan los ingredientes y dónde la preparación. En ese caso,
    # clasificamos línea a línea con la misma heurística que detecta
    # pasos de preparación, en vez de descartar todo el contenido.
    if not algun_encabezado_detectado and lineas_sin_seccion:
        for linea in lineas_sin_seccion:
            destino = "preparacion" if _parece_paso_preparacion(linea) else "ingredientes"
            _agregar(destino, linea)

    # Normalizamos "ALMUERZOS"/"CENAS" -> "Almuerzo, Cena". Se comprueban
    # las tres palabras de forma independiente (no con elif) porque a
    # veces vienen combinadas en la misma línea, p.ej. "Almuerzo o cena".
    tags = []
    for tag in listas["utilizar_en"]:
        t_norm = _normalizar(tag)
        encontrada = False
        if "almuerz" in t_norm:
            tags.append("Almuerzo")
            encontrada = True
        if "cena" in t_norm:
            tags.append("Cena")
            encontrada = True
        if "desayun" in t_norm:
            tags.append("Desayuno")
            encontrada = True
        if not encontrada and tag:
            tags.append(tag.strip().capitalize())
    if not tags:
        tags = ["Almuerzo", "Cena"]

    # Red de seguridad: si alguna línea que se ha clasificado como
    # "ingrediente" en realidad tiene toda la pinta de ser un paso de la
    # preparación (por ejemplo, porque el documento no tenía encabezados
    # claros), la pasamos a preparación en vez de dejarla mezclada.
    ingredientes_limpios = []
    pasos_reubicados = []
    for linea in listas["ingredientes"]:
        if _parece_paso_preparacion(linea):
            pasos_reubicados.append(linea)
        else:
            ingredientes_limpios.append(linea)

    macros_declarados, nombre_desde_tabla = _extraer_macros_declarados(listas["estudio_energetico"])
    if nombre == "Plato sin nombre" and nombre_desde_tabla:
        nombre = nombre_desde_tabla

    return {
        "nombre": nombre,
        "raciones": raciones,
        "ingredientes": ingredientes_limpios,
        "preparacion": "\n".join(pasos_reubicados + listas["preparacion"]),
        "utilizar_en": ", ".join(dict.fromkeys(tags)),  # sin duplicados, en orden
        "_pasos_reubicados": len(pasos_reubicados),
        "_kcal_documento": macros_declarados.get("kcal"),
        "_macros_declarados": macros_declarados,
        "_estudio_energetico_texto": "\n".join(listas["estudio_energetico"]),
    }


def procesar_docx_a_plato(file_like):
    """Combina el parseo del documento + la estimación nutricional y
    devuelve un diccionario listo para convertirse en fila del inventario.
    Nunca lanza una excepción por datos raros: si algo no se puede
    calcular, usa valores por defecto seguros."""
    datos = parse_docx(file_like)

    try:
        kcal, prot, carb, grasa, peso_g, no_reconocidos = estimar_macros(datos["ingredientes"], datos["raciones"])
    except Exception:
        kcal, prot, carb, grasa, peso_g, no_reconocidos = 0, 0.0, 0.0, 0.0, 0, []

    # Si el propio documento declara los cuatro datos nutricionales (kcal,
    # proteína, carbohidratos y grasas) de forma clara — típicamente en una
    # tabla de "Valor por ración" — son más fiables que la estimación a
    # partir de ingredientes, que depende de que cada línea esté bien
    # formada (cantidades en paréntesis al final, "un puñado generoso"...
    # no siempre se interpretan bien). El peso en gramos, en cambio, se
    # sigue calculando a partir de los ingredientes: es el único sitio
    # donde tenemos ese dato.
    macros_declarados = datos.get("_macros_declarados") or {}
    usa_valores_declarados = all(k in macros_declarados for k in ("kcal", "proteina_g", "carbos_g", "grasa_g"))
    if usa_valores_declarados:
        kcal = macros_declarados["kcal"]
        prot = macros_declarados["proteina_g"]
        carb = macros_declarados["carbos_g"]
        grasa = macros_declarados["grasa_g"]

    try:
        categoria = categorizar(kcal, prot, carb, grasa)
    except Exception:
        categoria = "Equilibrado"

    aviso_sin_ingredientes = len(datos["ingredientes"]) == 0

    kcal_doc_total = datos.get("_kcal_documento")
    kcal_doc_por_racion = None
    if kcal_doc_total and datos["raciones"] and not usa_valores_declarados:
        kcal_doc_por_racion = round(kcal_doc_total / datos["raciones"])

    return {
        "Plato": datos["nombre"] or "Plato sin nombre",
        "Categoria": categoria,
        "Kcal": int(round(kcal)) if kcal else 0,
        "Proteina_g": float(prot) if prot else 0.0,
        "Carbos_g": float(carb) if carb else 0.0,
        "Grasas_g": float(grasa) if grasa else 0.0,
        "Peso_g": float(peso_g) if peso_g else 0.0,
        "Utilizar_en": datos["utilizar_en"] or "Almuerzo, Cena",
        "Ingredientes": ", ".join(datos["ingredientes"]),
        "Preparacion": datos["preparacion"],
        "_raciones_detectadas": datos["raciones"],
        "_ingredientes_no_reconocidos": no_reconocidos,
        "_sin_ingredientes": aviso_sin_ingredientes,
        "_pasos_reubicados": datos.get("_pasos_reubicados", 0),
        "_kcal_documento_total": kcal_doc_total,
        "_kcal_documento_por_racion": kcal_doc_por_racion,
        "_usa_valores_declarados": usa_valores_declarados,
    }


# ----------------------------------------------------------------------
# LISTA DE LA COMPRA · agrega los ingredientes de todo el menú semanal
# ----------------------------------------------------------------------

# Ingredientes "de fondo de armario" que llevan los desayunos/meriendas fijos
# de la app. No tienen ficha propia en la base de datos, así que se listan
# aparte, sin intentar calcular una cantidad exacta.
_INGREDIENTES_FIJOS = {
    "Porridge/Huevos": ["Avena", "Huevos"],
    "Fruta": ["Fruta de temporada"],
    "Muesli": ["Muesli"],
}


def _formatear_gramos(gramos):
    if gramos >= 1000:
        return f"{gramos / 1000:.2f} kg".replace(".00 kg", " kg")
    return f"{round(gramos)} g"


def _formatear_unidades(unidades):
    if float(unidades).is_integer():
        unidades = int(unidades)
        return f"{unidades} ud" + ("s" if unidades != 1 else "")
    return f"{unidades:.1f} uds"


def generar_lista_compra(datos_menu):
    """A partir del menú semanal (almuerzos y cenas), agrupa y suma los
    ingredientes repetidos para generar una lista de la compra consolidada.

    Devuelve un dict con:
      - 'principales': lista de {'nombre', 'cantidad_texto'} con cantidad
        estimada (agrupando el mismo ingrediente aunque venga en distintas
        unidades o con nombres ligeramente distintos).
      - 'al_gusto': ingredientes sin cantidad relevante (sal, especias...).
      - 'fijos': recordatorio de lo que hace falta para desayunos/meriendas.
    """
    acumulado = {}  # clave_agrupacion -> {'nombre':..., 'gramos': x, 'unidades': y}
    al_gusto = set()
    fijos_detectados = set()

    for datos_dia in datos_menu.values():
        for campo_fijo in ("desayuno", "media_manana", "merienda"):
            valor = datos_dia.get(campo_fijo)
            if valor in _INGREDIENTES_FIJOS:
                fijos_detectados.update(_INGREDIENTES_FIJOS[valor])

        for tipo in ("almuerzo", "cena"):
            plato = datos_dia.get(tipo)
            if not plato:
                continue
            # si la ración de este plato se ajustó (más o menos cantidad
            # que la receta de referencia), escalamos también los
            # ingredientes en la misma proporción, para no pedir siempre
            # los de la receta completa
            factor_racion = plato.get("_factor_racion") or 1.0
            ingredientes_texto = plato.get("Ingredientes", "") or ""
            lineas = [l.strip() for l in ingredientes_texto.split(",") if l.strip()]

            for linea in lineas:
                if _parece_paso_preparacion(linea):
                    # Esto no es un ingrediente de verdad (probablemente un
                    # plato guardado antes de esta corrección, con texto de
                    # preparación colado). Lo ignoramos en vez de ensuciar
                    # la lista de la compra con frases largas.
                    continue
                cantidad, unidad, nombre = parse_ingrediente(linea)
                # quitamos puntuación sobrante al final (p.ej. "especias.")
                # para que coincida bien con la lista de ignorables
                nombre_limpio = re.sub(r"[\s.,;]+$", "", nombre.strip())
                nombre_norm = _normalizar(nombre_limpio)
                if not nombre_norm:
                    continue
                if _es_ignorable(nombre_norm):
                    al_gusto.add(nombre_limpio.capitalize())
                    continue

                clave_match = _buscar_ingrediente(nombre_norm)
                clave_agrupacion = clave_match or nombre_norm
                nombre_mostrar = clave_match.capitalize() if clave_match else nombre_limpio.capitalize()

                if cantidad is None:
                    cantidad = 1
                cantidad = cantidad * factor_racion

                entrada = acumulado.setdefault(
                    clave_agrupacion, {"nombre": nombre_mostrar, "gramos": 0.0, "unidades": 0.0}
                )
                if unidad and unidad in UNIDADES_GRAMOS:
                    entrada["gramos"] += cantidad * UNIDADES_GRAMOS[unidad]
                else:
                    entrada["unidades"] += cantidad

    principales = []
    for entrada in acumulado.values():
        partes = []
        if entrada["gramos"] > 0:
            partes.append(_formatear_gramos(entrada["gramos"]))
        if entrada["unidades"] > 0:
            partes.append(_formatear_unidades(entrada["unidades"]))
        principales.append({"nombre": entrada["nombre"], "cantidad_texto": " + ".join(partes) or "-"})
    principales.sort(key=lambda x: x["nombre"])

    return {
        "principales": principales,
        "al_gusto": sorted(al_gusto),
        "fijos": sorted(fijos_detectados),
    }
