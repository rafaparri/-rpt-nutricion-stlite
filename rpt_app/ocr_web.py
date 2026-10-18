# -*- coding: utf-8 -*-
"""
ocr_web.py
----------
Lectura de fotos de entrenamiento DENTRO DEL NAVEGADOR (versión stlite),
usando Tesseract.js (el mismo Tesseract, compilado para el navegador).
Solo funciona cuando la app corre en el navegador (sys.platform == 'emscripten').
"""
import sys
import json
import io

EN_NAVEGADOR = sys.platform == "emscripten"
URL_TESSERACT = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.esm.min.js"


async def leer_palabras(imagen_bytes):
    """Devuelve (palabras, ancho, alto) con el formato que espera
    entrenamiento.interpretar_palabras_ocr."""
    from PIL import Image
    from pyodide.code import run_js
    from pyodide.ffi import to_js
    import js

    imagen = Image.open(io.BytesIO(imagen_bytes))
    ancho, alto = imagen.size

    modulo = await run_js(
        f"import('{URL_TESSERACT}').then(m => (m.createWorker ? m : (m.default || m)))"
    )
    trabajador = await modulo.createWorker("spa")
    try:
        blob = js.Blob.new(to_js([to_js(imagen_bytes)]))
        resultado = await trabajador.recognize(blob)
        crudo = json.loads(js.JSON.stringify(resultado.data.words))
    finally:
        try:
            await trabajador.terminate()
        except Exception:
            pass

    palabras = []
    for w in crudo:
        texto = (w.get("text") or "").strip()
        if not texto:
            continue
        caja = w.get("bbox") or {}
        palabras.append({
            "texto": texto,
            "x": caja.get("x0", 0),
            "y": caja.get("y0", 0),
            "conf": int(w.get("confidence", 0) or 0),
        })
    return palabras, ancho, alto
