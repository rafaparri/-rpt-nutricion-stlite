# -*- coding: utf-8 -*-
"""
busqueda_recetas.py
--------------------
Conecta con TheMealDB (https://www.themealdb.com), una base de datos de
recetas gratuita y abierta, sin necesidad de registro ni clave de API,
para poder buscar platos e incorporarlos a tu base de datos sin tener que
escribirlos desde cero.

Ojo: TheMealDB es una base de datos en inglés. Los platos que traigas de
ahí se calculan igual que los demás (mismo motor de kcal/macros), pero el
nombre y la preparación llegan en inglés — la ficha se te muestra siempre
para revisarla (y traducirla si quieres) antes de guardarla.
"""

import re
import urllib.request
import urllib.parse
import json

BASE_URL = "https://www.themealdb.com/api/json/v1/1"
TIMEOUT_SEGUNDOS = 8


def _peticion(url):
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SEGUNDOS) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
        return datos, None
    except Exception as e:
        return None, (
            "No se ha podido conectar con la base de datos de recetas. "
            "Comprueba tu conexión a internet e inténtalo de nuevo. "
            f"(Detalle técnico: {e})"
        )


def buscar_recetas(consulta):
    """Busca platos por nombre en TheMealDB. Devuelve (lista_resultados,
    error). Cada resultado es {'id', 'nombre', 'categoria', 'miniatura'}."""
    consulta = (consulta or "").strip()
    if not consulta:
        return [], "Escribe algo para buscar (por ejemplo: chicken, salmon, pasta...)."

    url = f"{BASE_URL}/search.php?s={urllib.parse.quote(consulta)}"
    datos, error = _peticion(url)
    if error:
        return [], error

    meals = datos.get("meals") if datos else None
    if not meals:
        return [], None  # sin resultados, pero sin error

    resultados = [
        {
            "id": m.get("idMeal"),
            "nombre": m.get("strMeal", "Sin nombre"),
            "categoria": m.get("strCategory", ""),
            "area": m.get("strArea", ""),
            "miniatura": m.get("strMealThumb", ""),
        }
        for m in meals
    ]
    return resultados, None


def _ingredientes_de_receta(meal):
    """TheMealDB guarda los ingredientes como 20 pares de campos sueltos
    (strIngredient1..20 / strMeasure1..20). Los combinamos en líneas del
    tipo '250 g chicken breast', que es el formato que ya sabe leer el
    resto de la aplicación."""
    lineas = []
    for i in range(1, 21):
        nombre = (meal.get(f"strIngredient{i}") or "").strip()
        medida = (meal.get(f"strMeasure{i}") or "").strip()
        if not nombre:
            continue
        if medida and not re.match(r"^to\s*taste$", medida, re.IGNORECASE):
            lineas.append(f"{medida} {nombre}")
        else:
            lineas.append(f"1 {nombre}")
    return lineas


def obtener_receta(id_receta):
    """Descarga la ficha completa de una receta por su id. Devuelve
    (receta, error), donde receta es un dict con nombre, ingredientes
    (lista de líneas), preparación (texto) y miniatura."""
    url = f"{BASE_URL}/lookup.php?i={urllib.parse.quote(str(id_receta))}"
    datos, error = _peticion(url)
    if error:
        return None, error

    meals = datos.get("meals") if datos else None
    if not meals:
        return None, "No se ha encontrado esa receta (puede que ya no exista en la base de datos)."

    meal = meals[0]
    return {
        "nombre": meal.get("strMeal", "Plato sin nombre"),
        "ingredientes": _ingredientes_de_receta(meal),
        "preparacion": (meal.get("strInstructions") or "").strip(),
        "miniatura": meal.get("strMealThumb", ""),
        "categoria_origen": meal.get("strCategory", ""),
        "area": meal.get("strArea", ""),
    }, None
