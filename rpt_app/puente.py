# -*- coding: utf-8 -*-
"""
puente.py
---------
Recibe en Nutrición los datos que envía WorkOut 2.0 por el enlace
("Abrir en Nutrición"). Los datos viajan en el propio enlace (parámetro
'wo'), codificados en base64 URL-safe; no pasan por ningún servidor.

Como cualquiera puede escribir un enlace a mano, TODO se valida: solo se
aceptan campos conocidos, con valores razonables.

Formato (versión 1), JSON:
  {"v":1, "n":"Rafa", "p":94.0, "c":"M50 -94", "f":"2026-11-14",
   "cn":"Campeonato de España", "cd":"S", "hp":"08:00", "hi":"10:00",
   "w":"2026-10-19", "i":{"L":"A","M":"D","X":"A","J":"M","V":"D","S":"A","D":"D"}}
   n nombre · p peso (kg) · c categoría · f fecha de la competición ·
   cn nombre de la competición · cd día de la competición (L M X J V S D) ·
   hp hora del pesaje · hi hora de inicio · w lunes de la semana ·
   i intensidad por día: A alta, M media, D descanso.
"""
import base64
import json
import re
from datetime import date, datetime

DIAS = {"L": "Lunes", "M": "Martes", "X": "Miércoles", "J": "Jueves",
        "V": "Viernes", "S": "Sábado", "D": "Domingo"}
INTENSIDAD = {"A": "Alta", "M": "Media", "D": "Descanso"}


def codificar(datos):
    """Utilidad para pruebas: dict -> texto base64 URL-safe."""
    crudo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")


def _hora_a_min(texto):
    m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", str(texto or "").strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _texto(valor, maximo):
    valor = re.sub(r"[\x00-\x1f<>]", "", str(valor or "")).strip()
    return valor[:maximo]


def decodificar(texto):
    """Devuelve un dict ya validado, o None si el enlace no es válido.
    Claves del resultado: nombre, peso, categoria, competicion,
    fecha_competicion (date|None), semana (str|None), intensidades
    ({'Lunes': 'Alta', ...}), comp ({'dia','pesaje_min','inicio_min'}|None)."""
    if not texto or len(texto) > 4000:
        return None
    try:
        relleno = "=" * (-len(texto) % 4)
        crudo = base64.urlsafe_b64decode(texto + relleno).decode("utf-8")
        d = json.loads(crudo)
    except Exception:
        return None
    if not isinstance(d, dict) or d.get("v") != 1:
        return None

    nombre = _texto(d.get("n"), 60)
    if not nombre:
        return None

    res = {"nombre": nombre, "peso": None, "categoria": _texto(d.get("c"), 30),
           "competicion": _texto(d.get("cn"), 80), "fecha_competicion": None,
           "semana": None, "intensidades": {}, "comp": None}

    try:
        peso = float(d.get("p"))
        if 30 <= peso <= 250:
            res["peso"] = round(peso, 1)
    except (TypeError, ValueError):
        pass

    for clave, destino in (("f", "fecha_competicion"), ("w", "semana")):
        try:
            f = datetime.strptime(str(d.get(clave) or ""), "%Y-%m-%d").date()
            res[destino] = f if destino == "fecha_competicion" else f.isoformat()
        except ValueError:
            pass

    intens = d.get("i")
    if isinstance(intens, dict):
        for letra, val in intens.items():
            if letra in DIAS and val in INTENSIDAD:
                res["intensidades"][DIAS[letra]] = INTENSIDAD[val]

    cd = d.get("cd")
    if cd in DIAS:
        hp = _hora_a_min(d.get("hp"))
        hi = _hora_a_min(d.get("hi"))
        res["comp"] = {
            "dia": DIAS[cd],
            "pesaje_min": hp if hp is not None else 8 * 60,
            "inicio_min": hi if hi is not None else 10 * 60,
            "horas_indicadas": hp is not None and hi is not None,
        }
        if res["comp"]["inicio_min"] <= res["comp"]["pesaje_min"]:
            res["comp"]["pesaje_min"], res["comp"]["inicio_min"] = 8 * 60, 10 * 60
            res["comp"]["horas_indicadas"] = False
    return res


def resumen(datos):
    """Texto corto para mostrar al usuario qué ha llegado."""
    partes = [f"**{datos['nombre']}**"]
    if datos["peso"]:
        partes.append(f"{datos['peso']:g} kg")
    if datos["categoria"]:
        partes.append(f"categoría {datos['categoria']}")
    if datos["intensidades"]:
        partes.append(f"intensidad de {len(datos['intensidades'])} días")
    if datos["comp"]:
        partes.append(f"competición el {datos['comp']['dia']}")
    return " · ".join(partes)
