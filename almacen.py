"""Dónde se guarda la lista de tutoriales.

Si en los Secrets está VIDEOTECA_GITHUB_TOKEN, la lista se guarda como archivo
`data/videos.json` en una rama aparte del propio repositorio de GitHub
("datos-videoteca"), así no se pierde cuando Streamlit reinicia la app.
Si no, se usa la carpeta local (útil para pruebas en tu computadora).
"""

import base64
import json
import os
from pathlib import Path

import requests
import streamlit as st

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "videos.json"
RUTA_EN_REPO = "data/videos.json"


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


def _leer_github():
    """Devuelve (lista, sha). sha es None si el archivo todavía no existe."""
    r = _pedir("GET", f"/contents/{RUTA_EN_REPO}", params={"ref": RAMA_DATOS})
    if r.status_code == 404:
        return [], None
    if r.status_code != 200:
        raise ErrorAlmacen(f"No se pudo leer la lista en GitHub ({r.status_code}).")
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


def _guardar_github(videos, sha, mensaje):
    cuerpo = {
        "message": mensaje,
        "content": base64.b64encode(json.dumps(videos, ensure_ascii=False, indent=2).encode("utf-8")).decode(),
        "branch": RAMA_DATOS,
    }
    if sha:
        cuerpo["sha"] = sha
    r = _pedir("PUT", f"/contents/{RUTA_EN_REPO}", json=cuerpo)
    if r.status_code == 404 and not sha:
        _crear_rama_datos()
        r = _pedir("PUT", f"/contents/{RUTA_EN_REPO}", json=cuerpo)
    return r


# ---------- Interfaz usada por la app ----------

@st.cache_data(ttl=30, show_spinner=False)
def leer_videos():
    if USA_GITHUB:
        return _leer_github()[0]
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def modificar_videos(cambio, mensaje):
    """Aplica `cambio(lista) -> lista` sobre la versión más reciente y la guarda."""
    if USA_GITHUB:
        # Si otra persona guardó al mismo tiempo, GitHub responde 409: se reintenta con datos frescos.
        for _ in range(3):
            videos, sha = _leer_github()
            r = _guardar_github(cambio(videos), sha, mensaje)
            if r.status_code in (200, 201):
                break
            if r.status_code != 409:
                raise ErrorAlmacen(f"No se pudo guardar en GitHub ({r.status_code}).")
        else:
            raise ErrorAlmacen("No se pudo guardar en GitHub: inténtalo de nuevo.")
    else:
        try:
            videos = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            videos = []
        DATA_FILE.parent.mkdir(exist_ok=True)
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(cambio(videos), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_FILE)
    leer_videos.clear()
