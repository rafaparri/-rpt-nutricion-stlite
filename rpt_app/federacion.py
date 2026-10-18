# -*- coding: utf-8 -*-
"""
federacion.py
-------------
Categorías de peso oficiales de la Federación Internacional de
Halterofilia (IWF) y calendario de competiciones oficiales, para que se
puedan seleccionar en vez de escribirlas a mano.

Datos comprobados en julio de 2026. La IWF cambió sus categorías de peso
el 1 de agosto de 2026 (Congreso de la IWF, noviembre de 2025), así que
aquí se incluyen las dos vigencias: las nuevas (desde el 1/8/2026, las
que aplican a partir de ahora) y las anteriores (hasta el 31/7/2026, por
si el atleta compite antes de esa fecha).
"""

from datetime import date

CATEGORIAS_IWF = {
    "Vigentes desde el 1/8/2026": {
        "Hombre": ["60 kg", "65 kg", "70 kg", "75 kg", "85 kg", "95 kg", "110 kg", "+110 kg"],
        "Mujer": ["49 kg", "53 kg", "57 kg", "61 kg", "69 kg", "77 kg", "86 kg", "+86 kg"],
    },
    "Vigentes hasta el 31/7/2026": {
        "Hombre": ["60 kg", "65 kg", "71 kg", "79 kg", "88 kg", "94 kg", "110 kg", "+110 kg"],
        "Mujer": ["48 kg", "53 kg", "58 kg", "63 kg", "69 kg", "77 kg", "86 kg", "+86 kg"],
    },
}

CATEGORIA_PERSONALIZADA = "Otra / especificar a mano"

# Calendario de competiciones oficiales verificado (fecha de inicio real).
# 'fecha' es la fecha de inicio del evento o de las pruebas de halterofilia.
COMPETICIONES_OFICIALES = {
    "Commonwealth Games 2026 (Glasgow, GBR)": {
        "fecha": date(2026, 7, 26),
        "sede": "Glasgow, Escocia",
        "nota": "Pruebas de halterofilia: 26–30 de julio de 2026.",
    },
    "Campeonato del Mundo IWF 2026 (Ningbo, CHN)": {
        "fecha": date(2026, 10, 27),
        "sede": "Ningbo, China",
        "nota": "27 de octubre – 8 de noviembre de 2026.",
    },
}

COMPETICION_PERSONALIZADA = "Otra competición (no oficial / personalizada)"
