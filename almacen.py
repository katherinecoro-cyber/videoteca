"""Dónde se guardan la lista de tutoriales y las estadísticas de uso.

Si en los Secrets está VIDEOTECA_GITHUB_TOKEN, se guardan como archivos
`data/videos.json` y `data/estadisticas.json` en una rama aparte del propio
repositorio de GitHub ("datos-videoteca"), así no se pierden cuando Streamlit
reinicia la app. Si no, se usa la carpeta local (útil para pruebas).
"""

import base64
import json
import os
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

BASE = Path(__file__).parent
RUTA_VIDEOS = "data/videos.json"
RUTA_ESTADISTICAS = "data/estadisticas.json"


def _secreto(nombre, defecto=None):
    try:
        return st.secrets[nombre]
    except (KeyError, FileNotFoundError):
        return os.environ.get(nombre, defecto)


GITHUB_TOKEN = _secreto("VIDEOTECA_GITHUB_TOKEN")
GITHUB_REPO = _secreto("VIDEOTECA_GITHUB_REPO", "katherinecoro-cyber/videoteca")
# Rama aparte para los datos: guardar en la rama de la app la haría reiniciarse.
RAMA_DATOS = _secreto("VIDEOTECA_RAMA_DATOS", "datos-videoteca")
API = _secreto("VIDEOTECA_GITHUB_API", "https://api.github.com").rstrip("/")
USA_GITHUB = bool(GITHUB_TOKEN)
ZONA_HORARIA = ZoneInfo(_secreto("VIDEOTECA_ZONA_HORARIA", "America/La_Paz"))


class ErrorAlmacen(Exception):
    pass


# ---------- GitHub ----------

def _pedir(metodo, ruta, **kwargs):
    r = requests.request(metodo, f"{API}/repos/{GITHUB_REPO}{ruta}", timeout=20, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }, **kwargs)
    if r.status_code in (401, 403):
        raise ErrorAlmacen("GitHub rechazó el token. Revisa que VIDEOTECA_GITHUB_TOKEN sea correcto, no haya "
                           "vencido y tenga permiso de escritura (Contents) sobre el repositorio.")
    return r


def _leer_github(ruta, vacio):
    """Devuelve (datos, sha). sha es None si el archivo todavía no existe."""
    r = _pedir("GET", f"/contents/{ruta}", params={"ref": RAMA_DATOS})
    if r.status_code == 404:
        return vacio, None
    if r.status_code != 200:
        raise ErrorAlmacen(f"No se pudo leer {ruta} en GitHub ({r.status_code}).")
    datos = r.json()
    return json.loads(base64.b64decode(datos["content"]).decode("utf-8")), datos["sha"]


def _crear_rama_datos():
    principal = _pedir("GET", "").json()["default_branch"]
    r = _pedir("GET", f"/git/ref/heads/{principal}")
    if r.status_code != 200:
        raise ErrorAlmacen(f"No se encontró la rama {principal} en GitHub ({r.status_code}).")
    r = _pedir("POST", "/git/refs", json={"ref": f"refs/heads/{RAMA_DATOS}", "sha": r.json()["object"]["sha"]})
    if r.status_code not in (201, 422):  # 422: ya existe
        raise ErrorAlmacen(f"No se pudo crear la rama {RAMA_DATOS} en GitHub ({r.status_code}).")


def _guardar_github(ruta, datos, sha, mensaje):
    cuerpo = {
        "message": mensaje,
        "content": base64.b64encode(json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")).decode(),
        "branch": RAMA_DATOS,
    }
    if sha:
        cuerpo["sha"] = sha
    r = _pedir("PUT", f"/contents/{ruta}", json=cuerpo)
    if r.status_code == 404 and not sha:
        _crear_rama_datos()
        r = _pedir("PUT", f"/contents/{ruta}", json=cuerpo)
    return r


# ---------- Lectura y escritura de archivos JSON ----------

def _leer(ruta, vacio):
    if USA_GITHUB:
        return _leer_github(ruta, vacio)[0]
    try:
        return json.loads((BASE / ruta).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return vacio


def _modificar(ruta, vacio, cambio, mensaje):
    """Aplica `cambio(datos) -> datos` sobre la versión más reciente y la guarda."""
    if USA_GITHUB:
        # Si otra persona guardó al mismo tiempo, GitHub responde 409: se reintenta con datos frescos.
        for _ in range(3):
            datos, sha = _leer_github(ruta, vacio)
            r = _guardar_github(ruta, cambio(datos), sha, mensaje)
            if r.status_code in (200, 201):
                return
            if r.status_code != 409:
                raise ErrorAlmacen(f"No se pudo guardar en GitHub ({r.status_code}).")
        raise ErrorAlmacen("No se pudo guardar en GitHub: inténtalo de nuevo.")
    archivo = BASE / ruta
    archivo.parent.mkdir(exist_ok=True)
    tmp = archivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(cambio(_leer(ruta, vacio)), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(archivo)


# ---------- Tutoriales ----------

@st.cache_data(ttl=30, show_spinner=False)
def leer_videos():
    return _leer(RUTA_VIDEOS, [])


def modificar_videos(cambio, mensaje):
    _modificar(RUTA_VIDEOS, [], cambio, mensaje)
    leer_videos.clear()


# ---------- Estadísticas de uso ----------
# Guardar en GitHub cada visita sería lento y superaría los límites de la API, así que
# los conteos se acumulan en memoria y se guardan juntos cada pocos minutos.

GUARDAR_CADA_SEGUNDOS = 120
GUARDAR_CADA_EVENTOS = 25


def hoy():
    return datetime.now(ZONA_HORARIA).date().isoformat()


@st.cache_resource
def _pendientes():
    """Conteos aún no guardados, compartidos por todas las sesiones de la app."""
    return {"candado": threading.Lock(), "guardando": threading.Lock(), "ultimo": time.time(),
            "visitas": Counter(), "personas_nuevas": Counter(), "vistas_dia": Counter(),
            "vistas_video": Counter(),
            # Para no contar dos veces el mismo video en el mismo navegador y día.
            "vistos_hoy": set(), "dia_vistos": None}


CONTEOS = {"visitas": "visitas_por_dia", "personas_nuevas": "personas_nuevas_por_dia",
           "vistas_dia": "vistas_por_dia", "vistas_video": "vistas_por_video"}


def _sumar(destino, conteo):
    for clave, n in conteo.items():
        destino[clave] = destino.get(clave, 0) + n


def guardar_estadisticas():
    """Guarda en el archivo los conteos acumulados. Devuelve False si falló."""
    p = _pendientes()
    with p["guardando"]:
        with p["candado"]:
            lote = {k: p[k].copy() for k in CONTEOS}
            for k in lote:
                p[k].clear()
            p["ultimo"] = time.time()
        if not any(lote.values()):
            return True

        def aplicar(datos):
            for k, campo in CONTEOS.items():
                _sumar(datos.setdefault(campo, {}), lote[k])
            return datos

        try:
            _modificar(RUTA_ESTADISTICAS, {}, aplicar, "Actualizar estadísticas de uso")
            return True
        except (ErrorAlmacen, requests.RequestException):
            # Se devuelven los conteos para intentarlo en el próximo guardado.
            with p["candado"]:
                for k in lote:
                    p[k].update(lote[k])
            return False


def _registrar(visita=False, nueva_persona=False, video_id=None, visitante=None):
    p = _pendientes()
    with p["candado"]:
        dia = hoy()
        if visita:
            p["visitas"][dia] += 1
        if nueva_persona:
            p["personas_nuevas"][dia] += 1
        if video_id:
            if p["dia_vistos"] != dia:
                p["vistos_hoy"].clear()
                p["dia_vistos"] = dia
            if (visitante, video_id) in p["vistos_hoy"]:
                return
            p["vistos_hoy"].add((visitante, video_id))
            p["vistas_dia"][dia] += 1
            p["vistas_video"][video_id] += 1
        eventos = sum(p["visitas"].values()) + sum(p["vistas_dia"].values())
        toca = time.time() - p["ultimo"] >= GUARDAR_CADA_SEGUNDOS or eventos >= GUARDAR_CADA_EVENTOS
    if not USA_GITHUB:
        guardar_estadisticas()
    elif toca and not p["guardando"].locked():
        # En segundo plano, para que el estudiante no espere a GitHub.
        threading.Thread(target=guardar_estadisticas, daemon=True).start()


def registrar_visita(nueva_persona):
    """Una persona (navegador) entró hoy por primera vez."""
    _registrar(visita=True, nueva_persona=nueva_persona)


def registrar_vista(video_id, visitante):
    """Alguien abrió un tutorial; cuenta una vez por navegador, video y día."""
    _registrar(video_id=video_id, visitante=visitante)


def leer_estadisticas():
    """Estadísticas guardadas más las que aún están en memoria."""
    datos = _leer(RUTA_ESTADISTICAS, {})
    p = _pendientes()
    with p["candado"]:
        for k, campo in CONTEOS.items():
            _sumar(datos.setdefault(campo, {}), p[k])
    return datos
