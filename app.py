"""Videoteca de tutoriales hecha con Streamlit.

Los estudiantes buscan y ven tutoriales; el administrador sube videos
(archivo o enlace de YouTube) desde la sección "Administrar".
"""

import base64
import hmac
import html
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "videos.json"
UPLOAD_DIR = BASE / "uploads"
ASSETS = BASE / "assets"
DATA_FILE.parent.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

FORMATOS_VIDEO = ["mp4", "webm", "ogg", "mov"]
FORMATOS_IMAGEN = ["jpg", "jpeg", "png", "webp"]

# Colores institucionales de Digital Business School.
AZUL_OSCURO = "#1E3460"
AZUL = "#1D70B7"
BLANCO = "#FFFFFF"

st.set_page_config(page_title="Videoteca de Tutoriales · Digital Business School",
                   page_icon=str(ASSETS / "icono_dbs.png"), layout="wide")


# ---------- Encabezado institucional ----------

def imagen_base64(nombre):
    return base64.b64encode((ASSETS / nombre).read_bytes()).decode()


def encabezado():
    st.html(f"""
    <style>
      .vt-banner {{
        display: flex; align-items: center; gap: 24px;
        background: {BLANCO}; border: 1px solid #D6DEEA; border-radius: 14px;
        padding: 16px 24px 20px; position: relative; overflow: hidden;
      }}
      .vt-banner::after {{
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 6px;
        background: linear-gradient(90deg, {AZUL_OSCURO} 0 50%, {AZUL} 50% 100%);
      }}
      .vt-banner img {{ height: 72px; width: auto; flex-shrink: 0; }}
      .vt-banner .vt-texto {{ border-left: 3px solid {AZUL}; padding-left: 20px; }}
      .vt-banner h1 {{ color: {AZUL_OSCURO}; margin: 0; font-size: 1.9rem; line-height: 1.2; padding: 0; }}
      .vt-banner p {{ margin: 4px 0 0; color: {AZUL}; font-size: 0.95rem; font-weight: 600; }}
      @media (max-width: 640px) {{
        .vt-banner {{ flex-direction: column; align-items: center; text-align: center; gap: 10px; padding: 12px 12px 18px; }}
        .vt-banner img {{ height: 48px; }}
        .vt-banner .vt-texto {{ border-left: none; padding-left: 0; }}
        .vt-banner h1 {{ font-size: 1.3rem; }}
        .vt-banner p {{ font-size: 0.8rem; }}
      }}
    </style>
    <div class="vt-banner">
      <img src="data:image/png;base64,{imagen_base64('logo_dbs_horizontal.png')}"
           alt="Logo de Digital Business School">
      <div class="vt-texto">
        <h1>Videoteca de Tutoriales</h1>
        <p>Digital Business School</p>
      </div>
    </div>
    """)
    # Logo vertical en el menú lateral, sobre una tarjeta blanca para que se vea sobre el azul.
    st.sidebar.html(f"""
    <div style="background:{BLANCO}; border-radius:14px; padding:16px; text-align:center; margin-bottom:8px;">
      <img src="data:image/png;base64,{imagen_base64('logo_dbs_vertical.png')}"
           alt="Logo de Digital Business School" style="max-width:120px; width:100%; height:auto;">
    </div>
    """)
    # Estilos generales: títulos en azul oscuro, botones con borde azul.
    st.html(f"""
    <style>
      .stMainBlockContainer h1, .stMainBlockContainer h2, .stMainBlockContainer h3 {{ color: {AZUL_OSCURO}; }}
      .stMainBlockContainer .stButton button[kind="secondary"] {{
        border-color: {AZUL}; color: {AZUL}; font-weight: 600;
      }}
      .stMainBlockContainer .stButton button[kind="secondary"]:hover {{
        background: {AZUL}; border-color: {AZUL}; color: {BLANCO};
      }}
      .vt-categoria {{
        color: {AZUL}; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
    </style>
    """)


# ---------- Datos ----------

def leer_videos():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def guardar_videos(videos):
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)


def guardar_archivo(archivo):
    """Guarda un archivo subido con un nombre único y devuelve ese nombre."""
    extension = Path(archivo.name).suffix.lower()
    nombre = f"{uuid.uuid4()}{extension}"
    (UPLOAD_DIR / nombre).write_bytes(archivo.getbuffer())
    return nombre


def borrar_archivo(nombre):
    if nombre:
        (UPLOAD_DIR / Path(nombre).name).unlink(missing_ok=True)


def fuente_video(video):
    """Ruta local o enlace que entiende st.video."""
    if video.get("url"):
        return video["url"]
    return str(UPLOAD_DIR / video["archivo"])


def categorias(videos):
    return sorted({v["categoria"] for v in videos}, key=str.lower)


def fecha_legible(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y")


def contrasena_admin():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except (KeyError, FileNotFoundError):
        return os.environ.get("ADMIN_PASSWORD", "admin123")


# ---------- Vista de estudiantes ----------

def tarjeta(video, columna):
    with columna.container(border=True):
        if video.get("miniatura"):
            st.image(str(UPLOAD_DIR / video["miniatura"]), use_container_width=True)
        else:
            st.video(fuente_video(video))
        st.markdown(f'<span class="vt-categoria">{html.escape(video["categoria"])}</span>',
                    unsafe_allow_html=True)
        st.markdown(f"**{video['titulo']}**")
        if video["descripcion"]:
            resumen = video["descripcion"]
            st.write(resumen[:120] + ("…" if len(resumen) > 120 else ""))
        if st.button("▶ Ver tutorial", key=f"ver-{video['id']}", use_container_width=True):
            st.query_params["video"] = video["id"]
            st.rerun()


def pagina_reproductor(video, videos):
    if st.button("← Volver a todos los tutoriales"):
        del st.query_params["video"]
        st.rerun()

    principal, lateral = st.columns([3, 1], gap="large")
    with principal:
        st.video(fuente_video(video))
        st.title(video["titulo"])
        st.caption(f"{video['categoria']} · {fecha_legible(video['fecha'])}")
        if video["descripcion"]:
            st.write(video["descripcion"])

    with lateral:
        st.subheader("Más de esta categoría")
        otros = [v for v in videos if v["categoria"] == video["categoria"] and v["id"] != video["id"]]
        if not otros:
            st.caption("No hay más tutoriales en esta categoría.")
        for v in otros:
            if st.button(v["titulo"], key=f"rel-{v['id']}", use_container_width=True):
                st.query_params["video"] = v["id"]
                st.rerun()


def pagina_catalogo():
    videos = sorted(leer_videos(), key=lambda v: v["fecha"], reverse=True)

    seleccionado = st.query_params.get("video")
    if seleccionado:
        video = next((v for v in videos if v["id"] == seleccionado), None)
        if video:
            pagina_reproductor(video, videos)
            return
        st.warning("Ese tutorial ya no está disponible.")

    st.header("🎬 Tutoriales")
    st.write("Busca un tema o elige una categoría y pulsa **Ver tutorial**.")

    busqueda = st.text_input("Buscar", placeholder="🔍 Buscar tutoriales...", label_visibility="collapsed")
    categoria = st.pills("Categoría", ["Todas"] + categorias(videos), default="Todas",
                         label_visibility="collapsed")

    if categoria and categoria != "Todas":
        videos = [v for v in videos if v["categoria"] == categoria]
    if busqueda:
        q = busqueda.lower()
        videos = [v for v in videos if any(q in v[c].lower() for c in ("titulo", "descripcion", "categoria"))]

    if not videos:
        st.info("No se encontraron tutoriales." if busqueda or categoria != "Todas"
                else "Todavía no hay tutoriales publicados.")
        return

    columnas = st.columns(3)
    for i, video in enumerate(videos):
        tarjeta(video, columnas[i % 3])


# ---------- Vista de administración ----------

def formulario_login():
    st.title("🔒 Acceso de administrador")
    with st.form("login"):
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if hmac.compare_digest(clave, contrasena_admin()):
                st.session_state.admin = True
                st.rerun()
            st.error("Contraseña incorrecta.")


def formulario_subida(videos):
    st.subheader("Subir nuevo tutorial")
    origen = st.radio("Origen del video", ["Subir archivo", "Enlace de YouTube"], horizontal=True)

    with st.form("subir", clear_on_submit=True):
        titulo = st.text_input("Título *", max_chars=150)
        existentes = categorias(videos)
        categoria = st.selectbox("Categoría", existentes, index=None, accept_new_options=True,
                                 placeholder="Elige una o escribe una nueva")
        descripcion = st.text_area("Descripción", max_chars=5000)
        if origen == "Subir archivo":
            archivo = st.file_uploader("Archivo de video * (MP4 recomendado)", type=FORMATOS_VIDEO)
            url = None
        else:
            url = st.text_input("Enlace de YouTube *", placeholder="https://www.youtube.com/watch?v=...")
            archivo = None
        miniatura = st.file_uploader("Miniatura (opcional)", type=FORMATOS_IMAGEN)

        if not st.form_submit_button("Publicar tutorial", type="primary"):
            return
        if not titulo.strip():
            st.error("El título es obligatorio.")
            return
        if origen == "Subir archivo" and not archivo:
            st.error("Selecciona un archivo de video.")
            return
        if origen == "Enlace de YouTube" and not (url and url.strip().startswith("http")):
            st.error("Escribe un enlace válido.")
            return

        with st.spinner("Guardando el video..."):
            videos.append({
                "id": str(uuid.uuid4()),
                "titulo": titulo.strip(),
                "descripcion": descripcion.strip(),
                "categoria": (categoria or "").strip() or "General",
                "archivo": guardar_archivo(archivo) if archivo else None,
                "url": url.strip() if url else None,
                "miniatura": guardar_archivo(miniatura) if miniatura else None,
                "fecha": datetime.now().isoformat(timespec="seconds"),
            })
            guardar_videos(videos)
        st.success("✔ Tutorial publicado correctamente.")


def lista_publicados(videos):
    st.subheader(f"Tutoriales publicados ({len(videos)})")
    if not videos:
        st.caption("Aún no has subido tutoriales.")
        return

    for video in sorted(videos, key=lambda v: v["fecha"], reverse=True):
        with st.expander(f"{video['titulo']}  ·  {video['categoria']}"):
            with st.form(f"editar-{video['id']}"):
                titulo = st.text_input("Título", video["titulo"], max_chars=150)
                categoria = st.text_input("Categoría", video["categoria"], max_chars=80)
                descripcion = st.text_area("Descripción", video["descripcion"], max_chars=5000)
                if st.form_submit_button("Guardar cambios"):
                    if not titulo.strip():
                        st.error("El título es obligatorio.")
                    else:
                        video.update(titulo=titulo.strip(), categoria=categoria.strip() or "General",
                                     descripcion=descripcion.strip())
                        guardar_videos(videos)
                        st.rerun()

            confirmar = st.checkbox("Confirmo que quiero eliminar este tutorial", key=f"conf-{video['id']}")
            if st.button("🗑 Eliminar", key=f"del-{video['id']}", disabled=not confirmar):
                videos.remove(video)
                guardar_videos(videos)
                borrar_archivo(video.get("archivo"))
                borrar_archivo(video.get("miniatura"))
                st.rerun()


def pagina_admin():
    if not st.session_state.get("admin"):
        formulario_login()
        return

    st.title("⚙️ Administrar videoteca")
    if st.button("Cerrar sesión"):
        st.session_state.admin = False
        st.rerun()

    videos = leer_videos()
    formulario_subida(videos)
    st.divider()
    lista_publicados(videos)


# ---------- Navegación ----------

pagina = st.navigation([
    st.Page(pagina_catalogo, title="Videoteca", icon="🎬", default=True),
    st.Page(pagina_admin, title="Administrar", icon="⚙️", url_path="admin"),
])
encabezado()
pagina.run()
