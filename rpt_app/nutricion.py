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


# ----------------------------------------------------------------------
# DÍA DE COMPETICIÓN: línea de tiempo según hora de pesaje y de inicio
# ----------------------------------------------------------------------
def _hm(minutos):
    minutos = int(minutos) % (24 * 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def plan_dia_competicion(peso_kg, hora_pesaje_min, hora_inicio_min):
    """Devuelve (aviso, pasos). Las horas se dan en minutos desde las 00:00.
    pasos = lista de dicts {hora, titulo, detalle}. Pautas generales de
    nutrición deportiva para halterofilia (categoría por peso, pesaje previo);
    no sustituyen a un profesional si hay que ajustar peso."""
    try:
        p = float(peso_kg)
    except (TypeError, ValueError):
        p = 80.0
    W, T = int(hora_pesaje_min), int(hora_inicio_min)
    hueco = T - W
    aviso = None
    if hueco <= 0:
        return ("La hora de pesaje debe ser anterior a la hora de inicio de la competición.", [])
    if hueco < 60:
        aviso = (f"Solo hay {hueco} min entre pesaje y competición: se prioriza líquido con sodio e hidratos "
                 "muy fáciles de digerir, sin comida sólida.")

    c1 = round(p * 1.0)          # 1 g/kg
    c_lo, c_hi = round(p * 0.3), round(p * 0.5)
    c_post_lo, c_post_hi = round(p * 1.0), round(p * 1.2)
    prot_post_lo, prot_post_hi = round(p * 0.3), round(p * 0.4)
    cafeina = round(p * 3)

    pasos = []
    pasos.append({
        "hora": "Día anterior",
        "titulo": "Carga de hidratos y digestión ligera",
        "detalle": (f"Hidratos altos (unos {round(p*6)}–{round(p*8)} g en el día), grasa y fibra bajas "
                    "desde la tarde, nada nuevo. No recortes sal ni agua el día anterior salvo indicación "
                    f"de tu entrenador. Líquidos: unos {round(p*35)}–{round(p*40)} ml repartidos. Cena temprana "
                    "y fácil de digerir (arroz, pasta, patata, pollo o pescado a la plancha)."),
    })
    pasos.append({
        "hora": _hm(W - 150),
        "titulo": "Al levantarte (antes del pesaje)",
        "detalle": (f"Si estás holgado de peso: desayuno ligero de unos {round(p*0.5)}–{c1} g de hidratos, "
                    "bajo en fibra y grasa (tostadas con mermelada, arroz, plátano). "
                    "Si vas justo de peso: solo agua o bebida con electrolitos y espera al pesaje."),
    })
    pasos.append({
        "hora": _hm(W),
        "titulo": "⚖️ Pesaje",
        "detalle": "Llévate a la sala bebida con electrolitos, hidratos rápidos y un tentempié que ya conozcas.",
    })
    if hueco >= 60:
        pasos.append({
            "hora": _hm(W + 10),
            "titulo": "Tras el pesaje: rehidratar y comer",
            "detalle": (f"Bebe 500–750 ml con sodio en la primera hora y toma unos {c1} g de hidratos fáciles de "
                        f"digerir (arroz, pan blanco, plátano, bebida deportiva) con 20–30 g de proteína ligera. "
                        "Poca grasa y poca fibra."),
        })
    else:
        pasos.append({
            "hora": _hm(W + 5),
            "titulo": "Tras el pesaje: líquido e hidratos rápidos",
            "detalle": (f"Bebida con sodio e hidratos líquidos (unos {c_lo}–{c_hi} g) en sorbos; sin sólidos."),
        })
    if hueco >= 90:
        pasos.append({
            "hora": _hm(T - 60),
            "titulo": "1 hora antes de empezar",
            "detalle": (f"Hidratos simples: {c_lo}–{c_hi} g (gel, fruta madura, bebida deportiva). "
                        f"Si ya la usas habitualmente, cafeína unos 3 mg/kg (≈ {cafeina} mg); si no, no la pruebes hoy."),
        })
    pasos.append({
        "hora": _hm(T - 15),
        "titulo": "Calentamiento",
        "detalle": "Sorbos de agua o bebida isotónica. Nada de comida sólida a partir de ahora.",
    })
    pasos.append({
        "hora": _hm(T),
        "titulo": "🏋️ Durante la competición",
        "detalle": ("Entre intentos y bloques: 15–30 g de hidratos rápidos (gel, plátano, bebida deportiva) y "
                    "150–250 ml de líquido cuando haya margen. Si hay mucho tiempo entre arrancada y dos tiempos, "
                    "toma algo más sustancial y fácil de digerir."),
    })
    pasos.append({
        "hora": "Al terminar",
        "titulo": "Recuperación",
        "detalle": (f"En las 2 primeras horas: {c_post_lo}–{c_post_hi} g de hidratos y {prot_post_lo}–{prot_post_hi} g "
                    "de proteína, más líquidos con sal. Después, comida normal completa."),
    })
    return aviso, pasos
