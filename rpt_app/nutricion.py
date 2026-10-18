# -*- coding: utf-8 -*-
"""
nutricion.py
------------
Cálculo de las necesidades calóricas reales del atleta, en vez de un
número fijo inventado. Se basa en:

  1. Metabolismo basal (BMR) según la fórmula de Mifflin-St Jeor, la más
     precisa y más usada actualmente (necesita peso, altura, edad y sexo).
  2. Gasto energético total (TDEE) según la intensidad de entrenamiento
     de CADA día (un día de descanso no gasta lo mismo que un día de
     entrenamiento intenso).
  3. Ajuste según el objetivo de la fase actual (bajar de peso, mantener,
     subir de peso...).

Esto sustituye el antiguo "+600 kcal fijas" que no tenía ninguna base real.
"""

# Multiplicador sobre el metabolismo basal según la intensidad del
# entrenamiento de ese día concreto (equivalente al "factor de actividad"
# de las fórmulas clásicas de gasto energético, pero aplicado día a día).
FACTOR_INTENSIDAD = {
    "Descanso": 1.30,
    "Media": 1.55,
    "Alta": 1.80,
}

# Ajuste según el objetivo de la fase actual del atleta.
FACTOR_OBJETIVO = {
    "Bajar de peso": 0.82,
    "Mantener categoría": 1.00,
    "Subir de peso": 1.12,
    "Ganar fuerza base": 1.08,
    "Pico de forma competición": 0.95,
}

# Reparto orientativo del total diario entre las comidas. El postre de
# almuerzo y cena se resta de esas mismas comidas (no se añade aparte al
# total del día): el plato principal se hace un poco más pequeño para
# dejar sitio a la fruta y/o el yogur.
REPARTO_COMIDAS = {
    "desayuno": 0.18,
    "media_manana": 0.08,
    "almuerzo": 0.26,
    "postre_almuerzo": 0.06,
    "merienda": 0.08,
    "cena": 0.24,
    "postre_cena": 0.10,
}

BMR_POR_DEFECTO = 1600  # solo se usa si faltan datos del perfil


def calcular_bmr(peso_kg, altura_cm, edad, sexo):
    """Metabolismo basal (kcal/día en reposo) según Mifflin-St Jeor."""
    try:
        peso_kg = float(peso_kg)
        altura_cm = float(altura_cm)
        edad = float(edad)
    except (TypeError, ValueError):
        return BMR_POR_DEFECTO
    if peso_kg <= 0 or altura_cm <= 0 or edad <= 0:
        return BMR_POR_DEFECTO
    base = 10 * peso_kg + 6.25 * altura_cm - 5 * edad
    return base + 5 if sexo == "Hombre" else base - 161


def calcular_objetivo_dia(perfil, intensidad):
    """Devuelve (objetivo_kcal, bmr, tdee) para un día con la intensidad
    de entrenamiento indicada, a partir del perfil completo del atleta."""
    bmr = calcular_bmr(
        perfil.get("peso"), perfil.get("altura_cm"), perfil.get("edad"), perfil.get("sexo")
    )
    tdee = bmr * FACTOR_INTENSIDAD.get(intensidad, 1.45)
    factor_obj = FACTOR_OBJETIVO.get(perfil.get("objetivo_fase"), 1.0)
    objetivo = tdee * factor_obj
    # Nunca bajamos de un mínimo seguro (110% del metabolismo basal), para
    # no proponer nunca una ingesta peligrosamente baja.
    objetivo = max(objetivo, bmr * 1.1)
    return round(objetivo), round(bmr), round(tdee)


def repartir_comidas(objetivo_kcal):
    """Reparte el objetivo de kcal del día entre las 5 comidas."""
    return {clave: round(objetivo_kcal * pct) for clave, pct in REPARTO_COMIDAS.items()}


# ----------------------------------------------------------------------
# MACRONUTRIENTES
# ----------------------------------------------------------------------
# Gramos de proteína por kg de peso corporal y día. Para un halterófilo en
# fase competitiva, 1.6-2.2 g/kg es el rango respaldado por la evidencia
# (Rodriguez et al. 2009 / ACSM; Morton et al. 2018). Subimos algo el
# objetivo en fases de pérdida de peso (proteger masa muscular en déficit)
# y lo relajamos ligeramente en superávit (el propio superávit ya protege
# la masa magra, y deja más margen de kcal para carbohidratos/grasa).
PROTEINA_G_POR_KG = {
    "Bajar de peso": 2.2,
    "Mantener categoría": 2.0,
    "Subir de peso": 1.8,
    "Ganar fuerza base": 2.0,
    "Pico de forma competición": 2.0,
}
PROTEINA_G_POR_KG_DEFECTO = 2.0

# Grasa: al menos 0.8 g/kg (salud hormonal) y, por encima de eso, ~25% de
# las kcal totales del día.
GRASA_G_MIN_POR_KG = 0.8
GRASA_PORCENTAJE_KCAL = 0.25


def calcular_objetivo_macros(perfil, objetivo_kcal):
    """Calcula los gramos objetivo de proteína, carbohidratos y grasa para
    un día, a partir del peso del atleta, su fase actual y las kcal totales
    ya calculadas para ese día. Los carbohidratos se calculan con lo que
    queda de las kcal totales tras cubrir proteína y grasa (son los que más
    varían según cuánta energía necesite realmente el día en cuestión)."""
    try:
        peso = float(perfil.get("peso") or 0)
    except (TypeError, ValueError):
        peso = 0
    if peso <= 0:
        peso = 75  # valor de emergencia razonable si falta el peso

    g_prot_kg = PROTEINA_G_POR_KG.get(perfil.get("objetivo_fase"), PROTEINA_G_POR_KG_DEFECTO)
    proteina_g = peso * g_prot_kg
    kcal_proteina = proteina_g * 4

    grasa_g = max(peso * GRASA_G_MIN_POR_KG, (objetivo_kcal * GRASA_PORCENTAJE_KCAL) / 9)
    kcal_grasa = grasa_g * 9

    kcal_restante = max(objetivo_kcal - kcal_proteina - kcal_grasa, objetivo_kcal * 0.15)
    carbos_g = kcal_restante / 4

    return {
        "proteina_g": round(proteina_g),
        "carbos_g": round(carbos_g),
        "grasa_g": round(grasa_g),
    }


def repartir_macros_comidas(macros_dia):
    """Reparte los macros del día entre las 5 comidas, con el mismo
    criterio que el reparto de kcal."""
    return {
        comida: {
            "proteina_g": round(macros_dia["proteina_g"] * pct),
            "carbos_g": round(macros_dia["carbos_g"] * pct),
            "grasa_g": round(macros_dia["grasa_g"] * pct),
        }
        for comida, pct in REPARTO_COMIDAS.items()
    }


# Hidratación: una base de 35 ml/kg de peso (rango habitual en nutrición
# deportiva para un adulto activo), más un extra por el sudor perdido en
# el entrenamiento de ese día. La halterofilia no suda tanto como un
# deporte de resistencia, pero sí lo suficiente como para justificar un
# extra claro en los días de intensidad alta o media.
ML_POR_KG_BASE = 35
EXTRA_HIDRATACION_ML = {"Alta": 900, "Media": 600, "Descanso": 200}


def calcular_objetivo_hidratacion(perfil, intensidad):
    """Calcula el objetivo de agua del día en litros, a partir del peso
    del atleta y la intensidad de entrenamiento de ese día. Es una
    estimación orientativa, no una prescripción médica — el color de la
    orina y la sed son buenas señales complementarias para ajustar."""
    try:
        peso = float(perfil.get("peso") or 0)
    except (TypeError, ValueError):
        peso = 0
    if peso <= 0:
        peso = 75
    ml_totales = peso * ML_POR_KG_BASE + EXTRA_HIDRATACION_ML.get(intensidad, 500)
    return round(ml_totales / 1000, 1)
