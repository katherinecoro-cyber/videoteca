"""Dónde se guardan los tutoriales.

Si en los Secrets están SUPABASE_URL y SUPABASE_KEY, todo se guarda en
Supabase (permanente). Si no, se usa la carpeta local (útil para pruebas
en tu computadora, pero en Streamlit Cloud se borra al reiniciar).
"""

import json
import os
import uuid
from pathlib import Path

import requests
import streamlit as st

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "videos.json"
UPLOAD_DIR = BASE / "uploads"

TABLA = "videos"
BUCKET = "videoteca"
# Límite por archivo del plan gratuito de Supabase.
LIMITE_SUPABASE_MB = 50


def _secreto(nombre):
    try:
        return st.secrets[nombre]
    except (KeyError, FileNotFoundError):
        return os.environ.get(nombre)


SUPABASE_URL = (_secreto("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = _secreto("SUPABASE_KEY")
USA_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)


class ErrorAlmacen(Exception):
    pass


def _cabeceras(extra=None):
    cabeceras = {"apikey": SUPABASE_KEY}
    # Las claves antiguas (service_role) son JWT y también van en Authorization;
    # las nuevas (sb_secret_...) solo necesitan la cabecera apikey.
    if SUPABASE_KEY.startswith("eyJ"):
        cabeceras["Authorization"] = f"Bearer {SUPABASE_KEY}"
    cabeceras.update(extra or {})
    return cabeceras


def _revisar(respuesta):
    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("message") or respuesta.text
        except ValueError:
            detalle = respuesta.text
        raise ErrorAlmacen(f"Supabase respondió {respuesta.status_code}: {detalle}")
    return respuesta


# ---------- Lista de tutoriales ----------

@st.cache_data(ttl=60, show_spinner=False)
def leer_videos():
    if USA_SUPABASE:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{TABLA}", headers=_cabeceras(),
                         params={"select": "*", "order": "fecha.desc"}, timeout=20)
        return _revisar(r).json()
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _guardar_local(videos):
    DATA_FILE.parent.mkdir(exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def agregar_video(video):
    if USA_SUPABASE:
        _revisar(requests.post(f"{SUPABASE_URL}/rest/v1/{TABLA}", json=video,
                               headers=_cabeceras({"Prefer": "return=minimal"}), timeout=20))
    else:
        _guardar_local(leer_videos() + [video])
    leer_videos.clear()


def actualizar_video(id_video, cambios):
    if USA_SUPABASE:
        _revisar(requests.patch(f"{SUPABASE_URL}/rest/v1/{TABLA}", json=cambios,
                                params={"id": f"eq.{id_video}"},
                                headers=_cabeceras({"Prefer": "return=minimal"}), timeout=20))
    else:
        videos = leer_videos()
        for v in videos:
            if v["id"] == id_video:
                v.update(cambios)
        _guardar_local(videos)
    leer_videos.clear()


def eliminar_video(video):
    if USA_SUPABASE:
        _revisar(requests.delete(f"{SUPABASE_URL}/rest/v1/{TABLA}", params={"id": f"eq.{video['id']}"},
                                 headers=_cabeceras(), timeout=20))
    else:
        _guardar_local([v for v in leer_videos() if v["id"] != video["id"]])
    borrar_archivo(video.get("archivo"))
    borrar_archivo(video.get("miniatura"))
    leer_videos.clear()


# ---------- Archivos (videos y miniaturas) ----------

def guardar_archivo(archivo):
    """Guarda un archivo subido con un nombre único y devuelve ese nombre."""
    nombre = f"{uuid.uuid4()}{Path(archivo.name).suffix.lower()}"
    if USA_SUPABASE:
        if archivo.size > LIMITE_SUPABASE_MB * 1024 * 1024:
            raise ErrorAlmacen(
                f"El archivo pesa más de {LIMITE_SUPABASE_MB} MB, el máximo del plan gratuito. "
                "Súbelo a YouTube o Google Drive y usa la opción de enlace."
            )
        r = requests.post(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{nombre}", data=archivo.getvalue(),
                          headers=_cabeceras({"Content-Type": archivo.type or "application/octet-stream"}),
                          timeout=600)
        _revisar(r)
    else:
        UPLOAD_DIR.mkdir(exist_ok=True)
        (UPLOAD_DIR / nombre).write_bytes(archivo.getbuffer())
    return nombre


def ruta_archivo(nombre):
    """URL pública (Supabase) o ruta local que entienden st.video y st.image."""
    if USA_SUPABASE:
        return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{nombre}"
    return str(UPLOAD_DIR / Path(nombre).name)


def borrar_archivo(nombre):
    if not nombre:
        return
    if USA_SUPABASE:
        # Si falla, solo queda un archivo huérfano; no impide borrar el tutorial.
        requests.delete(f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{nombre}", headers=_cabeceras(), timeout=20)
    else:
        (UPLOAD_DIR / Path(nombre).name).unlink(missing_ok=True)
